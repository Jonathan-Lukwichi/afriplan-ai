# 016 — A drawn arc that crosses 0° is measured almost a full circle long

> **Status:** OPEN (found 2026-10-30 while adding the straight-route measure)

**Priority:** P2 · **Opened:** 2026-10-30

**Evidence.** `api/agent/dxf_pipeline/passes/recognize.py::_arc_len` computes the sweep as
`abs(end_angle − start_angle) % 360`. DXF arcs run counter-clockwise from start to end, so an arc from
350° to 10° sweeps 20°, but the formula gives 340°: that arc's wiring is measured 17× too long. The new
`_arc_chord` (route take-off) uses the correct sweep, `(end − start) % 360`.

**Why not fixed with the route take-off.** It changes the measured length of every wire line (the
`reticulation wire` lines, scored as GP wire) on drawings with such arcs, so it must be measured on its
own against the Wedela baseline, not mixed into another change.

**Acceptance criteria.**
1. A failing test: an arc from 350° to 10° of radius r measures `r × 20° in radians`.
2. `_arc_len` uses `(end − start) % 360`.
3. Wedela DXF re-scored before and after; the change in RS, coverage and quantity accuracy reported.
