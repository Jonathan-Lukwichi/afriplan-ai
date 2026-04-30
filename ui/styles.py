"""
Blueprint architectural CSS — v6.1.

Off-white paper background, blueprint-blue ink, drafting-grid overlay,
serif headings (Georgia / Fraunces fallback). Cyan circuit accents on
data elements. Designed to read as "tender document" not "AI tool".
"""

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --paper:        #F5F2EA;
  --paper-2:      #EDEAE0;
  --paper-edge:   #E2DDD0;
  --ink:          #0F1B3D;
  --ink-2:        #2A3556;
  --ink-muted:    #6B7280;
  --blueprint:    #1E40AF;
  --blueprint-2:  #1D4ED8;
  --blueprint-3:  #3B82F6;
  --circuit:      #00B8D4;
  --circuit-2:    #00879B;
  --amber:        #B45309;
  --emerald:      #047857;
  --rose:         #B91C1C;
  --hairline:     rgba(15, 27, 61, 0.10);
  --hairline-2:   rgba(15, 27, 61, 0.18);
  --shadow:       0 1px 0 rgba(15,27,61,.04), 0 8px 24px rgba(15,27,61,.06);
  --grid-major:   rgba(30, 64, 175, 0.12);
  --grid-minor:   rgba(30, 64, 175, 0.05);

  --serif:  'Fraunces', 'Georgia', 'Times New Roman', serif;
  --sans:   'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif;
  --mono:   'JetBrains Mono', 'SF Mono', 'Monaco', monospace;
}

/* ── Page + paper background ───────────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 600px at 80% -100px, rgba(30,64,175,0.05), transparent 70%),
    radial-gradient(800px 400px at 0% 100%, rgba(0,184,212,0.04), transparent 60%),
    var(--paper);
  color: var(--ink);
  font-family: var(--sans);
}

/* Drafting-grid overlay only on welcome hero region */
.afp-grid-bg {
  background-image:
    linear-gradient(var(--grid-major) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-major) 1px, transparent 1px),
    linear-gradient(var(--grid-minor) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-minor) 1px, transparent 1px);
  background-size: 80px 80px, 80px 80px, 16px 16px, 16px 16px;
  background-position: -1px -1px, -1px -1px, -1px -1px, -1px -1px;
}

/* ── Headings ──────────────────────────────────────────────────── */
h1, h2, h3, h4, .afp-h, .afp-display {
  font-family: var(--serif);
  color: var(--ink);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.afp-display { font-size: 44px; line-height: 1.1; }
.afp-h1      { font-size: 30px; line-height: 1.2; }
.afp-h2      { font-size: 22px; line-height: 1.25; }

/* Streamlit's own h1/h2/h3 inside markdown */
[data-testid="stMarkdownContainer"] h1 { font-family: var(--serif); color: var(--ink); }
[data-testid="stMarkdownContainer"] h2 { font-family: var(--serif); color: var(--ink); }
[data-testid="stMarkdownContainer"] h3 { font-family: var(--serif); color: var(--ink); font-weight: 600; }

/* ── Hero (used on welcome) ────────────────────────────────────── */
.afp-hero {
  position: relative;
  padding: 56px 48px 48px;
  border: 1px solid var(--hairline-2);
  border-radius: 4px;
  background: var(--paper-2);
  overflow: hidden;
  margin-bottom: 28px;
}
.afp-hero::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(var(--grid-major) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-major) 1px, transparent 1px),
    linear-gradient(var(--grid-minor) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-minor) 1px, transparent 1px);
  background-size: 80px 80px, 80px 80px, 16px 16px, 16px 16px;
  opacity: .55;
  pointer-events: none;
}
.afp-hero-inner { position: relative; z-index: 1; }
.afp-hero-eyebrow {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .25em;
  text-transform: uppercase;
  color: var(--blueprint);
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 10px;
}
.afp-hero-eyebrow::before {
  content: '';
  display: inline-block;
  width: 28px; height: 1px;
  background: var(--blueprint);
}
.afp-hero h1 {
  font-family: var(--serif);
  font-size: 52px;
  line-height: 1.05;
  font-weight: 600;
  color: var(--ink);
  margin: 0 0 14px 0;
  letter-spacing: -0.02em;
}
.afp-hero h1 .afp-accent {
  color: var(--blueprint);
  font-style: italic;
}
.afp-hero p {
  font-size: 16px;
  line-height: 1.55;
  color: var(--ink-2);
  max-width: 620px;
  margin: 0;
}

/* ── Page header (used on inner pages) ─────────────────────────── */
.afp-page-header {
  border-bottom: 2px solid var(--ink);
  padding-bottom: 14px;
  margin-bottom: 22px;
}
.afp-page-header .afp-step {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .25em;
  text-transform: uppercase;
  color: var(--blueprint);
  margin-bottom: 6px;
}
.afp-page-header h1 {
  font-family: var(--serif);
  font-size: 34px;
  line-height: 1.15;
  margin: 0;
  color: var(--ink);
  font-weight: 600;
}
.afp-page-header p {
  margin: 8px 0 0 0;
  color: var(--ink-2);
  font-size: 14px;
  max-width: 720px;
}

/* ── Value cards (welcome page) ────────────────────────────────── */
.afp-card {
  background: #FFFEFA;
  border: 1px solid var(--hairline-2);
  border-radius: 4px;
  padding: 22px 22px 18px;
  height: 100%;
  position: relative;
  box-shadow: var(--shadow);
}
.afp-card .afp-card-icon {
  font-size: 22px;
  margin-bottom: 12px;
  color: var(--blueprint);
}
.afp-card h3 {
  font-family: var(--serif);
  font-size: 18px;
  margin: 0 0 6px 0;
  color: var(--ink);
}
.afp-card p {
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--ink-2);
  margin: 0;
}

/* ── Step strip (How it works) ─────────────────────────────────── */
.afp-step-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  border: 1px solid var(--hairline-2);
  border-radius: 4px;
  background: #FFFEFA;
  margin-top: 12px;
  margin-bottom: 8px;
  overflow: hidden;
}
.afp-step-cell {
  padding: 18px 18px;
  border-right: 1px solid var(--hairline);
  position: relative;
}
.afp-step-cell:last-child { border-right: none; }
.afp-step-cell .afp-step-num {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: .25em;
  color: var(--blueprint);
  margin-bottom: 6px;
  display: block;
}
.afp-step-cell h4 {
  font-family: var(--serif);
  font-size: 15.5px;
  margin: 0 0 4px 0;
  color: var(--ink);
  font-weight: 600;
}
.afp-step-cell p {
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ink-muted);
  margin: 0;
}

/* ── Pipeline result card (extraction page) ────────────────────── */
.afp-pipeline-card {
  background: #FFFEFA;
  border: 1px solid var(--hairline-2);
  border-radius: 4px;
  padding: 20px 22px;
  box-shadow: var(--shadow);
  margin-bottom: 16px;
}
.afp-pipeline-card h3 {
  font-family: var(--serif);
  font-size: 19px;
  margin: 0 0 12px 0;
  color: var(--ink);
  font-weight: 600;
  display: flex; align-items: center; gap: 10px;
}
.afp-pipeline-card .afp-tag {
  display: inline-block;
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 2px;
  letter-spacing: .15em;
  text-transform: uppercase;
}
.afp-tag-pass    { background: rgba(4,120,87,0.10);  color: var(--emerald); border: 1px solid rgba(4,120,87,.25); }
.afp-tag-fail    { background: rgba(185,28,28,0.08); color: var(--rose);    border: 1px solid rgba(185,28,28,.25); }
.afp-tag-running { background: rgba(180,83,9,0.08);  color: var(--amber);   border: 1px solid rgba(180,83,9,.25); }
.afp-tag-idle    { background: rgba(15,27,61,0.04);  color: var(--ink-muted);border: 1px solid var(--hairline-2); }

/* ── Metric cell ───────────────────────────────────────────────── */
.afp-metric {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px;
  background: var(--paper-2);
  border-left: 2px solid var(--blueprint);
  border-radius: 0;
  min-width: 96px;
}
.afp-metric-label {
  color: var(--ink-muted);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: .15em;
}
.afp-metric-value {
  color: var(--ink);
  font-family: var(--serif);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* ── Comparison panel ──────────────────────────────────────────── */
.afp-comparison {
  background: #FFFEFA;
  border: 1px solid var(--hairline-2);
  border-radius: 4px;
  padding: 22px 24px;
  box-shadow: var(--shadow);
}
.afp-comparison::before {
  content: 'CROSS-PIPELINE COMPARISON';
  display: block;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .25em;
  color: var(--blueprint);
  margin-bottom: 10px;
}

/* ── Streamlit overrides ───────────────────────────────────────── */
/* File uploader */
[data-testid="stFileUploader"] {
  background: #FFFEFA;
  border: 1px dashed var(--blueprint);
  border-radius: 4px;
  padding: 8px;
}
[data-testid="stFileUploader"] section { background: transparent; }

/* Inputs */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input,
.stNumberInput input {
  background: #FFFEFA !important;
  color: var(--ink) !important;
  border: 1px solid var(--hairline-2) !important;
  border-radius: 2px !important;
  font-family: var(--sans) !important;
}
[data-baseweb="select"] > div {
  background: #FFFEFA !important;
  border: 1px solid var(--hairline-2) !important;
  border-radius: 2px !important;
}

/* Buttons */
.stButton > button {
  background: var(--ink);
  color: var(--paper);
  border: 1px solid var(--ink);
  border-radius: 2px;
  font-family: var(--sans);
  font-weight: 500;
  letter-spacing: .02em;
  padding: 10px 24px;
  transition: all .15s ease;
}
.stButton > button:hover {
  background: var(--blueprint);
  color: var(--paper);
  border-color: var(--blueprint);
}
.stButton > button:disabled {
  background: var(--paper-edge);
  color: var(--ink-muted);
  border-color: var(--hairline-2);
}

/* Primary button (CTA) */
.stButton > button[kind="primary"] {
  background: var(--blueprint);
  color: var(--paper);
  border: 1px solid var(--blueprint);
  font-weight: 600;
}
.stButton > button[kind="primary"]:hover {
  background: var(--ink);
  border-color: var(--ink);
}

/* Download button styled like outline */
[data-testid="stDownloadButton"] > button {
  background: #FFFEFA;
  color: var(--ink);
  border: 1px solid var(--ink);
}
[data-testid="stDownloadButton"] > button:hover {
  background: var(--ink);
  color: var(--paper);
}

/* Expanders */
[data-testid="stExpander"] {
  background: #FFFEFA;
  border: 1px solid var(--hairline-2) !important;
  border-radius: 4px !important;
  box-shadow: var(--shadow);
}
[data-testid="stExpander"] summary {
  font-family: var(--sans);
  font-weight: 500;
  color: var(--ink);
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--paper-2);
  border-right: 1px solid var(--hairline-2);
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  color: var(--ink-2);
  font-family: var(--sans);
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
  background: var(--blueprint);
  color: var(--paper);
  border-radius: 2px;
}

/* Tables / dataframes */
[data-testid="stDataFrame"] {
  background: #FFFEFA;
  border: 1px solid var(--hairline-2);
  border-radius: 2px;
}

/* Info / warning / error / success boxes */
[data-testid="stAlert"] {
  border-radius: 2px;
  border-left: 3px solid var(--blueprint);
  font-family: var(--sans);
}

/* Code / mono blocks */
code, pre, [data-testid="stCodeBlock"] {
  font-family: var(--mono) !important;
  background: var(--paper-2) !important;
  border: 1px solid var(--hairline-2);
  border-radius: 2px;
  color: var(--ink) !important;
}

/* Footer */
.afp-footer {
  margin-top: 48px;
  padding: 18px 0 24px;
  border-top: 1px solid var(--hairline);
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .15em;
  text-transform: uppercase;
  color: var(--ink-muted);
  text-align: center;
}

/* Section divider */
.afp-rule {
  border: none;
  border-top: 1px solid var(--hairline-2);
  margin: 28px 0;
}
.afp-rule-strong {
  border: none;
  border-top: 2px solid var(--ink);
  margin: 28px 0;
}

/* Eyebrow / label */
.afp-eyebrow {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .25em;
  text-transform: uppercase;
  color: var(--blueprint);
  margin-bottom: 8px;
}

/* Inline chip */
.afp-chip {
  display: inline-block;
  padding: 2px 8px;
  background: var(--paper-2);
  border: 1px solid var(--hairline-2);
  border-radius: 2px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-2);
  margin-right: 6px;
}

/* Hide Streamlit chrome we don't want */
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
