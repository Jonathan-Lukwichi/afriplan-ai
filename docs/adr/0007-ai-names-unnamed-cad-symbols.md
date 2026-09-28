# ADR-0007: AI names unnamed CAD symbols; geometry still counts and measures

- **Status:** accepted
- **Date:** 2026-09-28
- **Amends:** ADR-0001 (the DXF pipeline stays free of LLM imports), ADR-0002 (LLM = eyes, Python = brain)

## Context
On Wedela, about a fifth of the bill's value is light fittings that the DXF engine never
counted: the electrical symbols were imported into CAD from a PDF (layer
`PDF_MEP$$$Electrical`), so they are loose lines and circles with no block name. Geometry
can find every copy of a shape exactly, but cannot know that "a circle with a cross" is a
light fitting — a person knows that by reading the legend. Exact lengths are not the
problem: CAD geometry already measures them exactly, and an LLM would only estimate them.

## Decision
1. **Deterministic (DXF pipeline, no LLM):** group the loose symbol line-work of each drawing
   into repeated shapes with a rotation-independent signature; render ONE small image per
   distinct shape; count every copy. `agent/dxf_pipeline/passes/shapes.py`.
2. **Optional AI step (new top-level `api/assist/`, the only place with the LLM call):** show
   the model those images plus the drawing's legend text and make it choose, through a strict
   `tool_use` schema, one name from a FIXED list of catalogue items (or "not an electrical
   symbol" / "unsure"). It never counts, measures or prices.
3. The DXF pipeline receives the result as a plain `{signature: item}` mapping (dependency
   injection: `run_dxf_project(..., name_shapes=callable)`) — it still imports no LLM code.
4. Every AI-named line is `INFERRED` with a low gap ("named by AI from the legend — confirm");
   names are remembered per signature so a confirmed or corrected name is reused and not paid
   for again.
5. Off by default: without the switch, or without an API key, the DWG engine is unchanged —
   free, offline, byte-identical.

## Consequences
- Cost: one vision call per project with ~10–40 small images (a few rand), not per page.
- Counts stay exact and repeatable; only the *name* of a shape can be wrong, and it is shown
  with its picture so a person can correct it once.
- CI keeps enforcing "no LLM import in `agent/dxf_pipeline/`"; a new test enforces that
  nothing under `agent/` imports `assist`.
