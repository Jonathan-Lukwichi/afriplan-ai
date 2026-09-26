# 004 — DB and kiosk prices are 20–50× below the reference

> **Status:** FIXED 2026-09-26 (cd9e2be) — core.rate_model.db_build_up prices complete boards (PDF + DXF SLD).

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** PDF baseline: `db` predicted rate ~40× below the reference average; DXF uses a
nominal fixed enclosure price (`agent/dxf_pipeline/passes/assemble.py`, `db_enclosure_price`). A real
DB line includes MCCB incomer, surge arrestors, breakers and busbars, not just an
enclosure.

**Acceptance.** DB rate built from the SLD contents (incomer + breakers + protection +
enclosure) in `core/rate_model.py`; rate accuracy for `db` ≥ 70 % on Wedela.
