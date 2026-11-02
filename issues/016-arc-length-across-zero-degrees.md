# 016 — A drawn arc that crosses 0° is measured almost a full circle long

> **Status:** FIXED 2026-11-02 (found 2026-10-30 while adding the straight-route measure)

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

**Result (2026-11-02, same 18 files through the running app).** A quarter of the measured wire length was
never drawn. Reading accuracy unchanged at 75.1 %, coverage unchanged at 84.8 %. RS 64.3 % -> 63.7 %, quantity
accuracy 75.8 % -> 75.1 %. The fall is real and expected: a bill prices GP wire by colour, two or three
conductors per run, and we still bill each run once, so the false length was hiding part of that shortfall.
That shortfall is the route take-off's next step (conductors per run), not this issue.
