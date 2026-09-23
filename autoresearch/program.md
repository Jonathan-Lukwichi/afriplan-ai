# program.md — AutoResearch loop for AfriPlan (NOT yet started)

Status: **defined, not running.** Start only after (1) at least two reference projects
exist (one to optimise on, one held out), and (2) the first 3 runs happen in "loop
training mode" (a human approves every step).

## Goal
Raise the DXF pipeline's **project-level Reproduction Score** on the development
reference project without lowering it on the held-out project.

## The metric (fixed — never edited by the loop)
- Scorer: `evaluation/metrics.py` + `evaluation/taxonomy.py` (ADR-0003, FROZEN).
- Command: `python scripts/run_baseline.py --project <dev> --pipeline dxf`
  → read the "Project-level — pipeline as-is" RS.
- Guard: the same command on `<held-out>` must not drop by more than 1 point.
- Direction: higher is better. Current dev baseline: see `reports/baselines/README.md`.

## What the loop may change
- ONLY: `agent/dxf_pipeline/patterns.py` (the symbol / circuit-tag pattern table).
- NEVER: anything under `evaluation/`, `audit/`, `tests/`, `data/`, `reports/baselines/`.
  A PreToolUse hook should deny edits outside the allowed file before this loop runs.

## Rules
- One hypothesis → one focused change → measure. Same inputs every run
  (`python scripts/verify_data.py` must pass first).
- If dev RS improves and held-out RS does not drop: commit with the two numbers in the
  message. Otherwise `git checkout -- agent/dxf_pipeline/patterns.py` and try another idea.
- Append every experiment to `autoresearch/results.tsv`:
  `timestamp  hypothesis  dev_RS  heldout_RS  kept(y/n)`.
- The full test suite must stay green for a change to be kept.
- Do not weaken, special-case or "teach to" the reference bill (e.g. hard-coding Wedela
  block names is overfitting — the held-out guard exists to catch it).

## Why this file is not active yet
With a single project there is no held-out guard, and the metric would be optimised by
memorising Wedela's drawing conventions. The loop is worth running only once the dataset
has more than one project.
