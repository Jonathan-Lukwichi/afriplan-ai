# 007 — Derived items (boxes, chasing, conduit, wire) never reach the user's BOQ

> **Status:** FIXED 2026-09-26 (d1fff51) — page 3 'Complete with derived items' toggle.

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** Derived families (conduit, trunking, gp_wire, chasing, wall_box, round_box,
draw_wire, termination, trench …) are 12–20 % of each Wedela building bill; neither
pipeline emits them. `audit/completer.py` fills them (INFERRED, LOO-gated) but is only
used by `scripts/run_baseline.py`.

**Acceptance.** Page 3 offers "Complete with fitted derived items" (visibly INFERRED, gaps
listed); pipelines still do not import `audit` (the UI does).
