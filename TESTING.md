# How to test AfriPlan (product walkthrough)

## Start the app
```bash
python scripts/dev.py start     # macOS/Linux: python3 — backend :8000 + frontend :5180
```
(First time on a machine: `python scripts/dev.py setup`. To start the servers by hand, see README.)
Open **http://127.0.0.1:5180**, click *Sign in* (demo login, pre-filled).
The PDF path needs `ANTHROPIC_API_KEY` in `api/.env` (≈ R 2.50 per page with Claude Opus 5). DXF/DWG is free.
Wedela test files live in `data/projects/wedela/raw/` (local only — client data).

## Test 1 — Audit any BOQ (instant, free)
Menu **Audit a BoQ** → choose `Wedela BOQ Rev01 141125.xlsx` → **Audit this BoQ**.
Expect 9 bills, ~33 findings ranked by value at risk: priced install lines left out of
section totals, a duplicated DB line, a contingency not added to a total, two sheets
not rolled into the summary, broken `#REF!` cells.

## Test 2 — the whole CAD set → priced BOQ (free, ~1–2 min)
**Upload** → DXF / DWG → open `Wedela Electrical/`, select **all** the `.dwg` files
(Ctrl+A) → *Run DXF engine*.
- **Take-off**: the **Drawing set** panel lists each drawing as SLD / layout / site plan and
  says *Feeder routes measured on WD-OL-001…* with the number of feeders priced on them.
  The older `WD-PB-01-LIGHTING 100225` shows *skipped — older revision* (same sheet as the
  `100425` issue; reading both would bill the pool lights twice) and the gap report says so.
- **BoQ → Line items**: e.g. *SWA feeder MINI-SUB→KIOSK* priced on the measured route
  + 5 % + 1.5 m per end (its assumption says so); trench billed once where feeders share it. Feeders the site plan
  does not draw (DB-SGH, the pool pump boards) stay at an assumed 30 m — the **Gap report**
  says so, and says where the site plan and the SLD disagree (DB-AB1's source).
- *Extra markup %* starts at 0; **Audit** tab; Excel and PDF from *Export & email*.
One drawing alone still works (e.g. `WD-PB-01-SLD 100425.dwg`): then feeders are assumed
and the gap report asks for the site plan. Turn *Complete with derived items* on/off —
wall boxes, chasing, conduit and wire appear as `inferred` lines.

## Test 3 — PDF drawing set → priced BOQ (≈ 5 min, ≈ R 45 for the 18 Wedela pages)
**Upload** → PDF → both Wedela PDFs → run. Check the per-file classification, coverage
(site plan missing), legend, gap report; then BoQ as above.

## Test 4 — Compare and Live Pricing
Upload **Both** (a DWG + the PDFs) → **Compare**. From a BoQ → **Pricing**: request quotes
from the 4 mock suppliers and apply one.

## Automated checks
```powershell
# Windows (PowerShell)
api\.venv\Scripts\python.exe -m pytest -q -p no:warnings     # backend + evaluation + audit
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"; npm run build; npx playwright test   # browser
```
```bash
# macOS / Linux
api/.venv/bin/python -m pytest -q -p no:warnings
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run build && npx playwright test
```

## Known gaps (see `issues/`)
Feeder lengths are measured only when the electrical site plan is in the upload (DWG, or
a vector PDF — a scanned PDF cannot be measured); tags sitting between two symbols are
flagged, not guessed. PDF lines are not yet split per building (008); site lights drawn
on several PDF sheets are flagged, not merged (011); one reference project only (014).
