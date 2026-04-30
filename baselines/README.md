# Baselines — ground-truth BoQs for regression testing

Each `<project>.json` file in this directory is a hand-validated reference
extraction for one project. Both pipelines compute their MAPE against the
same baseline, which is the entire point: the baseline is the **ground
truth**, the pipelines are competing approximations of it.

## Schema

```json
{
  "project_name": "Wedela Recreational Club",
  "source_pdf": "Wedela_Electrical.pdf",
  "source_dxf": "wedela_layout.dxf",
  "validated_by": "Hervé",
  "validated_at": "2026-04-30",
  "notes": "Schedule J/K/L (specialist subcontract) excluded from regression.",

  "pdf_fixture_counts": {
    "downlights": 124,
    "panel_lights": 32,
    "double_sockets": 86,
    "single_sockets": 12,
    "data_outlets": 24,
    "switches_2lever": 38,
    "emergency_lights": 8
  },

  "dxf_block_counts_by_type": {
    "LED Downlight": 124,
    "LED Panel": 32,
    "Double Socket": 86,
    "Single Socket": 12,
    "Data Socket": 24,
    "2-Lever Switch": 38,
    "Emergency Light": 8
  },

  "boq_section_subtotals_zar": {
    "SECTION 5: LIGHTING INSTALLATION": 480000,
    "SECTION 6: POWER OUTLETS INSTALLATION": 210000,
    "SECTION 7: DATA & COMMUNICATIONS": 180000
  },

  "total_excl_vat_zar": 7612400
}
```

## Building a baseline

Run `python scripts/build_baselines.py --interactive <project_name>` —
it walks you through entering counts and writes the file.

Better yet: extract once with each pipeline, look at the BoQ side by
side, correct the extraction by hand, and save the corrected version
as the baseline.

## CI behaviour

* `pdf_fixture_counts` drives `PdfEvaluation.baseline_mape`
* `dxf_block_counts_by_type` drives `DxfEvaluation.baseline_mape`
* If a key is absent, the corresponding pipeline simply reports MAPE = `null`
