# How to test AfriPlan (product walkthrough)

## Start the app (two terminals)
```powershell
# 1. Backend — http://127.0.0.1:8000
cd api; .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
# 2. Frontend — http://localhost:5173
npm run dev
```
Open **http://localhost:5173**, click *Sign in* (demo login, pre-filled).
The PDF path needs `ANTHROPIC_API_KEY` in `api/.env` (≈ R 1 per page). DXF/DWG is free.
Wedela test files live in `data/projects/wedela/raw/` (local only — client data).

## Test 1 — Audit any BOQ (instant, free)
Menu **Audit a BoQ** → choose `Wedela BOQ Rev01 141125.xlsx` → **Audit this BoQ**.
Expect 9 bills, ~33 findings ranked by value at risk: priced install lines left out of
section totals, a duplicated DB line, a contingency not added to a total, two sheets
not rolled into the summary, broken `#REF!` cells.

## Test 2 — CAD drawing → priced BOQ (free, ~20 s)
**Upload** → DXF/CAD → `Wedela Electrical/WD-PB-01-SLD 100425.dwg` → run.
- **Take-off**: status passed; **Drawing coverage** says an SLD was recognised and asks
  for the lighting layout, plug layout and site plan.
- **BoQ**: boards DB-CR / DB-PFA priced as complete boards; feeders with earth,
  terminations and trench (lengths **assumed 30 m** — see the Gap report); *Extra markup %*
  starts at 0; **Audit** tab; download Excel and PDF from *Export & email*.
Repeat with `WD-AB-01-LIGHTING 250325.dwg` and turn *Complete with derived items* on/off —
wall boxes, chasing, conduit and wire appear as `inferred` lines.

## Test 3 — PDF drawing set → priced BOQ (≈ 12 min, ≈ R 20)
**Upload** → PDF → both Wedela PDFs → run. Check the per-file classification, coverage
(site plan missing), legend, gap report; then BoQ as above.

## Test 4 — Compare and Live Pricing
Upload **Both** (a DWG + the PDFs) → **Compare**. From a BoQ → **Pricing**: request quotes
from the 4 mock suppliers and apply one.

## Automated checks
```powershell
api\.venv\Scripts\python.exe -m pytest -q -p no:warnings     # backend + evaluation + audit
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"; npm run build; npx playwright test   # browser
```

## Known gaps (see `issues/`)
Feeder route lengths need a site plan (002); PDF lines are not yet split per building
(008); site lights can be double-counted across sheets (011); one reference project only (014).
