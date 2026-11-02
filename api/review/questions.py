"""
Things to check as questions a person can answer.

A reader's gaps say what it could not confirm. Here each becomes a question with fields to fill, and
what it is worth; an answer gives new findings, priced by the one pricer (ADR-0008). Pure: findings
in, findings out. The findings a reader produced are copied, never changed.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from agent.shared.boq import BQSection, GapItem, ItemConfidence
from agent.shared.companions import companion_findings
from agent.shared.findings import Evidence, FeederFinding, Findings, ItemFinding
from agent.shared.pricing import price_findings
from agent.shared.routes import equipment_key
from agent.shared.symbol_catalogue import catalogue_item
from core import constants

ANSWERED = "Answered"
_LEGEND = re.compile(r"^Legend lists '(.+)' but no instances were counted$")
_PRICE_MAPS = {"light": "LIGHT_PRICES", "socket": "SOCKET_PRICES", "switch": "SWITCH_PRICES", "db": "DB_PRICES"}
_ITEM_INSTALL_ZAR = 85.0         # as the readers price a counted item
_DEFAULT_CEILING_M = 3.0


class AnswerField(BaseModel):
    name: str
    label: str
    unit: str = ""
    value: Optional[float] = None    # what the bill uses now
    required: bool = True


class Option(BaseModel):
    label: str
    value: float
    change_zar: float = 0.0


class Question(BaseModel):
    id: str
    group: str
    title: str
    why: str = ""
    action: str = ""
    severity: str = "medium"
    fields: List[AnswerField] = Field(default_factory=list)
    options: List[Option] = Field(default_factory=list)
    on_bill_zar: float = 0.0         # what rests on this answer, before contingency and VAT
    per_unit_zar: float = 0.0
    per_unit: str = ""


class Bulk(BaseModel):
    label: str
    values: Dict[str, float] = Field(default_factory=dict)


class Group(BaseModel):
    key: str
    title: str
    bulk: Optional[Bulk] = None
    questions: List[Question] = Field(default_factory=list)


_GROUPS = {
    "no_route": ("Feeders with no drawn route", None),
    "lengths": ("Feeders with two lengths", None),
    "labour": ("Conduit labour", None),
    "ceiling": ("Ceiling heights", Bulk(label=f"All are {_DEFAULT_CEILING_M:g} m", values={"ceiling_m": _DEFAULT_CEILING_M})),
    "legend": ("In the legend, not found on any plan", Bulk(label="None of these are on the plans", values={"qty": 0})),
    "confirm": ("Confirm", Bulk(label="Confirm all")),
}


def _subtotal(findings: Findings) -> float:
    return price_findings(findings, pipeline="dxf").subtotal_zar


def _light(findings: Findings) -> Findings:
    """The findings without what pricing never reads, to copy cheaply while comparing."""
    return findings.model_copy(update={"sheet_words": {}})


def _feeder_id(f: FeederFinding) -> str:
    return f"feeder:{equipment_key(f.from_board)}>{equipment_key(f.to_board)}"


def _gap_id(description: str) -> str:
    return "confirm:" + hashlib.sha1(description.encode("utf-8")).hexdigest()[:12]


def _changed(findings: Findings, index: int, **changes) -> Findings:
    feeders = list(findings.feeders)
    feeders[index] = feeders[index].model_copy(update=changes)
    return findings.model_copy(update={"feeders": feeders})


def _feeder_question(f: FeederFinding, index: int, current: Findings, total: float) -> Optional[Question]:
    guessed = f.evidence == Evidence.ASSUMED
    if not guessed and not f.length_options:
        return None
    live = next((c for c in current.feeders if _feeder_id(c) == _feeder_id(f)), f)
    without = current.model_copy(update={"feeders": [c for c in current.feeders if _feeder_id(c) != _feeder_id(f)]})
    gap = next(iter(f.gaps), None)
    fields = [AnswerField(name="length_m", label="Cable length", unit="m", value=round(live.length_m, 2))]
    if guessed:
        fields.append(AnswerField(name="trench_m", label="Trench length (0 if not in a trench)", unit="m",
                                  value=round(live.trench_m, 2), required=False))
    return Question(
        id=_feeder_id(f), group="no_route" if guessed else "lengths",
        title=f"{f.from_board}→{f.to_board}: {f.cable_size_mm2:g} mm² cable",
        why=gap.assumption if gap else "", action=gap.suggested_action if gap else "",
        severity=gap.severity if gap and guessed else "medium", fields=fields,
        options=[Option(label=label, value=value,
                        change_zar=round(_subtotal(_changed(current, index, length_m=value)) - total, 2))
                 for label, value in f.length_options.items()],
        on_bill_zar=round(total - _subtotal(without), 2),
        per_unit_zar=round(_subtotal(_changed(current, index, length_m=live.length_m + 1)) - total, 2),
        per_unit="metre",
    )


def _conduit_questions(original: Findings, current: Findings, total: float) -> List[Question]:
    out: List[Question] = []
    buildings = [it.building for it in companion_findings(original)]
    for building in buildings:
        taller = dict(current.ceiling_m)
        now = taller.get(building, _DEFAULT_CEILING_M)
        taller[building] = now + 1
        out.append(Question(
            id=f"ceiling:{building}", group="ceiling", title=building or "This building",
            why=f"{_DEFAULT_CEILING_M:g} m assumed; drops = ceiling − mounting height.",
            action="Give the ceiling height; the conduit quantity follows it.", severity="low",
            fields=[AnswerField(name="ceiling_m", label="Ceiling height", unit="m", value=now)],
            per_unit_zar=round(_subtotal(current.model_copy(update={"ceiling_m": taller})) - total, 2),
            per_unit="metre of ceiling",
        ))
    if buildings:
        rate = current.conduit_install_zar
        out.append(Question(
            id="conduit_labour", group="labour", title="Labour to install conduit, per metre",
            why="Conduit is priced on material only.", action="Give your own rate.",
            fields=[AnswerField(name="rate", label="Labour rate", unit="R/m", value=rate or None)],
            per_unit_zar=round(_subtotal(current.model_copy(update={"conduit_install_zar": rate + 1})) - total, 2),
            per_unit="rand of labour rate",
        ))
    return out


def _gap_question(gap: GapItem) -> Optional[Question]:
    legend = _LEGEND.match(gap.description)
    if legend:
        item = legend.group(1)
        return Question(
            id=f"legend:{item}", group="legend", title=item,
            why="Listed in a legend, but not found on any plan.", action="Say how many there are, 0 if none.",
            fields=[AnswerField(name="qty", label="How many", value=0),
                    AnswerField(name="rate", label="Price each (blank: our rate)", unit="R", required=False)])
    if gap.severity == "low" or gap.description.startswith(("Feeder ", "Ceiling height", "Conduit install labour")):
        return None
    return Question(id=_gap_id(gap.description), group="confirm", title=gap.description, why=gap.assumption,
                    action=gap.suggested_action, severity=gap.severity)


def build_questions(original: Findings, current: Findings) -> List[Question]:
    """The questions the reader's findings raise, valued on the bill as it stands with `current`
    (the findings with the answers so far applied)."""
    original, current = _light(original), _light(current)
    total = _subtotal(current)
    questions = [q for i, f in enumerate(original.feeders) if (q := _feeder_question(f, i, current, total))]
    questions += _conduit_questions(original, current, total)
    seen = set()
    for gap in original.gaps:
        q = _gap_question(gap)
        if q is not None and q.id not in seen:
            seen.add(q.id)
            questions.append(q)
    return questions


def group_questions(questions: List[Question]) -> List[Group]:
    """A few groups, most urgent first; the biggest amounts first inside each."""
    out: List[Group] = []
    for key, (title, bulk) in _GROUPS.items():
        members = sorted((q for q in questions if q.group == key), key=lambda q: -q.on_bill_zar)
        if members:
            out.append(Group(key=key, title=title, bulk=bulk, questions=members))
    return out


def _catalogue_price(item: str) -> float:
    known = catalogue_item(item)
    return getattr(constants, _PRICE_MAPS[known.price_map]).get(known.price_key, 0.0) if known else 0.0


def _answered_item(item: str, section: BQSection, values: dict, by: str) -> ItemFinding:
    rate = values.get("rate")
    material = _catalogue_price(item)
    found = ItemFinding(
        description=item, section=section, item=item if catalogue_item(item) else "", qty=float(values["qty"]),
        price_zar=float(rate) if rate else None, material_zar=material,
        install_zar=_ITEM_INSTALL_ZAR if material else 0.0, sheet="answered", evidence=Evidence.ASSUMED,
        confidence=ItemConfidence.ASSUMED, source_label=ANSWERED, assumption=f"Count given by {by}.",
    )
    if not rate and not material:
        found.gaps.append(GapItem(
            section=section, description=f"No rate for '{item}' ({values['qty']:g} counted)",
            assumption="Priced at nothing.", suggested_action="Give a price for this item.",
            severity="high", drawing_ref="answered",
        ))
    return found


def apply_answers(findings: Findings, answers: Dict[str, dict], *, by: str) -> Findings:
    """New findings with these answers in them; `findings` is left as it was."""
    out = findings.model_copy(deep=True)
    for f in out.feeders:
        values = answers.get(_feeder_id(f))
        if values is None:
            continue
        f.length_m = float(values["length_m"])
        if values.get("trench_m") is not None:
            f.trench_m = float(values["trench_m"])
        f.evidence, f.source_label, f.gaps = Evidence.WRITTEN, ANSWERED, []
        f.assumption = f"Length given by {by}."
    gaps: List[GapItem] = []
    for gap in out.gaps:
        legend = _LEGEND.match(gap.description)
        values = answers.get(f"legend:{legend.group(1)}") if legend else None
        if values is not None:
            if values.get("qty"):
                out.items.append(_answered_item(legend.group(1), gap.section, values, by))
        elif _gap_id(gap.description) not in answers:
            gaps.append(gap)
    out.gaps = gaps
    for question_id, values in answers.items():
        if question_id.startswith("ceiling:"):
            out.ceiling_m[question_id.split(":", 1)[1]] = float(values["ceiling_m"])
        elif question_id == "conduit_labour":
            out.conduit_install_zar = float(values["rate"])
    return out
