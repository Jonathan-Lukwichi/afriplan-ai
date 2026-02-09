# 🏗️ AfriPlan AI — South African Architecture AI Platform (Prototype)

A Maket.ai-style floorplan generator built with Streamlit, specifically designed for the South African housing context — with SA material prices, local building typologies, and English interface.

## What This Prototype Does

1.  **🏠 Floorplan Generation** — Input plot dimensions and room requirements → AI generates multiple layout variations using constraint-based space partitioning
2.  **📊 Bill of Quantities (BQ)** — Automatically calculates material quantities (bricks, cement, roof sheeting, rebar, etc.) based on the generated plan
3.  **💰 Cost Estimation** — Prices everything using real South African market rates (Gauteng) in ZAR
4.  **📄 PDF Export** — Generate a professional quote document with floorplan and full BQ table

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

## How to Use

1.  **Configure your plot** in the sidebar (width × length in meters)
2.  **Choose a house preset** or customize rooms manually
3.  **Click "GENERATE PLANS"** to generate multiple variations
4.  **Review the plans** — compare layouts, check room dimensions
5.  **Check the BQ tab** — see all materials and costs calculated automatically
6.  **Export to PDF** — download a professional quote document

## Technical Architecture

```
┌─────────────────────────────────────────────┐
│                  FRONTEND                    │
│            Streamlit (Python)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Sidebar  │  │  Plans   │  │  BQ/PDF  │  │
│  │  Config   │  │  Viewer  │  │  Export   │  │
│  └──────────┘  └──────────┘  └──────────┘  │
├─────────────────────────────────────────────┤
│               AI ENGINE                      │
│  ┌──────────────────────────────────────┐   │
│  │  FloorplanGenerator                  │   │
│  │  - Recursive space partitioning      │   │
│  │  - Constraint satisfaction           │   │
│  │  - Multi-variation generation        │   │
│  └──────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│             DATA LAYER                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Room     │  │  SA      │  │  BQ      │  │
│  │  Presets  │  │Materials │  │Calculator│  │
│  └──────────┘  └──────────┘  └──────────┘  │
├─────────────────────────────────────────────┤
│             OUTPUT                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Matplotlib│  │   HTML   │  │  FPDF2   │  │
│  │  Plots   │  │  Tables  │  │  Export   │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

## Roadmap: Prototype → Production

| Phase | What | Technology |
|-------|------|-----------|
| ✅ Current | Algorithmic layout generation | Python, constraint-based |
| 🔜 Phase 2 | GAN-based generation | PyTorch, trained on South African floorplans |
| 🔜 Phase 3 | 3D visualization | Three.js, React |
| 🔜 Phase 4 | Natural language input | Large Language Model API, English NLP |
| 🔜 Phase 5 | Full-stack SaaS | Next.js + FastAPI + PostgreSQL |

## About

Built by **JLWanalytics** — Africa's Premier Data Refinery
Prototype for AfriPlan AI platform targeting the South African market.

---
*This is a prototype demonstrating the concept. Production version would include ML-based generation, 3D rendering, user accounts, and real-time collaboration.*
