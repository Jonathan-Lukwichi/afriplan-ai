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
