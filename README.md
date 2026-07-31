# AfriPlan Web

FastAPI + React rewrite of **AfriPlan Electrical** — a dual-pipeline
electrical Bill-of-Quantities extractor for South African contractors.
Upload a PDF drawing set, a DXF/CAD export, or both; get a SANS
10142-1:2017-checked, priced, tender-grade BoQ.

This is a new, separate project. The original Streamlit app it's rewritten
from keeps running unchanged. See [`CLAUDE.md`](CLAUDE.md) for the critical
architectural decisions carried over (and the ones deliberately changed).

## Status

Under active build, phase by phase:

- [x] Phase 1 — repo scaffold, independence-rule test harness
- [x] Phase 2 — public Landing page, demo Login gate
- [x] Phase 3 — shared types + core config/pricing/standards ported
- [x] Phase 4 — DXF pipeline
- [ ] Phase 5 — PDF pipeline
- [ ] Phase 6 — cross-pipeline comparison (resurrected as a real feature)
- [ ] Phase 7 — BOQ Generation, export, email delivery
- [ ] Phase 8 — design system
- [ ] Phase 9 — Live Pricing
- [ ] Phase 10 — responsive E2E harness
- [ ] Phase 11 — SQLite persistence
- [ ] Phase 12 — verification against real fixtures

## Run it

```powershell
cd api; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt; python main.py
npm install; npm run dev
```

Then open http://localhost:5173 — the Landing page, then Sign in (demo
credentials are pre-filled) takes you into the app.
