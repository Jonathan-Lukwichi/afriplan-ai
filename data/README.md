# data/ — reference projects (ground truth)

Every evaluation in this repo is run against a **reference project**: a real set of
electrical drawings together with the BOQ a human estimator priced from them.

```
data/projects/<project>/
    manifest.json        COMMITTED  every input file + SHA-256 + role + building
    raw/                 GITIGNORED the client's drawings, PDFs and BOQ workbook
    reference_boq.json   LOCAL ONLY parsed ground truth      (scripts/build_reference.py)
    ratio_model.json     LOCAL ONLY fitted derived ratios    (scripts/build_reference.py)
data/ml/                 GITIGNORED generated CNN training images (scripts/build_symbol_dataset.py)
```

## Why client files are not in git
The GitHub repository is public. `raw/` and everything derived from it that carries
the client's priced lines, rates or totals (`reference_boq.json`, `ratio_model.json`,
the Wedela baseline/audit reports) stay local and are gitignored (ADR-0005).
Regenerate them with `python scripts/build_reference.py wedela` once `raw/` is present.

`raw/` itself is client data (confidential, ~32 MB of binary CAD). The committed `manifest.json`
pins the exact bytes, so a colleague who receives the files separately can prove they
hold identical inputs:

```bash
python scripts/verify_data.py wedela        # → OK — 28 files verified
```

## File roles
`reference_boq` · `sld` · `lighting_layout` · `plug_layout` · `site_plan` · `architectural` ·
`pdf_sld` · `pdf_layouts`. A file marked `"superseded": true` is an older revision of
another file in the set and is never used (e.g. `WD-PB-01-LIGHTING 100225` is replaced
by `... 100425`).

## Adding a project
Follow `.claude/skills/add-reference-project/SKILL.md`.

## Current projects
| Project | Buildings | Files | Reference total (excl VAT) |
|---|---|---|---|
| wedela | 7 billed (+ Pool-Heat Pumps sheet, unpriced) | 28 | (kept locally) |
