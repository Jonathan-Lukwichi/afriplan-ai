"""
AfriPlan Electrical - Welcome Page
Premium futuristic landing page
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import (
    hero_section,
    section_header,
    tier_card,
    metric_card,
    timeline_steps,
    premium_footer,
)

inject_custom_css()

# ============================================
# HERO SECTION
# ============================================
hero_section(
    title="AFRIPLAN ELECTRICAL",
    subtitle="Complete Electrical Quotation Platform",
    badge_text="Built for South Africa",
    stats=[
        {"value": "4", "label": "Project Tiers"},
        {"value": "5+", "label": "SANS Standards"},
        {"value": "PDF", "label": "Export Ready"},
        {"value": "2025", "label": "SA Pricing"},
    ]
)

st.markdown("---")

# ============================================
# ABOUT SECTION
# ============================================
section_header("About the Platform", "Professional quotations in minutes")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(245,158,11,0.1); border-radius: 16px; padding: 1.5rem;">
        <p style="font-size: 16px; line-height: 1.8; color: #cbd5e1;">
            <strong style="color: #f59e0b;">AfriPlan Electrical</strong> is a comprehensive quotation platform
            designed specifically for the <strong style="color: #06b6d4;">South African electrical industry</strong>.
        </p>
        <p style="margin-top: 1rem; color: #94a3b8;">
            Whether you're an electrical contractor, consulting engineer, or project estimator,
            our platform helps you generate accurate, professional quotations in minutes with
            local pricing, SANS compliance, and industry standards built-in.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(245,158,11,0.1); border-radius: 16px; padding: 1.5rem;">
        <h4 style="color: #f59e0b; font-family: 'Rajdhani', sans-serif; margin-bottom: 1rem;
                   text-transform: uppercase; letter-spacing: 1px;">Who It's For</h4>
        <ul style="list-style: none; padding: 0; margin: 0;">
            <li style="padding: 0.4rem 0; color: #94a3b8;">&#9889; Electrical Contractors</li>
            <li style="padding: 0.4rem 0; color: #94a3b8;">&#9889; Consulting Engineers</li>
            <li style="padding: 0.4rem 0; color: #94a3b8;">&#9889; Project Estimators</li>
            <li style="padding: 0.4rem 0; color: #94a3b8;">&#9889; Quantity Surveyors</li>
            <li style="padding: 0.4rem 0; color: #94a3b8;">&#9889; Municipal Planners</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# FEATURES SECTION
# ============================================
section_header("Platform Features", "Everything you need for electrical quotations")

feat1, feat2, feat3, feat4 = st.columns(4)

with feat1:
    metric_card("4", "Quote Strategies", "amber")
    st.markdown("""
    <div style="text-align: center; margin-top: 0.8rem;">
        <p style="color: #f59e0b; font-weight: 600; font-size: 13px;">Smart Optimizer</p>
        <p style="color: #64748b; font-size: 12px;">Budget / Best Value / Premium / Competitive</p>
    </div>
    """, unsafe_allow_html=True)

with feat2:
    metric_card("5+", "SA Standards", "cyan")
    st.markdown("""
    <div style="text-align: center; margin-top: 0.8rem;">
        <p style="color: #06b6d4; font-weight: 600; font-size: 13px;">SANS Compliant</p>
        <p style="color: #64748b; font-size: 12px;">10142 / NRS 034 / MHSA / Eskom DSD</p>
    </div>
    """, unsafe_allow_html=True)

with feat3:
    metric_card("PDF", "Export", "amber")
    st.markdown("""
    <div style="text-align: center; margin-top: 0.8rem;">
        <p style="color: #f59e0b; font-weight: 600; font-size: 13px;">Professional PDFs</p>
        <p style="color: #64748b; font-size: 12px;">BQ / VAT / Terms / Branding</p>
    </div>
    """, unsafe_allow_html=True)

with feat4:
    metric_card("2025", "Pricing", "cyan")
    st.markdown("""
    <div style="text-align: center; margin-top: 0.8rem;">
        <p style="color: #06b6d4; font-weight: 600; font-size: 13px;">SA Market Rates</p>
        <p style="color: #64748b; font-size: 12px;">Materials / Labour / Municipal</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# PROJECT TIERS SECTION
# ============================================
section_header("Select Your Project Tier", "Choose the sector that matches your project")

tier1, tier2 = st.columns(2)

with tier1:
    tier_card(
        title="Residential",
        description="New house construction, renovations, solar & backup power, COC compliance, smart home automation, security systems, EV charging",
        tags=["SANS 10142", "COC Ready", "Solar"]
    )

with tier2:
    tier_card(
        title="Commercial",
        description="Office buildings, retail & shopping centres, hotels & restaurants, healthcare facilities, schools & educational institutions",
        tags=["Load Studies", "Emergency Power", "Fire Detection"]
    )

st.markdown("<br>", unsafe_allow_html=True)

tier3, tier4 = st.columns(2)

with tier3:
    tier_card(
        title="Industrial",
        description="Mining (surface & underground), factories & manufacturing, warehouses & distribution, agricultural, substations & HV",
        tags=["MHSA", "MCC Design", "MV/HV"]
    )

with tier4:
    tier_card(
        title="Infrastructure",
        description="Township electrification, rural electrification, street lighting, mini-grids & microgrids, utility-scale solar",
        tags=["NRS 034", "SANS 10098", "Eskom DSD"]
    )

st.markdown("---")

# ============================================
# HOW IT WORKS - TIMELINE
# ============================================
section_header("How It Works", "5 simple steps to your professional quotation")

timeline_steps([
    {"number": "1", "title": "Select Tier", "description": "Choose your project sector"},
    {"number": "2", "title": "Configure", "description": "Enter specifications"},
    {"number": "3", "title": "Calculate", "description": "View requirements"},
    {"number": "4", "title": "Optimize", "description": "Compare strategies"},
    {"number": "5", "title": "Export", "description": "Download PDF"},
])

st.markdown("---")

# ============================================
# CTA SECTION
# ============================================
section_header("Ready to Start?", "Use the sidebar to select your project tier")

st.markdown("""
<div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
            border: 1px solid rgba(245,158,11,0.1); border-radius: 16px;
            padding: 2rem; text-align: center;">
    <p style="font-size: 18px; color: #f1f5f9; margin-bottom: 1rem;">
        Navigate using the <strong style="color: #f59e0b;">sidebar menu</strong> to begin creating your quotation.
    </p>
    <p style="color: #64748b;">
        Select Residential, Commercial, Industrial, or Infrastructure to get started.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# FOOTER
# ============================================
premium_footer()
