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
# MOBILE-SPECIFIC CSS OVERRIDES
# ============================================
st.markdown("""
<style>
    /* Mobile responsive cards */
    @media screen and (max-width: 640px) {
        .mobile-card {
            height: auto !important;
            min-height: unset !important;
            padding: 1.25rem !important;
        }
        .mobile-card h3 {
            font-size: 1rem !important;
        }
        .mobile-card p {
            font-size: 0.85rem !important;
        }
        .mobile-icon {
            width: 60px !important;
            height: 60px !important;
        }
        .mobile-icon span {
            font-size: 1.75rem !important;
        }
        .cta-card {
            padding: 1.5rem 1rem !important;
        }
        .cta-card h2 {
            font-size: 1.3rem !important;
        }
        .cta-card .emoji-flow {
            font-size: 2rem !important;
        }
        .section-title h2 {
            font-size: 1.1rem !important;
        }
        .advantage-card {
            padding: 1.25rem !important;
        }
        .advantage-card h3 {
            font-size: 0.95rem !important;
        }
        .advantage-icon {
            width: 40px !important;
            height: 40px !important;
            min-width: 40px !important;
        }
        .advantage-icon span {
            font-size: 1.25rem !important;
        }
        .provider-card {
            padding: 1.25rem 1rem !important;
        }
        .provider-icon {
            width: 50px !important;
            height: 50px !important;
        }
        .provider-icon span {
            font-size: 1.5rem !important;
        }
        .compliance-tag {
            padding: 0.5rem 0.75rem !important;
            font-size: 0.75rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

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
<div class="cta-card" style="background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(0,212,255,0.05));
            border: 2px solid rgba(0,212,255,0.4); border-radius: 24px;
            padding: 2.5rem 1.5rem; text-align: center; margin: 1rem 0 2rem 0;
            box-shadow: 0 8px 32px rgba(0,212,255,0.15);">
    <div class="emoji-flow" style="font-size: 2.5rem; margin-bottom: 1rem;">📄 → 🤖 → 📊</div>
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; margin-bottom: 0.75rem; font-size: 1.5rem;">
        Upload. Extract. Export.
    </h2>
    <p style="font-size: 1rem; color: #cbd5e1; margin-bottom: 0.5rem; line-height: 1.5;">
        Upload your electrical drawings and let AI extract all quantities automatically.
    </p>
    <p style="font-size: 0.9rem; color: #94a3b8;">
        Download a ready-to-use Bill of Quantities in Excel.
    </p>
</div>
""", unsafe_allow_html=True)

# Start button
if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
    st.switch_page("pages/1_Smart_Upload.py")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

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
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 1.5rem 1rem; text-align: center; min-height: 220px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div class="mobile-icon" style="width: 60px; height: 60px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2rem;">📤</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.1rem; margin-bottom: 0.5rem; font-weight: 600;">
            1. UPLOAD
        </h3>
        <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.4; margin-bottom: 0;">
            Upload your electrical drawings
        </p>
        <p style="color: #64748b; font-size: 0.8rem; margin-top: 0.25rem;">
            PDF or images supported
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 1.5rem 1rem; text-align: center; min-height: 220px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div class="mobile-icon" style="width: 60px; height: 60px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2rem;">🤖</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.1rem; margin-bottom: 0.5rem; font-weight: 600;">
            2. EXTRACT
        </h3>
        <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.4; margin-bottom: 0;">
            AI extracts DBs, circuits, fixtures, cables
        </p>
        <p style="color: #64748b; font-size: 0.8rem; margin-top: 0.25rem;">
            Automatic & intelligent
        </p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 20px;
                padding: 1.5rem 1rem; text-align: center; min-height: 220px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div class="mobile-icon" style="width: 60px; height: 60px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                    border-radius: 16px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 1rem auto; border: 1px solid rgba(0,212,255,0.3);">
            <span style="font-size: 2rem;">📥</span>
        </div>
        <h3 style="color: #00D4FF; font-size: 1.1rem; margin-bottom: 0.5rem; font-weight: 600;">
            3. EXPORT
        </h3>
        <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.4; margin-bottom: 0;">
            Download Excel BQ
        </p>
        <p style="color: #64748b; font-size: 0.8rem; margin-top: 0.25rem;">
            Fill in your prices
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

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
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.25rem 0.75rem; text-align: center; min-height: 160px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 1.75rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.15rem;">DBs</div>
        <div style="color: #64748b; font-size: 0.65rem; text-transform: uppercase;
                    letter-spacing: 0.05em; margin-bottom: 0.75rem;">Distribution Boards</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.5rem;">
            <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.3;">
                Main breakers, ELCBs, surge protection
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.25rem 0.75rem; text-align: center; min-height: 160px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 1.75rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.15rem;">Circuits</div>
        <div style="color: #64748b; font-size: 0.65rem; text-transform: uppercase;
                    letter-spacing: 0.05em; margin-bottom: 0.75rem;">Full Schedule</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.5rem;">
            <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.3;">
                Cable sizes, breakers, point counts
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.25rem 0.75rem; text-align: center; min-height: 160px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 1.75rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.15rem;">Fixtures</div>
        <div style="color: #64748b; font-size: 0.65rem; text-transform: uppercase;
                    letter-spacing: 0.05em; margin-bottom: 0.75rem;">Lights & Sockets</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.5rem;">
            <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.3;">
                12 light types, 8 socket types
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="mobile-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
                padding: 1.25rem 0.75rem; text-align: center; min-height: 160px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="font-size: 1.75rem; color: #00D4FF; font-family: 'Orbitron', sans-serif;
                    font-weight: 700; margin-bottom: 0.15rem;">Cables</div>
        <div style="color: #64748b; font-size: 0.65rem; text-transform: uppercase;
                    letter-spacing: 0.05em; margin-bottom: 0.75rem;">Site Runs</div>
        <div style="background: rgba(0,212,255,0.1); border-radius: 8px; padding: 0.5rem;">
            <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; line-height: 1.3;">
                Lengths, trenching requirements
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

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
            border: 1px solid rgba(34,197,94,0.3); border-radius: 16px;
            padding: 1.25rem; margin: 0 0 1.5rem 0;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);">
    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;">
        <div class="compliance-tag" style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600; font-size: 0.8rem;">✓ Max 10 pts/circuit</span>
        </div>
        <div class="compliance-tag" style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600; font-size: 0.8rem;">✓ ELCB mandatory</span>
        </div>
        <div class="compliance-tag" style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600; font-size: 0.8rem;">✓ Surge protection</span>
        </div>
        <div class="compliance-tag" style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600; font-size: 0.8rem;">✓ 15% spare ways</span>
        </div>
        <div class="compliance-tag" style="background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));
                    padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid rgba(34,197,94,0.3);">
            <span style="color: #22C55E; font-weight: 600; font-size: 0.8rem;">✓ Dedicated circuits</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# ============================================
# ADVANTAGES FOR ELECTRICAL ENGINEERS
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h2 style="color: #00D4FF; font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
               letter-spacing: 0.1em; margin-bottom: 0.5rem;">ADVANTAGES FOR ELECTRICAL ENGINEERS</h2>
    <p style="color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em;">
        Why Professionals Choose AfriPlan
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 16px;
                padding: 1.25rem; margin-bottom: 1rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(0,212,255,0.3);">
                <span style="font-size: 1.25rem;">⏱️</span>
            </div>
            <h3 style="color: #00D4FF; font-size: 0.95rem; margin: 0; font-weight: 600;">
                Save 4-8 Hours Per Project
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            Manual quantity take-offs take hours. AI extracts in minutes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 16px;
                padding: 1.25rem; margin-bottom: 1rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(34,197,94,0.3);">
                <span style="font-size: 1.25rem;">✓</span>
            </div>
            <h3 style="color: #22C55E; font-size: 0.95rem; margin: 0; font-weight: 600;">
                Reduce Counting Errors
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            AI provides consistent extraction with confidence scoring.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 16px;
                padding: 1.25rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(245,158,11,0.3);">
                <span style="font-size: 1.25rem;">📋</span>
            </div>
            <h3 style="color: #F59E0B; font-size: 0.95rem; margin: 0; font-weight: 600;">
                Professional BOQ Output
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            14-section Excel BOQs ready for tendering.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 16px;
                padding: 1.25rem; margin-bottom: 1rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(139,92,246,0.3);">
                <span style="font-size: 1.25rem;">🏛️</span>
            </div>
            <h3 style="color: #8B5CF6; font-size: 0.95rem; margin: 0; font-weight: 600;">
                SANS 10142-1 Compliance
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            Auto-validation flags non-compliant items.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(0,212,255,0.25); border-radius: 16px;
                padding: 1.25rem; margin-bottom: 1rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(236,72,153,0.2), rgba(236,72,153,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(236,72,153,0.3);">
                <span style="font-size: 1.25rem;">💰</span>
            </div>
            <h3 style="color: #EC4899; font-size: 0.95rem; margin: 0; font-weight: 600;">
                Win More Tenders
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            Submit faster with accurate quantities.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="advantage-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(255,107,53,0.25); border-radius: 16px;
                padding: 1.25rem;
                box-shadow: 0 4px 24px rgba(0,0,0,0.3);">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <div class="advantage-icon" style="width: 40px; height: 40px; min-width: 40px; background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,107,53,0.1));
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        border: 1px solid rgba(255,107,53,0.3);">
                <span style="font-size: 1.25rem;">🆓</span>
            </div>
            <h3 style="color: #FF6B35; font-size: 0.95rem; margin: 0; font-weight: 600;">
                100% Free
            </h3>
        </div>
        <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.5; margin: 0;">
            Powered by Groq's free Llama 4 API.
        </p>
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
    <div class="provider-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(255,107,53,0.3); border-radius: 16px;
                padding: 1.25rem 1rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div class="provider-icon" style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,107,53,0.1));
                    border-radius: 12px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 0.75rem auto; border: 1px solid rgba(255,107,53,0.3);">
            <span style="font-size: 1.5rem;">🦙</span>
        </div>
        <div style="color: #FF6B35; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.5rem;">
            Groq + Llama 4
        </div>
        <div style="background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,107,53,0.1));
                    padding: 0.4rem 0.75rem; border-radius: 8px; border: 1px solid rgba(255,107,53,0.3);
                    display: inline-block;">
            <span style="color: #FF6B35; font-size: 0.75rem; font-weight: 700;">100% FREE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="provider-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(66,133,244,0.3); border-radius: 16px;
                padding: 1.25rem 1rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div class="provider-icon" style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(66,133,244,0.2), rgba(66,133,244,0.1));
                    border-radius: 12px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 0.75rem auto; border: 1px solid rgba(66,133,244,0.3);">
            <span style="font-size: 1.5rem;">🔷</span>
        </div>
        <div style="color: #4285F4; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.5rem;">
            Google Gemini
        </div>
        <div style="background: linear-gradient(135deg, rgba(66,133,244,0.2), rgba(66,133,244,0.1));
                    padding: 0.4rem 0.75rem; border-radius: 8px; border: 1px solid rgba(66,133,244,0.3);
                    display: inline-block;">
            <span style="color: #4285F4; font-size: 0.75rem; font-weight: 700;">FREE Tier</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="provider-card" style="background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(15,23,42,0.8));
                border: 1px solid rgba(139,92,246,0.3); border-radius: 16px;
                padding: 1.25rem 1rem; text-align: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div class="provider-icon" style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1));
                    border-radius: 12px; display: flex; align-items: center; justify-content: center;
                    margin: 0 auto 0.75rem auto; border: 1px solid rgba(139,92,246,0.3);">
            <span style="font-size: 1.5rem;">🤖</span>
        </div>
        <div style="color: #8B5CF6; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.5rem;">
            Claude AI
        </div>
        <div style="background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1));
                    padding: 0.4rem 0.75rem; border-radius: 8px; border: 1px solid rgba(139,92,246,0.3);
                    display: inline-block;">
            <span style="color: #8B5CF6; font-size: 0.75rem; font-weight: 700;">Paid Option</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# ============================================
# FOOTER
# ============================================
premium_footer()
