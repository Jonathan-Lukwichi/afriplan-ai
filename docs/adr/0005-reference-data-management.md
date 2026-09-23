# ADR-0005: Reference data in data/projects — raw gitignored, manifest committed

- **Status:** accepted
- **Date:** 2026-09-23

## Context
Evaluation must be reproducible by a colleague or buyer, but the drawings and priced
BOQ are confidential client data (~32 MB of binary CAD per project).

## Decision
`data/projects/<p>/raw/` holds the client files and is gitignored. A committed
`manifest.json` lists every file with SHA-256, role, building and a `superseded` flag
for older drawing revisions. Derived artefacts (`reference_boq.json`,
`ratio_model.json`) are committed. `scripts/verify_data.py` proves byte-identical inputs
before any baseline run.

## Consequences
- Anyone holding the files reproduces every committed number exactly.
- The parsed `reference_boq.json` is still client data: treat the repository as
  confidential.
