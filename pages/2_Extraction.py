"""
AfriPlan v6.1 — Step 2: Extraction.

User clicks "Run pipelines" → both pipelines run in a ThreadPoolExecutor.
Results land in two columns. Comparison panel appears below when both
pipelines pass. "Continue to BOQ Generation" CTA is enabled once at
least one pipeline produced a BoQ.
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
from ui.components import footer, page_header, rule
from ui.pipeline_column import render_pipeline_column
from ui.styles import inject_styles

logging.basicConfig(level=logging.INFO)
inject_styles()


# ─── Guard: must come from Upload ────────────────────────────────────

pdf_bytes = st.session_state.get("pdf_bytes")
dxf_bytes = st.session_state.get("dxf_bytes")
project_meta: Optional[ProjectMetadata] = st.session_state.get("project_meta")
contractor: Optional[ContractorProfile] = st.session_state.get("contractor_profile")
baseline_choice: str = st.session_state.get("baseline_choice", "(none)")


page_header(
    step="STEP 2 OF 3",
    title="Extraction & evaluation",
    subtitle=(
        "Both pipelines run in parallel. Watch the live confidence and coverage "
        "scores. Each pipeline produces its own BOQ — choose between them on the "
        "next step."
    ),
)


if pdf_bytes is None and dxf_bytes is None:
    st.warning(
        "No drawings uploaded yet. Go back to **Step 1 — Upload** to provide a PDF and / or DXF."
    )
    if st.button("← Back to Upload", type="primary"):
        st.switch_page("pages/1_Upload.py")
    footer()
    st.stop()


# ─── Job summary (read-only chips) ───────────────────────────────────

chip_html_parts = []
if pdf_bytes:
    chip_html_parts.append(
        f'<span class="afp-chip">PDF · {st.session_state.get("pdf_name") or "input.pdf"}</span>'
    )
if dxf_bytes:
    chip_html_parts.append(
        f'<span class="afp-chip">DXF · {st.session_state.get("dxf_name") or "input.dxf"}</span>'
    )
if project_meta and project_meta.project_name:
    chip_html_parts.append(f'<span class="afp-chip">Project · {project_meta.project_name}</span>')
if contractor and contractor.company_name:
    chip_html_parts.append(f'<span class="afp-chip">Contractor · {contractor.company_name}</span>')
if baseline_choice and baseline_choice != "(none)":
    chip_html_parts.append(f'<span class="afp-chip">Baseline · {baseline_choice}</span>')

if chip_html_parts:
    st.markdown(
        '<div style="margin: -8px 0 18px 0;">' + "".join(chip_html_parts) + "</div>",
        unsafe_allow_html=True,
    )


# ─── API key check (for the PDF pipeline) ────────────────────────────

api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
if pdf_bytes and not api_key:
    st.warning(
        "No `ANTHROPIC_API_KEY` is configured. The DXF pipeline will run "
        "regardless; the PDF pipeline will be skipped. Add the key in "
        "Streamlit Cloud secrets, or in `.streamlit/secrets.toml` locally."
    )


# ─── Pipeline runners ────────────────────────────────────────────────

def _baseline_or_none() -> Optional[str]:
    return None if baseline_choice == "(none)" else baseline_choice


def _run_pdf() -> Dict[str, Any]:
    try:
        if not api_key:
            return {"state": "failed", "failure_reasons": ["No ANTHROPIC_API_KEY available"]}
        run = run_pdf_pipeline(
            file_bytes=pdf_bytes,
            file_name=st.session_state.get("pdf_name") or "input.pdf",
            api_key=api_key,
            project=project_meta or ProjectMetadata(),
            contractor=contractor or ContractorProfile(),
            baseline_project=_baseline_or_none(),
            persist=True,
        )
        return _pdf_run_to_view(run)
    except Exception as e:                # noqa: BLE001
        logging.exception("PDF pipeline crashed")
        return {"state": "failed", "failure_reasons": [f"Pipeline crashed: {e}"]}


def _run_dxf() -> Dict[str, Any]:
    try:
        run = run_dxf_pipeline(
            file_bytes=dxf_bytes,
            file_name=st.session_state.get("dxf_name") or "input.dxf",
            project=project_meta or ProjectMetadata(),
            contractor=contractor or ContractorProfile(),
            baseline_project=_baseline_or_none(),
            persist=True,
        )
        return _dxf_run_to_view(run)
    except Exception as e:                # noqa: BLE001
        logging.exception("DXF pipeline crashed")
        return {"state": "failed", "failure_reasons": [f"Pipeline crashed: {e}"]}


def _pdf_run_to_view(run) -> Dict[str, Any]:
    boq = run.boq
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
        "downloads":       {},   # downloads happen on the BOQ page
        "eval_json":       run.evaluation.model_dump(),
        "boq":             boq,
        "raw_run":         run,
    }


def _dxf_run_to_view(run) -> Dict[str, Any]:
    boq = run.boq
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
        "downloads":       {},
        "eval_json":       run.evaluation.model_dump(),
        "boq":             boq,
        "raw_run":         run,
    }


# ─── Run button ──────────────────────────────────────────────────────

run_cols = st.columns([1, 2, 1])
with run_cols[1]:
    if st.button(
        "▶  Run pipelines",
        type="primary",
        use_container_width=True,
        key="run_pipelines",
    ):
        with ThreadPoolExecutor(max_workers=2) as ex:
            future_pdf = ex.submit(_run_pdf) if pdf_bytes else None
            future_dxf = ex.submit(_run_dxf) if dxf_bytes else None

            with st.spinner("Running pipelines in parallel — DXF finishes first…"):
                st.session_state.pdf_view = future_pdf.result() if future_pdf else None
                st.session_state.dxf_view = future_dxf.result() if future_dxf else None


rule()


# ─── Results section ─────────────────────────────────────────────────

st.markdown('<div class="afp-eyebrow">RESULTS</div>', unsafe_allow_html=True)
st.markdown(
    '<h2 class="afp-h2" style="margin-top:6px;margin-bottom:14px;">'
    "Pipeline outputs"
    "</h2>",
    unsafe_allow_html=True,
)

result_cols = st.columns(2)

pdf_view = st.session_state.get("pdf_view")
dxf_view = st.session_state.get("dxf_view")

with result_cols[0]:
    if pdf_view is None:
        render_pipeline_column(
            pipeline_label="PDF Pipeline" if pdf_bytes else "PDF Pipeline (no input)",
            state="idle",
        )
    else:
        render_pipeline_column(
            pipeline_label="PDF Pipeline",
            **{k: v for k, v in pdf_view.items() if k not in ("boq", "raw_run")},
        )

with result_cols[1]:
    if dxf_view is None:
        render_pipeline_column(
            pipeline_label="DXF Pipeline" if dxf_bytes else "DXF Pipeline (no input)",
            state="idle",
        )
    else:
        render_pipeline_column(
            pipeline_label="DXF Pipeline",
            **{k: v for k, v in dxf_view.items() if k not in ("boq", "raw_run")},
        )


# ─── Comparison ──────────────────────────────────────────────────────

if (
    pdf_view and dxf_view
    and pdf_view.get("state") == "passed"
    and dxf_view.get("state") == "passed"
):
    rule()
    try:
        from agent.comparison import compare_runs, render_comparison_panel
        comparison = compare_runs(pdf_run=pdf_view["raw_run"], dxf_run=dxf_view["raw_run"])
        st.session_state.comparison = comparison
        render_comparison_panel(comparison)
    except Exception as e:                  # noqa: BLE001
        st.info(f"Comparison layer unavailable: {e}")


# ─── Continue button ────────────────────────────────────────────────

at_least_one_passed = (
    (pdf_view and pdf_view.get("state") == "passed") or
    (dxf_view and dxf_view.get("state") == "passed")
)

rule()
nav_cols = st.columns([1, 1, 1])
with nav_cols[0]:
    if st.button("←  Back to Upload", use_container_width=True, key="back_to_upload"):
        st.switch_page("pages/1_Upload.py")

with nav_cols[2]:
    if st.button(
        "Continue to BOQ  →",
        type="primary",
        use_container_width=True,
        disabled=not at_least_one_passed,
        key="continue_to_boq",
    ):
        st.switch_page("pages/3_BOQ_Generation.py")

if (pdf_view or dxf_view) and not at_least_one_passed:
    st.info(
        "Neither pipeline passed its evaluation gate. Review the failure reasons "
        "above, adjust your inputs, and re-run."
    )


footer()
