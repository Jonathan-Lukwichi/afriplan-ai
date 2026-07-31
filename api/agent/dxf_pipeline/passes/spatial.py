"""
Pass 5 — spatial: place each recognised symbol in a room and a building.

An estimator organises the take-off room-by-room, building-by-building. Here we
do the same with geometry:

  1. Build ROOM REGIONS — closed polylines on room/area/space layers (with a
     shoelace area and a name from the room-label text inside them). Where a
     drawing has no room polygons, fall back to room-name TEXT labels as point
     regions.
  2. Assign each symbol to the room that CONTAINS it (point-in-polygon); if no
     polygon contains it, to the NEAREST room label.
  3. Tag every symbol with a building (a caller-supplied hint, e.g. the file /
     project name, since one CAD sheet is usually one building/block).

Pure geometry — deterministic, no LLM.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.recognize import DxfRecognition, _plain_text, _parse_area_m2

# Layers that carry room/space boundaries or room-name labels.
_ROOM_LAYER_RE = re.compile(r"room|area|space|zone|\brm\b|text.*room", re.I)
# Keywords that mark a text string as a room name (fallback when no room layer).
_ROOM_NAME_RE = re.compile(
    r"office|hall|store|storage|kitchen|scullery|ablut|\bwc\b|toilet|urinal|"
    r"lobby|guard|plant|pump|entrance|passage|duct|shop|reception|boardroom|"
    r"bedroom|bathroom|lounge|garage|balcony|courtyard|shaft|change|shower",
    re.I,
)


@dataclass
class RoomRegion:
    name: str
    cx: float
    cy: float
    area_m2: float = 0.0
    polygon: Optional[List[Tuple[float, float]]] = None   # None → point region (label only)


@dataclass
class SpatialResult:
    rooms: List[RoomRegion] = field(default_factory=list)
    counts_by_room: Dict[str, Dict[str, int]] = field(default_factory=dict)
    building: str = ""


# ─── geometry primitives ─────────────────────────────────────────────

def _shoelace_area(poly: List[Tuple[float, float]]) -> float:
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _centroid(poly: List[Tuple[float, float]]) -> Tuple[float, float]:
    n = len(poly)
    if n == 0:
        return (0.0, 0.0)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


# ─── room extraction ─────────────────────────────────────────────────

def extract_room_regions(doc: Drawing, units_to_metre: float) -> List[RoomRegion]:
    """Room polygons on room/area layers, else room-name text labels."""
    msp = doc.modelspace()
    labels: List[Tuple[str, float, float, float]] = []   # (name, x, y, area_m2)
    polygons: List[Tuple[List[Tuple[float, float]], str]] = []  # (poly, layer)

    for e in msp:
        kind = e.dxftype()
        layer = getattr(e.dxf, "layer", "0")
        if kind in ("TEXT", "MTEXT"):
            text = _plain_text(e).strip()
            if not text:
                continue
            is_room_layer = bool(_ROOM_LAYER_RE.search(layer))
            if is_room_layer or _ROOM_NAME_RE.search(text):
                px = getattr(e.dxf, "insert", None)
                x = px.x if px else 0.0
                y = px.y if px else 0.0
                name = text.splitlines()[0][:40].strip()
                labels.append((name, x, y, _parse_area_m2(text)))
        elif kind == "LWPOLYLINE" and bool(getattr(e, "closed", False)):
            if _ROOM_LAYER_RE.search(layer):
                pts = [(p[0], p[1]) for p in e.get_points("xy")]
                if len(pts) >= 3:
                    polygons.append((pts, layer))

    regions: List[RoomRegion] = []
    used_labels = set()

    # polygons first — name each from a label inside it
    for poly, _layer in polygons:
        cx, cy = _centroid(poly)
        name = ""
        for i, (lname, lx, ly, _a) in enumerate(labels):
            if i not in used_labels and _point_in_polygon(lx, ly, poly):
                name = lname
                used_labels.add(i)
                break
        regions.append(RoomRegion(
            name=name or "Room",
            cx=cx, cy=cy,
            area_m2=round(_shoelace_area(poly) * units_to_metre * units_to_metre, 2),
            polygon=poly,
        ))

    # remaining labels become point regions
    for i, (lname, lx, ly, area) in enumerate(labels):
        if i in used_labels:
            continue
        regions.append(RoomRegion(name=lname, cx=lx, cy=ly, area_m2=area, polygon=None))

    return regions


# ─── assignment ──────────────────────────────────────────────────────

def _assign_one(x: float, y: float, regions: List[RoomRegion]) -> str:
    # containing polygon wins
    for r in regions:
        if r.polygon and _point_in_polygon(x, y, r.polygon):
            return r.name
    # else nearest label/centroid
    if not regions:
        return ""
    nearest = min(regions, key=lambda r: math.hypot(r.cx - x, r.cy - y))
    return nearest.name


def assign_spatial(
    rec: DxfRecognition,
    doc: Drawing,
    *,
    building: str = "",
) -> SpatialResult:
    """Fill each symbol's room + building; return a per-room count summary."""
    regions = extract_room_regions(doc, rec.units_to_metre)
    counts: Dict[str, Dict[str, int]] = {}
    for s in rec.symbols:
        room = _assign_one(s.x, s.y, regions)
        s.room = room
        s.building = building
        bucket = counts.setdefault(room or "(unassigned)", {})
        bucket[s.canonical_name] = bucket.get(s.canonical_name, 0) + 1
    return SpatialResult(rooms=regions, counts_by_room=counts, building=building)
