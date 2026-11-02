"""
Fittings identified by a short label. Some drawings mark a fitting with a letter label beside its
glyph (`PS`, `FL`, `D/N`), and the legend row explains it: the label, then the description on the
same row. Each other copy of the label on the plan is one fitting, even when the glyph itself is
loose line work no block name can identify. The legend's own copy is never an instance.

Light fittings and day/night switches only: a labelled master switch or board is billed from the
SLD already.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, NamedTuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.passes.legend import _text_pos
from agent.dxf_pipeline.passes.recognize import _plain_text

_LABEL = re.compile(r"[A-Z]{1,3}(?:/[A-Z]{1,3})?")
_FITTING = re.compile(r"light|lantern|lamp|luminaire|\bmasts?\b|day\W?night", re.I)
_MIN_DESCRIPTION = 12            # characters: shorter text is a tag or a room name, not a legend row
_ROW_REACH = 12.0                # a description within this many text heights to the right is its row


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


def count_labelled_fittings(doc: Drawing) -> List[LabelledFitting]:
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
    counts: Dict[str, int] = {}
    for t in labels:
        if t.text in meaning and t not in keys:
            counts[t.text] = counts.get(t.text, 0) + 1
    return [LabelledFitting(label, meaning[label], n) for label, n in sorted(counts.items())]
