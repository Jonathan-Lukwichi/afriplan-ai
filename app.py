"""
AfriPlan Electrical v6.1 — entry point.

Four-page flow: Welcome → Upload → Extraction → BOQ Generation.
Each page lives in pages/, registered with st.navigation in order.
"""

import streamlit as st

st.set_page_config(
    page_title="AfriPlan Electrical · v6.1",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

welcome   = st.Page("pages/0_Welcome.py",        title="Welcome",      icon="🏠", default=True)
upload    = st.Page("pages/1_Upload.py",         title="Upload",       icon="📥")
extract   = st.Page("pages/2_Extraction.py",     title="Extraction",   icon="⚙️")
boq_gen   = st.Page("pages/3_BOQ_Generation.py", title="BOQ",          icon="📊")

pg = st.navigation([welcome, upload, extract, boq_gen])
pg.run()
