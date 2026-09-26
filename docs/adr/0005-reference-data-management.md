# ADR-0005: Reference data in data/projects — client data local only, manifest committed

- **Status:** accepted
- **Date:** 2026-09-23 (revised 2026-09-26: repository is public)

## Context
Evaluation must be reproducible by a colleague or buyer, but the drawings and priced
BOQ are confidential client data (~32 MB of binary CAD per project).

## Decision
`data/projects/<p>/raw/` holds the client files and is gitignored. A committed
`manifest.json` lists every file with SHA-256, role, building and a `superseded` flag
for older drawing revisions. Because the GitHub repository is **public**, every artefact
derived from the client's bill that carries priced lines, rates or totals is ALSO local
only and gitignored: `reference_boq.json`, `ratio_model.json`, the per-run Wedela
baseline reports, the Wedela audit reports, `baselines/wedela.json` / `trichard.json`.
They are regenerated deterministically from `raw/` by `scripts/build_reference.py`,
`run_baseline.py` and `audit_boq.py`. Committed docs quote only percentages and
non-monetary findings. Unpushed history was rewritten on 2026-09-26 to remove them. `scripts/verify_data.py` proves byte-identical inputs
before any baseline run.

## Consequences
- Anyone holding the files reproduces every committed number exactly.
- A fresh clone runs the full test suite; tests needing client data skip cleanly.
- Reproducing a committed baseline number requires the client files from the owner.
