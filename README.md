# AfriPlan Electrical · v6.2

**South African electrical Bill-of-Quantities estimator — with an honest, reproducible
measure of how good its bills are.**

Upload electrical drawings (a PDF set or CAD DWG/DXF). Two independent pipelines produce
a priced, SANS-style BOQ for tendering. An evaluation layer scores any BOQ line-by-line
against a real, human-priced reference project; an audit layer checks bills for errors
and tells you which drawings a complete BOQ needs.

> Pipelines do not share state. Pipelines do not call each other. (ADR-0001)
> The LLM is the eyes; Python is the brain. (ADR-0002)

---

## Quickstart

```bash
pip install -r requirements-dev.txt
python -m pytest -q -p no:warnings            # ~400 tests, no network
streamlit run app.py                          # the app (PDF path needs ANTHROPIC_API_KEY)
```
API key for the PDF pipeline: `.streamlit/secrets.toml` → `ANTHROPIC_API_KEY = "sk-ant-..."`.
DWG input needs LibreDWG `dwg2dxf` on PATH or in `~/libredwg/` (free, no login).

## Reproduce the evaluation (needs the Wedela reference files in `data/projects/wedela/raw/`)

```bash
python scripts/verify_data.py wedela                         # inputs == checksummed manifest
python scripts/build_reference.py wedela                     # parse the priced bill + fit ratios
python scripts/evaluate.py --project wedela --self-test      # scorer sanity: RS 100.0%
python scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<date>-wedela-dxf.md
python scripts/audit_boq.py --project wedela --out reports/audits/wedela-reference-audit.md
python scripts/audit_boq.py --project wedela --sufficiency --out reports/audits/wedela-drawing-sufficiency.md
```

## Where things stand (2026-09-26, Wedela reference)

| Pipeline | Reproduction Score (project-level) | Coverage | Cost |
|---|---:|---:|---:|
| DXF / DWG | 12.8 % | 59 % | R 0 |
| PDF | 17.8 % | 53 % | R 19.31 / 18 pages |

Most of an electrical bill's value is in the single-line diagram and cable routes (≈ 57 %)
and site lighting (≈ 17 %), not in the symbols pipelines count well (≈ 6 %). The ranked
fix list is in [`issues/`](issues/README.md); the numbers in
[`reports/baselines/`](reports/baselines/README.md).

The reference bill itself was audited: 33 findings, incl. priced install lines left
out of section totals and a duplicated DB line (report kept locally: client figures).

## Repository map

| Path | What |
|---|---|
| `agent/shared/` | the BOQ contract both pipelines emit; legend (LDSE) spec |
| `agent/pdf_pipeline/passes/` | PDF v2: classify → 3 LLM "eyes" passes → deterministic assembler |
| `agent/dxf_pipeline/passes/` | DXF v2: DWG→DXF, recognise, legend, spatial, template match, assemble |
| `core/` | rate model (crew × hours), prices, SANS helpers, model registry |
| `evaluation/` | reference parser, ItemKey taxonomy, layered BOQ network, fitted ratios, frozen scorer |
| `audit/` | BOQ rule audit, drawing sufficiency, derived-item completer |
| `ml/` | CAD → labelled symbol images (CNN training data; no model trained yet) |
| `sourcing/` | live supplier pricing (mock suppliers) |
| `pages/`, `ui/`, `exports/` | Streamlit app, Excel/PDF tender exports |
| `data/projects/` | reference projects (manifest committed, raw client files gitignored) |
| `reports/` | committed baselines and audits |
| `docs/` | architecture, ADRs, specs/plans, historical blueprints |
| `issues/` | known-defect backlog with evidence |
| `CLAUDE.md`, `context.md`, `.claude/` | AI-assistant context: rules, glossary, skills, hooks |

## Working on this repo (humans and AI assistants)
Read [`CLAUDE.md`](CLAUDE.md) → [`context.md`](context.md) → [`docs/architecture.md`](docs/architecture.md).
Test-first; the architecture rules are enforced by CI and by a Claude Code hook; the scorer
is frozen (ADR-0003); improvements are claimed only against a committed baseline.

## Client data
This repository is public. Client drawings, the parsed priced bill and every report
quoting client figures are kept locally and gitignored (ADR-0005); tests that need them
skip on a fresh clone. The checksummed `data/projects/*/manifest.json` lets anyone who
receives the files from the owner reproduce every number exactly.

*Hervé / Jonathan Lukwichi · JLWanalytics*
