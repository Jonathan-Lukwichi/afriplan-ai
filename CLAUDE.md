# CLAUDE.md — AfriPlan Electrical

Read at the start of every session. This file is PUSH context: only always-true,
high-value facts. Situational procedures live in `.claude/skills/` (PULL context).

## What this project is
A South African electrical **Bill of Quantities (BOQ)** estimator for contractors and
tender preparation. Two independent pipelines turn drawings into a priced BOQ — **PDF**
(vision LLM reads the drawings, Python prices them) and **DXF/DWG** (deterministic CAD
geometry). A read-only **evaluation + audit** layer scores any BOQ against a real,
human-priced reference project and audits bills and drawing sets for what is missing.
Author: Hervé / Jonathan Lukwichi (JLWanalytics). Commercial product in development.

## Read first
- `context.md` — the glossary. Use its exact terms in conversation, plans and code.
- `docs/architecture.md` — the whole system on one page.
- `docs/adr/` — decisions that must not be silently re-litigated.
- `issues/` — the known-defect backlog, each with evidence and acceptance criteria.

## Where things live
| Area | Path |
|---|---|
| Shared contract both pipelines emit (`BillOfQuantities`, `GapItem`, legend spec) | `agent/shared/` |
| PDF pipeline — live v2 5-pass estimator (`run_pdf_estimator`) | `agent/pdf_pipeline/passes/` |
| DXF pipeline — live v2 estimator (`run_dxf_estimator`), DWG conversion | `agent/dxf_pipeline/passes/`, `dwg.py` |
| Legacy v1 stage pipelines (kept green, not used by the UI) | `agent/*/pipeline.py`, `agent/*/stages/` |
| Rates (crew×hours build-up), prices, SANS helpers, model registry | `core/` |
| Ground truth, ItemKey taxonomy, layered BOQ network, fitted ratios, **frozen scorer** | `evaluation/` |
| BOQ audit rules, drawing sufficiency, BOQ completer | `audit/` |
| CNN training-data generator (no model trained yet — ADR-0004) | `ml/` |
| Live supplier pricing (mock suppliers) | `sourcing/` |
| Legacy totals-only scorer (superseded by `evaluation/`) | `scoring/` |
| Reference projects: manifest committed, raw client files gitignored | `data/projects/<p>/` |
| Streamlit UI (pages) · exporters | `pages/`, `ui/`, `app.py` · `exports/` |
| CLIs | `scripts/` |
| Committed baseline + audit reports | `reports/` |

## Feedback loops (run before every commit)
```bash
python -m pytest -q -p no:warnings                 # full suite (~400 tests, no network)
python -m pytest tests/architecture -q             # independence rules (also a PostToolUse hook)
python scripts/verify_data.py wedela               # raw inputs match the checksummed manifest
python scripts/evaluate.py --project wedela --self-test   # scorer sanity: RS 100.0%
streamlit run app.py                               # the app
```
Test dirs for top-level packages end in `_layer` (`tests/evaluation_layer/`) — a
`tests/evaluation/` package would shadow `evaluation` and break imports.

## Hard rules
1. **Pipelines do not share state and do not call each other.** Never import
   `agent.pdf_pipeline.*` from `agent/dxf_pipeline/` or vice versa. CI-enforced.
2. **No LLM SDK** in `agent/dxf_pipeline/`, `evaluation/`, `audit/`.
3. **Read-only layers stay read-only:** nothing under `agent/` imports `evaluation`,
   `audit`, `scoring`, `sourcing`, `ml` or `agent.comparison`.
4. **LLM = eyes, Python = brain** (ADR-0002). The PDF LLM only reports what is drawn,
   through `tool_use` with strict schemas (`prompts/pass_schemas.py`,
   `prompts/tool_schemas.py`) and retry-with-feedback in `llm.py`. Never hand-parse
   JSON, never let the LLM do arithmetic or invent a rate.
5. **Frozen system prompt:** no timestamps / request IDs / names in
   `agent/pdf_pipeline/prompts/system_prompt.py` (position 0 of the cache prefix).
6. **Model IDs only in `core/config.py`.**
7. **Never silent:** every estimated quantity is tagged `INFERRED`/`ASSUMED`/`PROVISIONAL`,
   carries an `assumption`, and emits a `GapItem`.
8. **The scorer is frozen** (ADR-0003): `evaluation/metrics.py` and
   `evaluation/taxonomy.py` define what "better" means. Change them only with a new
   ADR and a re-run of every baseline in `reports/baselines/`.

## Guardrails
ALWAYS: write the failing test first (`.claude/skills/tdd/`); run the feedback loop
before committing; report baseline numbers honestly, including regressions.

ASK FIRST: new dependency · changing `BillOfQuantities` or any public schema ·
paid API runs (PDF pipeline) · editing the scorer or taxonomy · committing client data.

NEVER: commit `data/**/raw/` or `.streamlit/secrets.toml` · weaken or delete a test to
go green · edit the scorer inside an optimisation loop · push/deploy without approval.

## Skills (follow them for these tasks)
- `.claude/skills/evaluate-boq/` — score a pipeline run against a reference project
- `.claude/skills/audit-boq/` — audit a bill and a drawing set
- `.claude/skills/add-reference-project/` — onboard a new priced project as ground truth
- `.claude/skills/tdd/` · `.claude/skills/karpathy-coding-discipline/`
- `prompts/review.md` — fresh-context review of a diff

## Current state (update when it changes)
- Reference projects: **wedela** (7 billed buildings).
- Baselines (`reports/baselines/README.md`), project-level RS: **DXF 2.4 %**, **PDF 16.9 %**.
  ~57 % of bill value is SLD/route-derived (feeders, DBs, trench, earth) and ~17 % is site
  lighting; DXF reads no SLD drawing, PDF assumes 30 m feeders. Top fixes: `issues/001-004`.
- Historical design docs (pre-v6.2): `docs/blueprints/`.
- Date of last restructure: 2026-09-23.
