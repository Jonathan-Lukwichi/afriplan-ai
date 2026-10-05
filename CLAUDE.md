# CLAUDE.md — AfriPlan Electrical (FastAPI + React)

Read at the start of every session. PUSH context: only always-true, high-value facts.
Situational procedures live in `.claude/skills/` (PULL context).

## What this project is
A South African electrical **Bill of Quantities (BOQ)** estimator for contractors and
tender preparation — **this repo is the product** (React + Vite frontend, FastAPI
backend). Two independent pipelines turn drawings into a priced BOQ: **PDF** (vision
LLM reads the drawings, Python prices them) and **DXF/DWG** (deterministic CAD
geometry). A read-only **evaluation + audit** layer scores any BOQ against a real,
human-priced reference project and audits bills and drawing sets for what is missing.
The earlier Streamlit app is retired — do not add Streamlit code.
Author: Hervé / Jonathan Lukwichi (JLWanalytics). Commercial product in development.

There are **two ways to produce a BoQ**:
1. **Web app** — React (http://127.0.0.1:5180) + FastAPI (http://127.0.0.1:8000/docs). For
   contractors and demos; its PDF reader is the paid Claude API or free Gemini.
2. **DOE workflow in VS Code / Claude Code** (`doe/` + skill `estimate-project`) — any project
   folder in, a priced BoQ (Excel + PDF) out in `<folder>/AfriPlan_Output`. Claude Code reads the
   PDF pages on the **subscription** (no API bill); Python prepares, validates, combines and prices.
   Best scores so far.

## Start of every session — ASK FIRST
Before any other work, ask the user (AskUserQuestion) which they want this session:
- **Web app** → start backend + frontend (commands below), confirm both answer, give the links.
- **DOE workflow** → ask for the project folder, then run the `estimate-project` skill.
- **Develop the code** → normal engineering work on this repo.
Skip the question only if the user's first message already makes the choice clear.

## Read first
- `context.md` — the glossary. Use its exact terms in conversation, plans and code.
- `docs/architecture.md` — the whole system on one page.
- `docs/adr/` — decisions that must not be silently re-litigated.
- `issues/` — the known-defect backlog, each with evidence and acceptance criteria.

## Where things live
| Area | Path |
|---|---|
| Thin HTTP layer (runs, compare, export, pricing, **audit**) | `api/routers/` |
| Shared BOQ contract, legend spec | `api/agent/shared/` |
| PDF pipeline — 5-pass estimator (`run_pdf_estimator`) | `api/agent/pdf_pipeline/passes/` |
| DXF pipeline (`run_dxf_estimator`, `run_dxf_project` for a set), SLD reader, site routes, DWG conversion | `api/agent/dxf_pipeline/passes/`, `dwg.py` |
| Route geometry shared by both pipelines (graph, tags, scale, dashes, symbols) | `api/agent/shared/routes.py` |
| Rate model (crew×hours, DB build-up), prices, config, run store/jobs | `api/core/` |
| Ground truth, ItemKey taxonomy, layered BOQ network, ratios, **frozen scorer** | `api/evaluation/` |
| BOQ rule audit, drawing sufficiency, derived-item completer | `api/audit/` |
| CNN training-data generator (no model trained — ADR-0004) | `api/ml/` |
| Live supplier pricing (mock suppliers) · Excel/PDF exports · SQLite | `api/sourcing/` · `api/exports/` · `api/db/` |
| React pages (Landing, Login, wizard, Pricing, **Audit a BoQ**) · design system · API client | `src/pages/` · `src/components/ui/` · `src/api/client.js` |
| Reference projects: manifest committed; raw files + parsed bill LOCAL ONLY | `data/projects/<p>/` |
| CLIs (verify data, build reference, evaluate, audit, baseline, symbol dataset) | `scripts/` |
| **DOE workflow** — playbook (rules, lessons) · brain (how to read pages) · execution (`project.py`) | `doe/playbook/` · `doe/brain/` · `doe/execution/` |
| Baseline index (per-run reports local — client figures) | `reports/baselines/` |

## Run, build, test
```powershell
# Backend (main.py has no __main__ block — run uvicorn)
cd api; .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
# Frontend
npm run dev                                          # http://127.0.0.1:5180
# DOE workflow (Claude Code reads the pages between the two steps — see skill estimate-project)
api\.venv\Scripts\python.exe doe\execution\project.py prepare "<project folder>"
api\.venv\Scripts\python.exe doe\execution\project.py finish  "<project folder>" [--reference wedela]
# Verify (all must pass before a commit)
api\.venv\Scripts\python.exe -m pytest -q -p no:warnings   # ~390 tests, no network (pytest.ini: pythonpath=api)
npm run build
npx playwright test                                  # e2e; audit spec needs the backend + local workbook
api\.venv\Scripts\python.exe scripts/evaluate.py --project wedela --self-test   # RS 100.0%
```
Test dirs for the new packages end in `_layer` (`tests/evaluation_layer/`) — a
`tests/evaluation/` package would shadow `evaluation`.

## Hard rules
1. **Pipelines do not share state and do not call each other.** `api/agent/pdf_pipeline`
   ↔ `api/agent/dxf_pipeline` never import each other (CI + a PostToolUse hook).
2. **No LLM SDK** in `api/agent/dxf_pipeline/`, `api/evaluation/`, `api/audit/`.
3. **Read-only layers stay read-only:** nothing under `api/agent/` imports `evaluation`,
   `audit`, `sourcing`, `ml`, `routers`, `db`, or `agent.comparison`.
4. **LLM = eyes, Python = brain** (ADR-0002): strict `tool_use` schemas + retry-with-
   feedback; never hand-parse JSON, never let the LLM do arithmetic or invent a rate.
5. **Frozen system prompt** (`api/agent/pdf_pipeline/prompts/system_prompt.py`): no
   timestamps / request IDs / names — it is the cache prefix.
6. **Model IDs only in `api/core/config.py`.**
7. **Never silent:** every estimated quantity is tagged `INFERRED`/`ASSUMED`/`PROVISIONAL`,
   carries an `assumption`, and emits a `GapItem`.
8. **The scorer is frozen** (ADR-0003): `api/evaluation/metrics.py` + `taxonomy.py`
   define "better". Change only with a new ADR and a re-run of every baseline.
9. **The GitHub repo is PUBLIC** (ADR-0005): never commit client data — raw drawings,
   `reference_boq.json`, `ratio_model.json`, or any client rand figure/quantity, in files
   OR commit messages. Grep staged files and messages before every push.
10. **Markup is applied once:** v2 bills declare `contractor_markup_pct = 0` (rates carry
    the x1.3 material markup); export/UI default to the bill's own value.

## Product decisions carried over — do not re-litigate
- **Login is demo-only** (`src/pages/Login.jsx`): no backend check; one shared contractor
  profile in SQLite. Real accounts are a deliberate future decision, not a bug.
- **Excel/PDF export stays server-side** (`openpyxl`/`fpdf2`) — the tender document is
  the core deliverable.
- **"Both" comparison is a live feature** (Upload → PDF + DXF concurrently → Compare).
- **Open item, surfaced not resolved:** blueprint says "Mean BOQ MAPE ≤ 15 %", code
  enforces `PDF_THRESHOLDS.max_baseline_mape = 0.20`. Ask Jonathan/Hervé.

## Guardrails
ALWAYS: failing test first (`.claude/skills/tdd/`); verify against the running app, not
just unit tests; report baseline numbers honestly, including regressions.
ASK FIRST: new dependency · changing `BillOfQuantities` or any public schema · paid API
runs (PDF pipeline) · editing the scorer/taxonomy · force-push · deleting branches.
NEVER: commit client data or `.env` · weaken/delete a test to go green · edit the scorer
inside an optimisation loop · push to `main` / deploy without approval.

## Skills
`.claude/skills/evaluate-boq/` · `audit-boq/` · `add-reference-project/` · `tdd/` ·
`karpathy-coding-discipline/` · `prompts/review.md` (fresh-context review).

## Current state (update when it changes)
- Reference project: **wedela** (7 billed buildings). Baselines (`reports/baselines/README.md`),
  project-level Reproduction Score (2026-09-27): **DXF 44.6 %** (45.3 % with completer),
  **PDF 27.1 %** (Opus 5, pages read in parallel, ~5 min; the Wedela PDF set has no site plan, so its feeder lengths stay assumed).
- Optional **AI symbol names** (ADR-0007): loose-line-work symbols are grouped into shapes
  (`dxf_pipeline/passes/shapes.py`, no LLM), named once by `api/assist/symbol_namer.py`
  from a fixed catalogue (`agent/shared/symbol_catalogue.py`), remembered in `symbol_names`;
  Wedela DXF 44.8 % → **46.2 %** (49.2 % with completer) for ~R 1.
- A DWG/DXF **set** runs as one project (`run_dxf_project`): feeders from every SLD are
  measured on the electrical site plan (`agent/shared/routes.py` + each pipeline's
  `passes/site_routes.py`); the PDF pipeline measures vector site-plan PDFs the same way.
- **One bill from both readers** (ADR-0008): each engine states *findings* (`agent/shared/findings.py`,
  with evidence: measured > counted > written > seen > assumed) priced by ONE pricer
  (`agent/shared/pricing.py`). `api/consolidate/combine.py` merges the two readers' findings
  (PDF pages paired with CAD sheets by shared words, `agent/shared/sheets.py`); names Python cannot
  pair go to the injected AI matcher `api/assist/finding_matcher.py`. Wedela combined **47.2 %**.
- **DOE workflow** (2026-10-02, `doe/execution/project.py` + skill `estimate-project`): PDF pages
  read by Claude Code on the subscription → Wedela PDF **47.5 %** (Claude API 27.1 %, Gemini free
  40.2 %); combined with the DWG set **55.8 % — the best so far**. Forms are saved per page so every
  result can be reproduced; a missing or invalid form stops `finish`.
- Biggest levers next: building attribution (008), a second reference project (014),
  tag→symbol attribution on site plans (leader lines), site-lighting double counts across
  PDF sheets (flagged, not yet merged).
- Streamlit app retired 2026-09-26; its final state is the tag `archive/legacy-streamlit-2026-09-26`.
