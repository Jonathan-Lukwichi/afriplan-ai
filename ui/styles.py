"""
Minimal CSS for v6.1. Premium dark-tech vibe without the 1000-line
monolith we used to ship.
"""

import streamlit as st


_CSS = """
<style>
:root {
  --primary: #00D4FF;
  --primary-dark: #0099FF;
  --bg: #0a0e1a;
  --surface: #111827;
  --surface-2: #1f2937;
  --text: #f1f5f9;
  --text-muted: #94a3b8;
  --success: #22C55E;
  --warning: #F59E0B;
  --danger: #EF4444;
  --border: rgba(255,255,255,0.08);
}

.stApp { background: var(--bg); color: var(--text); }

.afp-hero {
  background: linear-gradient(135deg, rgba(0,212,255,.08), rgba(0,153,255,.04));
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 28px;
  margin-bottom: 22px;
}
.afp-hero h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: .5px;
  color: var(--primary);
}
.afp-hero p {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: 14px;
}

.afp-pipeline-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
}
.afp-pipeline-card h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: var(--text);
}
.afp-pipeline-card .afp-tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  margin-left: 8px;
  letter-spacing: .5px;
  text-transform: uppercase;
}
.afp-tag-pass    { background: rgba(34,197,94,0.15); color: var(--success); }
.afp-tag-fail    { background: rgba(239,68,68,0.15); color: var(--danger); }
.afp-tag-running { background: rgba(245,158,11,0.15); color: var(--warning); }
.afp-tag-idle    { background: rgba(148,163,184,0.10); color: var(--text-muted); }

.afp-metric {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; background: var(--surface-2);
  border-radius: 8px; min-width: 100px;
}
.afp-metric-label { color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }
.afp-metric-value { color: var(--primary); font-size: 18px; font-weight: 600; }

.afp-comparison {
  background: linear-gradient(135deg, rgba(0,212,255,.04), rgba(0,153,255,.02));
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
}

[data-testid="stFileUploader"] {
  background: var(--surface);
  border: 1px dashed var(--border);
  border-radius: 10px;
  padding: 6px;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
