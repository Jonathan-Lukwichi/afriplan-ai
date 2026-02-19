"""
AfriPlan Electrical v4.2 — Main Application

SA Electrical Quotation Platform - Quantity Take-Off Accelerator
Simplified workflow: Upload → Extract → Export

v4.2 Simplified Pipeline:
INGEST → CLASSIFY → EXTRACT → VALIDATE → OUTPUT

No editing in-app - contractor fills prices in exported Excel file.
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

profile = st.Page(
    "pages/5_Profile.py",
    title="Settings",
    icon="⚙️"
)

# Navigation (v4.2 - simplified)
pg = st.navigation({
    "Main": [welcome, smart_upload],
    "Settings": [profile],
})

# Run the selected page
pg.run()
