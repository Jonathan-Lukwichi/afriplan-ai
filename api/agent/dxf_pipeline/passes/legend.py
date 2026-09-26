"""
DXF legend extraction (LDSE Pass A–B for the DXF pipeline).

Reads the drawing's legend text into the shared `Legend` dictionary, and — where
the legend graphic is a block — learns the block name for each symbol by pairing
each description with the nearest graphic to its left. That block name lets us
count instances exactly (mode 1). Where the legend graphic is exploded line-work
(Revit), the entry still records the item type; counting those instances is the
OpenCV geometry-matching job (mode 3, later).

Deterministic. No LLM. Independent of the PDF pipeline (shares only the spec).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.recognize import _plain_text
from agent.dxf_pipeline.patterns import is_skip_block_name
from agent.shared.legend import Legend, LegendEntry, build_legend_entry
from core.layer_aliases import is_architectural_layer


def _text_pos(e) -> Tuple[float, float]:
    px = getattr(e.dxf, "insert", None)
    return (px.x, px.y) if px else (0.0, 0.0)


def extract_legend(doc: Drawing, *, sheet_ref: str = "") -> Legend:
    """
    Build the drawing's legend dictionary from its text, and — where the legend
    glyphs are blocks — learn each block's meaning by pairing each *block name*
    (not each text) to its single nearest legend description. One block → one
    meaning, so a lone block can't smear across every description.
    """
    msp = doc.modelspace()

    # 1. legend descriptions (classifiable text) with positions
    legend_texts: List[Tuple[LegendEntry, float, float]] = []
    entries: Dict[str, LegendEntry] = {}   # keyed by canonical_item (dedupe)
    for e in msp:
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        text = _plain_text(e).strip()
        if not text:
            continue
        entry = build_legend_entry(text, source_ref=sheet_ref)
        if entry is None:
            continue
        tx, ty = _text_pos(e)
        legend_texts.append((entry, tx, ty))
        entries.setdefault(entry.canonical_item, entry)

    # 2. distinct block names (non-architectural) with a representative position
    block_pos: Dict[str, Tuple[float, float]] = {}
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        name = e.dxf.name
        if is_skip_block_name(name) or is_architectural_layer(getattr(e.dxf, "layer", "0")):
            continue
        block_pos.setdefault(name, (e.dxf.insert.x, e.dxf.insert.y))

    # 3. pair each BLOCK NAME to its single nearest legend description (within band)
    _, max_d = _pairing_bands(list(block_pos.values()))
    for name, (bx, by) in block_pos.items():
        best_entry, best_d = None, max_d
        for entry, tx, ty in legend_texts:
            d = math.hypot(tx - bx, ty - by)
            if d <= best_d:
                best_d, best_entry = d, entry
        if best_entry is not None and not entries[best_entry.canonical_item].symbol_key:
            entries[best_entry.canonical_item].symbol_key = name
            entries[best_entry.canonical_item].graphic_x = bx
            entries[best_entry.canonical_item].graphic_y = by

    return Legend(entries=list(entries.values()), source="dxf", sheet_ref=sheet_ref)


Region = Tuple[float, float, float, float]   # (x0, y0, x1, y1)


def legend_region(doc: Drawing, *, gap_frac: float = 0.02, min_texts: int = 3) -> Optional[Region]:
    """
    Locate the legend TABLE: the largest tight cluster of legend-style descriptions
    (text that classifies as an electrical item), expanded to the left to take in
    the glyphs drawn beside each description. A lone classifiable label on the plan
    ("DB-AB1") is its own tiny cluster and never stretches the region. Returns None
    when no cluster of at least `min_texts` descriptions exists.
    """
    from agent.shared.legend import classify_description

    pts: List[Tuple[float, float]] = []
    for e in doc.modelspace():
        if e.dxftype() in ("TEXT", "MTEXT") and classify_description(_plain_text(e).strip()):
            pts.append(_text_pos(e))
    if len(pts) < min_texts:
        return None
    try:
        emax = doc.header.get("$EXTMAX", (0, 0, 0)); emin = doc.header.get("$EXTMIN", (0, 0, 0))
        span = max(emax[0] - emin[0], emax[1] - emin[1])
    except Exception:  # noqa: BLE001
        span = 0.0
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if not (0 < span < 1e9):          # unset / sentinel extents (ezdxf writes ±1e20)
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    gap = span * gap_frac

    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]) <= gap:
                parent[find(i)] = find(j)
    groups: Dict[int, List[Tuple[float, float]]] = {}
    for i, p in enumerate(pts):
        groups.setdefault(find(i), []).append(p)
    best = max(groups.values(), key=len)
    if len(best) < min_texts:
        return None
    x0, x1 = min(p[0] for p in best), max(p[0] for p in best)
    y0, y1 = min(p[1] for p in best), max(p[1] for p in best)
    # glyphs sit to the LEFT of their description; allow a row of margin around
    return (x0 - gap, y0 - gap * 0.5, x1 + gap * 0.25, y1 + gap * 0.5)


def in_region(x: float, y: float, region: Optional[Region]) -> bool:
    return region is not None and region[0] <= x <= region[2] and region[1] <= y <= region[3]


def _pairing_bands(positions: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Scale the block→text pairing tolerance to the drawing's coordinates. A
    legend glyph sits within a small fraction of the drawing span of its text.
    """
    if not positions:
        return (250.0, 5000.0)
    xs = [p[0] for p in positions]
    span = (max(xs) - min(xs)) or 1000.0
    return (span * 0.01, span * 0.05)


def legend_block_counts(doc: Drawing, legend: Legend) -> Dict[str, int]:
    """
    Count instances (mode 1) for legend entries whose symbol resolved to a block.
    Returns {canonical_item: count}. Entries with no block (exploded line-work)
    are omitted — those are for the geometry-matching engine.
    """
    block_of: Dict[str, str] = {
        e.symbol_key.lower(): e.canonical_item for e in legend.entries if e.symbol_key
    }
    # position of each symbol's OWN legend glyph — exclude it from the plan count
    glyph_pos: Dict[str, Tuple[float, float]] = {
        e.symbol_key.lower(): (e.graphic_x, e.graphic_y)
        for e in legend.entries if e.symbol_key
    }
    if not block_of:
        return {}
    tally: Counter = Counter()
    for e in doc.modelspace():
        if e.dxftype() != "INSERT":
            continue
        key = e.dxf.name.lower()
        item = block_of.get(key)
        if not item:
            continue
        gx, gy = glyph_pos.get(key, (None, None))
        if gx is not None and math.hypot(e.dxf.insert.x - gx, e.dxf.insert.y - gy) < 1.0:
            continue   # this is the legend's own glyph, not a plan instance
        tally[item] += 1
    return dict(tally)
