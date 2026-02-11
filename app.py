"""
AfriPlan Electrical - Main Application
SA Electrical Quotation Platform - All Sectors
Uses Streamlit's modern navigation API for reliable multipage support
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define all pages using st.Page (no icons to avoid compatibility issues)
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

industrial = st.Page(
    "pages/3_Industrial.py",
    title="Industrial"
)

infrastructure = st.Page(
    "pages/4_Infrastructure.py",
    title="Infrastructure"
)

# Create navigation with all pages
pg = st.navigation(
    [welcome, smart_upload, residential, commercial, industrial, infrastructure],
    position="sidebar"
)

# Run the selected page
pg.run()
