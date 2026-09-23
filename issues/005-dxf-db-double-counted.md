# 005 — DXF counts each DB once per drawing

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** DXF baseline: `db` 27 predicted vs 10. `agent/dxf_pipeline/passes/assemble.py:124`
emits one DB line per `db_ref` per file; a building's lighting + plug + SLD runs each bill
the same DB tag.

**Acceptance.** DBs de-duplicated by name across a building's drawing set; `db` qty
accuracy ≥ 80 % project-level on Wedela.
