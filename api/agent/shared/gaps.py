"""
The list of things to check: one line per question, however many sheets ask it.

A drawing set asks the same question once per sheet or board. Each estimate must stay visible
(hard rule 7), but a person answers a question once, so gaps of one kind become one line that
still names everything in it. A lone gap is left exactly as written. Pure, no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

from agent.shared.boq import GapItem


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _names(found: Sequence[re.Match]) -> str:
    return ", ".join(sorted({m.group(1) for m in found}))


def _first_assumption(found: Sequence[re.Match], gaps: Sequence[GapItem]) -> str:
    return gaps[0].assumption


def _measured_note(found: Sequence[re.Match], gaps: Sequence[GapItem]) -> str:
    lengths = []
    allowance = ""
    for m, g in zip(found, gaps):
        note = re.match(r"Route measured ([\d.]+) m on the site plan, (.+)$", g.assumption)
        if note:
            lengths.append(f"{m.group(1)} {float(note.group(1)):g} m")
            allowance = note.group(2)
    return f"Measured on the site plan: {'; '.join(sorted(lengths))}. Each has {allowance}"


@dataclass(frozen=True)
class _Kind:
    pattern: re.Pattern
    line: Callable[[Sequence[re.Match]], str]
    assumption: Callable[[Sequence[re.Match], Sequence[GapItem]], str] = _first_assumption


_KINDS = (
    _Kind(re.compile(r"^Legend lists '(.+)' but no instances were counted$"),
          lambda f: f"{_plural(len({m.group(1) for m in f}), 'legend item')} not found on any plan: {_names(f)}"),
    _Kind(re.compile(r"^Feeder (.+) has no drawn route on the site plan$"),
          lambda f: f"{_plural(len(f), 'feeder')} with no drawn route on the site plan: {_names(f)}"),
    _Kind(re.compile(r"^Feeder (.+): lengths written on the site plan add to (.+), the drawn route scales to (.+)$"),
          lambda f: (f"{_plural(len(f), 'feeder')} where the written length differs from the drawn route: "
                     + ", ".join(sorted(f"{m.group(1)} ({m.group(2)} written, {m.group(3)} drawn)" for m in f)))),
    _Kind(re.compile(r"^Feeder (.+) length taken from the site-plan route$"),
          lambda f: f"{_plural(len(f), 'feeder length')} taken from the site-plan routes", _measured_note),
    _Kind(re.compile(r"^(\d+) symbols recognised as '(.+)' by AI$"),
          lambda f: (f"{_plural(len(f), 'symbol type')} named by AI: "
                     + ", ".join(sorted(f"{m.group(2)} ({m.group(1)})" for m in f)))),
    _Kind(re.compile(r"^Ceiling height for conduit drops in (.+) not on the drawing$"),
          lambda f: f"Ceiling height for conduit drops not on the drawings ({_plural(len(f), 'building')})"),
    _Kind(re.compile(r"^Conduit install labour has no rate in the rate model \((.+)\)$"),
          lambda f: f"Conduit install labour has no rate in the rate model ({_plural(len(f), 'building')})"),
    _Kind(re.compile(r"^(.+ tag) is about as close to (.+)'s symbol — check which route belongs to which board$"),
          lambda f: (f"{_plural(len(f), 'board tag')} about as close to another board's symbol: "
                     + ", ".join(sorted(f"{m.group(1)[:-4]} and {m.group(2)}" for m in f)))),
    _Kind(re.compile(r"^(.+) on the layouts is taken to be .+ on the SLD$"),
          lambda f: f"{_plural(len(f), 'board')} spelled differently on the layouts and the SLD: {_names(f)}"),
)


def group_gaps(gaps: Sequence[GapItem]) -> List[GapItem]:
    """Identical gaps once; gaps of one kind as one line, in the place of the first of them."""
    first: Dict[str, GapItem] = {}
    for g in gaps:
        first.setdefault(g.description, g)
    unique = list(first.values())
    members: Dict[int, list] = {}
    for g in unique:
        for k, kind in enumerate(_KINDS):
            m = kind.pattern.match(g.description)
            if m:
                members.setdefault(k, []).append((m, g))
                break
    out: List[GapItem] = []
    placed = set()
    for g in unique:
        k = next((k for k, kind in enumerate(_KINDS) if kind.pattern.match(g.description)), None)
        if k is None or len(members[k]) < 2:
            out.append(g)
        elif k not in placed:
            placed.add(k)
            found, group = zip(*members[k])
            out.append(group[0].model_copy(update={
                "description": _KINDS[k].line(found), "assumption": _KINDS[k].assumption(found, group),
                "building_block": "", "drawing_ref": "drawing set"}))
    return out
