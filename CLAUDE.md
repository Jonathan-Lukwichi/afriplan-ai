# CLAUDE.md — AfriPlan Electrical (FastAPI + React)

Read at the start of every session: only always-true facts (PUSH); procedures live in `.claude/skills/` (PULL).

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
- **Web app** → `python scripts/dev.py start` (or the commands below), confirm both answer, give the links.
- **DOE workflow** → ask for the project folder, then run the `estimate-project` skill.
- **Develop the code** → normal engineering work on this repo.
Skip the question only if the user's first message already makes the choice clear.

## The working loop — follow it in order, every session
Detail per step (files, commands, "done when", next): `.claude/rules/working-loop.md`. How work is
split (instructions → agent → engines + check): `.claude/rules/three-layer-approach.md`.
0. **Orient.** Ask the mode (above). Open `context/priorities.md` (what next) and `context/current-state.md`
   (scores, status; aim = READING accuracy on **wedela**). Words: `context.md` · system:
   `docs/architecture.md` · decisions: `docs/adr/` · defects: `issues/` · domain: `references/README.md`.

**A. DOE estimate** (a BoQ from a project folder)
1. *Instructions:* skill `estimate-project` → `doe/brain/BRAIN.md`, `doe/playbook/`, `doe/knowledge/BOQ_KNOWLEDGE.md`.
2. *Engines:* `project.py prepare` → you read the pages into forms → `project.py finish`.
3. *Check:* the read-only `checker` agent; `evaluate-boq` / `audit-boq` when a reference or a bill applies.
4. *Learn and report:* "draft for estimator review"; corrections → `fix-and-learn` → `doe/playbook/LESSONS.md`.

**B. Develop** (change the code)
1. *Pick* one item from `context/priorities.md` or `issues/`; plan non-trivial work in `docs/superpowers/plans/`.
2. *Find the layer:* skill/brain · catalogue/layers/rates · engine (`api/agent/`) · UI (`src/`).
3. *Failing test first:* skill `tdd` (Python `tests/`, UI `tests-e2e/`, boundaries `tests/architecture/`).
4. *Smallest change* at that layer: skill `karpathy-coding-discipline`.
5. *Check:* pytest · `npm run build` · `npx playwright test` · `/check-takeoff` (engines, catalogue, rates)
   · `evaluate-boq` (score claims) · `dashboard-qa-gate` (UI). A failure → `fix-and-learn` → check again.
6. *Record:* `context/current-state.md` · `issues/` · `docs/adr/` · commit (no client data) · CI green → back to 0.

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
| Live supplier pricing (mock suppliers) + **price catalogue** (`sourcing/catalogue.py`, built by `scripts/build_price_catalogue.py` into `data/catalogue/`, local only) · Excel/PDF exports · SQLite | `api/sourcing/` · `api/exports/` · `api/db/` |
| AI cover note for e-mailing a BoQ | `api/ai/` |
| React pages (Landing, Login, wizard, Pricing, **Audit a BoQ**) · design system · API client | `src/pages/` · `src/components/ui/` · `src/api/client.js` |
| Reference projects: manifest committed; raw files + parsed bill LOCAL ONLY | `data/projects/<p>/` |
| CLIs (verify data, build reference, evaluate, audit, baseline, symbol dataset, take-off check) | `scripts/` |
| **DOE workflow** — playbook (rules, lessons) · brain (how to read pages) · execution (`project.py`) | `doe/playbook/` · `doe/brain/` · `doe/execution/` |
| **BoQ domain knowledge** — how a QS prepares, measures and prices a BoQ; the 4 ways wiring is billed (SA = material by material, convention A) and the route take-off | `doe/knowledge/BOQ_KNOWLEDGE.md` |
| Baseline index (per-run reports local — client figures) | `reports/baselines/` |
| Project context (priorities, current state, about the project; `about-me.md` local only) · reference signposts, tool connections | `context/` · `references/` |
| Working loop + three-layer approach (rules) · skills · agents (`checker`, `researcher`) · settings + hooks | `.claude/rules/` · `.claude/skills/` · `.claude/agents/` · `.claude/settings.json` |
| Fresh-context review prompt · AutoResearch loop (defined, not running) | `prompts/review.md` · `autoresearch/program.md` |

## Run, build, test
Runs on **Windows, macOS and Linux**. Versions pinned in `.python-version` (3.12) and `.nvmrc` (20); CI and
Docker build with exactly these (a test checks Docker). `$PY` below = the project venv:
`api\.venv\Scripts\python.exe` on Windows, `api/.venv/bin/python` on macOS/Linux — never the
system `python`. Use forward slashes in paths; keep new code OS-neutral (`pathlib`, no `.exe`
or drive letters without a macOS/Linux equivalent).
```bash
python scripts/dev.py setup                          # first time on a machine (macOS: python3)
python scripts/dev.py start                          # backend :8000 + frontend :5180, Ctrl+C stops both
# ...or by hand (main.py has no __main__ block — run uvicorn from api/)
cd api && $PY -m uvicorn main:app --host 127.0.0.1 --port 8000
npm run dev                                          # http://127.0.0.1:5180
# DOE workflow (Claude Code reads the pages between the two steps — see skill estimate-project)
$PY doe/execution/project.py prepare "<project folder>"
$PY doe/execution/project.py finish  "<project folder>" [--reference wedela]
# Verify (all must pass before a commit)
$PY -m pytest -q -p no:warnings                      # ~575 tests, no network (pytest.ini: pythonpath=api)
$PY scripts/check_takeoff.py                         # take-off vs hand counts (skill check-takeoff)
npm run build
npx playwright test                                  # e2e; audit spec needs the backend + local workbook
$PY scripts/evaluate.py --project wedela --self-test # RS 100.0% (needs the local Wedela data)
```
A fresh clone skips the tests that need `data/projects/*/raw/` (client data, never in git).
**CI** (`.github/workflows/ci.yml`) on every push/PR: architecture rules, pytest, build, Playwright
(audit + DWG-set specs skip without the backend and client files), no-client-data check.
Test dirs for top-level packages end in `_layer` (`tests/evaluation_layer/`); `tests/evaluation/` would shadow it.

## Hard rules
1. **Pipelines do not share state and do not call each other.** `api/agent/pdf_pipeline`
   ↔ `api/agent/dxf_pipeline` never import each other (CI + a PostToolUse hook).
2. **No LLM SDK** in `api/agent/dxf_pipeline/`, `api/evaluation/`, `api/audit/`.
3. **Read-only layers stay read-only:** nothing under `api/agent/` imports `evaluation`,
   `audit`, `sourcing`, `ml`, `routers`, `db`, or `agent.comparison`.
4. **LLM = eyes, Python = brain** (ADR-0002): strict `tool_use` schemas + retry-with-
   feedback; never hand-parse JSON, never let the LLM do arithmetic or invent a rate.
   **Nobody invents a quantity or a rate** — not the LLM, not Claude Code, not a default in code:
   every number comes from a drawing, a rate table or a script run, or is tagged as in rule 7.
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
inside an optimisation loop · push to `main` / deploy without approval · send a BoQ or tender
document to a client before a qualified person has signed it off (who qualifies: `context/about-project.md`).

## Skills, agents, rules
Index in loop order: `.claude/README.md`. Project skills: `estimate-project` · `check-takeoff` · `fix-and-learn` ·
`tdd` · `evaluate-boq` · `audit-boq` · `add-reference-project` · `karpathy-coding-discipline`. **BoQ domain skills**
(rule IDs + confidence, each logs `FEEDBACK.md`, improved by `improving-boq-skills` via a hook): `reading-scope-modifiers`
· `reading-drawing-symbols` · `deriving-companion-items` · `writing-sa-bill-lines` · `checking-boq-completeness` ·
`consolidating-price-catalogue`. General (this file wins): `dashboard-qa-gate` · `frontend-design` · `data-app-deploy`.
