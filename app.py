"""
AfriPlan Electrical v1.0 — Main Application

SA Electrical Quotation Platform - Quantity Take-Off Accelerator

Primary Mode:
- Smart Upload: Step-by-step extraction with human validation (75%+ target)

v1.0 Pipeline:
INGEST → CLASSIFY → DISCOVER (Multi-Pass) → VALIDATE → PRICE → OUTPUT
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages (v1.0 - Smart Upload only)
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

boq_simulator = st.Page(
    "pages/5_BOQ_Simulator.py",
    title="BOQ Simulator",
    icon="🔧"
)

# Navigation
pg = st.navigation([welcome, smart_upload, boq_simulator])

# Run the selected page
pg.run()
