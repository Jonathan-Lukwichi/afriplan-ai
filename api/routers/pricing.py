"""
Live Pricing — request real supplier quotes for a BOQ's material lines and
apply the best one back into the bill. Consumes the independent sourcing/
layer only (never reaches into either extraction pipeline, same rule as the
original app's page docstring).

Sourcing reports are stored keyed by run_id (one active session per run) in
an in-memory store, following the same pattern as run_store/compare_store.
Applying quotes writes the result onto the RunRecord's sourced_boq field,
which /api/export/* then uses as the export basis instead of the raw
pipeline output.
"""

from __future__ import annotations

import os
import threading
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.run_store import run_store
from sourcing import SourcingEngine, apply_quotes, build_requests
from sourcing.models import SourcingReport, SupplierInfo
from sourcing.rfq import QuoteParser, draft_rfq
from sourcing.suppliers.mock import default_mock_suppliers
from sourcing.suppliers.price_list import DEFAULT_CATALOGUE, default_price_list_suppliers

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

CATALOGUE_PATH = DEFAULT_CATALOGUE   # data/catalogue/price_catalogue.csv (scripts/build_price_catalogue.py)


def _quote_panel():
    """The wholesalers plus one dated list-price supplier per catalogue supplier, when the catalogue
    is built on this machine. List prices are never recommended or auto-applied (availability unknown)."""
    return default_mock_suppliers() + default_price_list_suppliers(CATALOGUE_PATH)

_reports: Dict[str, SourcingReport] = {}
_lock = threading.Lock()


def _serialize_report(report: SourcingReport) -> dict:
    # SourcingReport.items_sourced/suppliers_contacted/potential_saving_zar
    # are @property computed fields, not included in model_dump() by
    # default - add them explicitly for the API response.
    data = report.model_dump(mode="json")
    data["items_sourced"] = report.items_sourced
    data["suppliers_contacted"] = report.suppliers_contacted
    data["potential_saving_zar"] = report.potential_saving_zar
    return data


def _base_boq_for(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    if record.status != "passed" or record.result is None or record.result.boq is None:
        raise HTTPException(409, "this run has no BoQ to price yet")
    return record.sourced_boq if record.sourced_boq is not None else record.result.boq


@router.get("/requests/{run_id}")
def get_requests(run_id: str):
    """Material lines available to source, plus the supplier panel."""
    boq = _base_boq_for(run_id)
    reqs = build_requests(boq)
    suppliers = _quote_panel()
    return {
        "requests": [r.model_dump(mode="json") for r in reqs],
        "suppliers": [s.info.model_dump(mode="json") for s in suppliers],
    }


class QuoteRequestBody(BaseModel):
    item_refs: List[str]


@router.post("/quotes/{run_id}")
def request_quotes(run_id: str, body: QuoteRequestBody):
    boq = _base_boq_for(run_id)
    all_reqs = build_requests(boq)
    reqs = [r for r in all_reqs if r.item_ref in set(body.item_refs)]
    if not reqs:
        raise HTTPException(400, "none of the given item_refs match this BoQ's material lines")

    engine = SourcingEngine(_quote_panel())
    report = engine.request_quotes(reqs, project_name=boq.project_name, boq_run_id=boq.run_id)
    with _lock:
        _reports[run_id] = report
    return _serialize_report(report)


@router.get("/quotes/{run_id}")
def get_quotes(run_id: str):
    with _lock:
        report = _reports.get(run_id)
    if report is None:
        raise HTTPException(404, "no sourcing report yet - call POST /api/pricing/quotes/{run_id} first")
    return _serialize_report(report)


class ApplyQuotesBody(BaseModel):
    choices: Dict[str, str]  # item_ref -> supplier_id ("__skip__" to keep the estimate)


@router.post("/apply/{run_id}")
def apply_chosen_quotes(run_id: str, body: ApplyQuotesBody):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "run not found")
    with _lock:
        report = _reports.get(run_id)
    if report is None:
        raise HTTPException(404, "no sourcing report yet - request quotes first")

    base_boq = _base_boq_for(run_id)
    chosen_quotes = {}
    for res in report.results:
        supplier_id = body.choices.get(res.request.item_ref)
        if not supplier_id or supplier_id == "__skip__":
            continue
        q = next((x for x in res.quotes if x.supplier_id == supplier_id), None)
        if q is not None:
            chosen_quotes[res.request.item_ref] = q

    updated = apply_quotes(base_boq, chosen_quotes)
    record.sourced_boq = updated
    run_store.put(record)
    return {
        "applied": len(chosen_quotes),
        "subtotal_before_zar": base_boq.subtotal_zar,
        "subtotal_after_zar": updated.subtotal_zar,
    }


class DraftRfqBody(BaseModel):
    item_refs: List[str]
    supplier_id: str
    contractor_name: str = ""


@router.post("/rfq/draft/{run_id}")
def draft_rfq_email(run_id: str, body: DraftRfqBody):
    boq = _base_boq_for(run_id)
    all_reqs = build_requests(boq)
    reqs = [r for r in all_reqs if r.item_ref in set(body.item_refs)]
    if not reqs:
        raise HTTPException(400, "none of the given item_refs match this BoQ's material lines")

    suppliers = default_mock_suppliers()
    target = next((s.info for s in suppliers if s.info.supplier_id == body.supplier_id), None)
    if target is None:
        raise HTTPException(404, f"unknown supplier_id '{body.supplier_id}'")
    if not target.contact_email:
        target = SupplierInfo(**{**target.model_dump(), "contact_email": f"sales@{body.supplier_id}.co.za"})

    return draft_rfq(target, reqs, contractor_name=body.contractor_name, project_name=boq.project_name)


class ParseReplyBody(BaseModel):
    item_refs: List[str]
    supplier_id: str
    reply_text: str


@router.post("/rfq/parse/{run_id}")
def parse_rfq_reply(run_id: str, body: ParseReplyBody):
    from core.config import ai_available
    if not ai_available():
        raise HTTPException(400, "No AI key configured (ANTHROPIC_API_KEY or GEMINI_API_KEY) - "
                                 "parsing a free-text reply needs the LLM")

    boq = _base_boq_for(run_id)
    all_reqs = build_requests(boq)
    reqs = [r for r in all_reqs if r.item_ref in set(body.item_refs)]
    suppliers = default_mock_suppliers()
    target = next((s.info for s in suppliers if s.info.supplier_id == body.supplier_id), None)
    if target is None:
        raise HTTPException(404, f"unknown supplier_id '{body.supplier_id}'")

    parser = QuoteParser()
    quotes = parser.parse_reply(target, reqs, body.reply_text)
    return {"quotes": [q.model_dump(mode="json") for q in quotes]}
