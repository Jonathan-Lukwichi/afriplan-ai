# Feedback log — reading-drawing-symbols

Evidence for and against this skill's rules, one entry per observation, **newest last, never deleted**.
Written and acted on by the `improving-boq-skills` skill (format, confidence levels and decision table
are there). Public repo: no client rand figures or quantities — ratios, rule IDs, sheet numbers and
item keys only.

<!-- Entry format:
### YYYY-MM-DD · <project or test> · <rule ID | NEW>
- Observed:
- Expected:
- Evidence:
- Verdict: confirms | contradicts | new-pattern | code | bill-vs-drawing | unclear
- Status: open | applied vN | rejected — <why>
-->

## Entries

### 2026-11-02 · Wedela DWG set, reading check against the drawings · NEW (labelled glyphs)
- Observed: solar post lights and high masts cost 24 reading points as "not read", yet both are on the Pool sheet: loose line-work glyphs, each with a short text label beside it (`PS`, `FL`) that the legend row explains. Counting the labels on the plan (minus the legend's own copy) matched the bill exactly for both items.
- Expected: a labelled glyph is a counted item (legend + DS-4).
- Evidence: text labels in the DWG; reading score 54.2 % -> 78.2 % with AI names, 47.7 % -> 71.8 % without. The legend's own QTY column disagreed with the plan for the masts, and the bill followed the plan: treat a printed QTY as a check, not as the count, when the plan can be counted.
- Verdict: new-pattern · code (legend naming: "2x600W LED" passed for a panel size; `legend_region` caught only one column of a multi-column legend table)
- Status: applied in feat/route-takeoff (`passes/labels.py`, light fittings only).

### 2026-11-02 · Wedela DWG set, things-to-check list · NEW (the legend names the shape)
- Observed: the AI gave a flood and a bulkhead the wrong name although the legend row beside the glyph names them, and named one shape differently from one run to the next. A remembered AI name then repeats the error for free on every later run. `D/N` labels were missed (a slash), and a board header `DB-HPS 1` was not read as a board because of the space, while its feeder line writes `DB-HPS1`.
- Expected: the drawing's own legend outranks the AI; a person's correction outranks both.
- Evidence: legend naming matched the bill within one fitting on both items and raised item precision from 76.0 % to 83.3 %. Trusting one sheet's legend went badly wrong first: real legends sit a row off on some sheets and disagree between sheets, and grid lines fuse glyphs. It only worked with the table's lines removed and two sheets agreeing. Simple shapes (a box, a plain rectangle) must never be named this way.
- Verdict: new-pattern · code · bill-vs-drawing (boards: the bill lists fewer pool boards than the SLD draws; the earlier exact board count was two misspelled tag-only boards hiding four unread real ones)
- Status: applied in feat/route-takeoff (`shapes.legend_shape_names`, `run._legend_names`, `labels.py`, `sld.py`). Open: a single sheet with a disagreeing legend still names nothing.
