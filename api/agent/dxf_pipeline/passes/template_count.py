"""
LDSE mode 3 — count exploded-line-work symbols by template matching.

When a symbol is drawn as loose line-work (Revit/ArchiCAD exports), it is
neither a block to count nor a clean circle. But the LEGEND still shows the
glyph. So: rasterise the legend glyph, rasterise the plan's symbol line-work at
the SAME scale (DXF is vector, so scale is exact — a huge advantage over raster
PDF), then template-match the glyph across the plan at 90° rotations with
non-max suppression, and count the hits. Deterministic. No LLM.

Only used for legend entries whose glyph is line-work (no block). Block-backed
entries are counted exactly by `legend_block_counts`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.recognize import _plain_text
from agent.shared.legend import Legend
from core.layer_aliases import is_architectural_layer, is_wiring_layer

try:
    import cv2
    _HAVE_CV2 = True
except Exception:  # noqa: BLE001
    _HAVE_CV2 = False


# ─── entity geometry → drawable segments ─────────────────────────────

BBox = Tuple[float, float, float, float]   # (x0, y0, x1, y1)


def _entity_bbox(e) -> Optional[BBox]:
    k = e.dxftype()
    try:
        if k == "LINE":
            xs = [e.dxf.start.x, e.dxf.end.x]; ys = [e.dxf.start.y, e.dxf.end.y]
        elif k == "CIRCLE":
            r = float(e.dxf.radius); cx, cy = e.dxf.center.x, e.dxf.center.y
            xs = [cx - r, cx + r]; ys = [cy - r, cy + r]
        elif k == "ARC":
            r = float(e.dxf.radius); cx, cy = e.dxf.center.x, e.dxf.center.y
            xs = [cx - r, cx + r]; ys = [cy - r, cy + r]
        elif k == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if not pts:
                return None
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        else:
            return None
    except Exception:  # noqa: BLE001
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _draw_entity(img: np.ndarray, e, x0: float, y1: float, ppu: float) -> None:
    """Draw one entity in black on a white image (consistent for glyph + plan)."""
    def tx(x, y):
        return (int(round((x - x0) * ppu)), int(round((y1 - y) * ppu)))  # y flipped
    k = e.dxftype()
    try:
        if k == "LINE":
            cv2.line(img, tx(e.dxf.start.x, e.dxf.start.y), tx(e.dxf.end.x, e.dxf.end.y), 0, 1)
        elif k == "CIRCLE":
            cv2.circle(img, tx(e.dxf.center.x, e.dxf.center.y), max(1, int(e.dxf.radius * ppu)), 0, 1)
        elif k == "ARC":
            c = tx(e.dxf.center.x, e.dxf.center.y)
            rr = max(1, int(e.dxf.radius * ppu))
            # y is flipped, so negate/swap the sweep for a consistent rendering
            a1, a2 = -float(e.dxf.end_angle), -float(e.dxf.start_angle)
            cv2.ellipse(img, c, (rr, rr), 0, a1, a2, 0, 1)
        elif k == "LWPOLYLINE":
            pts = [tx(p[0], p[1]) for p in e.get_points("xy")]
            if len(pts) >= 2:
                cv2.polylines(img, [np.array(pts, np.int32)], bool(e.closed), 0, 1)
    except Exception:  # noqa: BLE001
        pass


def _render(entities, bbox: BBox, ppu: float, pad: int = 2) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    w = max(1, int((x1 - x0) * ppu) + 2 * pad)
    h = max(1, int((y1 - y0) * ppu) + 2 * pad)
    img = np.full((h, w), 255, np.uint8)
    for e in entities:
        _draw_entity(img, e, x0 - pad / ppu, y1 + pad / ppu, ppu)
    return img


# ─── glyph extraction from the legend ────────────────────────────────

@dataclass
class _Glyph:
    canonical_item: str
    entities: list
    bbox: BBox


def _legend_text_positions(doc: Drawing, legend: Legend):
    """Locate each legend entry's description text position on the sheet."""
    wanted = {e.canonical_item: e for e in legend.entries if not e.symbol_key}
    positions = {}   # canonical -> (x, y)
    from agent.shared.legend import classify_description
    for e in doc.modelspace():
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        hit = classify_description(_plain_text(e).strip())
        if hit is None:
            continue
        item = hit[0]
        if item in wanted and item not in positions:
            px = getattr(e.dxf, "insert", None)
            if px is not None:
                positions[item] = (px.x, px.y)
    return positions


def _bbox_gap(a: BBox, b: BBox) -> float:
    """Smallest gap between two axis-aligned bboxes (0 if they overlap)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def _cluster_symbol_geometry(doc: Drawing) -> List[Tuple[BBox, list]]:
    """
    Group loose symbol line-work into discrete glyph instances by proximity
    (union-find). Returns [(bbox, entities)] for each cluster. Excludes wiring
    and architectural layers.
    """
    items = []   # (entity, bbox)
    for e in doc.modelspace():
        if e.dxftype() not in ("LINE", "CIRCLE", "ARC", "LWPOLYLINE"):
            continue
        layer = getattr(e.dxf, "layer", "0")
        if is_wiring_layer(layer) or is_architectural_layer(layer):
            continue
        bb = _entity_bbox(e)
        if bb:
            items.append((e, bb))
    n = len(items)
    if n == 0:
        return []

    # gap threshold = a small multiple of the median entity size
    sizes = sorted(max(b[2] - b[0], b[3] - b[1]) for _, b in items)
    med = sizes[len(sizes) // 2] or 1.0
    gap = med * 1.5

    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        bi = items[i][1]
        for j in range(i + 1, n):
            if _bbox_gap(bi, items[j][1]) <= gap:
                parent[find(i)] = find(j)

    groups: Dict[int, list] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(items[i])
    clusters = []
    for members in groups.values():
        bxs = [b for _, b in members]
        bbox = (min(b[0] for b in bxs), min(b[1] for b in bxs),
                max(b[2] for b in bxs), max(b[3] for b in bxs))
        clusters.append((bbox, [e for e, _ in members]))
    return clusters


def _collect_glyphs(doc: Drawing, legend: Legend, glyph_reach: float, y_band: float) -> List[_Glyph]:
    """
    For each line-work legend entry, isolate the ONE symbol cluster nearest its
    description text (to the left). Clustering keeps the glyph tight instead of
    scooping up everything in the band.
    """
    positions = _legend_text_positions(doc, legend)
    if not positions:
        return []
    clusters = _cluster_symbol_geometry(doc)
    if not clusters:
        return []

    # only symbol-sized clusters qualify as legend glyphs (not big line runs)
    max_glyph = glyph_reach   # a glyph is at most ~the reach band across
    candidates = [(bbox, ents, ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))
                  for bbox, ents in clusters
                  if max(bbox[2] - bbox[0], bbox[3] - bbox[1]) <= max_glyph]

    glyphs: List[_Glyph] = []
    used = set()
    for item, (tx, ty) in positions.items():
        best, best_d = None, glyph_reach
        for idx, (bbox, ents, (cx, cy)) in enumerate(candidates):
            if idx in used:
                continue
            if cx <= tx and abs(cy - ty) <= y_band:
                d = tx - cx
                if d < best_d:
                    best_d, best = d, (idx, bbox, ents)
        if best is not None:
            idx, bbox, ents = best
            used.add(idx)
            glyphs.append(_Glyph(canonical_item=item, entities=ents, bbox=bbox))
    return glyphs


# ─── matching ────────────────────────────────────────────────────────

def _iou(a, b) -> float:
    ax0, ay0, aw, ah = a; bx0, by0, bw, bh = b
    ax1, ay1, bx1, by1 = ax0 + aw, ay0 + ah, bx0 + bw, by0 + bh
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def _nms(boxes, iou_thresh=0.3):
    boxes = sorted(boxes, key=lambda b: -b[4])
    kept = []
    for b in boxes:
        if all(_iou(b[:4], k[:4]) <= iou_thresh for k in kept):
            kept.append(b)
    return kept


def _count_template(plan: np.ndarray, tmpl: np.ndarray, threshold: float) -> int:
    th, tw = tmpl.shape[:2]
    if th < 4 or tw < 4 or plan.shape[0] < th or plan.shape[1] < tw:
        return 0
    boxes = []
    base = tmpl
    for k in range(4):                      # 0/90/180/270 via np.rot90
        rt = np.rot90(base, k)
        rh, rw = rt.shape[:2]
        if plan.shape[0] < rh or plan.shape[1] < rw:
            continue
        res = cv2.matchTemplate(plan, rt, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= threshold)
        for x, y in zip(xs, ys):
            boxes.append((int(x), int(y), rw, rh, float(res[y, x])))
    return len(_nms(boxes))


# ─── public entry ────────────────────────────────────────────────────

# A glyph needs enough distinct line-work to be a reliable template. Simple
# 1–2 entity glyphs (a dot, an L) match almost anything → over-count. Skip them.
MIN_GLYPH_ENTITIES = 3


def count_by_template(
    doc: Drawing,
    legend: Legend,
    *,
    threshold: float = 0.62,
    target_glyph_px: float = 44.0,
    glyph_reach_frac: float = 0.04,
    min_glyph_entities: int = MIN_GLYPH_ENTITIES,
) -> Dict[str, int]:
    """
    Count line-work legend symbols across the plan by template matching.
    Returns {canonical_item: count}. Only DISTINCTIVE glyphs (≥ min entities)
    are matched — simple glyphs over-match, so they are left for the coverage
    report instead of producing a wrong number. Empty if OpenCV is missing or
    no distinctive glyph could be isolated.
    """
    if not _HAVE_CV2 or not legend or not legend.entries:
        return {}

    span = _drawing_span(doc)
    reach = span * glyph_reach_frac
    y_band = reach * 0.4
    glyphs = [g for g in _collect_glyphs(doc, legend, reach, y_band)
              if len(g.entities) >= min_glyph_entities]
    if not glyphs:
        return {}

    # one pixels-per-unit from the median glyph size so glyph ≈ target px
    sizes = [max(g.bbox[2] - g.bbox[0], g.bbox[3] - g.bbox[1]) for g in glyphs]
    med = sorted(sizes)[len(sizes) // 2] or 1.0
    ppu = target_glyph_px / med

    plan_entities, plan_bbox, _ = _plan_entities(doc, glyphs)
    if plan_bbox is None:
        return {}
    plan_img = _render(plan_entities, plan_bbox, ppu)

    counts: Dict[str, int] = {}
    for g in glyphs:
        tmpl = _render(g.entities, g.bbox, ppu)
        n = _count_template(plan_img, tmpl, threshold)
        if n > 0:
            counts[g.canonical_item] = n
    return counts


def _drawing_span(doc: Drawing) -> float:
    try:
        emax = doc.header.get("$EXTMAX", (0, 0, 0)); emin = doc.header.get("$EXTMIN", (0, 0, 0))
        return max(abs(emax[0] - emin[0]), abs(emax[1] - emin[1])) or 1000.0
    except Exception:  # noqa: BLE001
        return 1000.0


def _plan_entities(doc: Drawing, glyphs: List[_Glyph]):
    """Symbol line-work across the plan, excluding wiring, architecture, and the
    legend glyph regions (so the legend's own glyphs aren't counted)."""
    legend_boxes = [g.bbox for g in glyphs]
    ents = []
    xs, ys = [], []
    for e in doc.modelspace():
        if e.dxftype() not in ("LINE", "CIRCLE", "ARC", "LWPOLYLINE"):
            continue
        layer = getattr(e.dxf, "layer", "0")
        if is_wiring_layer(layer) or is_architectural_layer(layer):
            continue
        bb = _entity_bbox(e)
        if not bb:
            continue
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        if any(lx0 <= cx <= lx1 and ly0 <= cy <= ly1 for (lx0, ly0, lx1, ly1) in legend_boxes):
            continue
        ents.append(e); xs += [bb[0], bb[2]]; ys += [bb[1], bb[3]]
    if not ents:
        return [], None, legend_boxes
    return ents, (min(xs), min(ys), max(xs), max(ys)), legend_boxes
