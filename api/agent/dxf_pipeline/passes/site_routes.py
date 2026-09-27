"""
Site-route pass — measure feeder routes on an electrical site plan (issue 002).

Adapter from DXF entities to the shared route-network geometry
(`agent.shared.routes`). What counts as a cable route:

  * LINE / LWPOLYLINE / POLYLINE drawn in a dashed linetype (the SA convention for
    buried cable: Wedela draws them DASHED2 on layer 0), or
  * any linework on a layer whose name says cable / trench / route / sleeve / feeder.

Equipment symbols are small closed outlines of solid linework (a DB is a
rectangle with a diagonal; a kiosk or mini-sub a larger rectangle); the tag next
to each ('DB-AB1 Fed from DB-PFA') names it. Deterministic, no LLM.
"""

from __future__ import annotations

import math
import re
from typing import List, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.legend import in_region, legend_region
from agent.dxf_pipeline.passes.recognize import _plain_text
from agent.shared.routes import Label, RouteNetwork, Seg, build_route_network, equipment_boxes, parse_tag

_ROUTE_LAYER = re.compile(r"cable|trench|route|sleeve|feeder|reticulation|underground", re.I)
_DASHED = re.compile(r"dash|hidden|dot", re.I)
# Other disciplines' layers (NCS/AIA prefixes: architectural, civil, structural,
# landscape, general) draw dashed linework too — overhangs, boundaries, services.
_OTHER_DISCIPLINE = re.compile(r"^[ACSLG]-", re.I)
# $INSUNITS → drawing units per metre. Only a hint: length labels override it.
_INSUNITS_PER_M = {1: 39.37, 2: 3.281, 4: 1000.0, 5: 100.0, 6: 1.0, 14: 10.0}

Pts = List[Tuple[float, float]]


def _linetype(doc: Drawing, e) -> str:
    lt = e.dxf.get("linetype", "BYLAYER") or "BYLAYER"
    if lt.upper() == "BYLAYER":
        try:
            lt = doc.layers.get(e.dxf.layer).dxf.linetype
        except Exception:  # noqa: BLE001 — layer missing from the table
            lt = ""
    return lt or ""


def _points(e) -> Pts:
    t = e.dxftype()
    if t == "LINE":
        return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
    if t == "LWPOLYLINE":
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
    elif t == "POLYLINE":
        pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
    else:
        return []
    if getattr(e, "is_closed", False) and len(pts) > 2:
        pts.append(pts[0])
    return pts


def read_site_routes(doc: Drawing) -> RouteNetwork:
    """The drawing's cable-route network, or an empty one when it is not a site plan."""
    msp = doc.modelspace()
    region = legend_region(doc)

    labels: List[Label] = []
    for e in msp.query("TEXT MTEXT"):
        text = " ".join(_plain_text(e).split())
        if not text:
            continue
        p = e.dxf.insert
        if region is not None and in_region(p.x, p.y, region):
            continue
        h = float((e.dxf.get("char_height", 0) if e.dxftype() == "MTEXT" else e.dxf.get("height", 0)) or 0)
        labels.append(Label(text, p.x, p.y, h))
    tag_heights = sorted(lb.h for lb in labels if lb.h > 0 and parse_tag(lb.text))
    if not any((parse_tag(lb.text) or (None, None))[1] for lb in labels):
        return RouteNetwork()                           # no 'X fed from Y' tag: not a site plan

    segs: List[Seg] = []
    solid: List[Pts] = []
    for e in msp.query("LINE LWPOLYLINE POLYLINE"):
        pts = _points(e)
        if len(pts) < 2:
            continue
        if region is not None and all(in_region(x, y, region) for x, y in pts):
            continue
        layer = e.dxf.layer or ""
        if _ROUTE_LAYER.search(layer) or (
                _DASHED.search(_linetype(doc, e)) and not _OTHER_DISCIPLINE.match(layer)):
            segs += [Seg(x1, y1, x2, y2) for (x1, y1), (x2, y2) in zip(pts, pts[1:])
                     if math.hypot(x2 - x1, y2 - y1) > 0]
        elif not _OTHER_DISCIPLINE.match(layer):
            solid.append(pts)

    h = tag_heights[len(tag_heights) // 2] if tag_heights else 0.0
    boxes = equipment_boxes(solid, max_size=8 * h) if h > 0 else []
    units = doc.header.get("$INSUNITS", 0)
    return build_route_network(segs, labels, boxes, units_per_m=_INSUNITS_PER_M.get(units),
                               snap_decade=True)
