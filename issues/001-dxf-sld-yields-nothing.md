# 001 — DXF pipeline recognises nothing on SLD drawings

> **Status:** FIXED 2026-09-26 (25ea42c) — passes/sld.py reads boards, breakers, feeders; DXF project RS 2.4 % → 12.8 %.

**Priority:** P0 — largest value gap · **Opened:** 2026-09-23

**Evidence.** `reports/baselines/2026-09-23-wedela-dxf.md` run log: all 6 Wedela SLD DWGs
return 0 lines ("No electrical content recognised"). SLD-derived families (`swa_cable`,
`db`, `bcew`, `termination`, `trench`) are ~57 % of the Wedela reference value. This is the main reason the DXF Reproduction Score is 1.8 %.

**Cause (to confirm).** `agent/dxf_pipeline/passes/recognize.py` reads circuit tags on
electrical layers and cable on wiring layers only; an SLD is schematic text + blocks
(board names, breaker ratings, cable annotations such as `4C 95mm² PVC SWA 120m`).

**Acceptance.** A DXF SLD pass that extracts DBs (name, main breaker) and feeders (size,
cores, from→to, annotated length) into the existing assembler; tests with real SLD
strings; a new dated DXF baseline with project-level RS above 2.4 %.
