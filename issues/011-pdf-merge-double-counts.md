# 011 — PDF fact merging double-counts boards and rooms seen on two sheets

**Priority:** P2 · **Opened:** 2026-09-23

**Evidence.** `api/agent/pdf_pipeline/passes/orchestrator.py:118` and `:129` extend lists without
de-duplication; conflicting values across pages are never surfaced.

**Acceptance.** Merge by DB / room name; conflicts recorded as gaps; test with two
overlapping page facts.
