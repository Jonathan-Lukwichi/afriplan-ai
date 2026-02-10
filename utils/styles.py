"""
AfriPlan Electrical - Custom CSS Styles
"""

import streamlit as st

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');

    .stApp { background-color: #0B1120; }

    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 24px 30px;
        border-radius: 12px;
        border-left: 4px solid #F59E0B;
        margin-bottom: 24px;
    }
    .main-header h1 {
        color: #F59E0B;
        font-size: 28px;
        font-weight: 800;
        margin: 0;
    }
    .main-header p {
        color: #94A3B8;
        font-size: 14px;
        margin: 4px 0 0;
    }

    .metric-card {
        background: #1E293B;
        border-radius: 10px;
        padding: 16px;
        border-top: 3px solid #F59E0B;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #F59E0B;
    }
    .metric-label {
        font-size: 12px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .bq-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .bq-table th {
        background: #1E293B;
        color: #F59E0B;
        padding: 10px;
        text-align: left;
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .bq-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #1E293B;
        color: #CBD5E1;
    }
    .bq-table tr:hover td {
        background: #1E293B44;
    }

    .section-title {
        color: #F59E0B;
        font-size: 18px;
        font-weight: 700;
        margin: 20px 0 10px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #1E293B;
    }

    .tier-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .tier-card:hover {
        border-color: #F59E0B;
        transform: translateY(-2px);
    }
    .tier-card h3 {
        color: #F59E0B;
        margin: 0 0 10px 0;
    }
    .tier-card p {
        color: #94A3B8;
        margin: 0;
        font-size: 14px;
    }

    .quote-option {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 2px solid;
    }
    .quote-option.recommended {
        border-color: #22C55E;
        background: rgba(34, 197, 94, 0.1);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1E293B;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background: #F59E0B !important;
        color: #0F172A !important;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #0F172A;
    }

    /* Input styling */
    .stNumberInput input, .stSelectbox select, .stTextInput input {
        background-color: #1E293B !important;
        color: #E2E8F0 !important;
        border-color: #334155 !important;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: #0F172A;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #FBBF24 0%, #F59E0B 100%);
    }
</style>
"""

def inject_custom_css():
    """Inject custom CSS styles into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
