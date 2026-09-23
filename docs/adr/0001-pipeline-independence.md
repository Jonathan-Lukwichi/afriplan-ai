# ADR-0001: The PDF and DXF pipelines are independent

- **Status:** accepted
- **Date:** 2026-04-29 (recorded 2026-09-23)

## Context
Clients send PDFs, CAD files, or both. When one combined pipeline produced a wrong
line it was impossible to tell which input or which stage caused it.

## Decision
Two pipelines that share only the output contract (`agent/shared/`) and `core/`.
They never import each other, never share state, never call each other. The
comparison, evaluation, audit, sourcing and ml layers read pipeline output; the
pipelines never import them. Enforced by `tests/architecture/test_independence.py`
and a PostToolUse hook in `.claude/settings.json`.

## Consequences
- Failure attribution is trivial; either input alone yields a BOQ.
- Some logic is deliberately duplicated (each pipeline has its own assembler).
- Shared behaviour must live in `agent/shared/` (e.g. the LDSE legend spec) or `core/`.
