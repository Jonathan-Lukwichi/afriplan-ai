"""
AfriPlan Electrical v6.1 — Upload page.

Three vertical sections:
  1. Upload (PDF, DXF, project metadata)
  2. Two-column results (PDF pipeline | DXF pipeline)
  3. Cross-pipeline comparison (only if both ran)

The two pipelines run concurrently in a ThreadPoolExecutor. Each
column updates its own state in st.session_state — neither pipeline can
block the other.
"""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import streamlit as st

from agent.dxf_pipeline import run_dxf_pipeline
from agent.pdf_pipeline import run_pdf_pipeline
from agent.shared import ContractorProfile, ProjectMetadata
from exports.excel_boq import export_boq_to_excel
from exports.pdf_boq import export_boq_to_pdf
from ui.pipeline_column import render_pipeline_column
from ui.styles import inject_styles

logging.basicConfig(level=logging.INFO)


# ─── Page config and styles ────────────────────────────────────────────

inject_styles()

st.markdown(
    """
    <div class="afp-hero">
      <h1>AFRIPLAN ELECTRICAL · v6.1</h1>
      <p>Independent PDF and DXF pipelines, with cross-pipeline comparison.
      Upload either or both — at least one is required.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── Section 1 — Upload + project metadata ─────────────────────────────

st.subheader("1.  Upload")

upload_cols = st.columns(2)

pdf_file = upload_cols[0].file_uploader(
    "PDF (electrical drawings, multi-page)",
    type=["pdf"],
    key="pdf_upload",
)
dxf_file = upload_cols[1].file_uploader(
    "DXF (CAD geometry)",
    type=["dxf"],
    key="dxf_upload",
)

with st.expander("📋 Project details (optional)", expanded=False):
    meta_cols = st.columns(2)
    project_name   = meta_cols[0].text_input("Project name", "")
    client_name    = meta_cols[0].text_input("Client", "")
    consultant     = meta_cols[1].text_input("Consultant", "")
    site_address   = meta_cols[1].text_input("Site address", "")

with st.expander("🏷  Contractor profile (pricing)", expanded=False):
    profile_cols = st.columns(3)
    markup_pct      = profile_cols[0].number_input("Markup %", 0.0, 100.0, 20.0, 1.0)
    contingency_pct = profile_cols[1].number_input("Contingency %", 0.0, 50.0, 5.0, 1.0)
    vat_pct         = profile_cols[2].number_input("VAT %", 0.0, 25.0, 15.0, 1.0)

with st.expander("🔬 Research / baseline (optional)", expanded=False):
    baseline_choice = st.selectbox(
        "Compare against baseline",
        options=["(none)", "wedela", "trichard"],
        index=0,
    )

api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
if pdf_file and not api_key:
    st.warning(
        "No `ANTHROPIC_API_KEY` set. Add it to `.streamlit/secrets.toml` or "
        "your environment to run the PDF pipeline. The DXF pipeline will run regardless."
    )

run_clicked = st.button(
    "▶  Run pipelines",
    type="primary",
    disabled=(pdf_file is None and dxf_file is None),
    use_container_width=True,
)


# ─── Pipeline orchestration ────────────────────────────────────────────

def _project_meta() -> ProjectMetadata:
    return ProjectMetadata(
        project_name=project_name or "",
        client_name=client_name or "",
        consultant_name=consultant or "",
        site_address=site_address or "",
    )


def _contractor() -> ContractorProfile:
    return ContractorProfile(
        markup_pct=float(markup_pct),
        contingency_pct=float(contingency_pct),
        vat_pct=float(vat_pct),
    )


def _baseline_or_none() -> Optional[str]:
    return None if baseline_choice == "(none)" else baseline_choice


def _run_pdf_pipeline_safely(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """Run the PDF pipeline, never raise — return a dict the UI can render."""
    try:
        if not api_key:
            return {
                "state": "failed",
                "failure_reasons": ["No ANTHROPIC_API_KEY available"],
            }
        run = run_pdf_pipeline(
            file_bytes=file_bytes,
            file_name=file_name,
            api_key=api_key,
            project=_project_meta(),
            contractor=_contractor(),
            baseline_project=_baseline_or_none(),
            persist=True,
        )
        return _pdf_run_to_view(run)
    except Exception as e:                # noqa: BLE001
        logging.exception("PDF pipeline crashed")
        return {"state": "failed", "failure_reasons": [f"Pipeline crashed: {e}"]}


def _run_dxf_pipeline_safely(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    try:
        run = run_dxf_pipeline(
            file_bytes=file_bytes,
            file_name=file_name,
            project=_project_meta(),
            contractor=_contractor(),
            baseline_project=_baseline_or_none(),
            persist=True,
        )
        return _dxf_run_to_view(run)
    except Exception as e:                # noqa: BLE001
        logging.exception("DXF pipeline crashed")
        return {"state": "failed", "failure_reasons": [f"Pipeline crashed: {e}"]}


def _pdf_run_to_view(run) -> Dict[str, Any]:
    boq = run.boq
    downloads: Dict[str, bytes] = {}
    if boq is not None:
        downloads["pdf_boq.xlsx"] = export_boq_to_excel(boq)
        downloads["pdf_boq.pdf"]  = export_boq_to_pdf(boq)
    downloads["pdf_eval.json"] = json.dumps(
        run.evaluation.model_dump(), default=str, indent=2
    ).encode("utf-8")

    return {
        "state": "passed" if run.success else "failed",
        "score": run.evaluation.overall_score,
        "score_components": {
            "Confidence":  run.evaluation.mean_confidence,
            "Consistency": run.evaluation.consistency_score,
            "Regression":  (1 - run.evaluation.baseline_mape) if run.evaluation.baseline_mape is not None else 1.0,
        },
        "total_excl_vat": boq.total_excl_vat_zar if boq else None,
        "duration_s":     run.duration_s,
        "cost_zar":       run.cost_zar,
        "failure_reasons": run.evaluation.failure_reasons,
        "downloads":       downloads,
        "eval_json":       run.evaluation.model_dump(),
        "boq":             boq,
        "raw_run":         run,
    }


def _dxf_run_to_view(run) -> Dict[str, Any]:
    boq = run.boq
    downloads: Dict[str, bytes] = {}
    if boq is not None:
        downloads["dxf_boq.xlsx"] = export_boq_to_excel(boq)
        downloads["dxf_boq.pdf"]  = export_boq_to_pdf(boq)
    downloads["dxf_eval.json"] = json.dumps(
        run.evaluation.model_dump(), default=str, indent=2
    ).encode("utf-8")

    return {
        "state": "passed" if run.success else "failed",
        "score": run.evaluation.overall_score,
        "score_components": {
            "Coverage":   run.evaluation.coverage_score,
            "Regression": (1 - run.evaluation.baseline_mape) if run.evaluation.baseline_mape is not None else 1.0,
        },
        "total_excl_vat": boq.total_excl_vat_zar if boq else None,
        "duration_s":     run.duration_s,
        "cost_zar":       run.cost_zar,
        "failure_reasons": run.evaluation.failure_reasons,
        "downloads":       downloads,
        "eval_json":       run.evaluation.model_dump(),
        "boq":             boq,
        "raw_run":         run,
    }


# ─── Run on click ──────────────────────────────────────────────────────

if run_clicked:
    pdf_view: Optional[Dict[str, Any]] = None
    dxf_view: Optional[Dict[str, Any]] = None

    pdf_bytes = pdf_file.read() if pdf_file else None
    pdf_name  = pdf_file.name if pdf_file else None
    dxf_bytes = dxf_file.read() if dxf_file else None
    dxf_name  = dxf_file.name if dxf_file else None

    # Run both in parallel
    with ThreadPoolExecutor(max_workers=2) as ex:
        future_pdf = ex.submit(_run_pdf_pipeline_safely, pdf_bytes, pdf_name) if pdf_bytes else None
        future_dxf = ex.submit(_run_dxf_pipeline_safely, dxf_bytes, dxf_name) if dxf_bytes else None

        with st.spinner("Running pipelines in parallel…"):
            if future_pdf is not None:
                pdf_view = future_pdf.result()
            if future_dxf is not None:
                dxf_view = future_dxf.result()

    st.session_state["pdf_view"] = pdf_view
    st.session_state["dxf_view"] = dxf_view


# ─── Section 2 — Results, two columns ──────────────────────────────────

st.subheader("2.  Results")

result_cols = st.columns(2)

with result_cols[0]:
    pdf_view = st.session_state.get("pdf_view")
    if pdf_view is None:
        render_pipeline_column(pipeline_label="PDF pipeline", state="idle")
    else:
        render_pipeline_column(pipeline_label="PDF pipeline", **{k: v for k, v in pdf_view.items() if k not in ("boq", "raw_run")})

with result_cols[1]:
    dxf_view = st.session_state.get("dxf_view")
    if dxf_view is None:
        render_pipeline_column(pipeline_label="DXF pipeline", state="idle")
    else:
        render_pipeline_column(pipeline_label="DXF pipeline", **{k: v for k, v in dxf_view.items() if k not in ("boq", "raw_run")})


# ─── Section 3 — Comparison (only if both ran successfully) ────────────

if pdf_view and dxf_view and pdf_view.get("state") == "passed" and dxf_view.get("state") == "passed":
    st.subheader("3.  Cross-pipeline comparison")
    try:
        from agent.comparison import compare_runs, render_comparison_panel
        comparison = compare_runs(pdf_run=pdf_view["raw_run"], dxf_run=dxf_view["raw_run"])
        render_comparison_panel(comparison)
    except Exception as e:                  # noqa: BLE001
        st.info(f"Comparison layer unavailable: {e}")
