# ADR-0002: LLM = eyes, Python = brain (the determinism contract)

- **Status:** accepted
- **Date:** 2026-07-06 (recorded 2026-09-23)

## Context
An LLM asked to "produce a BOQ" varies run to run, invents rates and does arithmetic
badly. Contractors need the same drawings to give the same bill.

## Decision
The vision LLM only reports what is drawn (counts, sizes, whether a length is
annotated) through strict `tool_use` schemas with `additionalProperties: false` and
retry-with-feedback. Every rate, derived quantity, supply/install split, contingency
and VAT is computed in pure Python (`api/agent/pdf_pipeline/passes/assemble.py`,
`api/core/rate_model.py`). Missing values are reported as missing; Python decides what to
assume and emits a `GapItem`.

## Consequences
- Same facts → byte-identical bill (tested).
- Prompt changes cannot change pricing logic; pricing changes cannot break prompts.
- The LLM cannot "fill in" a plausible number — gaps are visible instead.
