"""
Renders one pipeline's status column: header, score, totals, downloads.

Both PDF and DXF columns use this — the pipeline name is a parameter
and the column reads only the public BillOfQuantities + per-pipeline
evaluation summary, never internals.
"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, Optional

import streamlit as st


def _tag_html(label: str, kind: str) -> str:
    return f'<span class="afp-tag afp-tag-{kind}">{label}</span>'


def render_pipeline_column(
    *,
    pipeline_label: str,
    state: str,                            # "idle" | "running" | "passed" | "failed"
    score: Optional[float] = None,         # 0..1 overall score
    score_components: Optional[Dict[str, float]] = None,
    total_excl_vat: Optional[float] = None,
    duration_s: Optional[float] = None,
    cost_zar: Optional[float] = None,
    failure_reasons: Optional[list[str]] = None,
    downloads: Optional[Dict[str, bytes]] = None,   # name → bytes
    eval_json: Optional[Any] = None,
) -> None:
    """Render a single pipeline column in the UI."""
    tag_kind = {
        "idle": "idle",
        "running": "running",
        "passed": "pass",
        "failed": "fail",
    }.get(state, "idle")
    tag_label = state.upper()

    container = st.container()
    with container:
        st.markdown(
            f"""
            <div class="afp-pipeline-card">
              <h3>{pipeline_label} {_tag_html(tag_label, tag_kind)}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if state == "idle":
            st.info("Upload an input file and click **Run pipelines**.")
            return

        if state == "running":
            st.markdown("⏳  Running…")
            return

        # Either passed or failed — show metrics
        cols = st.columns(4)
        if score is not None:
            cols[0].markdown(_metric("Score", f"{int(round(score * 100))}%"), unsafe_allow_html=True)
        if total_excl_vat is not None:
            cols[1].markdown(
                _metric("Total excl VAT", f"R {total_excl_vat:,.0f}"),
                unsafe_allow_html=True,
            )
        if duration_s is not None:
            cols[2].markdown(_metric("Time", f"{duration_s:.1f}s"), unsafe_allow_html=True)
        if cost_zar is not None:
            cols[3].markdown(_metric("Cost", f"R {cost_zar:.2f}"), unsafe_allow_html=True)

        if score_components:
            st.markdown("**Component scores**")
            comp_cols = st.columns(len(score_components))
            for i, (k, v) in enumerate(score_components.items()):
                comp_cols[i].markdown(
                    _metric(k, f"{int(round(v * 100))}%"),
                    unsafe_allow_html=True,
                )

        if state == "failed" and failure_reasons:
            st.error("Pipeline gate failed:\n\n- " + "\n- ".join(failure_reasons))

        if downloads:
            st.markdown("**Downloads**")
            for name, data in downloads.items():
                st.download_button(
                    label=f"📥 {name}",
                    data=data,
                    file_name=name,
                    key=f"dl_{pipeline_label}_{name}",
                )

        if eval_json is not None:
            with st.expander("📋 Evaluation JSON"):
                st.code(json.dumps(eval_json, indent=2, default=str), language="json")


def _metric(label: str, value: str) -> str:
    return (
        '<div class="afp-metric">'
        f'<span class="afp-metric-label">{label}</span>'
        f'<span class="afp-metric-value">{value}</span>'
        "</div>"
    )
