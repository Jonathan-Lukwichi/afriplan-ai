"""
Cable-route network measurement (issue 002) — pure geometry, no LLM, no I/O.

SLDs name each feeder ('DB-AB1 FED FROM DB-CR … 16mm²') but almost never print
its length. The length lives on the electrical SITE PLAN: dashed route lines
running between equipment symbols, each symbol tagged 'DB-AB1 Fed from DB-PFA',
often with the designer's run lengths written beside the route ('35m').

This module turns that drawing into a graph and answers "how long is the route
from X to Y?". It is fed by thin adapters in each pipeline (DXF entities, or
vector paths from a PDF page), so both pipelines measure the same way without
sharing state or calling each other.

    segments  → graph (endpoints snapped, T-junctions split)
    tag texts → equipment ('DB-CR', 'KIOSK', 'MINI SUB') anchored to the symbol
                box (or loose route end) nearest the tag
    'Nm' texts→ scale calibration (drawing units per metre) + stated lengths
    route(X,Y)→ shortest path length in metres + the edges used (trench union)
"""

from __future__ import annotations

import heapq
import math
import re
import statistics
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class Seg:
    """One straight piece of a drawn route, in drawing units."""
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class Label:
    """A text on the drawing: its content, insertion point and character height."""
    text: str
    x: float
    y: float
    h: float = 0.0


@dataclass(frozen=True)
class Box:
    """Axis-aligned extent of an equipment symbol outline (DB, kiosk, mini-sub)."""
    x0: float
    y0: float
    x1: float
    y1: float

    def distance(self, x: float, y: float) -> float:
        dx = max(self.x0 - x, 0.0, x - self.x1)
        dy = max(self.y0 - y, 0.0, y - self.y1)
        return math.hypot(dx, dy)


# ─── tags ────────────────────────────────────────────────────────────

_NAME = r"DB[\s-]?[A-Z0-9]+(?:-(?!FED\b)[A-Z0-9]+)?|KIOSK|MINI[\s-]*SUB(?:STATION)?"
_TAG = re.compile(
    rf"^\s*(?:EXISTING\s+|NEW\s+)?(?P<name>{_NAME})\b"
    rf"(?:\s*-?\s*FED\s+FROM\s+(?:EXISTING\s+)?(?P<src>{_NAME}))?", re.I)
_LENGTH = re.compile(r"^\s*(\d{1,4}(?:\.\d+)?)\s*m\s*$", re.I)


def equipment_key(name: str) -> str:
    """'DB-1', 'DB1', 'db 1' → 'DB1'; 'Existing Mini sub' → 'MINISUB'. Matching only."""
    s = re.sub(r"^\s*(EXISTING|NEW)\s+", "", name.strip(), flags=re.I).upper()
    s = re.sub(r"SUBSTATION$", "SUB", re.sub(r"[\s\-_]+", "", s))
    return s


def parse_tag(text: str) -> Optional[Tuple[str, Optional[str]]]:
    """An equipment tag → (key, source key or None); anything else → None."""
    m = _TAG.match(" ".join(text.split()))
    if not m:
        return None
    src = m.group("src")
    return equipment_key(m.group("name")), (equipment_key(src) if src else None)


def tag_name(text: str) -> str:
    """The equipment name as drawn ('DB-AB1 Fed from DB-PFA' → 'DB-AB1')."""
    m = _TAG.match(" ".join(text.split()))
    return m.group("name").upper() if m else text.strip()


def parse_length(text: str) -> Optional[float]:
    m = _LENGTH.match(text)
    return float(m.group(1)) if m else None


# ─── the network ─────────────────────────────────────────────────────

@dataclass
class Edge:
    a: int
    b: int
    length: float                      # drawing units
    label_m: Optional[float] = None    # designer's stated length for this run, if written beside it


@dataclass
class RouteMatch:
    from_key: str
    to_key: str
    length_m: float
    edges: FrozenSet[int]
    stated_m: Optional[float] = None   # sum of designer labels along the path, when any


@dataclass
class RouteNetwork:
    nodes: List[Tuple[float, float]] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    equipment: Dict[str, Set[int]] = field(default_factory=dict)     # key → anchor nodes
    names: Dict[str, str] = field(default_factory=dict)              # key → name as drawn
    fed_from: Dict[str, str] = field(default_factory=dict)           # key → source key (tags)
    units_per_m: float = 1.0
    scale_source: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.edges) and len(self.equipment) >= 2 and bool(self.fed_from)

    @property
    def total_m(self) -> float:
        return self.length_of(range(len(self.edges)))

    def length_of(self, edge_ids: Iterable[int]) -> float:
        return sum(self.edges[i].length for i in set(edge_ids)) / self.units_per_m

    def route(self, frm: str, to: str) -> Optional[RouteMatch]:
        """Shortest drawn route between two pieces of equipment, or None if either is unknown."""
        fk, tk = equipment_key(frm), equipment_key(to)
        src, dst = self.equipment.get(fk), self.equipment.get(tk)
        if not src or not dst or fk == tk:
            return None
        adj: Dict[int, List[Tuple[int, int]]] = {}
        for i, e in enumerate(self.edges):
            adj.setdefault(e.a, []).append((e.b, i))
            adj.setdefault(e.b, []).append((e.a, i))
        dist = {n: 0.0 for n in src}
        prev: Dict[int, Tuple[int, int]] = {}
        heap = [(0.0, n) for n in src]
        heapq.heapify(heap)
        end = None
        while heap:
            d, n = heapq.heappop(heap)
            if d > dist.get(n, math.inf):
                continue
            if n in dst:
                end = n
                break
            for m, ei in adj.get(n, []):
                nd = d + self.edges[ei].length
                if nd < dist.get(m, math.inf):
                    dist[m] = nd
                    prev[m] = (n, ei)
                    heapq.heappush(heap, (nd, m))
        if end is None:
            return None
        used: List[int] = []
        n = end
        while n in prev:
            n, ei = prev[n]
            used.append(ei)
        labels = [self.edges[i].label_m for i in used if self.edges[i].label_m is not None]
        return RouteMatch(
            from_key=fk, to_key=tk, length_m=dist[end] / self.units_per_m,
            edges=frozenset(used), stated_m=sum(labels) if labels else None,
        )


# ─── building it ─────────────────────────────────────────────────────

def _point_seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> Tuple[float, float]:
    """(distance, t along the segment 0..1)."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


class _Nodes:
    """Endpoint snapping on a grid: points closer than `tol` become one node."""

    def __init__(self, tol: float):
        self.tol = max(tol, 1e-9)
        self.xy: List[Tuple[float, float]] = []
        self._grid: Dict[Tuple[int, int], List[int]] = {}

    def get(self, x: float, y: float) -> int:
        gx, gy = int(math.floor(x / self.tol)), int(math.floor(y / self.tol))
        best, best_d = None, self.tol
        for i in range(gx - 1, gx + 2):
            for j in range(gy - 1, gy + 2):
                for n in self._grid.get((i, j), ()):
                    d = math.hypot(self.xy[n][0] - x, self.xy[n][1] - y)
                    if d <= best_d:
                        best, best_d = n, d
        if best is not None:
            return best
        self.xy.append((x, y))
        self._grid.setdefault((gx, gy), []).append(len(self.xy) - 1)
        return len(self.xy) - 1


def build_route_network(
    segments: Sequence[Seg],
    labels: Sequence[Label],
    boxes: Sequence[Box] = (),
    *,
    units_per_m: Optional[float] = None,
    snap_decade: bool = False,
    max_segments: int = 5000,
) -> RouteNetwork:
    """
    Build the route graph. `units_per_m` is the adapter's belief about the drawing
    scale (CAD units, or PDF points at the printed scale); when the designer wrote
    run lengths beside the route they calibrate it instead. `snap_decade` (CAD):
    round a label-derived scale to 1/10/100/1000 units per metre.
    """
    net = RouteNetwork()
    tags = [(lb, parse_tag(lb.text)) for lb in labels]
    tags = [(lb, t) for lb, t in tags if t is not None]
    if not any(src for _, (_, src) in tags) or len({k for _, (k, _) in tags}) < 2:
        return net                                   # not a site route overview
    if not segments or len(segments) > max_segments:
        if segments:
            net.warnings.append(f"{len(segments)} candidate route segments — too many to be a site plan")
        return net

    heights = [lb.h for lb, _ in tags if lb.h > 0]
    h = statistics.median(heights) if heights else 0.0
    if h <= 0:
        xs = [c for s in segments for c in (s.x1, s.x2)]
        ys = [c for s in segments for c in (s.y1, s.y2)]
        h = max(max(xs) - min(xs), max(ys) - min(ys)) / 200.0 or 1.0
    tol = 0.5 * h

    # 1. endpoints → nodes (snapped); split segments at T-junctions
    nodes = _Nodes(tol)
    raw = [(nodes.get(s.x1, s.y1), nodes.get(s.x2, s.y2)) for s in segments]
    pieces: List[Tuple[int, int]] = []
    for a, b in raw:
        if a == b:
            continue
        ax, ay = nodes.xy[a]
        bx, by = nodes.xy[b]
        cuts = []
        for n, (px, py) in enumerate(nodes.xy):
            if n in (a, b):
                continue
            d, t = _point_seg_dist(px, py, ax, ay, bx, by)
            if d <= tol and 0.0 < t < 1.0:
                cuts.append((t, n))
        chain = [a, *[n for _, n in sorted(cuts)], b]
        pieces += [(p, q) for p, q in zip(chain, chain[1:]) if p != q]
    seen: Set[Tuple[int, int]] = set()
    for p, q in pieces:
        key = (min(p, q), max(p, q))
        if key in seen:
            continue
        seen.add(key)
        (px, py), (qx, qy) = nodes.xy[p], nodes.xy[q]
        net.edges.append(Edge(p, q, math.hypot(qx - px, qy - py)))
    net.nodes = nodes.xy

    # 2. equipment anchors: symbol boxes touched by the route, else loose route ends
    degree: Dict[int, int] = {}
    for e in net.edges:
        degree[e.a] = degree.get(e.a, 0) + 1
        degree[e.b] = degree.get(e.b, 0) + 1
    candidates: List[Tuple[Box, Set[int]]] = []
    boxed: Set[int] = set()
    for bx in boxes:
        touching = {n for n in degree if bx.distance(*net.nodes[n]) <= tol}
        if touching:
            candidates.append((bx, touching))
            boxed |= touching
    for n, deg in degree.items():
        if deg == 1 and n not in boxed:
            x, y = net.nodes[n]
            candidates.append((Box(x, y, x, y), {n}))

    pairs = sorted(
        (bx.distance(lb.x, lb.y), ti, ci)
        for ti, (lb, _) in enumerate(tags) for ci, (bx, _) in enumerate(candidates))
    tag_done: Set[int] = set()
    cand_done: Set[int] = set()
    for _, ti, ci in pairs:
        if ti in tag_done or ci in cand_done:
            continue
        key = tags[ti][1][0]
        if key in net.equipment:                     # the same tag drawn twice
            tag_done.add(ti)
            continue
        tag_done.add(ti)
        cand_done.add(ci)
        net.equipment[key] = set(candidates[ci][1])
        net.names[key] = tag_name(tags[ti][0].text)
    # Honest about ambiguity: a tag about as close to another board's symbol as to its own.
    anchor_of = {tuple(sorted(v)): k for k, v in net.equipment.items()}
    for lb, (key, _) in tags:
        if key not in net.equipment:
            continue
        own = next(bx for bx, ns in candidates if ns == net.equipment[key])
        d_own = own.distance(lb.x, lb.y)
        for bx, ns in candidates:
            other = anchor_of.get(tuple(sorted(ns)))
            if other and other != key and bx.distance(lb.x, lb.y) < 1.25 * d_own:
                net.warnings.append(
                    f"{net.names.get(key, key)} tag is about as close to {net.names.get(other, other)}'s "
                    "symbol — check which route belongs to which board")
                break
    for _, (key, src) in tags:
        if src:
            net.fed_from[key] = src
    missing = sorted({k for _, (k, _) in tags} - set(net.equipment))
    if missing:
        net.warnings.append("Tagged but not on a drawn route: " + ", ".join(missing))

    # 3. designer lengths → nearest edge; scale calibration
    ratios: List[float] = []
    for lb in labels:
        value = parse_length(lb.text)
        if value is None or value <= 0:
            continue
        best, best_d = None, 4 * h
        for i, e in enumerate(net.edges):
            (ax, ay), (bx2, by2) = net.nodes[e.a], net.nodes[e.b]
            d, _ = _point_seg_dist(lb.x, lb.y, ax, ay, bx2, by2)
            if d < best_d:
                best, best_d = i, d
        if best is None:
            continue
        e = net.edges[best]
        e.label_m = (e.label_m or 0.0) + value
        ratios.append(e.length / value)

    if len(ratios) >= 3:
        r = statistics.median(ratios)
        if snap_decade:
            r = 10 ** round(math.log10(r))
        if units_per_m and 1 / 3 <= r / units_per_m <= 3:
            net.units_per_m, net.scale_source = units_per_m, "drawing scale (confirmed by length labels)"
        else:
            net.units_per_m = r
            net.scale_source = f"calibrated from {len(ratios)} length labels"
    elif units_per_m:
        net.units_per_m, net.scale_source = units_per_m, "drawing scale"
    else:
        net.units_per_m, net.scale_source = 1.0, "unknown — assumed 1 unit = 1 m"
        net.warnings.append("Drawing scale unknown: route lengths assume 1 drawing unit = 1 m")
    return net
