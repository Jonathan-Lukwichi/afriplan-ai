# 003 — Site lighting (solar post lanterns, high-mast floods) cannot be reported

> **Status:** FIXED 2026-09-26 (03c6c98) — solar_post_lights / high_mast_poles in schema, facts, assembler.

**Priority:** P0 · **Opened:** 2026-09-23

**Evidence.** PDF baseline "Not produced": `light_solar_post` and `light_highmast` — together
17 % of the reference value. `read_layout_takeoff` in
`api/agent/pdf_pipeline/prompts/pass_schemas.py` has no field for either (only `pole_lights`,
`floodlights`).

**Acceptance.** Schema + facts + assembler fields for solar post lanterns and high-mast
/ post-mounted floods (with pole height), prompt updated, tests; re-scored baseline.
