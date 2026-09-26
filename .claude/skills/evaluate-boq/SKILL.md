---
name: evaluate-boq
description: Score a pipeline BOQ against a human-priced reference project with the frozen scorer (Reproduction Score, coverage, precision, qty/rate accuracy, scoped metrics) and write a baseline report. Use when asked "how good is the output", to measure a pipeline change, or to produce/refresh a baseline.
---

# evaluate-boq

**Goal:** a trustworthy number for "how much of the real bill did we reproduce", and a
list of exactly what was missed — never an anecdote.

## Before you start
1. `python scripts/verify_data.py <project>` → must print `OK`. If not, stop: the inputs
   are not the ones the committed baselines were scored on.
2. `python scripts/evaluate.py --project <project> --self-test` → must print `RS 100.0%`.

## Score a whole pipeline (the baseline)
```bash
python scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<YYYY-MM-DD>-wedela-dxf.md
python scripts/run_baseline.py --project wedela --pipeline pdf --out reports/baselines/<YYYY-MM-DD>-wedela-pdf.md   # PAID — ask first
```
Read the four headline rows (per-building / project-level × as-is / +completer).
Per-building is strict (needs correct building attribution); project-level shows what
was quantified at all.

## Score one run or one BOQ
```bash
python scripts/evaluate.py --project wedela --run runs/dxf/<id>.json --building "Small Guard House" --source dwg
python scripts/evaluate.py --project wedela --boq boq.json --building "Storage" --source pdf --out reports/x.md
```

## How to read the report
- **RS** is the headline. **Coverage** low → items never produced (see "Not produced").
  **Qty accuracy** low → items produced with wrong quantities (see "Largest quantity errors").
- **Scoped** metrics exclude items the uploaded drawings cannot support. If full ≪ scoped,
  the problem is missing drawings (run the `audit-boq` skill, sufficiency mode), not the pipeline.
- Compare only against a committed baseline with the same manifest.

## Rules
- NEVER edit `evaluation/metrics.py` or `evaluation/taxonomy.py` to improve a score. If the
  taxonomy misclassifies a real description, fix it test-first, write/extend an ADR,
  rebuild the reference (`scripts/build_reference.py`) and re-run EVERY baseline in the
  same commit.
- Report regressions as plainly as improvements.
- Update `reports/baselines/README.md` and the "Current state" block of `CLAUDE.md` with
  percentages only. The per-run report quotes client figures: it is gitignored — never
  force-add it (the repo is public, ADR-0005).
