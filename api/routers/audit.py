"""
Audit endpoints — the commercial audit features over any Bill of Quantities.

    POST /api/audit/boq                 upload a priced BOQ workbook (.xlsx) → findings
    GET  /api/audit/run/{run_id}        audit the run's (priced, optionally completed) bill
    GET  /api/audit/coverage/{run_id}   which drawing types the run had, what to request
    GET  /api/audit/ratio-model         is derived-item completion available here?

Thin: logic lives in the read-only `audit` / `evaluation` packages. Nothing here
calls a pipeline or an LLM.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from audit.boq_rules import audit_boq, audit_reference
from audit.completer import available_ratio_model
from audit.report import summarise_findings
from audit.sufficiency import (
    drawing_type_from_filename,
    drawing_types_from_page_types,
    sufficiency,
)
from core.run_store import run_store
from evaluation.network import DrawingType
from evaluation.reference import parse_reference_xlsx
from routers.export import _priced_boq_for

router = APIRouter(prefix="/api/audit", tags=["audit"])

_DRAWING_NAMES = {
    "sld": "Single-line diagram (SLD)", "lighting_layout": "Lighting layout",
    "plug_layout": "Plug / power layout", "site_plan": "Site plan (cable routes)",
    "schedule": "DB / circuit schedule",
}


def _findings_payload(findings):
    s = summarise_findings(findings)
    return {
        "summary": {"count": s["count"], "high": s["high"], "value_at_risk_zar": round(s["value_at_risk_zar"], 2),
                    "by_rule": [{"rule": r, "count": n, "value_at_risk_zar": round(v, 2)} for r, n, v in s["by_rule"]]},
        "findings": [f.model_dump() for f in findings],
    }


@router.post("/boq")
async def audit_uploaded_boq(file: UploadFile = File(...)):
    data = await file.read()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "boq.xlsx"
        path.write_bytes(data)
        try:
            ref = parse_reference_xlsx(path, project=Path(file.filename or "boq").stem)
        except Exception as e:  # noqa: BLE001 — not a workbook / not a BOQ layout
            raise HTTPException(400, f"Could not read this file as a BOQ workbook: {e}") from e
    payload = _findings_payload(audit_reference(ref))
    payload["bills"] = [{
        "name": b.name, "in_summary": b.in_summary, "lines": len(b.lines),
        "stated_total_zar": round(b.total_excl_vat, 2), "sum_of_lines_zar": round(b.value, 2),
        "errors": len(b.errors),
    } for b in ref.buildings]
    payload["summary_total_excl_vat_zar"] = round(ref.summary_total_excl_vat, 2)
    return payload


@router.get("/run/{run_id}")
def audit_run(run_id: str, complete: bool = Query(False)):
    priced = _priced_boq_for(run_id, None, 5.0, 15.0, complete=complete)
    return _findings_payload(audit_boq(priced, building=priced.project_name or "This bill"))


def _uploaded_for(record) -> set:
    """Drawing types a run actually had: file types + evidence extracted (PDF), file name (DXF)."""
    result = record.result
    if record.pipeline == "dxf":
        dt = drawing_type_from_filename(record.input_file or getattr(result, "input_file", ""))
        return {dt} if dt else set()
    up = drawing_types_from_page_types(
        getattr(getattr(fc, "sheet_type", None), "value", "") for fc in getattr(result, "files", []) or [])
    facts = getattr(result, "facts", None)
    if facts is not None:
        if facts.spine.distribution_boards or facts.spine.feeders:
            up.add(DrawingType.SLD)
        rooms = facts.takeoff.rooms
        if any(r.light_points() for r in rooms):
            up.add(DrawingType.LIGHTING)
        if any(r.power_points() or r.isolators for r in rooms):
            up.add(DrawingType.PLUGS)
    return up


@router.get("/coverage/{run_id}")
def run_coverage(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    rep = sufficiency(_uploaded_for(record))
    return {
        "uploaded": rep.uploaded,
        "uploaded_names": [_DRAWING_NAMES.get(u, u) for u in rep.uploaded],
        "reproducible_families": rep.reproducible_families,
        "requests": rep.requests,
        "request_names": {d: _DRAWING_NAMES.get(d, d) for d in rep.requests},
        "complete": rep.complete,
    }


@router.get("/ratio-model")
def ratio_model_status():
    model = available_ratio_model()
    if model is None:
        return {"available": False}
    return {"available": True, "project_sources": model.project_sources,
            "ratios": [{"target": r.target, "weight": r.weight, "loo_error": r.loo_mape, "n": r.n}
                       for r in model.ratios]}
