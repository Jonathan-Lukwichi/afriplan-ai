"""
AfriPlan v6.1 — Step 1: Upload.

This page only collects inputs. It does NOT run pipelines (that happens
on the Extraction page). On click of "Continue to Extraction" we capture
file bytes + metadata into st.session_state and switch the page.

The contractor profile is loaded from / saved to ~/.afriplan/profile.json
so the user doesn't re-enter their company info on every visit.
"""

from __future__ import annotations

import streamlit as st

from agent.shared import ContractorProfile, ProjectMetadata
from agent.shared.contractor_io import (
    default_profile_path,
    load_contractor_profile,
    save_contractor_profile,
)
from ui.components import footer, page_header, rule
from ui.styles import inject_styles


inject_styles()


# ─── Page header ─────────────────────────────────────────────────────

page_header(
    step="STEP 1 OF 3",
    title="Upload electrical drawings",
    subtitle=(
        "Provide your project documents and contractor details. "
        "At least one of PDF or DXF is required — both is best."
    ),
)


# ─── Upload area ─────────────────────────────────────────────────────

st.markdown('<div class="afp-eyebrow">DRAWINGS</div>', unsafe_allow_html=True)

upload_cols = st.columns(2)
pdf_file = upload_cols[0].file_uploader(
    "Electrical PDF (multi-page)",
    type=["pdf"],
    key="pdf_upload",
    help="Multi-page PDF: title sheet, single-line diagrams, schedules, layouts.",
)
dxf_file = upload_cols[1].file_uploader(
    "DXF (CAD geometry)",
    type=["dxf"],
    key="dxf_upload",
    help="DXF export from AutoCAD or ArchiCAD. R 0.00 to extract.",
)


# ─── Project metadata ────────────────────────────────────────────────

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
st.markdown('<div class="afp-eyebrow">PROJECT</div>', unsafe_allow_html=True)

with st.expander("Project details (optional but recommended)", expanded=False):
    meta_cols = st.columns(2)
    project_name = meta_cols[0].text_input(
        "Project name",
        value=st.session_state.get("project_name", ""),
        placeholder="Wedela Recreational Club",
    )
    client_name = meta_cols[0].text_input(
        "Client",
        value=st.session_state.get("client_name", ""),
    )
    consultant = meta_cols[1].text_input(
        "Consultant",
        value=st.session_state.get("consultant", ""),
    )
    site_address = meta_cols[1].text_input(
        "Site address",
        value=st.session_state.get("site_address", ""),
    )


# ─── Contractor profile ──────────────────────────────────────────────

if "contractor_profile" not in st.session_state:
    st.session_state.contractor_profile = load_contractor_profile()
profile: ContractorProfile = st.session_state.contractor_profile

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
st.markdown('<div class="afp-eyebrow">CONTRACTOR PROFILE</div>', unsafe_allow_html=True)

label = "Saved contractor profile" if profile.company_name else "Set up contractor profile"
with st.expander(label, expanded=not bool(profile.company_name)):
    c1, c2 = st.columns(2)
    profile.company_name = c1.text_input(
        "Company name",
        value=profile.company_name,
        placeholder="JLW Analytics (Pty) Ltd",
    )
    profile.registration_number = c2.text_input(
        "ECSA / CIDB number",
        value=profile.registration_number,
    )
    profile.contact_name = c1.text_input("Contact person", value=profile.contact_name)
    profile.contact_phone = c2.text_input("Contact phone", value=profile.contact_phone)
    profile.contact_email = c1.text_input("Contact email", value=profile.contact_email)
    profile.vat_number = c2.text_input("VAT number", value=profile.vat_number)
    profile.physical_address = st.text_input(
        "Physical address",
        value=profile.physical_address,
    )

    st.markdown(
        '<div style="height:6px"></div>'
        '<div class="afp-eyebrow">PRICING DEFAULTS</div>',
        unsafe_allow_html=True,
    )
    p1, p2, p3 = st.columns(3)
    profile.markup_pct = p1.number_input(
        "Markup %", min_value=0.0, max_value=100.0,
        value=float(profile.markup_pct), step=1.0,
    )
    profile.contingency_pct = p2.number_input(
        "Contingency %", min_value=0.0, max_value=50.0,
        value=float(profile.contingency_pct), step=1.0,
    )
    profile.vat_pct = p3.number_input(
        "VAT %", min_value=0.0, max_value=25.0,
        value=float(profile.vat_pct), step=0.5,
    )
    profile.payment_terms = st.selectbox(
        "Payment terms",
        options=["40/40/20", "50/30/20", "30/30/30/10"],
        index=["40/40/20", "50/30/20", "30/30/30/10"].index(profile.payment_terms)
        if profile.payment_terms in ("40/40/20", "50/30/20", "30/30/30/10") else 0,
    )

    save_col, status_col = st.columns([1, 3])
    if save_col.button("💾  Save profile"):
        path = save_contractor_profile(profile)
        if path:
            status_col.success(
                f"Profile saved to `{path}` — your details will pre-fill next time."
            )
        else:
            status_col.warning(
                f"Could not write to `{default_profile_path()}` — your changes are kept for this session only."
            )


# ─── Baseline selector ──────────────────────────────────────────────

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
st.markdown('<div class="afp-eyebrow">RESEARCH (OPTIONAL)</div>', unsafe_allow_html=True)
with st.expander("Compare against a baseline", expanded=False):
    baseline_choice = st.selectbox(
        "Baseline",
        options=["(none)", "wedela", "trichard", "example"],
        index=["(none)", "wedela", "trichard", "example"].index(
            st.session_state.get("baseline_choice", "(none)")
        ),
        help="When set, both pipelines compute a MAPE score against `baselines/<name>.json`.",
    )


rule()


# ─── Continue button ────────────────────────────────────────────────

st.markdown('<div class="afp-eyebrow">READY?</div>', unsafe_allow_html=True)

both_missing = pdf_file is None and dxf_file is None
if both_missing:
    st.info("Upload at least one file (PDF or DXF) to continue.")

cta_cols = st.columns([1, 1, 1])
with cta_cols[1]:
    if st.button(
        "Continue to Extraction  →",
        type="primary",
        use_container_width=True,
        disabled=both_missing,
        key="continue_to_extraction",
    ):
        # Capture bytes BEFORE switching page — UploadedFile.read() is one-shot
        if pdf_file is not None:
            st.session_state.pdf_bytes = pdf_file.read()
            st.session_state.pdf_name = pdf_file.name
        else:
            st.session_state.pdf_bytes = None
            st.session_state.pdf_name = None

        if dxf_file is not None:
            st.session_state.dxf_bytes = dxf_file.read()
            st.session_state.dxf_name = dxf_file.name
        else:
            st.session_state.dxf_bytes = None
            st.session_state.dxf_name = None

        # Project metadata
        st.session_state.project_name = project_name
        st.session_state.client_name = client_name
        st.session_state.consultant = consultant
        st.session_state.site_address = site_address
        st.session_state.project_meta = ProjectMetadata(
            project_name=project_name,
            client_name=client_name,
            consultant_name=consultant,
            site_address=site_address,
        )

        # Contractor + baseline
        st.session_state.contractor_profile = profile
        st.session_state.baseline_choice = baseline_choice

        # Clear any old extraction results so the next page knows to re-run
        st.session_state.pdf_view = None
        st.session_state.dxf_view = None

        st.switch_page("pages/2_Extraction.py")


footer()
