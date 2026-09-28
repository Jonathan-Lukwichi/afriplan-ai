"""
SLD pass — read distribution boards, breakers and feeders from a single-line
diagram drawn in CAD (issue 001).

A CAD SLD is schematic TEXT, usually on layer 0, so the plan-oriented
`recognise()` (electrical layers only) sees nothing. The text follows stable SA
conventions, observed on every Wedela SLD:

    DB header   'DB-AB1  400V, 100A, 15kA, 50Hz, 3PH+N+E'
    breaker     '20A'  (one per way, near its board)      'SPARE' for spare ways
    feeder      'DB-AB1 FED FROM DB-CR | Incoming main cable 16mm²'

Deterministic, no LLM. A feeder is only recorded when its cable size is printed
(a site-overview 'DB1-fed from DB-CR' with no size is a diagram label, not a bill
item). SLDs rarely print route lengths: `length_annotated` stays False and the
assembler assumes + flags the length (issue 002).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.recognize import _plain_text

_HEADER = re.compile(
    r"^\s*(?P<name>DB[-\s]?[A-Z0-9]+)\s+(?P<v>\d{3})\s*V\s*,\s*(?P<a>\d{2,4})\s*A\s*,"
    r"\s*(?P<ka>\d+(?:\.\d+)?)\s*kA.*?(?P<ph>[13])\s*PH", re.I | re.S)
_FEEDER = re.compile(
    r"(?P<to>DB[-\s]?[A-Z0-9]+)\s+FED\s+FROM\s+(?P<frm>[A-Z0-9][A-Z0-9-]*)"
    r".*?cable\s+(?P<size>\d+(?:\.\d+)?)\s*mm", re.I | re.S)
_LENGTH = re.compile(r"\b(\d{1,4}(?:\.\d+)?)\s*m\b(?!m)", re.I)
_BREAKER = re.compile(r"^\s*(\d{1,3})\s*A\s*$", re.I)
# A main kiosk / MSB header often carries no DB name: '400V, 300A, 15kA, 50Hz, 3PH+N+E'
_ANON_HEADER = re.compile(
    r"^\s*(?P<v>\d{3})\s*V\s*,\s*(?P<a>\d{2,4})\s*A\s*,\s*(?P<ka>\d+(?:\.\d+)?)\s*kA.*?(?P<ph>[13])\s*PH",
    re.I | re.S)
# Incoming supply: 'EXISTING MINI SUB' + '95mm² 4CORE COPPER PVC PVC SWA PVC CABLE'
_MINI_SUB = re.compile(r"MINI\s*-?\s*SUB", re.I)
# Motor-control and 3-phase parts drawn on the board (pool pumps, fans…)
_DOL = re.compile(r"^\s*DOL\b", re.I)
_ISOLATOR = re.compile(r"^\s*ISO\s*\d+\s*$|ISOLATOR", re.I)
_MASTER = re.compile(r"(MASTER|MAIN)\s+SWITCH", re.I)
_FOUR_CORE = re.compile(r"\d+(?:\.\d+)?\s*mm.*?X\s*4\s*C\b", re.I | re.S)
_SUPPLY_CABLE = re.compile(r"(?P<size>\d+(?:\.\d+)?)\s*mm.*?(?P<cores>\d)\s*CORE.*?SWA", re.I | re.S)


def _norm_db(name: str) -> str:
    return re.sub(r"\s+", "-", name.strip().upper()).replace("--", "-")


@dataclass
class SldBoard:
    name: str
    voltage_v: int = 400
    main_breaker_a: int = 0
    ka: float = 0.0
    phases: int = 3
    x: float = 0.0
    y: float = 0.0
    circuits: List[Tuple[int, int]] = field(default_factory=list)   # (amps, poles)
    spares: int = 0
    source: str = ""                # sheet the board was read from
    motor_starters: int = 0         # 'DOL' starters (pool pumps, fans)
    isolators: int = 0              # 'ISO1'… local isolators on the board
    master_switch: bool = False     # 'MASTER SWITCH' / 'MAIN SWITCH' disconnector
    three_phase_ways: int = 0       # outgoing circuits wired in 4-core (x4C) cable


@dataclass
class SldFeeder:
    from_source: str
    to_db: str
    cable_size_mm2: float
    cable_cores: int = 4
    length_m: float = 0.0
    length_annotated: bool = False
    is_underground: bool = True
    source: str = ""                # sheet the feeder was read from


@dataclass
class SldFacts:
    boards: List[SldBoard] = field(default_factory=list)
    feeders: List[SldFeeder] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.boards or self.feeders)


def _pos(e) -> Tuple[float, float]:
    p = getattr(e.dxf, "insert", None)
    return (p.x, p.y) if p is not None else (0.0, 0.0)


def _anon_board_name(sheet_name: str) -> str:
    """Name for a board whose header carries none: the kiosk on a kiosk sheet, else the MSB."""
    return "KIOSK" if re.search(r"KIOSK", sheet_name, re.I) else "MSB"


def read_sld(doc: Drawing, sheet_name: str = "") -> SldFacts:
    facts = SldFacts()
    boards: dict = {}
    breakers: List[Tuple[int, float, float]] = []
    spares: List[Tuple[float, float]] = []
    seen_feeders = set()
    parts: List[Tuple[str, float, float]] = []     # motor-control / 3-phase markers
    mini_sub = False
    supply_cable = None

    for e in doc.modelspace():
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        text = _plain_text(e).strip()
        if not text:
            continue
        x, y = _pos(e)
        h = _HEADER.search(text) or _ANON_HEADER.search(text)
        if h:
            name = (_norm_db(h.group("name")) if "name" in h.groupdict()
                    else _anon_board_name(sheet_name))
            if name not in boards:                       # the same header can be drawn twice
                boards[name] = SldBoard(
                    name=name, voltage_v=int(h.group("v")), main_breaker_a=int(h.group("a")),
                    ka=float(h.group("ka")), phases=int(h.group("ph")), x=x, y=y, source=sheet_name)
            continue
        f = _FEEDER.search(text)
        if f:
            key = (_norm_db(f.group("frm")), _norm_db(f.group("to")))
            if key not in seen_feeders:
                seen_feeders.add(key)
                tail = text[f.end():]
                lm = _LENGTH.search(tail)
                facts.feeders.append(SldFeeder(
                    from_source=key[0], to_db=key[1], cable_size_mm2=float(f.group("size")),
                    length_m=float(lm.group(1)) if lm else 0.0, length_annotated=bool(lm),
                    source=sheet_name))
            continue
        if _MINI_SUB.search(text):
            mini_sub = True
            continue
        c = _SUPPLY_CABLE.search(text)
        if c and supply_cable is None:
            supply_cable = (float(c.group("size")), int(c.group("cores")))
            continue
        b = _BREAKER.match(text)
        if b:
            breakers.append((int(b.group(1)), x, y))
        elif text.upper() == "SPARE":
            spares.append((x, y))
        elif _DOL.match(text):
            parts.append(("dol", x, y))
        elif _ISOLATOR.search(text):
            parts.append(("iso", x, y))
        elif _MASTER.search(text):
            parts.append(("master", x, y))
        elif _FOUR_CORE.search(text):
            parts.append(("4c", x, y))

    facts.boards = list(boards.values())
    # The incoming supply: a mini-sub on the sheet, a SWA cable spec, and an unnamed
    # main board it feeds (named boards already declare their source with FED FROM).
    anon = _anon_board_name(sheet_name)
    if mini_sub and supply_cable and anon in boards and ("MINI-SUB", anon) not in seen_feeders:
        facts.feeders.insert(0, SldFeeder(
            from_source="MINI-SUB", to_db=anon, cable_size_mm2=supply_cable[0],
            cable_cores=supply_cable[1], source=sheet_name))
    if facts.boards:
        # Boards drawn side by side own the breaker COLUMN below their header: assign
        # along the layout axis (plain Euclidean distance pulls the lower breakers of one
        # column towards the neighbouring header).
        xs = [bd.x for bd in facts.boards]
        ys = [bd.y for bd in facts.boards]
        by_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))

        def nearest(x: float, y: float) -> SldBoard:
            if len(facts.boards) == 1:
                return facts.boards[0]
            return min(facts.boards, key=lambda bd: (abs(bd.x - x), abs(bd.y - y)) if by_x
                       else (abs(bd.y - y), abs(bd.x - x)))
        for amps, x, y in breakers:
            nearest(x, y).circuits.append((amps, 1))
        for x, y in spares:
            nearest(x, y).spares += 1
        for kind, x, y in parts:
            bd = nearest(x, y)
            if kind == "dol":
                bd.motor_starters += 1
            elif kind == "iso":
                bd.isolators += 1
            elif kind == "master":
                bd.master_switch = True
            else:
                bd.three_phase_ways += 1
    return facts


def find_board(facts: SldFacts, name: str) -> Optional[SldBoard]:
    return next((b for b in facts.boards if b.name == _norm_db(name)), None)
