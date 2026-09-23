---
name: audit-boq
description: Audit a Bill of Quantities (human or pipeline) for arithmetic errors, unpriced or untotalled lines, duplicates, roll-up and contingency errors, orphan sheets and missing companion items; and audit a drawing set for whether it can produce a complete BOQ. Use when asked to check/verify/audit a BOQ or a tender, or "what drawings do we need".
---

# audit-boq

**Goal:** every defect in a bill, ranked by rand value at risk, and a clear statement of
what the uploaded drawings can and cannot support.

## Audit a reference (human-priced) bill
```bash
python scripts/audit_boq.py --project wedela --out reports/audits/wedela-reference-audit.md
```

## Audit a pipeline bill
```bash
python scripts/audit_boq.py --project wedela --boq <boq-or-run.json> --building "Storage"
```

## Drawing sufficiency (complete vs partial BOQ)
```bash
python scripts/audit_boq.py --project wedela --sufficiency --out reports/audits/wedela-drawing-sufficiency.md
```
"Coverage ceiling" = the share of the bill's value the available drawing types can
reproduce. "Request next" = which drawing unlocks the most value.

## Fill what the pipeline never calculates
`audit.completer.complete_boq(boq, load_ratio_model("wedela"), building=...)` adds
derived items (wall boxes, chasing, conduit, GP wire, terminations…) tagged INFERRED,
only for ratios with leave-one-building-out error ≤ 35 %; the rest become gaps.

## Rules
- A finding is a statement about the bill, not a correction: never edit client data.
- When presenting findings, lead with value at risk, and separate orphan sheets
  (NOT_IN_SUMMARY) from defects in the priced bill.
- New audit rule → test-first in `tests/audit_layer/test_boq_rules.py` with one positive
  and one negative case, and add it to the rule list in `audit/boq_rules.py`'s docstring.
