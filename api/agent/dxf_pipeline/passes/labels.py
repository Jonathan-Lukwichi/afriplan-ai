"""
Fittings identified by a short label. Some drawings mark a fitting with a letter label beside its
glyph (`PS`, `FL`, `D/N`), and the legend row explains it: the label, then the description on the
same row. Each other copy of the label on the plan is one fitting, even when the glyph itself is
loose line work no block name can identify. The legend's own copy is never an instance.

Light fittings and day/night switches only: a labelled master switch or board is billed from the
SLD already.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Sequence, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.legend import _text_pos
from agent.dxf_pipeline.passes.recognize import _plain_text

_LABEL = re.compile(r"[A-Z]{1,3}(?:/[A-Z]{1,3})?")
_FITTING = re.compile(r"light|lantern|lamp|luminaire|\bmasts?\b|day\W?night", re.I)
_MIN_DESCRIPTION = 12            # characters: shorter text is a tag or a room name, not a legend row
_ROW_REACH = 12.0                # a description within this many text heights to the right is its row
_BESIDE_LABEL = 3.0              # a glyph within this many text heights of a label is what it labels


@dataclass(frozen=True)
class LabelledFitting:
    label: str
    description: str
    qty: int


class _Text(NamedTuple):
    text: str
    x: float
    y: float
    height: float


def _texts(doc: Drawing) -> List[_Text]:
    out = []
    for e in doc.modelspace():
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        text = " ".join(_plain_text(e).split())
        if text:
            x, y = _text_pos(e)
            height = getattr(e.dxf, "height", 0.0) if e.dxftype() == "TEXT" else getattr(e.dxf, "char_height", 0.0)
            out.append(_Text(text, x, y, float(height or 0.0)))
    return out


def _row_description(label: _Text, descriptions: List[_Text]) -> str:
    """The legend description this label is the key of, or "" when the label is on the plan."""
    on_row = [d for d in descriptions
              if 0 < d.x - label.x <= _ROW_REACH * max(d.height, label.height)
              and abs(d.y - label.y) <= max(d.height, label.height)]
    return min(on_row, key=lambda d: d.x).text if on_row else ""


def _plan_labels(doc: Drawing) -> Tuple[List[_Text], Dict[str, str]]:
    """(each label on the plan that a legend row explains, {label: its description})."""
    texts = _texts(doc)
    labels = [t for t in texts if _LABEL.fullmatch(t.text)]
    descriptions = [t for t in texts if len(t.text) >= _MIN_DESCRIPTION and _FITTING.search(t.text)]
    meaning: Dict[str, str] = {}
    keys = set()
    for t in labels:
        row = _row_description(t, descriptions)
        if row:
            meaning.setdefault(t.text, row)
            keys.add(t)
    return [t for t in labels if t.text in meaning and t not in keys], meaning


def count_labelled_fittings(doc: Drawing) -> List[LabelledFitting]:
    plan, meaning = _plan_labels(doc)
    counts: Dict[str, int] = {}
    for t in plan:
        counts[t.text] = counts.get(t.text, 0) + 1
    return [LabelledFitting(label, meaning[label], n) for label, n in sorted(counts.items())]


def is_labelled_shape(positions: Sequence[Tuple[float, float]], doc: Drawing) -> bool:
    """True when every copy of a shape sits beside a counted label: it is that fitting's glyph, so
    counting it too would bill the fitting twice. One copy elsewhere and it is a fitting of its own."""
    plan, _ = _plan_labels(doc)
    return bool(positions) and bool(plan) and all(
        any(math.hypot(x - t.x, y - t.y) <= _BESIDE_LABEL * t.height for t in plan) for x, y in positions)
