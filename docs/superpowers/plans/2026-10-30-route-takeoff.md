# Plan: route take-off, high-confidence rules first

> **Status 2026-10-30: PAUSED after task 1** (by the plan's own stop rule — the evidence went against it).
> Task 1 (CO-C1) is built and tested, but on Wedela it adds no RS (44.8 % → 44.8 %; coverage +1.9,
> precision +0.4, quantity accuracy −2.2): the DXF's drawn wiring ≈ 2.85 × the bill's conduit, and the
> bill's GP wire ≈ 5.0 × its conduit (part of the wiring runs in trunking). Also DXF wires file the
> circuit label as their building, so drops were 0. Logged in `deriving-companion-items/FEEDBACK.md`.
> **Before task 2:** (a) DXF wires carry the real building; (b) split the route by containment
> (conduit vs trunking) from layers/legend; (c) re-score task 1. Not merged into `main`.

Spec: `docs/superpowers/specs/2026-10-30-route-takeoff-design.md` (approved 2026-10-30: findings
schema may be extended; precision may drop for a higher RS, measured; H rules first).
Rules: `.claude/skills/deriving-companion-items/RULES.md`. Branch `feat/route-takeoff`.

Each task: failing test with synthetic findings (`tests/shared/test_companions.py`, invented numbers)
→ the smallest code in `api/agent/shared/companions.py` → full pytest → `/check-takeoff` → Wedela DXF
re-score (`run_baseline.py --project wedela --pipeline dxf`, data linked locally, link removed after),
RS / coverage / precision reported against 44.8 % / 61.3 % / 89.0 % → commit.

| # | Rule | What | Line |
|---|---|---|---|
| 1 | CO-C1 | conduit = R (measured wiring per circuit) + D (one drop per wall switch/socket/isolator: ceiling − mounting height) | `20mm PVC conduit`, m, INFERRED; heights in the assumption; a gap when the ceiling height is assumed |
| 2 | CO-C3 + C5 | GP conductors = 2.0 × conduit per size (1.5 lighting, 2.5 power); replaces the surfix wire line for conduit wiring | `1.5mm² / 2.5mm² GP wire`, m |
| 3 | CO-C4 | circuit earth = Σ conductors ÷ 2 per size | `BCEW 1.5mm² / 2.5mm²`, m |
| 4 | CO-C7 | draw wire = conduit m | `Draw wire`, m |
| 5 | CO-C10/C11 | wall boxes: 100×50 = switches; 100×100 = sockets + isolators | No |

Rules for every task: a counted companion (an existing finding) wins and the rule only checks it;
prices only from `core/constants.py` (no price → line priced 0 + a GapItem "unpriced"); never in the
quantity: waste. Stop and report if a task drops Wedela RS.
