---
name: improving-boq-skills
description: Use after a scored BoQ run (doe/execution/project.py finish, scripts/evaluate.py), when the user corrects a quantity, item, wording or rule ("that's wrong", "a QS would…", "this is missing"), when an accuracy report or audit shows a gap a BoQ skill should have prevented, when a new reference bill or knowledge source arrives, or when a BoQ skill's rule turns out wrong.
---

# Improving the BoQ skills from feedback

## Overview
The BoQ skills are a learning system. Every rule has an ID and a confidence; every run, test and
correction is evidence for or against a rule. This skill turns that evidence into rule changes —
**the rule follows the evidence, never one project's number.**

Skills in the loop (each has `FEEDBACK.md` beside its `SKILL.md`):
`reading-scope-modifiers` (SM-) · `reading-drawing-symbols` (DS-) · `deriving-companion-items` (CO-,
rules in its `RULES.md`) · `writing-sa-bill-lines` (LN-) · `checking-boq-completeness` (CK-) ·
`consolidating-price-catalogue` (PC-; a price correction is an override row, logged here too).
General lessons also go to `doe/playbook/LESSONS.md`; domain facts to `doe/knowledge/BOQ_KNOWLEDGE.md`.

## Confidence levels (used in every rule table)
| Conf | Means |
|---|---|
| **H** | exact or consistent in ≥ 3 independent sources (different consultants / projects), or confirmed by a person checking the drawing |
| **M** | 2 sources, or 1 source with arithmetic verified across the whole bill |
| **L** | 1 source, a rule of thumb, or US-only practice |

H rules may drive emitted lines (INFERRED). M rules emit ASSUMED lines with a GapItem. L rules only
flag ("thing to check"), never add value to a bill.

## The loop (every time this skill fires)
1. **Collect** what this run or correction showed. Sources, in this order:
   - the user's words (a correction from the owner/QS outranks every other source);
   - `<folder>/AfriPlan_Output/accuracy_report.md` gaps (item, cause, kind of fix) and `things_to_check.md`;
   - audit findings, test failures, a new bill in `doe/knowledge/example_boqs/`.
2. **Attribute** each observation to one rule ID, or `NEW` if no rule covers it. If the miss is a
   code bug (the rule is right, the code ignored it), log it as `code` — it is a fix, not a rule change.
3. **Log** one entry per observation in that skill's `FEEDBACK.md` (format below). Always log, even
   when nothing changes — repeated weak evidence is how L becomes M.
4. **Decide** with the table below. Count entries for the same rule across *different* projects or
   sources; two runs of one project are one source.
5. **Apply** the change: edit the rule row (quantity, range, gate, conf, evidence), bump the skill's
   `Version` line, set the entries' status to `applied vN`. One rule change per edit.
6. **Verify**:
   - text-only change → re-read the edited section against its evidence;
   - rule that code implements → follow `tdd` (failing test first), then re-score with `evaluate-boq` /
     `finish --reference`; keep the change only if Reproduction Score and reading accuracy are not
     worse, or the user accepts a stated trade-off. Report regressions honestly.
7. **Report** to the user in plain words: which rules changed, why, and what stayed open.

## Decision table
| Evidence | Action |
|---|---|
| User correction (explicit) | apply now; source `user YYYY-MM-DD`; conf unchanged unless the user says it is general |
| 1 source contradicts an H/M rule | log `contradicts`, keep the rule, add a "check" note to its row |
| 2+ independent sources contradict | amend the quantity/range or add a gate; lower conf if the sources still disagree |
| Same new pattern in 2+ sources | add a rule at M (or H if ≥ 3) with a new ID |
| A rule caused a wrong line twice and nothing supports it | lower conf (H→M→L); at L it stops emitting |
| Reference bill differs from the drawing | log as `bill-vs-drawing` — do not change a reading rule to match a bill |

## FEEDBACK.md entry format (append, newest last, never delete)
```
### 2026-11-03 · <project or test name> · CO-C8
- Observed: round boxes ÷ conduit was 1 per 9 m on this project's layouts
- Expected: CO-C8 says 1 per 3–7 m
- Evidence: <drawing sheet / page>, accuracy_report item `round_box|20mm`, or "user said …"
- Verdict: contradicts | confirms | new-pattern | code | bill-vs-drawing | unclear
- Status: open | applied v3 | rejected — <why>
```

## Guardrails
- **Public repo** (hard rule 9): no client rand figures or quantities in any skill or FEEDBACK file —
  write ratios, rule IDs, sheet numbers, item keys. Grep before every commit.
- **Never tune to one project**: a range moves only with a second independent source (or a user
  correction). Wedela measures rules; it never sets them.
- **The scorer is frozen** (ADR-0003): never edit `api/evaluation/metrics.py` or `taxonomy.py` to make
  a skill look right.
- **Rule IDs are permanent**: retire a rule by marking it `retired vN — <why>`, never reuse its ID.
- Schema, new dependency, paid API runs: still **ask first** (CLAUDE.md guardrails).

## Common mistakes
| Mistake | Fix |
|---|---|
| Rewriting a rule after one run "because it scored better" | log it; wait for a second source |
| Logging "the bill is missing X" with the client's quantity | log the ratio or the rule ID only |
| Changing a reading rule because the reference bill differs | check the drawing first; often the bill differs from the drawing |
| Editing several rules in one go, then re-scoring | one rule per change, so the score change has one cause |

## Version
v1 · 2026-10-29 · created from the transformer / CNN / ANN study of `doe/knowledge/`.
