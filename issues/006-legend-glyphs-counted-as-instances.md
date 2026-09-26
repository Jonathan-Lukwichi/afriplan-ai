# 006 — Legend glyph blocks are counted as real symbols

> **Status:** FIXED 2026-09-26 (0642e1c) — legend_region excludes legend glyphs (real AB lighting: 15 → 13 switches).

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** `ml/DATASET_CARD.md` and the labelled preview of `WD-AB-01-LIGHTING`: switch
boxes inside the legend table. DXF baseline: `switch|1lever|1way` 44 vs 20,
`day_night_switch` 18 vs 6. `recognise()` counts every INSERT; only `legend_block_counts()`
excludes the legend glyph.

**Acceptance.** Symbols inside the detected legend region excluded in `recognise()` and in
`ml/symbol_dataset.labels_from_doc`; unit test with a synthetic legend + plan.
