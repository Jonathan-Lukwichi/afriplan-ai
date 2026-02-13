"""
AfriPlan Electrical v3.0 - Main Application
SA Electrical Quotation Platform - 3 Service Tiers
Uses Streamlit's modern navigation API for reliable multipage support

v3.0 Changes:
- Simplified to 3 tiers: Residential, Commercial, Maintenance/COC
- Industrial and Infrastructure deprecated (scope refocus)
- Added AI Agent pipeline integration
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define all pages using st.Page (v3.0 - 3 tiers)
welcome = st.Page(
    "pages/0_Welcome.py",
    title="Welcome",
    default=True
)

smart_upload = st.Page(
    "pages/5_Smart_Upload.py",
    title="Smart Upload"
)

residential = st.Page(
    "pages/1_Residential.py",
    title="Residential"
)

commercial = st.Page(
    "pages/2_Commercial.py",
    title="Commercial"
)

maintenance = st.Page(
    "pages/3_Maintenance.py",
    title="Maintenance & COC"
)

# Create navigation with 3 active tiers (v3.0)
# Industrial and Infrastructure removed - scope refocus
pg = st.navigation(
    [welcome, smart_upload, residential, commercial, maintenance],
    position="sidebar"
)

# Run the selected page
pg.run()
