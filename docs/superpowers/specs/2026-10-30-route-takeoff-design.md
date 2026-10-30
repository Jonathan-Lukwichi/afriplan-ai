# Route take-off: convention-A wiring lines from measured routes — design

Status: **draft for the owner's approval** (2026-10-30). Nothing is built yet.

## Why
South African bills price final-circuit wiring **material by material** (convention A,
`doe/knowledge/BOQ_KNOWLEDGE.md` §3): conduit by diameter, GP wire by size and colour, circuit earth,
draw wire, wall and round boxes, chasing. AfriPlan emits **one "reticulation wire" line per circuit**,
priced as 3-core surfix (`agent/shared/pricing.py::_wire_line`). Wedela's biggest losses include exactly
these items ("derived material not produced", GP wire too low, BCEW and 20 mm conduit missing). The
completer only fills them from client ratios, locally (`audit/completer.py`).

## What already exists (build on it, do not duplicate)
- **The rules**: `.claude/skills/deriving-companion-items/RULES.md`, `CO-C1`…`CO-C20`, each with formula,
  gate, confidence (H/M/L) and evidence from public bills; and the skill's procedure (one rule at a
  time, test first, re-score). These live on the other session's branch
  `feat/boq-skills-and-price-catalogue` (not yet pushed or merged): **this work starts after that
  branch is merged into `main`** (see Order of work).
- **Measurement**: the DXF engine already measures drawn wiring per circuit (`rec.cable_length_m_by_circuit`,
  the horizontal route R, exact on the sample since issue 015) and counts every symbol by category.
  The PDF engine has points per room and ceiling height, and `core/rate_model.py` has
  `routed_length`, `classify_point`, `average_length_per_point`.
- **The check**: `/check-takeoff` (hand counts) and the frozen scorer (`evaluate-boq`).

## Design
1. **One pure module** `api/agent/shared/companions.py`: `(findings, context) -> (lines, gaps)`, called
   from `price_findings`. Both engines get it, so web app and DOE bill the same way. No import of
   `audit`/`evaluation` (hard rule 3). Weights in one frozen table citing the rule ID.
2. **Inputs per circuit** (the route take-off, BOQ_KNOWLEDGE §4):
   - R — horizontal route: measured on CAD (DXF), else the CO-C2 allowance (ASSUMED + gap).
   - D — drops: one per wall point (switch, socket, isolator), ceiling height − mounting height
     (defaults stated in the config: sockets 0.5 m, switches 1.2–1.4 m; ceiling from the drawing, else 3 m, ASSUMED).
   - kind (lighting / power / dedicated), points by type, ceiling points.
3. **Rules, in this order** (each its own test-first step; H rules emit INFERRED lines, M rules
   ASSUMED + GapItem, L rules only flag):
   CO-C1 conduit = R + D · CO-C5 sizes · CO-C3 GP conductors (2.0 × conduit; 2.2 lighting with switch legs)
   · CO-C6 colours (M) · CO-C4 earth = Σ conductors ÷ 2 per size · CO-C7 draw wire = conduit
   · CO-C10/C11 wall boxes = switches / sockets + isolators · CO-C8 round boxes (M) and CO-C9 lids
   · CO-C15 chasing per drop (M, wall gate).
4. **The surfix line goes away when conduit wiring is emitted**: the gate is `wiring_method`; surfix
   drawings keep today's line. No double counting: a counted companion (a finding) wins over a rule.
5. **Prices** only from `core/constants.py` / `rate_model.py`; a missing price is a GapItem.

## Decisions for the owner (each changes what gets built)
1. **Schema change (ASK FIRST in CLAUDE.md):** `WireFinding` needs drops, kind, and points by type
   (or a new `RouteFinding`). OK to extend `agent/shared/findings.py`?
2. **Precision may fall** where the reference bill omits a companion; RS should rise. Accept a lower
   precision for a higher RS, measured on Wedela?
3. **Which rules first:** I propose the H rules only (C1, C3, C4, C5, C7, C10, C11) in the first
   pass, then the M rules after a Wedela re-score.

## Order of work
0. Merge `feat/boq-skills-and-price-catalogue` into `main` (5 conflicting files: CI, CLAUDE.md,
   `estimate-project` skill, `Navbar.jsx`, `Landing.jsx`), by one session.
1. Owner answers the three decisions above.
2. A plan in `docs/superpowers/plans/` (writing-plans), one task per rule.
3. Each rule: failing test with synthetic findings → pure function → pytest → `/check-takeoff` →
   Wedela re-score (RS, coverage, precision, reading accuracy), regressions reported.

## Done when
- A DXF drawing with measured wiring bills conduit, GP wire per size, earth, draw wire and boxes,
  each with its rule ID in the assumption; no surfix line for conduit-wired drawings.
- Wedela DXF RS up, with any precision drop reported; `/check-takeoff` still PASS.
