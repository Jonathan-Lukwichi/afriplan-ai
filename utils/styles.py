"""
AfriPlan Electrical - Premium Futuristic Dark-Tech Styles
ViperFi-inspired design with glassmorphism, glow effects, and animations
"""

import streamlit as st

CUSTOM_CSS = """
<style>
    /* ========================================
       FONTS - Futuristic Typography
    ======================================== */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

    /* ========================================
       GLOBAL BACKGROUND - Animated Grid
    ======================================== */
    .stApp {
        background:
            radial-gradient(ellipse at 20% 50%, rgba(6, 182, 212, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(245, 158, 11, 0.04) 0%, transparent 50%),
            linear-gradient(180deg, #0a0e1a 0%, #0f172a 50%, #0a0e1a 100%) !important;
        background-attachment: fixed !important;
    }

    /* Animated Grid Overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            linear-gradient(rgba(6, 182, 212, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.03) 1px, transparent 1px);
        background-size: 60px 60px;
        pointer-events: none;
        z-index: 0;
        animation: gridShift 20s linear infinite;
    }

    @keyframes gridShift {
        0% { transform: translateY(0); }
        100% { transform: translateY(60px); }
    }

    /* ========================================
       FLOATING GLOW ORBS
    ======================================== */
    .glow-orb {
        position: fixed;
        border-radius: 50%;
        filter: blur(80px);
        opacity: 0.4;
        pointer-events: none;
        animation: float 15s ease-in-out infinite;
        z-index: 0;
    }

    .glow-orb-1 {
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(6,182,212,0.15), transparent);
        top: 10%; left: 5%;
    }

    .glow-orb-2 {
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(245,158,11,0.1), transparent);
        bottom: 20%; right: 10%;
        animation-delay: -7s;
    }

    @keyframes float {
        0%, 100% { transform: translate(0, 0); }
        33% { transform: translate(30px, -20px); }
        66% { transform: translate(-20px, 15px); }
    }

    /* ========================================
       TYPOGRAPHY HIERARCHY
    ======================================== */
    h1, h2, h3, .section-title {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }

    h4, h5, h6, .label, .metric-label {
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        color: #94a3b8 !important;
    }

    p, li, span, .body-text, .stMarkdown {
        font-family: 'Inter', sans-serif !important;
        color: #cbd5e1 !important;
        line-height: 1.7 !important;
    }

    /* ========================================
       HERO SECTION
    ======================================== */
    .hero-section {
        position: relative;
        min-height: 50vh;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 3rem 2rem;
        overflow: hidden;
    }

    .hero-badge {
        display: inline-block;
        padding: 8px 20px;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 50px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #f59e0b;
        background: rgba(245, 158, 11, 0.05);
        margin-bottom: 1.5rem;
        animation: fadeInDown 0.8s ease-out;
    }

    .hero-title {
        font-family: 'Orbitron', sans-serif !important;
        font-size: clamp(2rem, 5vw, 4rem) !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin-bottom: 1rem !important;
        background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 3s linear infinite, fadeInUp 1s ease-out;
    }

    @keyframes shimmer {
        0% { background-position: 0% center; }
        100% { background-position: 200% center; }
    }

    .hero-subtitle {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 1.2rem !important;
        color: #94a3b8 !important;
        text-transform: uppercase !important;
        letter-spacing: 3px !important;
        margin-bottom: 1rem !important;
    }

    .hero-description {
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        color: #64748b !important;
        max-width: 600px !important;
        margin: 0 auto 2rem !important;
    }

    .hero-stats {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-top: 2rem;
        flex-wrap: wrap;
    }

    .stat-item {
        text-align: center;
        animation: fadeInUp 1s ease-out;
    }

    .stat-number {
        display: block;
        font-family: 'Orbitron', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        color: #06b6d4;
        text-shadow: 0 0 20px rgba(6, 182, 212, 0.3);
    }

    .stat-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #64748b;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ========================================
       GLASSMORPHISM CARDS
    ======================================== */
    .glass-card {
        background: linear-gradient(135deg,
            rgba(17, 24, 39, 0.8),
            rgba(15, 23, 42, 0.6)) !important;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(245, 158, 11, 0.1) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .glass-card::before {
        content: '';
        position: absolute;
        top: 0; left: 10%; right: 10%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #f59e0b, transparent);
        border-radius: 2px;
    }

    .glass-card:hover {
        border-color: rgba(245, 158, 11, 0.3) !important;
        box-shadow:
            0 0 30px rgba(245, 158, 11, 0.08),
            0 20px 60px rgba(0, 0, 0, 0.3) !important;
        transform: translateY(-4px);
    }

    .glass-card::after {
        content: '';
        position: absolute;
        top: 8px; right: 8px;
        width: 20px; height: 20px;
        border-top: 2px solid rgba(6, 182, 212, 0.4);
        border-right: 2px solid rgba(6, 182, 212, 0.4);
        border-radius: 0 8px 0 0;
    }

    /* ========================================
       TIER CARDS
    ======================================== */
    .tier-card {
        background: linear-gradient(135deg,
            rgba(17, 24, 39, 0.9),
            rgba(15, 23, 42, 0.7)) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(30, 41, 59, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        min-height: 200px;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative;
        overflow: hidden;
    }

    .tier-card::before {
        content: '';
        position: absolute;
        top: 0; left: 20%; right: 20%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #f59e0b, transparent);
    }

    .tier-card:hover {
        border-color: rgba(245, 158, 11, 0.5) !important;
        box-shadow:
            0 0 40px rgba(245, 158, 11, 0.15),
            0 20px 60px rgba(0, 0, 0, 0.4) !important;
        transform: translateY(-6px) !important;
    }

    .tier-card h3 {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #f59e0b, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.8rem !important;
    }

    .tier-card p {
        font-family: 'Inter', sans-serif !important;
        color: #94a3b8 !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }

    .tier-icon {
        width: 56px; height: 56px;
        background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(6,182,212,0.15));
        border: 1px solid rgba(245, 158, 11, 0.2);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        margin-bottom: 1rem;
    }

    .tier-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 1rem;
    }

    .tag {
        padding: 4px 10px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-radius: 4px;
        color: #06b6d4;
        background: rgba(6, 182, 212, 0.05);
    }

    /* ========================================
       METRIC CARDS
    ======================================== */
    .metric-card {
        background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6)) !important;
        border: 1px solid rgba(245, 158, 11, 0.15) !important;
        border-radius: 12px !important;
        padding: 1.2rem !important;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 30%; right: 30%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #06b6d4, transparent);
    }

    .metric-value {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #f59e0b !important;
        text-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
    }

    .metric-label {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        color: #64748b !important;
        margin-top: 0.3rem;
    }

    /* Streamlit Metrics Override */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6)) !important;
        border: 1px solid rgba(245, 158, 11, 0.1) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 1.8rem !important;
        color: #f59e0b !important;
    }

    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        color: #64748b !important;
    }

    /* ========================================
       SECTION HEADERS
    ======================================== */
    .section-header {
        text-align: center;
        padding: 2rem 0 1.5rem;
    }

    .section-line {
        width: 60px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #f59e0b, transparent);
        margin: 0 auto 1rem;
    }

    .section-title {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 4px !important;
        background: linear-gradient(135deg, #f1f5f9, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
    }

    .section-subtitle {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 14px !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }

    /* ========================================
       TIMELINE - How It Works
    ======================================== */
    .timeline {
        display: flex;
        justify-content: space-between;
        position: relative;
        padding: 2rem 0;
        margin: 1rem 0;
    }

    .timeline::before {
        content: '';
        position: absolute;
        top: 32px;
        left: 10%; right: 10%;
        height: 2px;
        background: linear-gradient(90deg,
            #f59e0b, #06b6d4, #f59e0b, #06b6d4, #f59e0b);
        background-size: 200% 100%;
        animation: lineFlow 4s linear infinite;
    }

    @keyframes lineFlow {
        0% { background-position: 0% 0; }
        100% { background-position: 200% 0; }
    }

    .timeline-step {
        position: relative;
        text-align: center;
        flex: 1;
        z-index: 1;
    }

    .step-number {
        width: 48px; height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: #0a0e1a;
        font-family: 'Orbitron', sans-serif;
        font-weight: 800;
        font-size: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.8rem;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
    }

    .step-title {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #f1f5f9;
    }

    .step-desc {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
    }

    /* ========================================
       BUTTONS
    ======================================== */
    .stButton > button {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important;
        color: #0a0e1a !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 28px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3) !important;
        position: relative;
        overflow: hidden;
    }

    .stButton > button:hover {
        box-shadow: 0 6px 30px rgba(245, 158, 11, 0.5) !important;
        transform: translateY(-2px) !important;
    }

    /* ========================================
       TABS
    ======================================== */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(17, 24, 39, 0.6) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid rgba(30, 41, 59, 0.5) !important;
        gap: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-size: 13px !important;
        border-radius: 8px !important;
        color: #64748b !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #f59e0b, #d97706) !important;
        color: #0a0e1a !important;
        box-shadow: 0 2px 12px rgba(245, 158, 11, 0.3) !important;
    }

    /* ========================================
       INPUTS
    ======================================== */
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input {
        background: rgba(17, 24, 39, 0.8) !important;
        border: 1px solid rgba(30, 41, 59, 0.8) !important;
        border-radius: 8px !important;
        color: #f1f5f9 !important;
        font-family: 'Inter', sans-serif !important;
        transition: border-color 0.3s ease !important;
    }

    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus {
        border-color: #f59e0b !important;
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15) !important;
    }

    .stSelectbox label,
    .stNumberInput label,
    .stTextInput label {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 12px !important;
        color: #94a3b8 !important;
    }

    /* ========================================
       SIDEBAR
    ======================================== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #070b14 0%, #0d1224 100%) !important;
        border-right: 1px solid rgba(30, 41, 59, 0.5) !important;
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Orbitron', sans-serif !important;
        background: linear-gradient(135deg, #f59e0b, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ========================================
       BQ TABLE
    ======================================== */
    .bq-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }

    .bq-table th {
        background: rgba(17, 24, 39, 0.9);
        color: #f59e0b;
        padding: 12px;
        text-align: left;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 2px solid rgba(245, 158, 11, 0.2);
    }

    .bq-table td {
        padding: 10px 12px;
        border-bottom: 1px solid rgba(30, 41, 59, 0.5);
        color: #cbd5e1;
    }

    .bq-table tr:hover td {
        background: rgba(245, 158, 11, 0.05);
    }

    /* ========================================
       ALERTS & TOASTS
    ======================================== */
    .success-toast {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        animation: slideIn 0.5s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    /* Streamlit info/success/warning boxes */
    .stAlert {
        background: rgba(17, 24, 39, 0.8) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(30, 41, 59, 0.5) !important;
    }

    /* ========================================
       LOADING ANIMATION
    ======================================== */
    .loading-pulse {
        display: flex;
        gap: 8px;
        justify-content: center;
        padding: 2rem;
    }

    .loading-pulse span {
        width: 12px; height: 12px;
        border-radius: 50%;
        background: #f59e0b;
        animation: pulse 1.4s ease-in-out infinite;
    }

    .loading-pulse span:nth-child(2) { animation-delay: 0.2s; }
    .loading-pulse span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes pulse {
        0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
        40% { transform: scale(1); opacity: 1; }
    }

    /* ========================================
       FOOTER
    ======================================== */
    .premium-footer {
        text-align: center;
        padding: 2rem;
        margin-top: 2rem;
        border-top: 1px solid rgba(30, 41, 59, 0.5);
    }

    .premium-footer p {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 12px !important;
        color: #475569 !important;
        letter-spacing: 1px !important;
    }

    .premium-footer .brand {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 700 !important;
        color: #f59e0b !important;
    }

    /* ========================================
       QUOTE OPTIONS CARDS
    ======================================== */
    .quote-option {
        background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(15,23,42,0.7)) !important;
        border: 2px solid rgba(30, 41, 59, 0.5) !important;
        border-radius: 12px !important;
        padding: 1.2rem !important;
        transition: all 0.3s ease !important;
    }

    .quote-option:hover {
        border-color: rgba(245, 158, 11, 0.4) !important;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.1) !important;
    }

    .quote-option.recommended {
        border-color: #10b981 !important;
        background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(17,24,39,0.9)) !important;
    }

    /* ========================================
       MAIN HEADER (Legacy Support)
    ======================================== */
    .main-header {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.9), rgba(15, 23, 42, 0.7)) !important;
        backdrop-filter: blur(12px);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid rgba(245, 158, 11, 0.1);
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: 0; left: 10%; right: 10%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #f59e0b, transparent);
    }

    .main-header h1 {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #f59e0b, #fbbf24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 0.5rem 0 !important;
    }

    .main-header p {
        font-family: 'Rajdhani', sans-serif !important;
        color: #64748b !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        margin: 0 !important;
    }

    /* ========================================
       EXPANDER STYLING
    ======================================== */
    .streamlit-expanderHeader {
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        background: rgba(17, 24, 39, 0.6) !important;
        border-radius: 8px !important;
    }

    /* ========================================
       DIVIDERS
    ======================================== */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.3), transparent) !important;
        margin: 1.5rem 0 !important;
    }

</style>

<!-- Glow Orbs HTML -->
<div class="glow-orb glow-orb-1"></div>
<div class="glow-orb glow-orb-2"></div>
"""


def inject_custom_css():
    """Inject premium futuristic CSS styles into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
