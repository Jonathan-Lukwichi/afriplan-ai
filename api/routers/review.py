"""
Review endpoints — a person answers the run's things to check.

    GET    /api/review/{run_id}            the questions, what each is worth, the bill's change
    PUT    /api/review/{run_id}/answers    give or change an answer
    DELETE /api/review/{run_id}/answers    undo one

Thin: the logic lives in `review/`. Nothing here changes a stored run, calls a pipeline or an LLM.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.run_store import run_store
from db.review_answers import delete_answer, save_answer
from review.run_review import DEFAULT_BY, drawings_key, fields_of, project_key, review_payload

router = APIRouter(prefix="/api/review", tags=["review"])


class Answer(BaseModel):
    question_id: str
    values: Dict[str, object] = {}
    by: Optional[str] = None


def _record(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    return record


def _checked(fields: List, values: Dict[str, object]) -> Dict[str, float]:
    """Only the question's own fields, as numbers of zero or more, with the required ones given."""
    allowed = {f.name: f for f in fields}
    unknown = set(values) - set(allowed)
    if unknown:
        raise HTTPException(422, f"Not part of this question: {', '.join(sorted(unknown))}")
    missing = [f.label for f in fields if f.required and values.get(f.name) is None]
    if missing:
        raise HTTPException(422, f"Please give: {', '.join(missing)}")
    out: Dict[str, float] = {}
    for name, value in values.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise HTTPException(422, f"{allowed[name].label} must be a number of zero or more")
        out[name] = float(value)
    return out


@router.get("/{run_id}")
def get_review(run_id: str):
    return review_payload(_record(run_id))


@router.put("/{run_id}/answers")
def put_answer(run_id: str, body: Answer):
    record = _record(run_id)
    if getattr(record.result, "findings", None) is None:
        raise HTTPException(409, "this run has nothing to review")
    fields = fields_of(record, body.question_id)
    if fields is None:
        raise HTTPException(404, "no such question on this run")
    save_answer(project_key(record), body.question_id, _checked(fields, body.values),
                (body.by or "").strip() or DEFAULT_BY, drawings_key(record))
    return review_payload(record)


@router.delete("/{run_id}/answers")
def undo_answer(run_id: str, question_id: str = Query(...)):
    record = _record(run_id)
    delete_answer(project_key(record), question_id)
    return review_payload(record)
