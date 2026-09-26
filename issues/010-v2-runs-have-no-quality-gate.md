# 010 — v2 estimator runs have no quality gate

**Priority:** P2 · **Opened:** 2026-09-23

**Evidence.** `api/agent/pdf_pipeline/passes/run.py:255` and `api/agent/dxf_pipeline/passes/run.py:140`
set `success=bool(boq.line_items)`; `PDF_THRESHOLDS` / `DXF_THRESHOLDS` in `api/core/config.py`
are unused by v2 (also action #1 in `docs/blueprints/PROMPT-ENGINEERING-BLUEPRINT.md`).

**Acceptance.** A per-pipeline gate → `passed | review | failed`, shown in the UI; tests.
