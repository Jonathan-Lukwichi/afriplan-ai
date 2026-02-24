"""
AfriPlan Electrical v4.11 — Main Application

SA Electrical Quotation Platform - Quantity Take-Off Accelerator

Two upload modes:
- Smart Upload: Fast automated extraction (38% accuracy with Llama 4)
- Guided Upload: Step-by-step extraction with user validation (70%+ target)

v4.11 Pipeline:
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

# Define pages (v4.2 - simplified to 3 pages)
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

guided_upload = st.Page(
    "pages/6_Guided_Upload.py",
    title="Guided Upload",
    icon="📋"
)

profile = st.Page(
    "pages/5_Profile.py",
    title="Settings",
    icon="⚙️"
)

# Navigation (v4.11 - with Guided Upload)
pg = st.navigation({
    "Main": [welcome, smart_upload, guided_upload],
    "Settings": [profile],
})

# Run the selected page
pg.run()
