"""
AfriPlan v6.1 — Step 2: Extraction (single pipeline).

Runs ONLY the source chosen on Step 1 — never both, never in parallel.

    PDF  → run_pdf_estimator over the drawing set (5-pass estimator)
    DXF  → run_dxf_pipeline over the single DXF (deterministic)

The result BOQ is stashed in session for Step 3. For the PDF path we surface
the per-file classification and let the user re-tag any low-confidence file
before re-running (the manual-tag fallback).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import streamlit as st

from agent.shared import ContractorProfile, ProjectMetadata
from ui.components import footer, page_header, rule
from ui.styles import inject_styles

logging.basicConfig(level=logging.INFO)
inject_styles()


SHEET_TYPE_OPTIONS = [
    "auto", "register", "sld", "lighting_layout", "plugs_layout", "schedule", "notes",
]


def _metric(label: str, value: str) -> str:
    return (
        '<div class="afp-metric">'
        f'<span class="afp-metric-label">{label}</span>'
        f'<span class="afp-metric-value">{value}</span>'
        "</div>"
    )


def _render_legend(legend, boq) -> None:
    """Show the drawing's own legend as its symbol dictionary, marking each
    declared symbol as counted (in the BOQ) or still a gap to verify."""
    if not legend or not getattr(legend, "entries", None):
        return
    from agent.shared.legend import billed_canonical_items
    billed = billed_canonical_items(l.description for l in (boq.line_items if boq else []))
    counted = sum(1 for e in legend.entries if e.canonical_item in billed)
    with st.expander(
        f"📖 Legend — {len(legend.entries)} symbol type(s) declared · {counted} counted",
        expanded=False,
    ):
        st.caption(
            "The drawing's own legend, read as its symbol dictionary. Each declared "
            "symbol is either counted into the BOQ or flagged as a gap to verify."
        )
        for e in sorted(legend.entries, key=lambda x: x.section.section_number):
            mark = "✅ counted" if e.canonical_item in billed else "⚠️ verify count"
            mh = f" · @{e.mounting_mm}mm" if getattr(e, "mounting_mm", None) else ""
            st.markdown(
                f"- **{e.canonical_item}** _[{e.section.short_label}]_{mh} — {mark}"
            )


def _render_sufficiency(uploaded) -> None:
    """Which BOQ items these drawings can support, and which drawing to send next."""
    from audit.sufficiency import sufficiency
    rep = sufficiency(set(uploaded))
    names = {"sld": "Single-line diagram (SLD)", "lighting_layout": "Lighting layout",
             "plug_layout": "Plug / power layout", "site_plan": "Site plan (cable routes)",
             "schedule": "DB / circuit schedule"}
    with st.expander(
        f"🧩 Drawing coverage — {len(rep.reproducible_families)} item types supported · "
        f"{len(rep.requests)} drawing type(s) missing",
        expanded=bool(rep.requests),
    ):
        st.caption("What this upload can quantify, and what to request for a complete BOQ. "
                   "Items without supporting drawings become PROVISIONAL, never silent.")
        st.markdown("**Recognised drawing types:** "
                    + (", ".join(names.get(u, u) for u in rep.uploaded) or "none"))
        for d, fams in rep.requests.items():
            st.markdown(f"- ➕ **{names.get(d, d)}** would unlock: "
                        + ", ".join(f.replace('_', ' ') for f in fams[:10])
                        + ("…" if len(fams) > 10 else ""))
        if not rep.requests:
            st.success("All drawing-derived items are supported by this upload.")


source: Optional[str] = st.session_state.get("source")
project: ProjectMetadata = st.session_state.get("project_meta") or ProjectMetadata()
contractor: ContractorProfile = st.session_state.get("contractor_profile") or ContractorProfile()


page_header(
    step="STEP 2 OF 3",
    title="Extraction",
    subtitle="Run the pipeline for your chosen source. The result feeds the BOQ on the next step.",
)


# ─── Guard: must arrive from Upload with inputs ──────────────────────

pdf_file_set = st.session_state.get("pdf_file_set")
dxf_bytes = st.session_state.get("dxf_bytes")

if source == "pdf" and not pdf_file_set:
    _no_input = True
elif source == "dxf" and not dxf_bytes:
    _no_input = True
elif source not in ("pdf", "dxf"):
    _no_input = True
else:
    _no_input = False

if _no_input:
    st.warning("No inputs found. Go back to **Step 1** and choose a source.")
    if st.button("← Back to Upload", type="primary"):
        st.switch_page("pages/1_Upload.py")
    footer()
    st.stop()


# ═══════════════════════════════════════════════════════════════════════
#  PDF PATH
# ═══════════════════════════════════════════════════════════════════════

if source == "pdf":
    from agent.pdf_pipeline.passes.run import run_pdf_estimator

    st.markdown('<div class="afp-eyebrow">DRAWING SET</div>', unsafe_allow_html=True)
    names = [name for _, name in pdf_file_set]
    for n in names:
        st.markdown(f'<span class="afp-chip">📄 {n}</span>', unsafe_allow_html=True)

    # API key check
    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error(
            "No `ANTHROPIC_API_KEY` configured — the PDF estimator needs it. "
            "Add it to `.streamlit/secrets.toml` and reload."
        )

    # Manual file-type tags (the low-confidence fallback)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    with st.expander("Advanced · tag file types manually", expanded=False):
        st.caption(
            "Leave on **auto** to let the estimator classify each file. Override "
            "any file the estimator got wrong (or flagged as low-confidence)."
        )
        manual_types = {}
        for n in names:
            prev = st.session_state.get(f"tag::{n}", "auto")
            choice = st.selectbox(
                n, options=SHEET_TYPE_OPTIONS,
                index=SHEET_TYPE_OPTIONS.index(prev) if prev in SHEET_TYPE_OPTIONS else 0,
                key=f"tag::{n}",
            )
            if choice != "auto":
                manual_types[n] = choice

    rule()

    run_cols = st.columns([1, 2, 1])
    with run_cols[1]:
        run_clicked = st.button(
            "▶  Run PDF estimator", type="primary", use_container_width=True,
            disabled=not api_key, key="run_pdf",
        )

    if run_clicked:
        with st.spinner("Running the 5-pass estimator over your drawing set…"):
            try:
                run = run_pdf_estimator(
                    pdf_file_set, api_key=api_key, project=project,
                    contractor=contractor, manual_types=manual_types or None,
                    persist=True,
                )
                st.session_state.pdf_run = run
                st.session_state.pdf_view = {
                    "state": "passed" if run.success else "failed",
                    "boq": run.boq,
                    "raw_run": run,
                }
            except Exception as e:                       # noqa: BLE001
                logging.exception("PDF estimator crashed")
                st.session_state.pdf_run = None
                st.error(f"Estimator failed: {e}")

    run = st.session_state.get("pdf_run")
    if run is not None:
        rule()
        st.markdown('<div class="afp-eyebrow">RESULT</div>', unsafe_allow_html=True)

        m = st.columns(4)
        m[0].markdown(_metric("Pages", str(run.page_count)), unsafe_allow_html=True)
        m[1].markdown(_metric("Line items", str(len(run.boq.line_items) if run.boq else 0)), unsafe_allow_html=True)
        m[2].markdown(_metric("Gaps", str(run.gap_count)), unsafe_allow_html=True)
        m[3].markdown(_metric("Cost", f"R {run.cost_zar:,.2f}"), unsafe_allow_html=True)

        # Per-file classification
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.markdown("**How each file was read**")
        for fc in run.files:
            flag = " ⚠️ low confidence — consider tagging it above" if fc.needs_manual else ""
            tag = "manual" if fc.manual else f"{fc.confidence:.0%}"
            st.markdown(
                f"- `{fc.file_name}` → **{fc.sheet_type.value}** ({tag}){flag}"
            )

        # Drawing coverage: file types + evidence actually extracted
        from audit.sufficiency import drawing_types_from_page_types
        from evaluation.network import DrawingType
        _up = drawing_types_from_page_types(fc.sheet_type.value for fc in run.files)
        if run.facts.spine.distribution_boards or run.facts.spine.feeders:
            _up.add(DrawingType.SLD)
        if any(r.light_points() for r in run.facts.takeoff.rooms):
            _up.add(DrawingType.LIGHTING)
        if any(r.power_points() or r.isolators for r in run.facts.takeoff.rooms):
            _up.add(DrawingType.PLUGS)
        _render_sufficiency(_up)

        # Legend dictionary (LDSE)
        _render_legend(getattr(run, "legend", None), run.boq)

        # Gap report
        if run.boq and run.boq.gaps:
            with st.expander(f"Gap report — {len(run.boq.gaps)} item(s) to verify", expanded=False):
                for g in run.boq.gaps:
                    st.markdown(
                        f"- **[{g.severity}]** {g.description} — _{g.assumption}_  "
                        f"→ {g.suggested_action}"
                    )

        if run.success:
            st.success("Estimator produced a Bill of Quantities. Continue to build the tender BOQ.")
        else:
            st.warning(run.error or "No billable items were extracted.")


# ═══════════════════════════════════════════════════════════════════════
#  DXF PATH
# ═══════════════════════════════════════════════════════════════════════

elif source == "dxf":
    from agent.dxf_pipeline.passes.run import run_dxf_estimator

    dxf_name = st.session_state.get("dxf_name") or "input.dxf"
    st.markdown('<div class="afp-eyebrow">DXF / DWG FILE</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="afp-chip">📐 {dxf_name}</span>', unsafe_allow_html=True)

    rule()
    run_cols = st.columns([1, 2, 1])
    with run_cols[1]:
        if st.button("▶  Run DXF estimator", type="primary", use_container_width=True, key="run_dxf"):
            with st.spinner("Parsing CAD geometry (deterministic, R 0.00)…"):
                try:
                    dxf_run = run_dxf_estimator(
                        file_bytes=dxf_bytes, file_name=dxf_name,
                        project=project, contractor=contractor, persist=True,
                    )
                    st.session_state.dxf_run = dxf_run
                    st.session_state.dxf_view = {
                        "state": "passed" if dxf_run.success else "failed",
                        "boq": dxf_run.boq,
                        "raw_run": dxf_run,
                    }
                except Exception as e:                   # noqa: BLE001
                    logging.exception("DXF estimator crashed")
                    st.error(f"DXF estimator failed: {e}")

    dxf_run = st.session_state.get("dxf_run")
    if dxf_run is not None:
        rule()
        st.markdown('<div class="afp-eyebrow">RESULT</div>', unsafe_allow_html=True)
        boq = dxf_run.boq
        m = st.columns(4)
        m[0].markdown(_metric("Symbols", str(dxf_run.symbol_count)), unsafe_allow_html=True)
        m[1].markdown(_metric("Cable (m)", f"{dxf_run.electrical_cable_length_m:,.0f}"), unsafe_allow_html=True)
        m[2].markdown(_metric("Total ex VAT", f"R {boq.total_excl_vat_zar:,.0f}" if boq else "—"), unsafe_allow_html=True)
        m[3].markdown(_metric("Cost", "R 0.00"), unsafe_allow_html=True)

        if dxf_run.converted_from_dwg:
            st.caption("Converted from DWG automatically (LibreDWG / ODA).")
        if dxf_run.circuit_ids or dxf_run.db_refs:
            st.markdown(
                f"**Recognised:** circuits {', '.join(dxf_run.circuit_ids) or '—'} · "
                f"DBs {', '.join(dxf_run.db_refs) or '—'}"
            )

        # Drawing coverage for this single CAD file
        from audit.sufficiency import drawing_type_from_filename
        _dt = drawing_type_from_filename(dxf_name)
        _render_sufficiency({_dt} if _dt else set())

        # Legend dictionary (LDSE) + template-matched counts
        _render_legend(getattr(dxf_run, "legend", None), boq)
        tm = [l for l in (boq.line_items if boq else []) if "template-matched" in l.description]
        if tm:
            st.markdown(
                "**Template-matched symbols:** "
                + " · ".join(f"{l.description.replace(' (template-matched)', '')} ×{int(l.qty)}" for l in tm)
            )

        if boq and boq.gaps:
            with st.expander(f"Gap report — {len(boq.gaps)} item(s) to verify", expanded=False):
                for g in boq.gaps:
                    st.markdown(f"- **[{g.severity}]** {g.description} — _{g.assumption}_ → {g.suggested_action}")

        if dxf_run.success:
            st.success("DXF estimator produced a Bill of Quantities (exact counts, measured cable).")
        else:
            st.warning(getattr(dxf_run, "error", None) or "No electrical content recognised.")


# ─── Navigation ──────────────────────────────────────────────────────

rule()
nav = st.columns([1, 1, 1])
with nav[0]:
    if st.button("←  Back to Upload", use_container_width=True, key="back_upload"):
        st.switch_page("pages/1_Upload.py")

_view = st.session_state.get("pdf_view") if source == "pdf" else st.session_state.get("dxf_view")
_can_continue = bool(_view and _view.get("state") == "passed" and _view.get("boq"))
with nav[2]:
    if st.button("Continue to BOQ  →", type="primary", use_container_width=True,
                 disabled=not _can_continue, key="to_boq"):
        st.switch_page("pages/3_BOQ_Generation.py")


footer()
