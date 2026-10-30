# Feedback log — consolidating-price-catalogue

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

### 2026-10-29 · first real build (Schneider 2026 list) · NEW → PC-10
- Observed: table detection took ~45 min and put overflowing description letters in the price cell — 407 rows "without a price", most of them readable
- Verdict: code
- Status: applied v2 — span reader: 32 s, 8 rows without a price

### 2026-10-29 · first real build · NEW → PC-11
- Observed: ~1 750 rows disappeared silently (keyed by part number); the list repeats clipped part numbers for different products
- Verdict: code
- Status: applied v2 — exact repeats dropped and counted (22), other repeats kept as <id>~2 (1 301)

### 2026-10-29 · first real build · PC-10
- Observed: 3 438 items had no category — sub-collection and group printed as one glued span
- Status: applied v2 — split where the next column has no span of its own; 0 without a category

### 2026-10-29 · first real build · PC-6
- Observed: an HMI "Connection Cable" was family `cable`; drives / PLCs / SCADA fell into `other`
- Status: applied v2 — `automation` family checked first. `other` still 1 226 (meters, capacitors, relays, accessories) — open: add families when the pricer needs them
