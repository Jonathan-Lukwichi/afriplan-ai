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

The picture + the legend text are what a person (or the optional AI step, which lives
outside this pipeline in api/assist/) needs to name the shape once.
"""

from __future__ import annotations

import base64
import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.legend import in_region, legend_region
from agent.dxf_pipeline.passes.template_count import _entity_bbox, _render
from core.layer_aliases import is_architectural_layer, is_wiring_layer

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # noqa: BLE001
    _HAVE_CV2 = False

_KINDS = ("LINE", "CIRCLE", "ARC", "LWPOLYLINE")
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


def find_shape_groups(doc: Drawing, sheet: str = "", *, max_parts: int = 60,
                      size_spread: float = 6.0) -> List[ShapeGroup]:
    """Repeated symbol shapes on one drawing, most frequent first."""
    region = legend_region(doc)
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
        if region is not None and in_region((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, region):
            continue
        items.append((e, bb))

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
