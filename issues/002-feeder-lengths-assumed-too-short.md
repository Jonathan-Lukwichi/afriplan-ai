# 002 — Feeder lengths default to 30 m; real routes are 200–250 m

**Priority:** P0 · **Opened:** 2026-09-23 · **Status:** ✅ fixed 2026-09-27 (DWG; PDF when a vector site plan is uploaded)

**Evidence.** PDF baseline, largest quantity errors: `swa_cable|95mm2|4c` 60 m vs 450 m,
`bcew|70mm2` 60 vs 450, `swa_cable|50mm2|4c` 30 vs 150. `AssembleConfig.assumed_feeder_m
= 30.0` in `api/agent/pdf_pipeline/passes/assemble.py`. SLDs rarely print route lengths; the
reference measured them from the site plan (`reports/audits/wedela-drawing-sufficiency.md`:
the PDF set has no site plan).

**Acceptance.** Feeder length taken from the site plan when uploaded (route measurement),
else a documented per-project default with a HIGH gap and a request for the site plan;
feeder qty accuracy measurably up in a re-scored baseline.

## Resolution
- The electrical site plan is `WD-OL-001` (filed as an "SLD"): dashed cable routes
  (DASHED2, layer 0), DB symbols (rectangle + diagonal), tags *"DB-AB1 Fed from DB-PFA"*
  and the designer's run lengths (*"35m"*). The architectural site plan has no routes.
- `api/agent/shared/routes.py` — pure geometry used by both pipelines: route graph
  (snapped ends, T-junctions, straight legs), tag → symbol anchoring (with a warning when
  a tag is about as close to another board's symbol), scale from the drawing or from the
  designer's lengths, shortest route per feeder, trench union, plotter-dash rebuilding.
- DXF: `passes/site_routes.py` + `run_dxf_project(files)` — the whole DWG set is one run;
  SLD feeders take the measured route + 5 % + 1.5 m per end (INFERRED + low gap); a trench
  shared by several feeders is billed once; feeders with no drawn route stay assumed with a
  HIGH gap; SLD-vs-site-plan disagreements are gaps. The kiosk SLD's mini-sub supply
  (95 mm² 4c SWA) is now read as a feeder.
- PDF: `passes/site_routes.py` reads vector site-plan PDFs (dash patterns or plotter
  strokes; scale from "1:N" or the written lengths). R 0 — the LLM measures nothing.
- Web: Upload accepts a whole DWG set; Take-off shows each drawing's role and the site plan used.

**Result (Wedela, project-level RS):** DXF 12.8 % → **44.6 %** (+completer 45.3 %).
Ablation: one-project run 28.4 %, + kiosk supply 32.5 %, + site-plan routes 44.6 %
(quantity accuracy 53 % → 73 %). Validated on the real site plan plotted to an A1 PDF:
the four clearly drawn feeders read within ~5 % of the DWG measurement.

**Still open.** Tag → symbol attribution where tags sit far from their symbol (AB1/AB2,
PFA) is flagged, not solved — leader lines from tag to symbol would settle it. DB-SGH has
no drawn route in the DWG. The Wedela PDF set has no site plan, so PDF feeders stay assumed.
