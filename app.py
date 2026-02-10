"""
AfriPlan Electrical - Main Application
SA Electrical Quotation Platform - All Sectors
Uses Streamlit's modern navigation API for reliable multipage support
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define all pages using st.Page with Material Icons
welcome = st.Page(
    "pages/0_Welcome.py",
    title="Welcome",
    icon=":material/home:",
    default=True
)

residential = st.Page(
    "pages/1_Residential.py",
    title="Residential",
    icon=":material/house:"
)

commercial = st.Page(
    "pages/2_Commercial.py",
    title="Commercial",
    icon=":material/business:"
)

industrial = st.Page(
    "pages/3_Industrial.py",
    title="Industrial",
    icon=":material/factory:"
)

infrastructure = st.Page(
    "pages/4_Infrastructure.py",
    title="Infrastructure",
    icon=":material/public:"
)

# Create navigation with all pages
pg = st.navigation(
    [welcome, residential, commercial, industrial, infrastructure],
    position="sidebar"
)

# Run the selected page
pg.run()
