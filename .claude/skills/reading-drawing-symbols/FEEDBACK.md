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

### 2026-11-02 · Wedela DOE re-run on the new CAD reader · NEW (combined adds instead of merging)
- Observed: combined now reads below CAD alone: reading 70.3 % vs 73.0 %, RS 60.3 % vs 62.2 %. Items both readers count come out near their sum: sockets, isolators and 1-lever switches at about twice CAD's count, and vapour-proof lights 1.26x. A mast is one over, taken from the page's legend QTY.
- Expected: a fitting on a PDF page and its paired CAD sheet is one fitting (DS-7, ADR-0008: one bill from both readers).
- Evidence: `accuracy_report` reading items, CAD alone vs Combined (delivered): `socket_double`, `isolator`, `switch|1lever|1way`, `light_vapour_proof`, `light_highmast`. Boards are one over: the page reader's layout spelling `DB-LGR` skips the CAD spelling check.
- Verdict: code (`consolidate/combine.py`)
- Status: open. Decides priorities step 7: on a project with CAD, take notes from the pages, not quantities.

### 2026-11-02 · Wedela DOE re-run · NEW (architectural sheets read as layouts)
- Observed: `finish` reads every DWG in the folder, so 7 architectural sheets count as layouts: CAD alone 73.0 % against 75.1 % on the 18 electrical sheets. Their copies of the electrical symbols add to sockets, switches and isolators.
- Expected: a sheet with no electrical content adds nothing; the reference manifest marks these sheets architectural.
- Evidence: the same bill scored on 24 files and on 18; items `socket_double`, `switch|1lever|1way`, `isolator`, `light_vapour_proof`.
- Verdict: code (`doe/execution/project.py::discover`, or a sheet-role step in the DXF run)
- Status: open.

### 2026-11-02 · Wedela DOE re-run · step 2 (legend QTY columns)
- Observed: `things_to_check` shows a printed legend quantity differing from the plan count on several sheets (vapour-proof, flood, 2-lever). Where the bill can settle it (masts, floods), it sides with the plan count or falls between.
- Expected: step 2 says to use the printed counts.
- Evidence: Wedela sheets AB-LIGHTING, ECH-LIGHTING, LGH-LIGHTING; bill items `light_highmast`, `light_flood`.
- Verdict: contradicts (1 source)
- Status: open, kept with a check note on step 2 of the skill. One project: the rule stays.

### 2026-11-02 · Wedela drawings vs bill · bill-vs-drawing
- Observed: three places where the bill differs from the drawings: the pool's 95 mm² feeder (about 5.5x the drawn Kiosk to DB-CR route, close to the whole Mini sub to DB-CR route), boards (drawn 1.2x the bill, 4 pool boards named only on the SLD), and 3-core cable to two boards the SLDs show as 3-phase.
- Expected: the reader follows the drawings.
- Evidence: site sheet WD-OL-001, SLD headers, bill sheets Swimming Pool, Storage, Large Guard House. A person has not confirmed which is right.
- Verdict: bill-vs-drawing
- Status: open, no rule changed; queried in the local `bill_queries.json`.

### 2026-11-02 · Wedela Small Guard House, hand measurement · NEW (a labelled switch counted twice)
- Observed: a day/night switch is drawn with a plain switch block beside its `D/N` label, so it is billed as a day/night switch and as a 1-lever switch. The bill has no 1-lever switch in that building.
- Expected: one device, one line. A label beside a block names that block.
- Evidence: sheet WD-SGH-01-LIGHTING, tag S21; local case `wedela-small-guard-house`, which fails on this one item only.
- Verdict: code
- Status: open.

### 2026-11-02 · Wedela Small Guard House · bill-vs-drawing (vapour-proof lights)
- Observed: plan, legend QTY and the SLD's circuit note agree with each other and all differ from the bill (the bill is 0.5 × them).
- Evidence: sheet WD-SGH-01-LIGHTING, SLD circuit L1, bill sheet Small Guard House.
- Verdict: bill-vs-drawing
- Status: open, a question on the hand sheet.
