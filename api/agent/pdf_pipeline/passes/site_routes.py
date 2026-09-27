"""
Site-route pass for PDFs (issue 002) — deterministic, no LLM, R 0.

A vector PDF of an electrical site plan carries the same evidence as the DWG:
dashed cable routes between equipment symbols, 'DB-X Fed from DB-Y' tags and
often the designer's run lengths ('35m'). This adapter reads PyMuPDF's vector
paths and text and measures with the shared route geometry
(`agent.shared.routes`) — the LLM is not asked to measure anything.

Dashed routes reach a PDF two ways and both are read:
  * a stroked path carrying a dash pattern, or
  * the plotter's own dashes: separate short strokes (rebuilt by join_dashes).
Scale: the '1:500' printed on the sheet (points per metre = 72/0.0254/500),
confirmed or replaced by the designer's written lengths when there are enough.
A scanned (raster) page has no vectors and yields nothing — the feeder gaps say so.
"""

from __future__ import annotations

import logging
import math
import re
import statistics
from collections import Counter
from typing import List, Optional, Sequence, Tuple

import fitz  # PyMuPDF

from agent.shared.routes import (
    Label, RouteNetwork, Seg, build_route_network, equipment_boxes, join_dashes, parse_tag,
)

log = logging.getLogger(__name__)

_SCALE = re.compile(r"\b1\s*:\s*(\d{2,5})\b")
_POINTS_PER_M = 72 / 0.0254
_SOLID_DASHES = {"", "[] 0", "[] 0.0", "[]0", "[] 0 d"}

Pts = List[Tuple[float, float]]


def _labels(page: "fitz.Page") -> List[Label]:
    """Every text line, plus each multi-line block joined (tags wrap: 'DB-AB1 Fed' / 'from DB-PFA')."""
    out: List[Label] = []
    for block in page.get_text("dict").get("blocks", []):
        lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = " ".join("".join(s.get("text", "") for s in spans).split())
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            size = max((s.get("size", 0.0) for s in spans), default=0.0)
            out.append(Label(text, (x0 + x1) / 2, (y0 + y1) / 2, size))
            lines.append((text, line["bbox"], size))
        if len(lines) > 1:
            x0 = min(b[0] for _, b, _ in lines)
            y0 = min(b[1] for _, b, _ in lines)
            x1 = max(b[2] for _, b, _ in lines)
            y1 = max(b[3] for _, b, _ in lines)
            out.append(Label(" ".join(t for t, _, _ in lines), (x0 + x1) / 2, (y0 + y1) / 2,
                             max(s for _, _, s in lines)))
    return out


def _paths(page: "fitz.Page") -> Tuple[List[Seg], List[Seg], List[Pts]]:
    """(dash-pattern segments, short solid strokes, solid outlines) from the page's vector paths."""
    dashed: List[Seg] = []
    solid_segs: List[Seg] = []
    outlines: List[Pts] = []
    for path in page.get_drawings():
        if path.get("type") == "f":                     # fill only (hatch, solid areas): not linework
            continue
        is_dashed = (path.get("dashes") or "").strip() not in _SOLID_DASHES
        segs: List[Seg] = []
        for item in path.get("items", []):
            kind = item[0]
            if kind == "l":
                a, b = item[1], item[2]
                segs.append(Seg(a.x, a.y, b.x, b.y))
            elif kind == "c":                            # Bézier: its chord is enough for routes
                a, b = item[1], item[4]
                segs.append(Seg(a.x, a.y, b.x, b.y))
            elif kind == "re":
                r = item[1]
                outlines.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)])
            elif kind == "qu":
                q = item[1]
                pts = [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]
                outlines.append(pts + [pts[0]])
        segs = [s for s in segs if (s.x1, s.y1) != (s.x2, s.y2)]
        if is_dashed:
            dashed += segs
        else:
            solid_segs += segs
            outlines += [[(s.x1, s.y1), (s.x2, s.y2)] for s in segs]
    return dashed, solid_segs, outlines


def _page_scale(page_text: str) -> Optional[float]:
    """Points per metre from the most common '1:N' printed on the sheet, if any."""
    scales = Counter(int(m) for m in _SCALE.findall(page_text) if 20 <= int(m) <= 5000)
    if not scales:
        return None
    return _POINTS_PER_M / scales.most_common(1)[0][0]


def read_page_routes(page: "fitz.Page") -> RouteNetwork:
    labels = _labels(page)
    tags = [lb for lb in labels if parse_tag(lb.text)]
    if not any(parse_tag(lb.text)[1] for lb in tags):
        return RouteNetwork()                           # no 'X fed from Y' tag: not a site plan
    h = statistics.median([lb.h for lb in tags if lb.h > 0] or [0.0]) or 1.0
    dashed, solid_segs, outlines = _paths(page)
    strokes = [s for s in solid_segs if math.hypot(s.x2 - s.x1, s.y2 - s.y1) <= 3 * h]
    route_segs = dashed + join_dashes(strokes, max_gap=1.5 * h)
    boxes = equipment_boxes(outlines, max_size=8 * h)
    return build_route_network(route_segs, labels, boxes, units_per_m=_page_scale(page.get_text()),
                               snap_decade=False)


def read_pdf_site_routes(files: Sequence[Tuple[bytes, str]]) -> Tuple[Optional[RouteNetwork], str]:
    """The best site-plan route network in a PDF set → (network, 'file p<n>'), or (None, '')."""
    best: Optional[RouteNetwork] = None
    where = ""
    for data, name in files:
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:  # noqa: BLE001 — unreadable file: the other passes report it
            log.info("site routes: cannot open %s: %s", name, e)
            continue
        with doc:
            for i, page in enumerate(doc):
                try:
                    net = read_page_routes(page)
                except Exception as e:  # noqa: BLE001 — never let a geometry oddity sink the run
                    log.warning("site routes: %s p%d skipped: %s", name, i, e)
                    continue
                if net.found and (best is None or len(net.equipment) > len(best.equipment)):
                    best, where = net, f"{name} p{i}"
    return best, where
