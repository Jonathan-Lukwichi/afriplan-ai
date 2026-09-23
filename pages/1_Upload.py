"""
AfriPlan v6.1 — Step 1: Choose source & upload.

DECISION: choose the source FIRST (PDF or DXF), then upload only that
pipeline's inputs. The two pipelines run SEPARATELY on their own result
pages — there is no cross-comparison here.

    PDF path → a SET of drawing PDFs (SLD + layouts + register)  → PDF estimator
    DXF path → one DXF (CAD geometry)                            → DXF pipeline
"""

from __future__ import annotations

import streamlit as st

from agent.shared import ContractorProfile, ProjectMetadata
from ui.components import footer, page_header, rule
from ui.styles import inject_styles


inject_styles()


page_header(
    step="STEP 1 OF 3",
    title="Choose your source",
    subtitle=(
        "Pick how you want to extract the Bill of Quantities. Each source runs "
        "its own pipeline independently — pick one to begin."
    ),
)


# ─── Source choice ───────────────────────────────────────────────────

source = st.session_state.get("source")

st.markdown('<div class="afp-eyebrow">SOURCE</div>', unsafe_allow_html=True)
choice_cols = st.columns(2)
with choice_cols[0]:
    if st.button("📄  PDF drawings", use_container_width=True,
                 type="primary" if source == "pdf" else "secondary"):
        source = "pdf"
        st.session_state.source = "pdf"
    st.caption("Vision estimator · SLD + layouts + register · reads schedules & notes")
with choice_cols[1]:
    if st.button("📐  DXF / CAD", use_container_width=True,
                 type="primary" if source == "dxf" else "secondary"):
        source = "dxf"
        st.session_state.source = "dxf"
    st.caption("Deterministic CAD parser · exact block counts · R 0.00 to run")


rule()


# ─── PDF path — multi-file uploader ──────────────────────────────────

def _continue_pdf(files) -> None:
    """Capture bytes for each uploaded PDF (read() is one-shot) and advance."""
    file_set = [(f.read(), f.name) for f in files]
    st.session_state.pdf_file_set = file_set
    st.session_state.source = "pdf"
    st.session_state.pop("pdf_run", None)      # clear any previous run
    st.session_state.pop("pdf_view", None)
    _ensure_defaults()
    st.switch_page("pages/2_Extraction.py")


def _continue_dxf(dxf) -> None:
    st.session_state.dxf_bytes = dxf.read()
    st.session_state.dxf_name = dxf.name
    st.session_state.source = "dxf"
    st.session_state.pop("dxf_view", None)
    _ensure_defaults()
    st.switch_page("pages/2_Extraction.py")


def _ensure_defaults() -> None:
    st.session_state.setdefault("project_meta", ProjectMetadata())
    st.session_state.setdefault("contractor_profile", ContractorProfile())
    st.session_state.setdefault("baseline_choice", "(none)")


if source == "pdf":
    st.markdown('<div class="afp-eyebrow">PDF DRAWING SET</div>', unsafe_allow_html=True)
    files = st.file_uploader(
        "Upload every PDF for this project — SLD, layouts, register, schedules",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_files",
        help="Drop the whole set at once. The estimator classifies each file "
             "(SLD → power spine, layout → take-off, register → context).",
    )
    if files:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        for f in files:
            st.markdown(
                f'<span class="afp-chip">📄 {f.name}</span>',
                unsafe_allow_html=True,
            )
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        cta = st.columns([1, 1, 1])
        with cta[1]:
            if st.button("Continue to Extraction  →", type="primary",
                         use_container_width=True, key="pdf_continue"):
                _continue_pdf(files)
    else:
        st.info("Upload at least one PDF to continue.")


# ─── DXF path — single-file uploader ─────────────────────────────────

elif source == "dxf":
    st.markdown('<div class="afp-eyebrow">DXF FILE</div>', unsafe_allow_html=True)
    dxf = st.file_uploader(
        "Upload your DXF or DWG export (AutoCAD / ArchiCAD)",
        type=["dxf", "dwg"],
        key="dxf_file_single",
        help="The DXF pipeline is deterministic — exact block counts and cable "
             "lengths, no API cost. DWG files are auto-converted (needs the ODA "
             "File Converter installed).",
    )
    if dxf is not None:
        st.markdown(
            f'<span class="afp-chip">📐 {dxf.name}</span>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        cta = st.columns([1, 1, 1])
        with cta[1]:
            if st.button("Continue to Extraction  →", type="primary",
                         use_container_width=True, key="dxf_continue"):
                _continue_dxf(dxf)
    else:
        st.info("Upload a DXF file to continue.")


else:
    st.info("Choose **PDF drawings** or **DXF / CAD** above to begin.")


footer()
