# 013 — Small correctness / hygiene fixes

**Priority:** P3 · **Opened:** 2026-09-23

- `agent/dxf_pipeline/passes/assemble.py:156` — fitting install ignores `crew`; use
  `core.rate_model.fitting_install_rate(..., crew)` where known.
- `agent/pdf_pipeline/passes/assemble.py:107-111` — switches filed under Power Outlets;
  the legend spec and the reference bill (section D) put them with lighting.
- `pages/1_Upload.py:121` — says DWG needs ODA; LibreDWG is the primary converter.
- `datetime.utcnow()` — 14 call sites, 214 test warnings; use `datetime.now(timezone.utc)`.

**Acceptance.** Each fixed with a test where behaviour changes; warning count ~0.
