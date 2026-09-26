# ADR-0006: evaluation, audit, sourcing and ml are top-level read-only packages

- **Status:** accepted
- **Date:** 2026-09-23

## Context
Scoring, auditing, live pricing and training-data generation all consume pipeline
output. Inside `api/agent/` they would tempt pipelines to import them — and a pipeline
must never "see" its own scorer.

## Decision
Packages `api/evaluation/`, `api/audit/`, `api/sourcing/`, `api/ml/`, next to `api/agent/` (the web layer `api/routers/` and `api/db/` are equally off-limits to the pipelines).
They may import `agent.shared` and `core`; `api/ml/` may import the DXF pattern table as its
label source. Nothing under `api/agent/` imports them. `api/evaluation/` and `api/audit/` import no
pipeline and no LLM SDK. Their tests live in `tests/<name>_layer/` to avoid package
shadowing.

## Consequences
- The ruler is independent of what it measures (CI-enforced).
- `scripts/` is the only place pipelines and layers meet (e.g. `run_baseline.py`).
