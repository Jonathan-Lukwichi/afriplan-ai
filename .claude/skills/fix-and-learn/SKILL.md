---
name: fix-and-learn
description: Fix a failing engine, a failing /check-takeoff, or a quantity, symbol or rate the user corrected, and make the fix permanent. Use when a run errors, check-takeoff fails, or the user says a count, length, symbol or rate is wrong.
---

# fix-and-learn

Goal: the problem is fixed at the right layer, proven, and written down so it does not come back.

1. **Read the error or the correction in full.** Say in one sentence what went wrong.
2. **Find the layer** (`.claude/rules/three-layer-approach.md`):
   - wrong steps or order → the skill or `doe/brain/` (instructions)
   - unknown symbol, wrong item name, missing rate → `agent/shared/symbol_catalogue.py`, `legend.py`,
     `api/core/constants.py` (ask before editing)
   - wrong count, length or calculation → the engine (`api/agent/...`)
3. **Failing test first** (`.claude/skills/tdd/`): a test that shows the problem, failing for the
   right reason. If a test drawing would show it, propose one with its hand counts; the user
   confirms the counts.
4. **Make the smallest fix** at that layer.
5. **Prove it:** the new test passes, the full pytest suite passes, and `/check-takeoff` passes.
6. **Write it down:** a DOE lesson goes in `doe/playbook/LESSONS.md`; a decision with lasting
   consequences gets an ADR in `docs/adr/`; a known defect not fixed now goes in `issues/`.
7. **Stop after 3 attempts** that do not pass. Report what you tried and what you think is wrong.

Rules
- Never change a test's expected values to make it pass. Expected counts change only when the user
  confirms a hand count was wrong, and the commit message says so.
- Ask before anything that costs money or touches client files.

## In the loop
Entered from A4 or B5 when something fails. Next: back into the check that failed (A3 or B5); after 3 failed attempts, stop and report.
