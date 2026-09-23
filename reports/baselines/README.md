# Baselines — how good is the output, honestly?

Scored with the frozen scorer (`evaluation/metrics.py`, ADR-0003) against the Wedela
reference BOQ — its priced building lines (excl. contingency, VAT, P&Gs).
Reproduce any row with the command shown; saved runs re-score at R 0 with `--from-runs`.

| Date | Pipeline | View | **RS** | Coverage | Precision | Qty acc | Report |
|---|---|---|---:|---:|---:|---:|---|
| 2026-09-23 | DXF | project-level | **2.4 %** | 20.2 % | 100 % | 12.1 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | DXF + completer | project-level | **3.4 %** | 23.3 % | 100 % | 14.6 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | DXF | per building | **1.8 %** | 19.9 % | 99.7 % | 9.2 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | PDF | project-level | **16.9 %** | 50.9 % | 70.5 % | 33.2 % | [pdf](2026-09-23-wedela-pdf.md) |
| 2026-09-23 | PDF | per building | **10.3 %** | 30.4 % | 65.4 % | 34.0 % | [pdf](2026-09-23-wedela-pdf.md) |

PDF run: 18 pages, R 18.46, 687 s (run `b0a84e5563bf`). DXF: 17 drawings, R 0.

## What the numbers say
1. **The value of an electrical bill sits in the SLD and the routes, not the symbols.**
   Feeders, DBs, trench and earth ≈ 57 % of Wedela's value; site lighting ≈ 17 %; the
   fittings/outlets/switches our pipelines count well ≈ 6 %. A perfect symbol counter
   alone would score below 10 %.
2. **DXF (2.4 %)** — reads nothing from any SLD drawing ([issue 001](../../issues/001-dxf-sld-yields-nothing.md)),
   double-counts DBs across drawings (27 vs 10, [005](../../issues/005-dxf-db-double-counted.md)),
   counts legend glyphs as switches ([006](../../issues/006-legend-glyphs-counted-as-instances.md)).
3. **PDF (16.9 %)** — reads the SLD (DBs, feeders matched) but assumes 30 m feeders where the
   real routes are 200–250 m ([002](../../issues/002-feeder-lengths-assumed-too-short.md)), cannot
   report solar post / high-mast site lighting ([003](../../issues/003-site-lighting-not-in-takeoff-schema.md)),
   and prices DBs ~40× low ([004](../../issues/004-db-and-kiosk-rates-far-below-reference.md)).
4. **Scoped vs full** differs little: the missing value is mostly *reproducible* from the
   uploaded drawings — the gap is the pipelines, not the inputs (except site-plan items
   for the PDF set; see `reports/audits/wedela-drawing-sufficiency.md`).
5. **Completer** adds +1 point to DXF (derived boxes/chasing/conduit); 0 for PDF until
   lines carry their building ([008](../../issues/008-pdf-building-attribution.md)).

## Reproduce
```bash
python scripts/verify_data.py wedela
python scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<date>-wedela-dxf.md
python scripts/run_baseline.py --project wedela --pipeline pdf --from-runs b0a84e5563bf --out reports/baselines/<date>-wedela-pdf.md
```
(`runs/` is gitignored — keep the run JSONs if you want to re-score without paying.)

## Rule
A change that claims an improvement adds a new dated row here, same manifest, same scorer.
A scorer/taxonomy change (ADR-0003) re-scores every row in the same commit.
