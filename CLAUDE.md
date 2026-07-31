# CLAUDE.md — AfriPlan Web (FastAPI + React rewrite)

This is a **new, separate** rewrite of AfriPlan Electrical, built alongside
the original Streamlit app at `../afplan AI` (untouched, still running). Read
that project's own `CLAUDE.md`/`README.md`/blueprint doc for the original
domain rules — this file only covers what's *different* in the rewrite.

## Where this came from

Built using the [`engineering-webapp-skills`](https://github.com/Jonathan-Lukwichi/engineering-webapp-skills)
skill set, adapted to AfriPlan's actual domain logic — not a generic
template. Full plan and rationale: see the session that built this (the
"what gets ported verbatim / re-plumbed / newly built" breakdown is the
single most important reference document for this repo).

## Critical decisions carried over from the original app — do not re-litigate

1. **Pipelines do not share state. Pipelines do not call each other.**
   Enforced by `tests/architecture/test_independence.py`, ported near-verbatim
   from the original app. Never soften this when editing `api/agent/`.
2. **The `passes/` estimator is the ported pipeline, not `stages/`.** The
   original repo has two parallel implementations; the `passes/` one is what
   the live Streamlit app actually runs, so it's the one being ported here.
   `stages/` is legacy and intentionally not present in this rewrite.
3. **The cross-pipeline comparison feature is a real, live feature here** —
   unlike the original app, where it exists (tested) but is disconnected from
   the wizard. A "Both" option in Upload runs PDF + DXF concurrently and
   shows the real comparison panel.
4. **Login is intentionally demo-only** — prefilled credentials, no backend
   check, no real session (see `src/pages/Login.jsx`). This was an explicit
   choice, not an oversight. Consequence: contractor-profile persistence
   (SQLite) is currently a single shared demo profile, not per-user. If real
   multi-user accounts are ever wanted, that's a deliberate follow-up
   decision, not a bug to silently fix.
5. **Excel/PDF export stays server-side** (`openpyxl`/`fpdf2`, ported from
   the original `exports/`), a deliberate exception to the skill set's
   default "client-side PDF" recommendation — the tender document IS this
   product's core deliverable, already correct and tested.
6. **One open item, not yet resolved**: the original blueprint's CI table
   says "Mean BOQ MAPE ≤ 15%" but the actual enforced
   `PDF_THRESHOLDS.max_baseline_mape` is `0.20`. This rewrite ports the
   code's actual value (20%) — flagged to Jonathan/Hervé, not silently
   picked.

## Stack & layout

Same shape as `engineering-webapp-scaffold`: `api/routers/` (thin),
`api/core/` (fat — rate model, config, constants, standards, layer aliases,
ported verbatim from the original `core/`), `api/agent/` (shared/,
pdf_pipeline/, dxf_pipeline/, comparison/ — same independence rule as the
original), `api/db/` (SQLite persistence, new — the original used local
files), `api/exports/` (Excel/PDF generators, ported). Frontend: `src/pages/`
(Landing, Login, then the wizard), `src/components/ui/` (design system,
tokens ported from the original `ui/styles.py`), `src/api/client.js`.

## Run / build / test

```powershell
# Backend
cd api; .venv\Scripts\Activate.ps1; python main.py     # http://localhost:8000

# Frontend
npm run dev                                             # http://localhost:5173

# Verify
npm run build
npx playwright test
pytest tests/architecture/                              # independence rule — must stay green
```

## Definition of done

Same standard as every project in this session: build passes, tests pass,
verified against the running app (not assumed), the independence rule stays
green, and any open domain question (like item 6 above) is surfaced to
Jonathan/Hervé rather than silently resolved.
