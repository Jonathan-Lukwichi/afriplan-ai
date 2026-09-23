---
name: add-reference-project
description: Onboard a new real electrical project (drawings + human-priced BOQ) as ground truth under data/projects/, with a checksummed manifest, parsed reference BOQ, refitted ratios and first baselines. Use when the user provides a new project's drawings and BOQ, or asks to grow the evaluation dataset.
---

# add-reference-project

Every extra reference project makes the scorer, the fitted ratios and (eventually) the
CNN more trustworthy. Ratios need ≥ 3 buildings for a LOO error; a CNN needs 5–10 projects.

## Steps
1. **Copy raw files** to `data/projects/<project>/raw/` (drawings PDF/DWG/DXF + the
   priced BOQ `.xlsx`). Skip `.bak`, `.dwl`, `.dwl2`, `plot.log`. Never commit raw/.
2. **Manifest.** Extend `scripts/verify_data.py` with this project's drawing-code →
   building map (like `WEDELA_CODES`) and building list, then:
   `python scripts/verify_data.py <project> --write` → review every role/building/
   `superseded` flag by hand → `python scripts/verify_data.py <project>` prints OK.
3. **Parse the bill:** `python scripts/build_reference.py <project>`. Check the
   printed summary total equals the workbook's. Then list unclassified lines:
   ```python
   from evaluation.reference import load_reference
   ref = load_reference("<project>")
   print([l.description for l in ref.all_lines() if l.key_family == "other" and l.value > 0])
   ```
   Any priced 'other' line is a taxonomy gap → extend `evaluation/taxonomy.py`
   **test-first** (real strings into `tests/evaluation_layer/test_taxonomy.py`). This
   changes the frozen ruler: re-run every existing baseline in the same commit (ADR-0003).
4. **Audit the reference** (`audit-boq` skill). Record its defects in the project's
   section of `data/README.md` — ground truth is not assumed perfect.
5. **Refit ratios across all projects** if the ratio fit is extended to multi-project,
   and compare LOO errors before/after.
6. **Baselines** (`evaluate-boq` skill) for DXF (free) and PDF (paid — ask first).
7. Update `data/README.md` table, `reports/baselines/README.md`, `CLAUDE.md` current state.

## Rules
- Do not "fix" the client's workbook; audit findings are recorded, not corrected.
- Keep the project's parsed JSON out of any public share — it is client data.
