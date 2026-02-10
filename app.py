"""
AfriPlan Electrical - Home Page
SA Electrical Quotation Platform - All Sectors
"""

import streamlit as st
from utils.styles import inject_custom_css

st.set_page_config(
    page_title="AfriPlan Electrical",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# Header
st.markdown("""
<div class="main-header">
    <h1>⚡ AfriPlan Electrical</h1>
    <p>SA Electrical Quotation Platform - Residential | Commercial | Industrial | Infrastructure</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Welcome message
st.markdown("""
### Welcome to AfriPlan Electrical

South Africa's comprehensive electrical quotation platform covering **ALL** sectors:
- **Residential**: New builds, renovations, solar, security, EV charging
- **Commercial**: Offices, retail, hospitality, healthcare, education
- **Industrial**: Mining, manufacturing, warehouses, substations
- **Infrastructure**: Township electrification, rural, street lighting, utility solar

---

### Select a Tier to Get Started

Navigate using the sidebar or click one of the options below:
""")

# Tier selection cards
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="tier-card">
        <h3>🏠 Residential</h3>
        <p>New house construction, renovations, solar & backup power, COC compliance, smart home, security systems, EV charging</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Residential →", key="res", use_container_width=True):
        st.switch_page("pages/1_Residential.py")

with col2:
    st.markdown("""
    <div class="tier-card">
        <h3>🏢 Commercial</h3>
        <p>Office buildings, retail & shopping, hotels & restaurants, healthcare facilities, schools & educational</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Commercial →", key="com", use_container_width=True):
        st.switch_page("pages/2_Commercial.py")

col3, col4 = st.columns(2)

with col3:
    st.markdown("""
    <div class="tier-card">
        <h3>🏭 Industrial</h3>
        <p>Mining (surface & underground), factories & manufacturing, warehouses, agricultural, substations & HV</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Industrial →", key="ind", use_container_width=True):
        st.switch_page("pages/3_Industrial.py")

with col4:
    st.markdown("""
    <div class="tier-card">
        <h3>🌍 Infrastructure</h3>
        <p>Township electrification, rural electrification, street lighting, mini-grids, utility-scale solar</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Go to Infrastructure →", key="inf", use_container_width=True):
        st.switch_page("pages/4_Infrastructure.py")

st.markdown("---")

# Features summary
st.markdown("### Platform Features")

feat_col1, feat_col2, feat_col3, feat_col4 = st.columns(4)

with feat_col1:
    st.markdown("""
    **📊 Smart Cost Optimizer**

    4 quotation strategies:
    - Budget Friendly
    - Best Value ⭐
    - Premium Quality
    - Competitive Bid
    """)

with feat_col2:
    st.markdown("""
    **📋 SANS Compliance**

    Standards supported:
    - SANS 10142
    - NRS 034
    - MHSA
    - Eskom DSD
    """)

with feat_col3:
    st.markdown("""
    **📄 PDF Export**

    Professional quotes:
    - Detailed BQ
    - VAT calculations
    - Terms & conditions
    - Branding ready
    """)

with feat_col4:
    st.markdown("""
    **💰 SA Pricing**

    2024/2025 prices:
    - Materials
    - Labour rates
    - Municipal fees
    - COC costs
    """)

st.markdown("---")

# Footer
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 12px;">
    AfriPlan Electrical © 2025 | Built for South Africa 🇿🇦
</div>
""", unsafe_allow_html=True)
