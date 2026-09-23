---
name: tdd
description: Force test-driven development — one behaviour at a time, red then green then refactor. Use for any behaviour change in this repo.
---

# tdd

Work strictly test-first, one behaviour at a time.

1. **RED.** Write ONE failing test for a single behaviour. Run it. Confirm it fails for
   the RIGHT reason (not an import error or typo).
2. **GREEN.** Write the minimal code that makes it pass. Nothing more.
3. **REFACTOR.** Clean up with the test as a safety net; keep it green.

Rules
- One behaviour per cycle.
- Never modify a test to make failing code pass. If a test is wrong, fix it deliberately
  and say so in the commit message.
- Prefer testing at the boundary of a deep module (`score()`, `audit_reference()`,
  `run_dxf_estimator()`), not every helper.
- Use real strings from real drawings/bills as fixtures (the taxonomy tests do this).
- Tests must not hit the network; tests needing `data/projects/*/raw/` use
  `pytest.mark.skipif(not raw_available(...))`.
- After each green: `python -m pytest -q -p no:warnings` (full suite) before committing.

Test locations: `tests/<pipeline>/unit/`, `tests/shared/`, and `tests/<layer>_layer/`
for top-level packages (never `tests/evaluation/` — it would shadow the package).
