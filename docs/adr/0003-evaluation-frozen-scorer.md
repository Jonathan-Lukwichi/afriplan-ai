# ADR-0003: Evaluate against a human-priced reference with a frozen scorer

- **Status:** accepted
- **Date:** 2026-09-23

## Context
The retired Streamlit app's `scoring/harness.py` compared only totals and a few fixture counts. A
pipeline could hit the total by accident while reproducing almost none of the bill,
and nobody could see which lines were never produced.

## Decision
- Ground truth is a real priced BOQ parsed line by line (`api/evaluation/reference.py`).
- Lines are matched on a normalised **ItemKey** (`api/evaluation/taxonomy.py`) per building,
  Supply/Install collapsed; a spec-less prediction is compared with the reference
  family total.
- Headline metric: **Reproduction Score** = Σ ref value × matched × qty accuracy ÷ Σ ref
  value; plus coverage, precision, quantity / rate / total accuracy — each also
  **scoped** to what the uploaded drawing types can reproduce.
- `api/evaluation/metrics.py` and `api/evaluation/taxonomy.py` are **frozen**: they define
  "better". Changing either needs a new ADR and a re-run of every baseline in
  `reports/baselines/` in the same change.

## Consequences
- Scores are comparable over time and across pipelines.
- The scorer can serve as the fixed metric of an AutoResearch loop
  (`autoresearch/program.md`); the loop may never edit it.
- New projects will need taxonomy extensions for new wording; each is a deliberate,
  reviewed change with re-baselining. (The first baseline run already found and fixed
  two taxonomy bugs — DB lines naming an MCCB incomer, a trench mentioning the kiosk.)
