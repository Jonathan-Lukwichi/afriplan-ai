"""
AfriPlan Electrical v6.1 — Welcome / landing page.

Minimal: hero, four value cards, four-step "How it works" strip,
Start Here CTA. The CTA pushes the user to the Upload page.
"""

from __future__ import annotations

import streamlit as st

from ui.components import footer, hero, page_header, rule, step_strip, value_cards
from ui.styles import inject_styles


inject_styles()


# ─── Hero ────────────────────────────────────────────────────────────

hero(
    eyebrow="AFRIPLAN ELECTRICAL · v6.1",
    title_html=(
        "Tender-grade electrical "
        '<span class="afp-accent">Bills of Quantities</span>, '
        "extracted from your drawings."
    ),
    subtitle=(
        "Upload an electrical PDF, a DXF, or both. Two independent pipelines "
        "produce a SANS 10142-1:2017 compliant BOQ — exact counts from CAD geometry, "
        "schedule data from vision LLM. Built for South African contractors and "
        "consulting engineers preparing tenders."
    ),
)


# ─── Value cards ─────────────────────────────────────────────────────

value_cards([
    (
        "⚡",
        "Zero-cost DXF extraction",
        "Deterministic ezdxf parser. Exact block counts, exact cable lengths. "
        "Runs offline, no API calls, R 0.00 per project.",
    ),
    (
        "🤖",
        "AI-powered PDF reading",
        "Anthropic Claude with strict tool-use schemas reads schedules, "
        "single-line diagrams, and layout drawings. Confidence-scored.",
    ),
    (
        "🏗️",
        "SANS-compliant BOQ output",
        "14-section tender format. SANS 10142-1, NRS 034, SANS 10400-XA "
        "compliance declarations. Excel + signed PDF, ready for submission.",
    ),
    (
        "📊",
        "Dual-pipeline cross-check",
        "When both PDF and DXF run, you get a side-by-side comparison "
        "and an MAPE score against any baseline you choose to maintain.",
    ),
])


rule(strong=True)


# ─── How it works ───────────────────────────────────────────────────

st.markdown(
    '<div class="afp-eyebrow">HOW IT WORKS</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<h2 class="afp-h1" style="margin-top:6px;margin-bottom:14px;">'
    "Four steps from drawing to tender."
    "</h2>",
    unsafe_allow_html=True,
)

step_strip([
    ("1", "Upload",      "Drop in your electrical PDF and / or DXF, plus project and contractor info."),
    ("2", "Extract",     "Run both pipelines in parallel. Watch live confidence + coverage scores."),
    ("3", "Review",      "Read the cross-pipeline comparison. Pick the BOQ that best matches your project."),
    ("4", "Export BOQ",  "Generate a tender-ready SANS-compliant Excel and signed PDF in one click."),
])


rule()


# ─── Start Here CTA ─────────────────────────────────────────────────

cta_cols = st.columns([1, 1, 1])
with cta_cols[1]:
    if st.button("Start Here  →", type="primary", use_container_width=True, key="welcome_cta"):
        st.switch_page("pages/1_Upload.py")

st.markdown(
    '<p style="text-align:center;color:var(--ink-muted);font-size:12.5px;'
    'margin-top:10px;font-family:var(--mono);letter-spacing:.1em;">'
    "BLUEPRINT v6.1 · DUAL-PIPELINE · SOUTH AFRICAN ELECTRICAL STANDARD"
    "</p>",
    unsafe_allow_html=True,
)


footer()
