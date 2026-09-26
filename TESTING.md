# How to test AfriPlan (product walkthrough)

Start the app:

```bash
streamlit run app.py          # opens http://localhost:8501
```
The PDF path needs `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml` (≈ R 1 per page).
The DXF/DWG path is free. Wedela test files are in `data/projects/wedela/raw/` (local only).

## Test 1 — PDF drawing set → priced BOQ (≈ 12 min, ≈ R 20)
1. **Upload** → *PDF drawings* → drop `Wedela SLD 260525.pdf` and `Wedela Lighting&Plugs 260525.pdf` → *Continue*.
2. **Extraction** → *Run PDF estimator*. Check:
   - each file's type (SLD / lighting layout) and confidence;
   - **🧩 Drawing coverage** — should say a **site plan** is missing (unlocks sleeves, manholes, true feeder routes);
   - **📖 Legend** and the **gap report** (every assumed feeder length is listed).
3. **BOQ** → check:
   - *Complete with derived items* is ON: wall boxes, chasing, conduit, GP wire lines appear, tagged `inferred`;
   - *Extra markup %* starts at **0** (rates already include markup);
   - **🔎 BOQ audit** — feeders without earth/terminations etc.;
   - DB lines are priced as complete boards (R 10 k–40 k), site lighting (solar posts, high-mast) appears if drawn;
   - download Excel / PDF / JSON.

## Test 2 — CAD (DWG) → priced BOQ (free, ~20 s per file)
1. **Upload** → *DXF / CAD* → pick e.g. `Wedela Electrical/WD-PB-01-SLD 100425.dwg` → *Run DXF estimator*.
   Expect boards DB-CR / DB-PFA with breaker counts, and feeders (95/70/50/35 mm²) with earth,
   terminations, trench — lengths **assumed 30 m** and flagged (the SLD has no route lengths).
2. Repeat with `WD-AB-01-LIGHTING 250325.dwg` — switches counted **without** the legend glyphs.

## Test 3 — Audit any BOQ (free, instant)
**Audit a BOQ** → upload `data/projects/wedela/raw/Wedela BOQ Rev01 141125.xlsx`.
Expect ~33 findings: priced install lines left out of section totals (Swimming Pool), a
duplicated DB line, Storage contingency not added to its total, two sheets (minisub,
Pool-Heat Pumps) not in the summary. Download the report.

## Test 4 — Live Pricing
After Test 1 or 2, **Live Pricing** → request quotes from the 4 mock suppliers → apply the
best quote to a line → back on **BOQ** the line shows the live price. (Suppliers are
simulated until real supplier connections exist.)

## What is known to be incomplete (see `issues/`)
- Feeder route lengths need a site plan (issue 002); until then they are assumed and flagged.
- A single upload is scored per project, not split per building (issue 008).
- The pipelines are measured against Wedela only; a second reference project is needed (issue 014).

## For developers
```bash
python -m pytest -q -p no:warnings                      # all tests incl. headless page smoke tests
python scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<date>-wedela-dxf.md
```
