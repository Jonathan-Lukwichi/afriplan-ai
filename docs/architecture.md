# Architecture — AfriPlan Electrical (FastAPI + React)

```
 Browser ── React + Vite (src/) ──────────────────────────────────────────────────────┐
   Landing · Login(demo) · Welcome · Upload · Take-off · Compare · BoQ · Pricing · Audit │
                                   │  src/api/client.js (fetch, same-origin in prod)   │
 ──────────────────────────────────┼────────────────────────────────────────────────────┘
 FastAPI (api/main.py) ── routers/ (thin)
   runs     POST /api/runs, GET /api/runs/{id}        → core/run_jobs → a pipeline (threadpool)
   compare  POST /api/compare, GET …                   → both pipelines + agent/comparison
   export   GET /api/export/{json,excel,pdf}/{id}?markup&complete, POST /api/export/email
   pricing  /api/pricing/*                             → sourcing/ (mock suppliers, RFQ)
   audit    POST /api/audit/boq · GET /api/audit/{run,coverage}/{id} · /ratio-model
                                   │
         ┌─────────────────────────┴──────────────────────────┐
         ▼                                                    ▼
 agent/pdf_pipeline/passes          (never import each other)   agent/dxf_pipeline/passes
 classify (Haiku) → 3 LLM "eyes"                                dwg→dxf (LibreDWG) → recognise
 passes (Sonnet, tool_use) → facts                              → sld (boards/feeders) → legend
 → assemble.py (pure Python brain)                              → spatial → template → assemble
         └──────────── both emit agent.shared.BillOfQuantities ───────────┘
                                   │  core/run_store (SQLite, api/data/)
                                   ▼
 READ-ONLY LAYERS (never imported by agent/):
   evaluation/  reference parser · ItemKey taxonomy · layered BOQ network · fitted ratios ·
                FROZEN scorer (metrics.py)            ← data/projects/<p>/ (client data local)
   audit/       boq_rules · sufficiency · completer (used by routers/audit + export ?complete)
   ml/          CAD → labelled symbol images (future CNN)
   sourcing/    supplier quotes
```

## The two pipelines
| | PDF (`run_pdf_estimator`) | DXF (`run_dxf_estimator`) |
|---|---|---|
| Input | a set of PDFs, classified per page | one DXF/DWG |
| Perception | vision LLM, strict `tool_use`, retry-with-feedback | ezdxf geometry, SLD text, legend, OpenCV template match |
| Arithmetic | pure Python (`passes/assemble.py`, `core/rate_model.py`) | pure Python (`passes/assemble.py`) |
| Cost | ≈ R 1 / page | R 0 |

## What "good" means (evaluation)
A real priced reference BOQ is parsed line by line; every line gets an **ItemKey**; the
frozen scorer matches predicted lines per building and reports the **Reproduction
Score** (value share reproduced, discounted by quantity error), coverage, precision and
scoped variants. The **layered BOQ network** (drawings → evidence → quantities → priced
lines → totals) says which drawings each item needs — it drives the coverage panel, the
sufficiency report and the partial-BOQ policy. See ADR-0003/0004.

## Invariants (CI-enforced, `tests/architecture/`)
- PDF ↔ DXF pipelines never import each other; DXF imports no LLM SDK.
- `api/agent/` never imports `evaluation`, `audit`, `sourcing`, `ml`, `routers`, `db`, `agent.comparison`.
- `api/evaluation/` and `api/audit/` import no pipeline and no LLM SDK.

## Reproducible baseline
```powershell
$py = "api\.venv\Scripts\python.exe"   # macOS/Linux: py=api/.venv/bin/python, then $py instead of & $py
& $py scripts/verify_data.py wedela
& $py scripts/build_reference.py wedela
& $py scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<date>-wedela-dxf.md
```
