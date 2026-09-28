# Baselines — how good is the output, honestly?

Scored with the frozen scorer (`api/evaluation/metrics.py`, ADR-0003) against the Wedela
reference BOQ — its priced building lines (excl. contingency, VAT, P&Gs).
Reproduce any row with the command shown; saved runs re-score at R 0 with `--from-runs`.
The per-run reports linked below quote client figures and are kept locally (gitignored).

| Date | Pipeline | View | **RS** | Coverage | Precision | Qty acc | Report |
|---|---|---|---:|---:|---:|---:|---|
| 2026-09-23 | DXF | project-level | **2.4 %** | 20.2 % | 100 % | 12.1 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | DXF + completer | project-level | **3.4 %** | 23.3 % | 100 % | 14.6 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | DXF | per building | **1.8 %** | 19.9 % | 99.7 % | 9.2 % | [dxf](2026-09-23-wedela-dxf.md) |
| 2026-09-23 | PDF | project-level | **16.9 %** | 50.9 % | 70.5 % | 33.2 % | [pdf](2026-09-23-wedela-pdf.md) |
| 2026-09-23 | PDF | per building | **10.3 %** | 30.4 % | 65.4 % | 34.0 % | [pdf](2026-09-23-wedela-pdf.md) |
| 2026-09-26 | DXF (+SLD reader, legend fix) | project-level | **12.8 %** | 59.3 % | 82.3 % | 21.6 % | [dxf](2026-09-26-wedela-dxf.md) |
| 2026-09-26 | DXF + completer | project-level | **13.5 %** | 62.4 % | 82.8 % | 21.6 % | [dxf](2026-09-26-wedela-dxf.md) |
| 2026-09-26 | DXF | per building | **11.1 %** | 44.9 % | 80.7 % | 24.6 % | [dxf](2026-09-26-wedela-dxf.md) |
| 2026-09-26 | PDF (+site lighting, DB build-up) | project-level | **17.8 %** | 53.0 % | 41.5 % | 33.6 % | [pdf](2026-09-26-wedela-pdf.md) |
| 2026-09-26 | PDF | per building | **5.6 %** | 17.9 % | 67.7 % | 31.5 % | [pdf](2026-09-26-wedela-pdf.md) |

| 2026-09-27 | DXF (one-project run + site-plan routes) | project-level | **44.6 %** | 61.1 % | 85.1 % | 73.0 % | [dxf](2026-09-27-wedela-dxf.md) |
| 2026-09-27 | DXF + completer | project-level | **45.3 %** | 64.2 % | 85.3 % | 70.5 % | [dxf](2026-09-27-wedela-dxf.md) |
| 2026-09-27 | DXF | per building | **30.7 %** | 60.5 % | 83.4 % | 50.7 % | [dxf](2026-09-27-wedela-dxf.md) |
| 2026-09-27 | PDF (saved 09-26 facts, boards/feeders de-duplicated) | project-level | **17.1 %** | — | 39.2 % | 34.7 % | re-score, R 0 |
| 2026-09-28 | DXF (+ board contents, built-up trench, kiosk) | project-level | **44.8 %** | 61.3 % | 89.0 % | 73.1 % | [dxf](2026-09-28-wedela-dxf.md) |
| 2026-09-28 | DXF + AI symbol names (ADR-0007, run `567266a07a97`, AI R 1.20) | project-level | **46.2 %** | 63.1 % | 84.9 % | 73.3 % | [dxf-ai](2026-09-28-wedela-dxf-ai.md) |
| 2026-09-28 | DXF + AI symbol names + completer | project-level | **49.2 %** | 66.3 % | 85.5 % | 74.2 % | [dxf-ai](2026-09-28-wedela-dxf-ai.md) |
| 2026-09-28 | PDF (Opus 5, pages in parallel, run `41c02f9505b0`, 288 s) | project-level | **27.1 %** | 63.1 % | 96.0 % | 43.0 % | [pdf](2026-09-28-wedela-pdf.md) |
| 2026-09-28 | PDF + completer | project-level | **29.0 %** | 66.3 % | 96.2 % | 43.7 % | [pdf](2026-09-28-wedela-pdf.md) |
| 2026-09-28 | **Combined** DWG + PDF (ADR-0008: DWG set R 0 with remembered AI names + saved PDF run `41c02f9505b0`; exact name matching — AI matcher not run, no API credit) | project-level | **47.2 %** | 63.3 % | 84.6 % | 74.6 % | [combined](2026-09-28-wedela-combined.md) |
| 2026-09-28 | Combined + completer | project-level | **49.2 %** | 66.5 % | 85.5 % | 73.9 % | [combined](2026-09-28-wedela-combined.md) |

PDF runs: 18 pages — `b0a84e5563bf` R 18.46 (09-23), `6d7094fe359b` R 19.31 (09-26). DXF: 17 drawings, R 0.

### 2026-09-28 — one bill from both readers (ADR-0008)
- Both engines now state **findings** and price them with **one pricer**; re-pricing gave the
  identical DWG bill (every line, gap and total) and the identical PDF score (27.1 %).
- **Combined 47.2 %** vs the better single engine (DWG + AI names) 46.2 % and PDF 27.1 %.
  11 PDF pages were paired with their DWG sheet by the words both print; on those sheets the
  DWG's counted symbols and measured wiring replaced the PDF's reading, and the PDF's
  "length assumed" warnings went with the feeders the DWG measured.
- Small gain because Wedela has a DWG for every sheet — the PDF can add little. The gain to
  expect is on projects where some sheets exist only as PDF (needs a second project, issue 014).
- Left for the AI matcher: the PDF's "KIOSK busbar" feeder (a duplicate of the DWG's kiosk supply).

### 2026-09-27 — what changed and what it showed (issues 002, 011)
- **DXF 12.8 % → 44.6 %.** Ablation on the same data, same scorer:
  `main` 12.8 % → whole DWG set as ONE project run (boards/feeders billed once, no layout
  DB duplicates) **28.4 %** → + kiosk SLD's mini-sub supply cable **32.5 %** → + feeder
  lengths and trench measured on the electrical site plan (`WD-OL-001`) **44.6 %**.
  Quantity accuracy 21.6 % → 73.0 %. The baseline now runs the set exactly as a user
  uploads it (`run_dxf_project`), so this number is what the product produces.
- **PDF 17.8 % → 17.1 %** (free re-merge of the saved run's boards/feeders): removing
  duplicate feeders is correct, but each duplicate had added another assumed 30 m —
  accidentally closer to the real routes. The PDF set has no site plan, so its feeder
  lengths remain the limit; a vector site-plan PDF is now measured when uploaded (R 0).
  Rooms could not be re-merged (the saved run has no page numbers) — a new paid run would.

### 2026-09-26 — what changed and what it showed
- **DXF 2.4 % → 12.8 %** (coverage 20 % → 59 %): SLD drawings now yield boards, breakers
  and feeders (issue 001); legend glyphs no longer counted (006). Quantity accuracy is
  now limited by feeder lengths assumed at 30 m vs 200–250 m real routes (issue 002).
- **PDF 16.9 % → 17.8 %**: DB rate ~12× higher (still below the reference average; rate
  accuracy 47 % → 55 %). Precision fell 70 % → 42 % because the model reported **89 pole
  lights** (R 612 k): the drawing legend says *"Outdoor pole light 2300mm, 60W"* while the
  priced bill has solar post lanterns and high-mast posts — a genuine drawing-vs-bill
  difference — and 89 is several times the bill's site-light count, so site lights are
  double-counted across sheets (issue 011).
- **PDF per-building 10.3 % → 5.6 %**: building attribution varies between LLM runs
  (issue 008); treat per-building PDF numbers as unreliable until 008 is fixed.

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
