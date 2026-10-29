---
name: check-takeoff
description: Check AfriPlan's take-off against hand counts on known drawings and report PASS or FAIL per item. Use after any change to an engine, the symbol catalogue, layer aliases, rates or a reading skill; when asked to test or verify the take-off; before a release; and weekly.
---

# check-takeoff

Goal: a clear PASS or FAIL for the take-off, measured on drawings whose correct counts are known.

1. Run `$PY scripts/check_takeoff.py` (`$PY` = the project venv, see CLAUDE.md). It checks:
   - the **synthetic sample** (built on the fly, no client data: 11 downlights, 13 double sockets,
     1 board, 34.25 m of 2.5 mm² cable);
   - every **local case** in `data/takeoff_tests/<name>/raw/`: one `.dxf`/`.dwg` plus
     `expected.csv` (`item,unit,expected,tolerance_pct`, item = an ItemKey such as
     `light_downlight`, `socket_double`, `db`, `surfix|2.5mm2`). These folders are gitignored
     (client data, ADR-0005).
   Each drawing runs through the DXF engine **twice**; the output must be identical.
2. Report the table the script prints, exactly as printed (do not recompute or round), and the
   OVERALL line. A case folder without exactly one drawing and an `expected.csv` is "not tested",
   never a pass.
3. On FAIL, use `/fix-and-learn`. Known today: the sample FAILS (issue 015).

Rules
- Never change an `expected.csv` to make a case pass. A hand count changes only when the user
  confirms it was wrong, and the commit message says so.
- Never copy a client drawing or its counts out of `data/takeoff_tests/`.
- Counts must match exactly; lengths within the row's tolerance.

## In the loop
Step B5 of `.claude/rules/working-loop.md`. PASS → B6, record. FAIL → `fix-and-learn`, then run this again.
