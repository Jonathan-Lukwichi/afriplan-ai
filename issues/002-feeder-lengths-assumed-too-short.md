# 002 — Feeder lengths default to 30 m; real routes are 200–250 m

**Priority:** P0 · **Opened:** 2026-09-23

**Evidence.** PDF baseline, largest quantity errors: `swa_cable|95mm2|4c` 60 m vs 450 m,
`bcew|70mm2` 60 vs 450, `swa_cable|50mm2|4c` 30 vs 150. `AssembleConfig.assumed_feeder_m
= 30.0` in `api/agent/pdf_pipeline/passes/assemble.py`. SLDs rarely print route lengths; the
reference measured them from the site plan (`reports/audits/wedela-drawing-sufficiency.md`:
the PDF set has no site plan).

**Acceptance.** Feeder length taken from the site plan when uploaded (route measurement),
else a documented per-project default with a HIGH gap and a request for the site plan;
feeder qty accuracy measurably up in a re-scored baseline.
