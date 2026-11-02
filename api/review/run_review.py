"""
The review of a stored run: which project it belongs to, which answers hold, the bill they give.

An answer belongs to a project (the sheets, whatever their revision) and is tied to the drawings it
was given on. Different drawings, even under the same names, ask it again rather than apply it. The
run keeps what the reader found: accuracy is always judged on that.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from agent.dxf_pipeline.passes.revisions import sheet_and_revision
from agent.shared.boq import BillOfQuantities
from agent.shared.pricing import finalise_totals, price_findings
from db.review_answers import load_answers
from review.questions import Group, apply_answers, build_questions, group_questions

DEFAULT_BY = "the estimator"


def _digest(parts: List[str]) -> str:
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()[:24]


def _files(record) -> List[Tuple[str, str]]:
    """(file name, content hash when known) of each drawing."""
    notes = getattr(record.result, "files", None) or []
    files = [(n.file_name, getattr(n, "sha256", "")) for n in notes]
    return files or [(record.input_file, "")]


def project_key(record) -> str:
    return _digest([sheet_and_revision(name)[0] for name, _ in _files(record)])


def drawings_key(record) -> str:
    return _digest([f"{name}|{sha}" for name, sha in _files(record)])


def _standing(record) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """(answers given on these drawings, answers given on other drawings)."""
    now = drawings_key(record)
    held, old = {}, {}
    for question_id, answer in load_answers(project_key(record)).items():
        (held if answer["drawings"] == now else old)[question_id] = answer
    return held, old


def _answered_findings(record, held: Dict[str, dict]):
    by = ", ".join(sorted({a["by"] for a in held.values()})) or DEFAULT_BY
    return apply_answers(record.result.findings, {q: a["values"] for q, a in held.items()}, by=by)


def _carry_prices(bill: BillOfQuantities, sourced: BillOfQuantities) -> None:
    """Live supplier prices already applied to this run stay on the answered bill."""
    prices = {(l.description, l.line_kind): l.unit_price_zar for l in sourced.line_items}
    for line in bill.line_items:
        line.unit_price_zar = prices.get((line.description, line.line_kind), line.unit_price_zar)
    finalise_totals(bill)


def reviewed_bill(record) -> Optional[BillOfQuantities]:
    """The bill with the answers that hold, or None when there are none."""
    findings = getattr(record.result, "findings", None)
    held, _ = _standing(record) if findings is not None else ({}, {})
    if not held:
        return None
    original = record.result.boq
    bill = price_findings(_answered_findings(record, held), pipeline=original.pipeline,
                          project_name=original.project_name, run_id=original.run_id)
    if record.sourced_boq is not None:
        _carry_prices(bill, record.sourced_boq)
    return bill


def question_ids(record) -> set:
    findings = record.result.findings
    return {q.id for q in build_questions(findings, findings)}


def fields_of(record, question_id: str):
    findings = record.result.findings
    return next((q.fields for q in build_questions(findings, findings) if q.id == question_id), None)


def _status(question_id: str, held: dict, old: dict) -> dict:
    if question_id in held:
        return {"status": "answered", "answer": _public(held[question_id])}
    if question_id in old:
        return {"status": "recheck", "answer": _public(old[question_id])}
    return {"status": "open", "answer": None}


def _public(answer: dict) -> dict:
    return {k: answer[k] for k in ("values", "by", "at")}


def _group_payload(group: Group, held: dict, old: dict) -> dict:
    questions = [{**q.model_dump(), **_status(q.id, held, old)} for q in group.questions]
    return {"key": group.key, "title": group.title, "bulk": group.bulk.model_dump() if group.bulk else None,
            "open": sum(1 for q in questions if q["status"] != "answered"), "questions": questions}


def review_payload(record) -> dict:
    """Everything the review needs to show, valued on the bill as it stands now."""
    findings = getattr(record.result, "findings", None)
    if record.status != "passed" or findings is None or record.result.boq is None:
        return {"available": False}
    held, old = _standing(record)
    current = _answered_findings(record, held)
    groups = [_group_payload(g, held, old) for g in group_questions(build_questions(findings, current))]
    questions = [q for g in groups for q in g["questions"]]
    bill = reviewed_bill(record) or record.result.boq
    return {
        "available": True,
        "groups": groups,
        "open": sum(1 for g in groups if g["open"]),
        "answered": sum(1 for q in questions if q["status"] == "answered"),
        "recheck": sum(1 for q in questions if q["status"] == "recheck"),
        "reader_subtotal_zar": record.result.boq.subtotal_zar,
        "subtotal_zar": bill.subtotal_zar,
        "change_zar": round(bill.subtotal_zar - record.result.boq.subtotal_zar, 2),
        "total_incl_vat_zar": bill.total_incl_vat_zar,
    }
