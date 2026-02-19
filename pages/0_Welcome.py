"""
AfriPlan Electrical v4.2 - Welcome Page
Simplified landing page with direct CTA
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import (
    hero_section,
    section_header,
    metric_card,
    premium_footer,
)

inject_custom_css()

# ============================================
# HERO SECTION
# ============================================
hero_section(
    title="AFRIPLAN ELECTRICAL",
    subtitle="AI-Powered Quantity Take-Off",
    badge_text="100% FREE with Groq",
    stats=[
        {"value": "AI", "label": "Extraction"},
        {"value": "SANS", "label": "Compliant"},
        {"value": "Excel", "label": "Export"},
        {"value": "FREE", "label": "Forever"},
    ]
)

st.markdown("---")

# ============================================
# MAIN CTA
# ============================================
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,212,255,0.05));
            border: 2px solid rgba(0,212,255,0.3); border-radius: 20px;
            padding: 2.5rem; text-align: center; margin: 1rem 0 2rem 0;">
    <div style="font-size: 3rem; margin-bottom: 1rem;">📄 → 🤖 → 📊</div>
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; margin-bottom: 1rem;">
        Upload. Extract. Export.
    </h2>
    <p style="font-size: 1.1rem; color: #94a3b8; margin-bottom: 1.5rem;">
        Upload your electrical drawings and let AI extract all quantities automatically.
        <br>Download a ready-to-use Bill of Quantities in Excel.
    </p>
</div>
""", unsafe_allow_html=True)

# Start button
if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
    st.switch_page("pages/1_Smart_Upload.py")

st.markdown("---")

# ============================================
# HOW IT WORKS
# ============================================
section_header("How It Works", "3 simple steps")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 2rem; text-align: center; height: 200px;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">📤</div>
        <h3 style="color: #00D4FF; font-size: 1.2rem; margin-bottom: 0.5rem;">1. Upload</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">
            Upload your electrical drawings (PDF or images)
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 2rem; text-align: center; height: 200px;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🤖</div>
        <h3 style="color: #00D4FF; font-size: 1.2rem; margin-bottom: 0.5rem;">2. Extract</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">
            AI extracts DBs, circuits, fixtures, cables automatically
        </p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 2rem; text-align: center; height: 200px;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">📥</div>
        <h3 style="color: #00D4FF; font-size: 1.2rem; margin-bottom: 0.5rem;">3. Export</h3>
        <p style="color: #94a3b8; font-size: 0.9rem;">
            Download Excel BQ - fill in your prices
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# FEATURES
# ============================================
section_header("What Gets Extracted", "Comprehensive quantity take-off")

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("DBs", "Distribution Boards", "cyan")
    st.caption("Main breakers, ELCBs, surge protection")

with col2:
    metric_card("Circuits", "Full Schedule", "cyan")
    st.caption("Cable sizes, breakers, point counts")

with col3:
    metric_card("Fixtures", "Lights & Sockets", "cyan")
    st.caption("12 light types, 8 socket types")

with col4:
    metric_card("Cables", "Site Runs", "cyan")
    st.caption("Lengths, trenching requirements")

st.markdown("---")

# ============================================
# COMPLIANCE
# ============================================
section_header("SANS 10142-1 Compliance", "Automatic validation")

st.markdown("""
<div style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05));
            border: 1px solid rgba(34,197,94,0.3); border-radius: 12px;
            padding: 1.5rem; margin: 1rem 0;">
    <div style="display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;">
        <span style="background: rgba(34,197,94,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: #22C55E;">
            ✓ Max 10 points/circuit
        </span>
        <span style="background: rgba(34,197,94,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: #22C55E;">
            ✓ ELCB mandatory
        </span>
        <span style="background: rgba(34,197,94,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: #22C55E;">
            ✓ Surge protection
        </span>
        <span style="background: rgba(34,197,94,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: #22C55E;">
            ✓ 15% spare ways
        </span>
        <span style="background: rgba(34,197,94,0.2); padding: 0.5rem 1rem; border-radius: 20px; color: #22C55E;">
            ✓ Dedicated circuits
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# AI PROVIDER INFO
# ============================================
section_header("Powered By", "Free AI extraction")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255,107,53,0.1), rgba(255,107,53,0.05));
                border: 1px solid rgba(255,107,53,0.3); border-radius: 12px;
                padding: 1.5rem; text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🦙</div>
        <div style="color: #FF6B35; font-weight: 700;">Groq + Llama 4</div>
        <div style="color: #94a3b8; font-size: 0.85rem;">100% FREE</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(66,133,244,0.1), rgba(66,133,244,0.05));
                border: 1px solid rgba(66,133,244,0.3); border-radius: 12px;
                padding: 1.5rem; text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🔷</div>
        <div style="color: #4285F4; font-weight: 700;">Google Gemini</div>
        <div style="color: #94a3b8; font-size: 0.85rem;">FREE tier</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(139,92,246,0.1), rgba(139,92,246,0.05));
                border: 1px solid rgba(139,92,246,0.3); border-radius: 12px;
                padding: 1.5rem; text-align: center;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🤖</div>
        <div style="color: #8B5CF6; font-weight: 700;">Claude</div>
        <div style="color: #94a3b8; font-size: 0.85rem;">Paid option</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================
# FOOTER
# ============================================
premium_footer()
