"""
GET /api/export/{excel,pdf,json}/{run_id}, POST /api/export/email

Reads the run's BoQ from the keyed run_store (never recomputes it — the
same /last-materialization discipline the DXF/PDF endpoints already follow),
reprices it on demand with the caller's markup/contingency/VAT/quote_ref,
and streams the tender document. Email is a genuinely new feature (the
original Streamlit app only had download buttons) — see api/ai/boq_email.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr

from agent.shared import ContractorProfile, ProjectMetadata
from agent.shared.contractor_io import load_contractor_profile, save_contractor_profile
from ai import boq_email
from core import notify
from core.boq_pricing import reprice_boq
from core.run_store import run_store
from exports import export_boq_to_excel, export_boq_to_pdf

router = APIRouter(prefix="/api", tags=["export"])


def _priced_boq_for(
    run_id: str, markup: float, contingency: float, vat: float,
):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    if record.status != "passed" or record.result is None or record.result.boq is None:
        raise HTTPException(409, "this run has no BoQ to export yet")
    return reprice_boq(record.result.boq, markup, contingency, vat)


@router.get("/boq/profile")
def get_contractor_profile():
    return load_contractor_profile().model_dump(mode="json")


@router.put("/boq/profile")
def put_contractor_profile(profile: dict):
    contractor = ContractorProfile.model_validate(profile)
    path = save_contractor_profile(contractor)
    return {"saved": path is not None, "profile": contractor.model_dump(mode="json")}


@router.get("/export/excel/{run_id}")
def export_excel(
    run_id: str,
    markup: float = Query(20.0), contingency: float = Query(5.0), vat: float = Query(15.0),
    quote_ref: Optional[str] = Query(None), validity_days: int = Query(30),
):
    priced = _priced_boq_for(run_id, markup, contingency, vat)
    xlsx_bytes = export_boq_to_excel(
        priced, project=ProjectMetadata(project_name=priced.project_name),
        contractor=ContractorProfile(markup_pct=markup, contingency_pct=contingency, vat_pct=vat),
        quote_ref=quote_ref, validity_days=validity_days,
    )
    ref = quote_ref or f"AFP-{datetime.utcnow():%Y%m%d}-{priced.run_id[:6].upper()}"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={ref}_BOQ.xlsx"},
    )


@router.get("/export/pdf/{run_id}")
def export_pdf(
    run_id: str,
    markup: float = Query(20.0), contingency: float = Query(5.0), vat: float = Query(15.0),
    quote_ref: Optional[str] = Query(None), validity_days: int = Query(30),
):
    priced = _priced_boq_for(run_id, markup, contingency, vat)
    pdf_bytes = export_boq_to_pdf(
        priced, project=ProjectMetadata(project_name=priced.project_name),
        contractor=ContractorProfile(markup_pct=markup, contingency_pct=contingency, vat_pct=vat),
        quote_ref=quote_ref, validity_days=validity_days,
    )
    ref = quote_ref or f"AFP-{datetime.utcnow():%Y%m%d}-{priced.run_id[:6].upper()}"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={ref}_BOQ.pdf"},
    )


@router.get("/export/json/{run_id}")
def export_json(
    run_id: str,
    markup: float = Query(20.0), contingency: float = Query(5.0), vat: float = Query(15.0),
):
    priced = _priced_boq_for(run_id, markup, contingency, vat)
    return priced.model_dump(mode="json")


class EmailBoqRequest(BaseModel):
    run_id: str
    to: EmailStr
    recipient_name: Optional[str] = None
    markup: float = 20.0
    contingency: float = 5.0
    vat: float = 15.0
    quote_ref: Optional[str] = None
    validity_days: int = 30


@router.post("/export/email")
def email_boq(body: EmailBoqRequest):
    priced = _priced_boq_for(body.run_id, body.markup, body.contingency, body.vat)
    ref = body.quote_ref or f"AFP-{datetime.utcnow():%Y%m%d}-{priced.run_id[:6].upper()}"
    contractor = ContractorProfile(markup_pct=body.markup, contingency_pct=body.contingency, vat_pct=body.vat)
    project = ProjectMetadata(project_name=priced.project_name)

    xlsx_bytes = export_boq_to_excel(priced, project=project, contractor=contractor, quote_ref=ref, validity_days=body.validity_days)
    pdf_bytes = export_boq_to_pdf(priced, project=project, contractor=contractor, quote_ref=ref, validity_days=body.validity_days)

    valid_until = datetime.utcnow() + timedelta(days=body.validity_days)
    context = {
        "project_name": priced.project_name, "quote_ref": ref,
        "total_items": priced.total_items, "total_incl_vat_zar": priced.total_incl_vat_zar,
        "gap_count": len(priced.gaps), "valid_until": f"{valid_until:%Y-%m-%d}",
    }

    raw = boq_email.generate_note(context)
    if raw:
        subject, sections, closing = boq_email.parse_note(raw)
    else:
        subject = f"Bill of Quantities — {priced.project_name}"
        sections, closing = [], f"Your Bill of Quantities ({ref}) is attached, valid until {valid_until:%Y-%m-%d}."

    html_body = boq_email.compose_html(body.recipient_name, sections, closing, "AfriPlan Estimator")

    sent = notify.send_email(
        to=body.to, subject=subject, html=html_body,
        attachments=[(f"{ref}_BOQ.xlsx", xlsx_bytes), (f"{ref}_BOQ.pdf", pdf_bytes)],
    )

    return {"sent": sent, "subject": subject, "quote_ref": ref}
