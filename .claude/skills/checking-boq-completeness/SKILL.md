---
name: checking-boq-completeness
description: Use right after any BoQ is produced (DOE project.py finish, a web-app run, a baseline run) and before it goes to the owner, when asked "is this bill complete / plausible / ready to send", when auditing a human or uploaded bill for missing companion lines, closing items, wrong units or descriptions missing attributes, or when adding such a check to api/audit/boq_rules.py or the Audit a BoQ page. Complements audit-boq (arithmetic, duplicates, roll-ups).
---

# Checking BoQ completeness

## Overview
Before a bill leaves, find what a QS would find in ten minutes: missing companions, ratios that
cannot be right, absent closing items, lines in the wrong shape. **A failed check means re-read the
drawing (or ask) — never scale a number until it passes.** Today `api/audit/boq_rules.py`
`_companion_rules` covers SWA feeders only.

## CK — checks (in order)
Tolerances come from the spread across the public SA bills; rule IDs refer to
`deriving-companion-items/RULES.md`.

Check tolerances are deliberately a little wider than the rule ranges in RULES.md (a band around the
rule), so a bill is flagged only when it is clearly off. Line-shape rules LN-* are in
`writing-sa-bill-lines`; confidence levels in `improving-boq-skills`.

| ID | Check | Pass condition | Severity |
|---|---|---|---|
| CK-0 | Primaries present | every feeder ends at a billed board; switches ⇒ luminaires; points ⇒ circuits on a board; each building has its DB | high |
| CK-1 | Feeder companions (CO-F1–F9) | each SWA size: supply + install equal, terminations = 2 × runs (even), earth unless ECC and of the CO-F3 size, trench + tape if buried — each subject to its gate | medium |
| CK-2 | Earth vs conductors (CO-C4) | circuit earth ÷ GP conductors = 0.50 ± 0.05, per size | medium |
| CK-3 | Conductors vs conduit (CO-C3) | 1.8–2.3 (rule 2.0–2.2) | medium |
| CK-4 | Draw wire vs conduit (CO-C7) | equal ± 5 % when billed | low |
| CK-5 | Boxes vs conduit (CO-C8, C9) | 3–7 m conduit per round box; dome lids = round boxes | low |
| CK-6 | Point floors (CO-C10, C11) | 100×100 ≥ sockets + boxed isolators; 100×50 ≥ switches; round boxes ≥ ceiling lights — unless "complete with box" | medium |
| CK-7 | Appliances (CO-C16) | one isolator per geyser / AC / pump / dryer / signage | medium |
| CK-8 | Circuits | ≤ 10 points per circuit; spare ways ≥ 15 % or the spec's % (`core/standards.py`, currently unused by the pricer) | medium |
| CK-9 | Board/feeder graph | every board fed once, every feeder ends at a board, no board twice (issue 005); SLD vs site-plan "fed from" disagreements listed | high |
| CK-10 | Underground (CO-F8, F9) | backfill = excavation; tape = trench; trench ≤ Σ buried feeder routes | low |
| CK-11 | Closing set (CO-B1–B4) | per building: earthing & bonding, test & COC, as-built; each provisional sum has P&A; VAT on the summary only, once | medium |
| CK-12 | Derived share | derived families ≥ ~10 % of each building's value (issue 007) | medium |
| CK-13 | Line shape (LN-1–LN-4) | unit matches family; required slots present; brand → "or equivalent"; Supply qty = Install qty; "measured elsewhere" points to an existing line; "complete with X" means no separate X | low |
| CK-14 | Arithmetic | ARITH, UNTOTALLED, NO_RATE, DUPLICATE, ROLLUP… (skill `audit-boq`) | high |
| CK-15 | Never silent | every estimated line INFERRED/ASSUMED/PROVISIONAL with `assumption` + GapItem (hard rule 7) | high |
| CK-16 | Density (flag only) | lights ≈ 1 / 10 m², sockets ≈ 1 / 10–15 m²; outside 0.3×–3× → flag | low |

## Running it on our own output (DOE / web)
1. Load the bill (`<folder>/AfriPlan_Output/summary.json`, the run JSON, or `GET /api/audit/run/{id}`).
2. Per building, sum quantities by family with `audit.boq_rules.building_from_boq` (classifies exactly
   like the scorer).
3. Compute the checks in a throwaway script in the session scratchpad — never in the repo, never with
   client figures in a committed file.
4. Write each failure: building · check ID · observed vs expected · which drawing to re-read · severity.
   Lead with high severity, then value at risk. Separate "the drawing differs from the bill" from "we misread".
5. Add the failures to `things_to_check.md`; log any rule that misfired in `FEEDBACK.md`
   (skill `improving-boq-skills`).

## Adding a check as an audit rule
1. Failing test first in `tests/audit_layer/test_boq_rules.py`: one bill that passes, one that fails,
   invented quantities only.
2. A pure function `(RefBuilding) -> List[AuditFinding]` in `api/audit/boq_rules.py` next to
   `_companion_rules`, using `key_family`, `key_spec`, `role`, `unit`; wire it into `_audit_building` and
   `audit_boq`; add the rule code (`COMPANION`, `INVARIANT`, `CLOSING`, `UNIT_FAMILY`, `SLOTS`,
   `ROLE_PAIR`) to the module docstring.
3. Tolerances in one frozen table at the top, citing the CK/CO IDs. `api/audit/` stays LLM-free and
   read-only; families missing from the frozen taxonomy are matched by a local regex inside `api/audit/`
   and proposed in an ADR.
4. Run it on the reference bill too (`scripts/audit_boq.py --project wedela`): a human bill that fails is
   a finding about that bill, not proof the rule is wrong — log it; widen a tolerance only with a second
   consultant's bill (decision table in `improving-boq-skills`).
5. `$PY -m pytest -q -p no:warnings`, `npm run build`, the audit e2e spec if the page changed; check the
   finding shows on **Audit a BoQ** with a clear `suggested_action`.

## Common mistakes
| Mistake | Fix |
|---|---|
| Adding lines by hand to make a check pass | only the pipelines and the completer add lines (INFERRED + gapped) |
| Scoring P&G / provisional sums with the reproduction scorer | they are excluded (context.md); judge them with CK-11 |
| Editing `metrics.py` / `taxonomy.py` so checks pass | frozen (ADR-0003) |

## Version
v1 · 2026-10-29 · from the ANN (loss checks) and CNN (completeness lint) studies.

v2 · 2026-10-29 · first feedback loop: planted-error test (with skills 11/11, baseline 9/11); fixes logged in FEEDBACK.md.
