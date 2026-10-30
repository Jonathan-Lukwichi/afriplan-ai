---
name: deriving-companion-items
description: Use when adding, changing or reviewing derived (never-drawn) BoQ lines — conduit, GP wire and circuit earth, draw wire, round/wall boxes, dome lids, engraving, chasing, isolators, cable terminations and joints, feeder earth, trench, backfill, tape, sleeves and seals, lightning, per-bill closing items — in api/agent/shared/pricing.py, api/audit/completer.py or api/evaluation/ratios.py, or when an accuracy report blames "derived material not produced".
---

# Deriving companion items

## Overview
A QS never counts a dome lid — he writes "lids = round boxes". Many SA bill lines are **functions of
other lines**, and most wiring material is a function of the **route**, not the point count. The rules
live in [RULES.md](RULES.md) (IDs `CO-F*`, `CO-C*`, `CO-B*`, each with quantity, gate, confidence and
evidence). This skill says how to apply them without breaking the hard rules.

Read first: `doe/knowledge/BOQ_KNOWLEDGE.md` §3–6 (convention A, route take-off), ADR-0002, ADR-0008.

## Where the change goes
| You want to… | File |
|---|---|
| Emit a companion in every bill (web app + DOE) | a pure module in `api/agent/shared/` (e.g. `companions.py`), called from `price_findings` in `agent/shared/pricing.py` — no import of `audit`/`evaluation` (hard rule 3) |
| Flag a missing companion in any bill | `api/audit/boq_rules.py` — skill `checking-boq-completeness` |
| Fill from fitted client ratios (local only) | `api/audit/completer.py` — keep as the fallback, never the only source |
| Measure how wrong a prior is | two-layer ratio specs in `api/evaluation/ratios.py` (`gp_wire ← conduit`, `round_box ← conduit`, …) |

Adding route/drop/ECC fields to `findings.py` or lines to `BillOfQuantities` → **ask first** (public schema).

## How to emit a derived line (never silent — hard rule 7)
- Only rules at conf **H** emit INFERRED lines; **M** rules emit ASSUMED lines + GapItem; **L** rules only flag.
- `source = INFERRED` when computed from measured/counted primaries; `ASSUMED` when it rests on an
  allowance (CO-C2, CO-F6, CO-B*); sums are `PROVISIONAL`.
- `assumption` names the rule ID, the formula and the inputs:
  `"CO-C7: draw wire = total conduit (20mm PVC + 20mm galv)"`.
- One `GapItem` per building per rule family; `building_block` and `drawing_ref` = the primary's.
- Prices only from `core/rate_model.py` / `core/constants.py`; a missing price → GapItem, not a guess.
- **No double count**: if a reader already counted the companion, that finding wins (evidence rank
  measured > counted > written > seen > assumed); the rule only checks it.
- Check the gate first (skill `reading-scope-modifiers`): ECC cable, "complete with boxes", "excavations
  by builder", surfix wiring all switch rules off or change them.

## Known gaps in the code today (verify before relying on them)
| Gap | Where | Rule |
|---|---|---|
| Earth added to every feeder, also ECC cable | `pricing.py` `_feeder_lines` | CO-F2 |
| Earth sizes differ from the bills (4→6, 16→10, 240→70) | `core/rate_model.py` `earth_size_for` | CO-F3 (check SANS 10142-1 first) |
| All final wiring priced as one surfix line | `pricing.py`, both `assemble.py` | CO-C3–C6 |
| Completer adds nothing without the local client ratio model | `audit/completer.py` | all |
| No closing items emitted (`BQSection.EARTHING`, `TESTING` unused by pricers) | `pricing.py` | CO-B1–B3 |

## Procedure (one rule at a time)
1. Pick ONE rule ID. Failing test first (skill `tdd`) with a synthetic `Findings` — invented numbers,
   never client data. Pricing tests: `tests/shared/`; audit: `tests/audit_layer/`.
2. Implement as a pure function `(findings, context) -> lines + gaps`; keep weights in one frozen table
   that cites the rule ID.
3. `$PY -m pytest -q -p no:warnings`.
4. Re-score (skill `evaluate-boq`, or `finish --reference wedela`): RS, coverage, **precision**
   (companions can lower it when the reference bill omits them), reading accuracy. Report regressions.
5. Log the result in `FEEDBACK.md` and run `improving-boq-skills`.

## Common mistakes
| Mistake | Fix |
|---|---|
| Fitting a ratio to Wedela and hard-coding it | priors come from the public bills; Wedela only measures them |
| Adding waste to the quantity | waste stays in the rate |
| Letting the LLM estimate wire | the reader reports route/counts; Python derives (ADR-0002) |
| Adding a taxonomy family for a new companion | needs an ADR (ADR-0003); unscored lines are fine |

## Version
v1 · 2026-10-29 · rules from the transformer + ANN + CNN studies (they agreed independently on CO-C4, CO-C7, CO-C9, CO-F2, CO-F4).

v2 · 2026-10-29 · first feedback loop: planted-error test (with skills 11/11, baseline 9/11); fixes logged in FEEDBACK.md.
