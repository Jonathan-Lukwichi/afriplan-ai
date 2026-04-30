# CLAUDE.md — AfriPlan Electrical v6.1

This file is the project-level guide for Claude (and any other AI assistant) when working in this repository. It supersedes every previous CLAUDE\_\* doc.

## Project Overview

| | |
|---|---|
| **Name** | AfriPlan Electrical |
| **Version** | 6.1 (Dual-Pipeline Edition) |
| **Purpose** | South African electrical Bill-of-Quantities extractor for contractors and tender preparation |
| **Architecture** | Two **independent** pipelines — PDF (LLM) and DXF (deterministic) — plus a read-only cross-comparison layer |
| **Author** | Hervé / JLWanalytics |
| **Blueprint** | [AFRIPLAN\_V6\_1\_DUAL\_PIPELINE\_BLUEPRINT.md](AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md) |

## The single rule

> **Pipelines do not share state. Pipelines do not call each other.**

Everything in the architecture follows from this. The CI suite [`tests/architecture/`](tests/architecture/) enforces it by grepping the source tree on every push. Do not soften this rule when making edits.

## Architecture

```
agent/
├── shared/               types both pipelines emit (BillOfQuantities, ProjectMetadata, ComplianceFlag, …)
├── pdf_pipeline/         vision LLM → BoQ            (anthropic SDK; tool_use; retry-with-feedback)
├── dxf_pipeline/         deterministic ezdxf → BoQ   (zero LLM imports — CI-checked)
└── comparison/           read-only diff              (consumed by UI only; pipelines may NOT import it)

core/
├── config.py             model registry + per-pipeline gate thresholds
├── constants.py          SA unit prices (shared)
├── standards.py          SANS 10142-1 helpers (shared)
└── layer_aliases.py      DXF layer-name normalisation

exports/                  BillOfQuantities → .xlsx / .pdf
ui/                       Streamlit primitives (no business logic)
pages/1_Upload.py         single-page UI (upload → run both → compare)
app.py                    20-line entry point
```

## What's where

| If the task is… | Look in… |
|---|---|
| Add a new fixture / block to DXF recognition | [`agent/dxf_pipeline/patterns.py`](agent/dxf_pipeline/patterns.py) |
| Add a new page-type tool to PDF extraction | [`agent/pdf_pipeline/prompts/tool_schemas.py`](agent/pdf_pipeline/prompts/tool_schemas.py) and a corresponding prompt in [`prompts/page_prompts.py`](agent/pdf_pipeline/prompts/page_prompts.py) |
| Tune a gate threshold | [`core/config.py`](core/config.py) — `PDF_THRESHOLDS` or `DXF_THRESHOLDS` |
| Edit the system prompt for vision extraction | [`agent/pdf_pipeline/prompts/system_prompt.py`](agent/pdf_pipeline/prompts/system_prompt.py) — keep it FROZEN (no timestamps / per-request data) |
| Change BoQ section list / pricing | [`agent/shared/boq.py`](agent/shared/boq.py) and [`core/constants.py`](core/constants.py) |
| Add a new compliance check | [`agent/pdf_pipeline/stages/evaluate.py`](agent/pdf_pipeline/stages/evaluate.py) (`_sans_checks`) |
| Add a comparison metric | [`agent/comparison/compare.py`](agent/comparison/compare.py) |
| Author a baseline | `python scripts/build_baselines.py interactive <project>` |

## Hard rules for AI edits

1. **Never** add an import from `agent.pdf_pipeline.*` inside `agent/dxf_pipeline/` (or vice versa). The architecture test suite catches this and fails CI.
2. **Never** add `import anthropic` (or any LLM SDK) inside `agent/dxf_pipeline/`.
3. **Never** introduce a function called `parse_json_safely` or hand-roll JSON parsing in `agent/pdf_pipeline/`. Always use `tool_use` with a strict schema in [`prompts/tool_schemas.py`](agent/pdf_pipeline/prompts/tool_schemas.py); validation failures must go through the retry-with-feedback mechanism in [`llm.py`](agent/pdf_pipeline/llm.py).
4. **Never** import `agent.comparison.*` from inside either pipeline. The comparison layer reads pipelines, not the other way round.
5. **Never** put dynamic data (timestamps, request IDs, contractor names) into the PDF system prompt — it lives at position 0 in the cache prefix and breaks prompt caching.
6. Hard-code model IDs only in [`core/config.py`](core/config.py). Every other module imports `HAIKU_4_5`, `SONNET_4_5`, `OPUS_4_6` (or the pipeline-role aliases).

## Testing

```bash
pytest tests/dxf_pipeline/        # deterministic, no network
pytest tests/pdf_pipeline/        # mocked LLM via MockAnthropic, no network
pytest tests/comparison/          # cross-pipeline diff
pytest tests/architecture/        # independence-rule enforcement
```

CI runs each suite as a separate GitHub Actions job. None of the suites need an `ANTHROPIC_API_KEY` — the PDF pipeline tests use the mock client in [`tests/pdf_pipeline/conftest.py`](tests/pdf_pipeline/conftest.py).

If you add a new pipeline stage, also add a unit test for it under the matching pipeline's `unit/` directory. Tests must not exercise the network in CI.

## Models and cost

```
Haiku 4.5    classify_page                  ~ R 0.18 / page
Sonnet 4.5   per-page-type extraction       ~ R 1.80 / page
Opus 4.6     escalation only                ~ R 8.50 / page
DXF pipeline                                 R 0.00 / run
```

Token spend is tracked per-stage in `PdfPipelineRun.stage_costs` and surfaced in the UI (`Cost` metric). If a real run exceeds R 8.00 average that's a regression — investigate the prompt or the page count.

## Run logs

Each pipeline writes to `runs/<pipeline>/<run_id>.json` when called with `persist=True` (the UI does this; tests and ad-hoc CLI calls don't). Files are gitignored and contain the entire `model_dump_json()` of the run object — input hashes, every stage's output, every cost, the BoQ. They're the source of truth for any cost / accuracy / regression study.

## Today

Today's date is **2026-04-30**. The blueprint was authored 2026-04-29; this codebase is the implementation of that blueprint.
