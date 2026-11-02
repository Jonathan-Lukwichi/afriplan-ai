"""
Repeated unnamed symbols — group loose line-work into shapes (ADR-0007). No LLM.

Drawings exported or imported from PDF carry their electrical symbols as loose lines
and circles with no block name. Geometry can find every copy of a shape exactly; it
just cannot say what the shape IS. This pass:

  1. takes symbol line-work (not wiring, not other disciplines' layers, not the legend),
  2. splits it into individual symbols — pieces that touch or overlap,
  3. gives each symbol a signature that ignores position and rotation
     (entity kinds + size + proportions after turning its long side horizontal),
  4. groups identical signatures, counts them and draws ONE picture per group.

The legend names a shape first: the row beside its glyph says what it is, whatever size the
plan draws it at. Otherwise the picture + the legend text are what a person (or the optional
AI step, which lives outside this pipeline in api/assist/) needs to name the shape once.
"""

from __future__ import annotations

import base64
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.labels import _row_description, _Text, _texts
from agent.dxf_pipeline.passes.legend import in_region, legend_region
from agent.dxf_pipeline.passes.template_count import _entity_bbox, _render
from agent.shared.legend import classify_description
from agent.shared.symbol_catalogue import catalogue_item
from core.layer_aliases import is_architectural_layer, is_wiring_layer

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # noqa: BLE001
    _HAVE_CV2 = False

_KINDS = ("LINE", "CIRCLE", "ARC", "LWPOLYLINE")
_MIN_DISTINCTIVE_PARTS = 3
_MAX_GLYPH_PART = 4.0            # × the median piece: longer pieces in a legend are the table's lines
BBox = Tuple[float, float, float, float]


@dataclass
class ShapeGroup:
    """Every copy of one repeated symbol shape on one drawing."""
    signature: str
    count: int
    sheet: str = ""
    size: float = 0.0                   # largest side, drawing units
    image_png_b64: str = ""             # one sample, black on white
    positions: List[Tuple[float, float]] = field(default_factory=list)
    legend_item: str = ""               # what the legend row beside this shape says it is


def _points(e) -> List[Tuple[float, float]]:
    k = e.dxftype()
    if k == "LINE":
        return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
    if k in ("CIRCLE", "ARC"):
        c, r = e.dxf.center, float(e.dxf.radius)
        return [(c.x + r * math.cos(a), c.y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    if k == "LWPOLYLINE":
        return [(p[0], p[1]) for p in e.get_points("xy")]
    return []


def signature_of(entities) -> Tuple[str, float]:
    """(signature, size): entity kinds + size class + proportions, independent of
    where the symbol sits and which way it is turned."""
    pts = np.array([p for e in entities for p in _points(e)], dtype=float)
    if len(pts) < 2:
        return "", 0.0
    centred = pts - pts.mean(axis=0)
    # turn the long side horizontal (principal axis), so a rotated copy matches
    cov = np.cov(centred.T) if len(pts) > 2 else np.eye(2)
    eigvals, eigvecs = np.linalg.eigh(cov)
    axis = eigvecs[:, int(np.argmax(eigvals))]
    angle = math.atan2(axis[1], axis[0])
    rot = np.array([[math.cos(-angle), -math.sin(-angle)], [math.sin(-angle), math.cos(-angle)]])
    turned = centred @ rot.T
    w, h = np.ptp(turned[:, 0]), np.ptp(turned[:, 1])
    size = float(max(w, h))
    if size <= 0:
        return "", 0.0
    kinds = Counter(e.dxftype() for e in entities)
    kind_part = ",".join(f"{k}{kinds[k]}" for k in _KINDS if kinds[k])
    size_class = round(math.log(size, 1.2))              # ~20 % size steps
    aspect = round(min(w, h) / size, 1)
    return f"{kind_part}|s{size_class}|a{aspect}", size


def _split_symbols(items: List[Tuple[object, BBox]]) -> List[List[Tuple[object, BBox]]]:
    """Pieces that touch or overlap form one symbol (grid-accelerated union-find)."""
    if not items:
        return []
    sizes = sorted(max(b[2] - b[0], b[3] - b[1]) for _, b in items)
    tol = (sizes[len(sizes) // 2] or 1.0) * 0.05
    cell = max(sizes[len(sizes) // 2] * 2, 1e-6)
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid: Dict[Tuple[int, int], List[int]] = {}
    for i, (_, b) in enumerate(items):
        for gx in range(int(b[0] // cell), int(b[2] // cell) + 1):
            for gy in range(int(b[1] // cell), int(b[3] // cell) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for members in grid.values():
        for a_i, a in enumerate(members):
            ba = items[a][1]
            for b in members[a_i + 1:]:
                bb = items[b][1]
                if (ba[0] - tol <= bb[2] and bb[0] - tol <= ba[2]
                        and ba[1] - tol <= bb[3] and bb[1] - tol <= ba[3]):
                    parent[find(a)] = find(b)
    groups: Dict[int, List[Tuple[object, BBox]]] = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    return list(groups.values())


def _png_b64(entities, bbox: BBox, px: int = 96) -> str:
    if not _HAVE_CV2:
        return ""
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    img = _render(entities, bbox, px / max(w, h, 1e-9), pad=6)
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""


def _symbol_items(doc: Drawing, region, *, inside: bool) -> List[Tuple[object, BBox]]:
    """Symbol line-work outside the legend region, or inside it."""
    items: List[Tuple[object, BBox]] = []
    for e in doc.modelspace():
        if e.dxftype() not in _KINDS:
            continue
        layer = getattr(e.dxf, "layer", "0")
        if is_wiring_layer(layer) or is_architectural_layer(layer):
            continue
        bb = _entity_bbox(e)
        if bb is None:
            continue
        if in_region((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, region) == inside:
            items.append((e, bb))
    return items


def shape_kind(signature: str) -> str:
    """A signature without its size class: a legend glyph is not always drawn at the plan's size."""
    kinds, _, aspect = signature.split("|")
    return f"{kinds}|{aspect}"


def is_distinctive(signature: str) -> bool:
    """Enough pieces to recognise: a lone box or a pair of lines matches every door and window."""
    return sum(int(re.sub(r"\D", "", k)) for k in signature.split("|")[0].split(",")) >= _MIN_DISTINCTIVE_PARTS


def legend_shape_names(doc: Drawing) -> Dict[str, str]:
    """{shape_kind: legend item} for each distinctive glyph with one legend row beside it. A glyph
    on two rows names nothing, and boards are left out: they are billed from the SLD."""
    region = legend_region(doc)
    if region is None:
        return {}
    rows = [t for t in _texts(doc) if in_region(t.x, t.y, region) and classify_description(t.text)]
    items = _symbol_items(doc, region, inside=True)
    if not items:
        return {}
    # the table's grid lines touch its glyphs: without them each glyph stands alone
    side = statistics.median(max(b[2] - b[0], b[3] - b[1]) for _, b in items)
    glyph_parts = [(e, b) for e, b in items if max(b[2] - b[0], b[3] - b[1]) <= _MAX_GLYPH_PART * side]
    seen: Dict[str, set] = {}
    for parts in _split_symbols(glyph_parts):
        sig, _ = signature_of([e for e, _ in parts])
        if not sig or not is_distinctive(sig):
            continue
        x = (min(b[0] for _, b in parts) + max(b[2] for _, b in parts)) / 2
        y = (min(b[1] for _, b in parts) + max(b[3] for _, b in parts)) / 2
        row = _row_description(_Text("", x, y, 0.0), rows)
        if row:
            seen.setdefault(shape_kind(sig), set()).add(classify_description(row)[0])
    out: Dict[str, str] = {}
    for kind, items in seen.items():
        item = next(iter(items))
        known = catalogue_item(item)
        if len(items) == 1 and known and known.price_map != "db":
            out[kind] = item
    return out


def find_shape_groups(doc: Drawing, sheet: str = "", *, max_parts: int = 60,
                      size_spread: float = 6.0) -> List[ShapeGroup]:
    """Repeated symbol shapes on one drawing, most frequent first."""
    items = _symbol_items(doc, legend_region(doc), inside=False)

    symbols = [s for s in _split_symbols(items) if 1 <= len(s) <= max_parts]
    if not symbols:
        return []
    sized = []
    for parts in symbols:
        ents = [e for e, _ in parts]
        sig, size = signature_of(ents)
        if sig:
            bbox = (min(b[0] for _, b in parts), min(b[1] for _, b in parts),
                    max(b[2] for _, b in parts), max(b[3] for _, b in parts))
            sized.append((sig, size, ents, bbox))
    if not sized:
        return []
    # symbol-sized only: drop outline runs far bigger than a typical symbol
    typical = statistics.median(s for _, s, _, _ in sized)
    by_sig: Dict[str, List[tuple]] = {}
    for sig, size, ents, bbox in sized:
        if size <= typical * size_spread:
            by_sig.setdefault(sig, []).append((size, ents, bbox))

    groups: List[ShapeGroup] = []
    for sig, members in by_sig.items():
        size, ents, bbox = members[0]
        groups.append(ShapeGroup(
            signature=sig, count=len(members), sheet=sheet, size=size,
            image_png_b64=_png_b64(ents, bbox),
            positions=[((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for _, _, b in members],
        ))
    groups.sort(key=lambda g: (-g.count, g.signature))
    return groups
