"""
AfriPlan Electrical v6.1 — entry point.

Single-page app: pages/1_Upload.py owns everything (upload, run, results,
comparison). Per the v6.1 blueprint, there is no tier-specific quotation
page — both pipelines are general-purpose.
"""

import streamlit as st

st.set_page_config(
    page_title="AfriPlan Electrical · v6.1",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

upload = st.Page(
    "pages/1_Upload.py",
    title="Upload",
    icon="📥",
    default=True,
)

pg = st.navigation([upload])
pg.run()
