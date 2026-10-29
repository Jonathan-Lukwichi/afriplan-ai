# Approach: three layers + check

Adapted for AfriPlan from the playbook's `three-layer-check` pack (2026-10-29). It restates
CLAUDE.md hard rules 4 and 7 as one working method; where they differ, CLAUDE.md wins.

| Layer | What it is | Where it lives in AfriPlan |
|---|---|---|
| 1. Instructions | Plain-English steps for each task | `.claude/skills/` (`estimate-project`, `check-takeoff`, `fix-and-learn`, …), `doe/brain/`, `doe/playbook/` |
| 2. Agent (you) | Read the instructions, run the right engine, handle odd cases, explain the result | this session |
| 3. Engines | Fixed code: same input, same output, every time | `api/agent/` (both pipelines, one pricer), `api/core/` (rates), `doe/execution/project.py`, `scripts/` |
| + Check | Every result is checked before anyone relies on it | `scripts/check_takeoff.py` (`/check-takeoff`), pytest, `scripts/evaluate.py` (the frozen scorer), the `checker` agent |

## Rules
1. **You never do the arithmetic.** Counts, lengths, rates, amounts and totals come only from engine
   or script output. Never type a number that is not in an output or a project file.
2. **Every BoQ line keeps its source** (`source`: EXTRACTED, INFERRED, ASSUMED, PROVISIONAL …).
   Anything estimated carries an `assumption` and a `GapItem` (hard rule 7).
3. **Missing data stays missing.** An unknown symbol, a missing rate or an unclear unit becomes a gap
   for the estimator, never a guess.
4. **Rate and catalogue changes need approval.** Propose edits to `api/core/constants.py`,
   `rate_model.py` or `agent/shared/symbol_catalogue.py`, and wait for a yes.
5. **The result is a draft.** Say "draft for estimator review" until a qualified person signs it off.
6. **Ask before** sending, publishing, deploying, pushing, spending money, or touching client files.
7. **When something breaks, use `fix-and-learn`:** failing test first, fix at the right layer, prove
   it, then write the lesson down.
8. **After any change** to an engine, a rate, the symbol catalogue or a reading skill, run
   `/check-takeoff`. A change that fails it is not finished.

## When this approach is working (keep criteria)
- Counts on the test drawings match the hand counts exactly; lengths within the stated tolerance.
- Every BoQ line has a source; no invented numbers.
- The same drawing run twice gives identical output.
