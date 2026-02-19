"""
AfriPlan Electrical v4.2 - Welcome Page
Professional landing page with card-based design
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import (
    hero_section,
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

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# ============================================
# MAIN CTA CARD
# ============================================
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(0,212,255,0.05));
            border: 2px solid rgba(0,212,255,0.4); border-radius: 24px;
            padding: 3rem; text-align: center; margin: 1rem 0 2rem 0;
            box-shadow: 0 8px 32px rgba(0,212,255,0.15);">
    <div style="font-size: 3.5rem; margin-bottom: 1.5rem;">📄 → 🤖 → 📊</div>
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; margin-bottom: 1rem; font-size: 2rem;">
        Upload. Extract. Export.
    </h2>
    <p style="font-size: 1.15rem; color: #cbd5e1; margin-bottom: 0.5rem; line-height: 1.6;">
        Upload your electrical drawings and let AI extract all quantities automatically.
    </p>
    <p style="font-size: 1rem; color: #94a3b8;">
        Download a ready-to-use Bill of Quantities in Excel.
    </p>
</div>
""", unsafe_allow_html=True)

# Start button
if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
    st.switch_page("pages/1_Smart_Upload.py")

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# ============================================
# HOW IT WORKS - Section Header in Card
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
               letter-spacing: 0.1em; margin-bottom: 0.5rem;">HOW IT WORKS</h2>
    <p style="color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em;">
        3 Simple Steps
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 2.5rem 1.5rem; text-align: center; height: 280px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);
                transition: all 0.3s ease;">
        <div style="width: 80px; height: 80px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 20px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.5rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2.5rem;">📤</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.3rem; margin-bottom: 0.75rem; font-weight: 600;">
            1. UPLOAD
        </h3>
        <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0;">
            Upload your electrical drawings
        </p>
        <p style="color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;">
            PDF or images supported
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 2.5rem 1.5rem; text-align: center; height: 280px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);
                transition: all 0.3s ease;">
        <div style="width: 80px; height: 80px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 20px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.5rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2.5rem;">🤖</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.3rem; margin-bottom: 0.75rem; font-weight: 600;">
            2. EXTRACT
        </h3>
        <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0;">
            AI extracts DBs, circuits, fixtures, cables
        </p>
        <p style="color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;">
            Automatic & intelligent
        </p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 2.5rem 1.5rem; text-align: center; height: 280px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);
                transition: all 0.3s ease;">
        <div style="width: 80px; height: 80px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 20px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.5rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2.5rem;">📥</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.3rem; margin-bottom: 0.75rem; font-weight: 600;">
            3. EXPORT
        </h3>
        <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0;">
            Download Excel BQ
        </p>
        <p style="color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;">
            Fill in your prices
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# ============================================
# WHAT GETS EXTRACTED - Section Header
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
               letter-spacing: 0.1em; margin-bottom: 0.5rem;">WHAT GETS EXTRACTED</h2>
    <p style="color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em;">
        Comprehensive Quantity Take-Off
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.75rem 1rem; text-align: center; height: 200px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 2.5rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.25rem;">DBs</div>
        <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.1em; margin-bottom: 1rem;">Distribution Boards</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.75rem;">
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0; line-height: 1.4;">
                Main breakers, ELCBs, surge protection
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.75rem 1rem; text-align: center; height: 200px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 2.5rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.25rem;">Circuits</div>
        <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.1em; margin-bottom: 1rem;">Full Schedule</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.75rem;">
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0; line-height: 1.4;">
                Cable sizes, breakers, point counts
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.75rem 1rem; text-align: center; height: 200px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 2.5rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.25rem;">Fixtures</div>
        <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.1em; margin-bottom: 1rem;">Lights & Sockets</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.75rem;">
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0; line-height: 1.4;">
                12 light types, 8 socket types
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.75rem 1rem; text-align: center; height: 200px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 2.5rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.25rem;">Cables</div>
        <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.1em; margin-bottom: 1rem;">Site Runs</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.75rem;">
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0; line-height: 1.4;">
                Lengths, trenching requirements
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# ============================================
# SANS COMPLIANCE - Card
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
               letter-spacing: 0.1em; margin-bottom: 0.5rem;">SANS 10142-1 COMPLIANCE</h2>
    <p style="color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em;">
        Automatic Validation
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
            border: 1px solid rgba(34,197,94,0.3); border-radius: 20px;
            padding: 2rem; margin: 0 0 2rem 0;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);">
    <div style="display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;">
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.75rem 1.25rem; border-radius: 12px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600;">✓ Max 10 points/circuit</span>
        </div>
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.75rem 1.25rem; border-radius: 12px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600;">✓ ELCB mandatory</span>
        </div>
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.75rem 1.25rem; border-radius: 12px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600;">✓ Surge protection</span>
        </div>
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.75rem 1.25rem; border-radius: 12px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600;">✓ 15% spare ways</span>
        </div>
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.75rem 1.25rem; border-radius: 12px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600;">✓ Dedicated circuits</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# ============================================
# AI PROVIDERS - Section Header
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
               letter-spacing: 0.1em; margin-bottom: 0.5rem;">POWERED BY</h2>
    <p style="color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em;">
        Free AI Extraction
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(255,107,53,0.3); border-radius: 16px;
                padding: 2rem 1.5rem 2.5rem 1.5rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="width: 70px; height: 70px; background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,107,53,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.25rem auto; border: 1px solid rgba(255,107,53,0.3);">
            <span style="font-size: 2rem;">🦙</span>
        </div>
        <div style="color: #FF6B35; font-weight: 700; font-size: 1.1rem; margin-bottom: 1rem;">
            Groq + Llama 4
        </div>
        <div style="background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,107,53,0.1));
                    padding: 0.6rem 1.25rem; border-radius: 10px; border: 1px solid rgba(255,107,53,0.3);
                    display: inline-block;">
            <span style="color: #FF6B35; font-size: 0.9rem; font-weight: 700;">100% FREE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(66,133,244,0.3); border-radius: 16px;
                padding: 2rem 1.5rem 2.5rem 1.5rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="width: 70px; height: 70px; background: linear-gradient(135deg, rgba(66,133,244,0.2), rgba(66,133,244,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.25rem auto; border: 1px solid rgba(66,133,244,0.3);">
            <span style="font-size: 2rem;">🔷</span>
        </div>
        <div style="color: #4285F4; font-weight: 700; font-size: 1.1rem; margin-bottom: 1rem;">
            Google Gemini
        </div>
        <div style="background: linear-gradient(135deg, rgba(66,133,244,0.2), rgba(66,133,244,0.1));
                    padding: 0.6rem 1.25rem; border-radius: 10px; border: 1px solid rgba(66,133,244,0.3);
                    display: inline-block;">
            <span style="color: #4285F4; font-size: 0.9rem; font-weight: 700;">FREE Tier</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(139,92,246,0.3); border-radius: 16px;
                padding: 2rem 1.5rem 2.5rem 1.5rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="width: 70px; height: 70px; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1.25rem auto; border: 1px solid rgba(139,92,246,0.3);">
            <span style="font-size: 2rem;">🤖</span>
        </div>
        <div style="color: #8B5CF6; font-weight: 700; font-size: 1.1rem; margin-bottom: 1rem;">
            Claude AI
        </div>
        <div style="background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1));
                    padding: 0.6rem 1.25rem; border-radius: 10px; border: 1px solid rgba(139,92,246,0.3);
                    display: inline-block;">
            <span style="color: #8B5CF6; font-size: 0.9rem; font-weight: 700;">Paid Option</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# ============================================
# FOOTER
# ============================================
premium_footer()
