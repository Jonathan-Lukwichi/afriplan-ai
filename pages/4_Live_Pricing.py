"""
AfriPlan v6.1 — Live Pricing & Supplier Quotations.

An OPTIONAL enrichment step that sits after the BOQ is generated. The engineer
picks which material lines to price, the app fans a quote request out to 3-4
suppliers, and shows price / availability / lead time side by side per item.
Choosing a supplier per line writes its live price back onto the BOQ (tagged as
a manual/live source), so the tender export reflects real, current pricing
instead of the built-in estimate.

This page consumes the independent `sourcing/` layer only — it never reaches
into either extraction pipeline.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from agent.shared import BillOfQuantities
from sourcing import SourcingEngine, apply_quotes, build_requests
from sourcing.models import ItemSourcingResult, SourcingReport, SupplierInfo
from sourcing.rfq import QuoteParser, draft_rfq
from sourcing.suppliers.mock import default_mock_suppliers
from ui.components import footer, page_header, rule
from ui.styles import inject_styles


inject_styles()

page_header(
    step="OPTIONAL · LIVE PRICING",
    title="Get real supplier prices for your BOQ",
    subtitle=(
        "Request live pricing, stock availability and lead times from multiple "
        "suppliers per item — then apply the best quote straight into the bill. "
        "Cuts out phoning around each manufacturer."
    ),
)


# ─── Resolve a BOQ to price ──────────────────────────────────────────────────

def _resolve_boq() -> Optional[BillOfQuantities]:
    boq = st.session_state.get("priced_boq")
    if isinstance(boq, BillOfQuantities):
        return boq
    for key in ("pdf_view", "dxf_view"):
        view = st.session_state.get(key)
        if view and view.get("state") == "passed" and view.get("boq") is not None:
            return view["boq"]
    return None


base_boq = _resolve_boq()
if base_boq is None:
    st.warning(
        "No BOQ found yet. Generate a bill first on **Step 3 — BOQ Generation**, "
        "then come back here to price it."
    )
    if st.button("← Go to BOQ Generation", type="primary"):
        st.switch_page("pages/3_BOQ_Generation.py")
    footer()
    st.stop()


# ─── Pick the lines to source ────────────────────────────────────────────────

st.markdown('<div class="afp-eyebrow">1 · CHOOSE ITEMS</div>', unsafe_allow_html=True)

all_reqs = build_requests(base_boq)  # material lines only
if not all_reqs:
    st.info("This BOQ has no material lines to price (only labour/site items).")
    footer()
    st.stop()

label_for = {r.item_ref: f"{r.item_ref}  ·  {r.description}  ({r.qty:g} {r.unit})" for r in all_reqs}
default_refs = [r.item_ref for r in all_reqs][:15]  # cap default selection for a snappy demo

chosen_refs: List[str] = st.multiselect(
    "Which items should we request live prices for?",
    options=[r.item_ref for r in all_reqs],
    default=default_refs,
    format_func=lambda ref: label_for.get(ref, ref),
)

suppliers = default_mock_suppliers()
st.caption(
    "Panel: " + " · ".join(s.info.name for s in suppliers)
    + "  (simulated suppliers — swap in web-catalog / RFQ-email adapters later)."
)

if st.button("📨  Request live quotes", type="primary", disabled=not chosen_refs):
    reqs = [r for r in all_reqs if r.item_ref in set(chosen_refs)]
    engine = SourcingEngine(suppliers)
    report = engine.request_quotes(
        reqs, project_name=base_boq.project_name, boq_run_id=base_boq.run_id
    )
    st.session_state.sourcing_report = report.model_dump()
    # seed default per-item supplier choices with the recommendation
    st.session_state.sourcing_choice = {
        res.request.item_ref: res.recommended_supplier_id for res in report.results
    }


# ─── Show the comparison + collect choices ───────────────────────────────────

report_data: Optional[Dict[str, Any]] = st.session_state.get("sourcing_report")
if report_data:
    report = SourcingReport(**report_data)

    rule()
    st.markdown('<div class="afp-eyebrow">2 · COMPARE & CHOOSE</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Items sourced", report.items_sourced)
    m2.metric("Suppliers contacted", report.suppliers_contacted)
    m3.metric("Potential saving vs estimate", f"R {report.potential_saving_zar:,.0f}")

    choice: Dict[str, str] = dict(st.session_state.get("sourcing_choice", {}))

    for res in report.results:
        req = res.request
        with st.expander(f"{req.item_ref} · {req.description}", expanded=False):
            rows = []
            for q in res.quotes:
                rows.append({
                    "Supplier": q.supplier_name,
                    "Unit R": round(q.unit_price_zar, 2),
                    "Availability": q.availability.value.replace("_", " "),
                    "Lead (days)": q.lead_time_days,
                    "vs estimate": (
                        f"{(q.unit_price_zar - req.anchor_price_zar) / req.anchor_price_zar * 100:+.0f}%"
                        if req.anchor_price_zar > 0 else "—"
                    ),
                    "Recommended": "★" if q.supplier_id == res.recommended_supplier_id else "",
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            options = [q.supplier_id for q in res.quotes] + ["__skip__"]
            def _fmt(sid: str, _res: ItemSourcingResult = res) -> str:
                if sid == "__skip__":
                    return "Keep BOQ estimate (don't source this line)"
                q = next(x for x in _res.quotes if x.supplier_id == sid)
                return f"{q.supplier_name} — R{q.unit_price_zar:,.2f} · {q.availability.value} · {q.lead_time_days}d"

            current = choice.get(req.item_ref) or (res.recommended_supplier_id or "__skip__")
            idx = options.index(current) if current in options else 0
            picked = st.selectbox(
                "Use price from:", options, index=idx,
                format_func=_fmt, key=f"pick::{req.item_ref}",
            )
            choice[req.item_ref] = picked

    st.session_state.sourcing_choice = choice

    # ─── Apply to the bill ────────────────────────────────────────────────
    rule()
    st.markdown('<div class="afp-eyebrow">3 · APPLY TO BOQ</div>', unsafe_allow_html=True)

    if st.button("✅  Apply chosen supplier prices to the BOQ", type="primary"):
        chosen_quotes = {}
        for res in report.results:
            sid = choice.get(res.request.item_ref)
            if not sid or sid == "__skip__":
                continue
            q = next((x for x in res.quotes if x.supplier_id == sid), None)
            if q is not None:
                chosen_quotes[res.request.item_ref] = q

        updated = apply_quotes(base_boq, chosen_quotes)
        st.session_state.priced_boq = updated  # page 3 export picks this up

        c1, c2 = st.columns(2)
        c1.metric("Subtotal (before)", f"R {base_boq.subtotal_zar:,.0f}")
        c2.metric(
            "Subtotal (live sourced)", f"R {updated.subtotal_zar:,.0f}",
            delta=f"R {updated.subtotal_zar - base_boq.subtotal_zar:,.0f}",
            delta_color="inverse",
        )
        st.success(
            f"Applied live prices to {len(chosen_quotes)} line(s). "
            "The updated bill is now the basis for your tender export on Step 3."
        )
        if st.button("→  Go to BOQ Generation to export"):
            st.switch_page("pages/3_BOQ_Generation.py")


# ─── RFQ email channel (trade-counter suppliers with no online price) ────────

rule()
st.markdown('<div class="afp-eyebrow">RFQ EMAIL · TRADE-COUNTER SUPPLIERS</div>', unsafe_allow_html=True)
st.caption(
    "Suppliers like Voltex / ARB price on request. Auto-draft a professional RFQ "
    "email for the selected items, send it, then paste their reply below to parse "
    "it into structured quotes automatically."
)

with st.expander("Draft an RFQ email & parse a reply", expanded=False):
    if not chosen_refs:
        st.info("Select some items above first.")
    else:
        reqs = [r for r in all_reqs if r.item_ref in set(chosen_refs)]
        sup_names = {s.info.supplier_id: s.info.name for s in suppliers}
        target_id = st.selectbox(
            "Supplier to address", list(sup_names.keys()),
            format_func=lambda sid: sup_names[sid],
        )
        target = next(s.info for s in suppliers if s.info.supplier_id == target_id)
        # give the demo suppliers a plausible RFQ inbox
        target = SupplierInfo(**{**target.model_dump(), "contact_email": target.contact_email or f"sales@{target_id}.co.za"})

        contractor = st.session_state.get("contractor_profile")
        draft = draft_rfq(
            target, reqs,
            contractor_name=getattr(contractor, "company_name", "") if contractor else "",
            project_name=base_boq.project_name,
        )
        st.text_input("To", draft["to"], disabled=True)
        st.text_input("Subject", draft["subject"], disabled=True)
        st.text_area("Body", draft["body"], height=240)

        st.markdown("**Parse a supplier reply**")
        reply = st.text_area(
            "Paste the supplier's emailed reply here",
            placeholder="e.g. 'Downlights R210.50 each ex stock; sockets R145, 5 working days...'",
            height=140,
        )
        if st.button("🧠  Parse reply into quotes"):
            api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                st.error("No `ANTHROPIC_API_KEY` configured — parsing a free-text reply needs the LLM.")
            elif not reply.strip():
                st.warning("Paste the supplier's reply first.")
            else:
                try:
                    parser = QuoteParser(api_key=api_key)
                    parsed = parser.parse_reply(target, reqs, reply)
                    if not parsed:
                        st.warning("Couldn't extract any quotes from that reply.")
                    else:
                        st.dataframe(pd.DataFrame([{
                            "Item": q.item_ref, "Unit R": q.unit_price_zar,
                            "Availability": q.availability.value,
                            "Lead (days)": q.lead_time_days,
                            "Confidence": f"{q.parse_confidence:.0%}",
                        } for q in parsed]), hide_index=True, use_container_width=True)
                        st.success(f"Parsed {len(parsed)} quote(s) from {target.name}.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Parsing failed: {e}")


# ─── Nav ─────────────────────────────────────────────────────────────────────

rule()
nav = st.columns([1, 1, 1])
with nav[0]:
    if st.button("←  Back to BOQ Generation", use_container_width=True):
        st.switch_page("pages/3_BOQ_Generation.py")

footer()
