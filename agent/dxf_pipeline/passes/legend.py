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
