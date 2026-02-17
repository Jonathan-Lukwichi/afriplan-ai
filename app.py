"""
AfriPlan Electrical v4.1 — Main Application

SA Electrical Quotation Platform - Quantity Take-Off Accelerator
Uses Streamlit's modern navigation API for reliable multipage support.

v4.1 Philosophy:
- AI extracts quantities, contractor reviews/corrects
- Contractor applies their own prices (not auto-generated)
- Primary output: Quantity-only BQ
- Secondary output: Estimated BQ (reference only)

Pipeline: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define all pages using st.Page (v4.1 - 7-stage workflow)
welcome = st.Page(
    "pages/0_Welcome.py",
    title="Welcome",
    icon="🏠",
    default=True
)

smart_upload = st.Page(
    "pages/1_Smart_Upload.py",
    title="Smart Upload",
    icon="📤"
)

# v4.1: New workflow pages
profile = st.Page(
    "pages/5_Profile.py",
    title="Contractor Profile",
    icon="👤"
)

review = st.Page(
    "pages/6_Review.py",
    title="Review & Edit",
    icon="✏️"
)

site_conditions = st.Page(
    "pages/7_Site_Conditions.py",
    title="Site Conditions",
    icon="🏗️"
)

results = st.Page(
    "pages/8_Results.py",
    title="Results",
    icon="📊"
)

# Legacy tier pages (kept for backwards compatibility)
residential = st.Page(
    "pages/2_Residential.py",
    title="Residential (Legacy)",
    icon="🏡"
)

commercial = st.Page(
    "pages/3_Commercial.py",
    title="Commercial (Legacy)",
    icon="🏢"
)

maintenance = st.Page(
    "pages/4_Maintenance.py",
    title="Maintenance (Legacy)",
    icon="🔧"
)

# Navigation sections
pg = st.navigation({
    "AI Workflow": [welcome, smart_upload, review, site_conditions, results],
    "Settings": [profile],
    "Legacy": [residential, commercial, maintenance],
})

# Run the selected page
pg.run()
