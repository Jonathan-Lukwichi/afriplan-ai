"""
AfriPlan Electrical - Welcome Page
Platform overview and navigation hub
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css

inject_custom_css()

# Hero Header
st.markdown("""
<div class="main-header">
    <h1>AfriPlan Electrical</h1>
    <p>South Africa's Complete Electrical Quotation Platform</p>
</div>
""", unsafe_allow_html=True)

# About Section
st.markdown("---")

col_about1, col_about2 = st.columns([2, 1])

with col_about1:
    st.markdown("""
    ## About AfriPlan Electrical

    AfriPlan Electrical is a comprehensive quotation platform designed specifically for the
    **South African electrical industry**. Whether you're an electrical contractor, consulting
    engineer, or project estimator, our platform helps you generate accurate, professional
    quotations in minutes.

    **Built for South Africa** with local pricing, SANS compliance, and industry standards.
    """)

with col_about2:
    st.markdown("""
    ### Who It's For

    - Electrical Contractors
    - Consulting Engineers
    - Project Estimators
    - Quantity Surveyors
    - Municipal Planners
    """)

st.markdown("---")

# Key Features
st.markdown("## Platform Features")

feat1, feat2, feat3, feat4 = st.columns(4)

with feat1:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">4</div>
        <div class="metric-label">Quote Strategies</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    **Smart Cost Optimizer**
    - Budget Friendly
    - Best Value
    - Premium Quality
    - Competitive Bid
    """)

with feat2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">5+</div>
        <div class="metric-label">SA Standards</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    **SANS Compliance**
    - SANS 10142
    - NRS 034
    - MHSA
    - Eskom DSD
    - SANS 10098
    """)

with feat3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">PDF</div>
        <div class="metric-label">Professional Export</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    **PDF Quotations**
    - Detailed Bill of Quantities
    - VAT Calculations
    - Terms & Conditions
    - Company Branding
    """)

with feat4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">2025</div>
        <div class="metric-label">Updated Pricing</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    **SA Market Rates**
    - Material Prices
    - Labour Rates
    - Municipal Fees
    - COC Costs
    """)

st.markdown("---")

# Project Tiers
st.markdown("## Select Your Project Tier")
st.markdown("Choose the sector that matches your project:")

tier1, tier2 = st.columns(2)

with tier1:
    st.markdown("""
    <div class="tier-card">
        <h3>Residential</h3>
        <p>New house construction, renovations, solar & backup power, COC compliance,
        smart home automation, security systems, EV charging installations</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("SANS 10142 compliant | COC ready | Solar & battery sizing")

with tier2:
    st.markdown("""
    <div class="tier-card">
        <h3>Commercial</h3>
        <p>Office buildings, retail & shopping centres, hotels & restaurants,
        healthcare facilities, schools & educational institutions</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("Load studies | Emergency power | Fire detection | Access control")

tier3, tier4 = st.columns(2)

with tier3:
    st.markdown("""
    <div class="tier-card">
        <h3>Industrial</h3>
        <p>Mining (surface & underground), factories & manufacturing plants,
        warehouses & distribution, agricultural, substations & HV installations</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("MHSA compliant | MCC design | MV/HV equipment | Motor loads")

with tier4:
    st.markdown("""
    <div class="tier-card">
        <h3>Infrastructure</h3>
        <p>Township electrification, rural electrification, street lighting,
        mini-grids & microgrids, utility-scale solar installations</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("NRS 034 | SANS 10098 | Eskom DSD | Grid connection")

st.markdown("---")

# How It Works
st.markdown("## How It Works")

step1, step2, step3, step4, step5 = st.columns(5)

with step1:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">1</div>
        <div class="metric-label">Select Tier</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Choose Residential, Commercial, Industrial, or Infrastructure")

with step2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">2</div>
        <div class="metric-label">Configure</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Enter project parameters and specifications")

with step3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">3</div>
        <div class="metric-label">Calculate</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("View electrical requirements and load analysis")

with step4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">4</div>
        <div class="metric-label">Optimize</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Compare 4 quotation strategies")

with step5:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-value">5</div>
        <div class="metric-label">Export</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Download professional PDF quotation")

st.markdown("---")

# Get Started CTA
st.markdown("## Ready to Start?")
st.markdown("Use the **sidebar navigation** to select your project tier and begin creating your quotation.")

st.success("Select a page from the sidebar to get started!")

st.markdown("---")

# Footer
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 12px; padding: 20px;">
    <strong>AfriPlan Electrical</strong> | Built for South Africa<br>
    Accurate Quotations | SANS Compliant | Professional PDFs<br>
    <br>
    2025 | Powered by Streamlit
</div>
""", unsafe_allow_html=True)
