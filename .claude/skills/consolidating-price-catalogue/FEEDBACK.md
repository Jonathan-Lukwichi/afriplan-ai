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

### 2026-10-30 · Live Pricing step A, matched against the real catalogue · NEW → PC-13
- Observed: protective devices matched well (20A 1P MCB → iC60H 1P 20A; 63A 2P 30mA ELCB → iID RCCB; 250A 3P 36kA MCCB → NSX250 75kA; surge → iPRD); wiring devices did not ("1-Lever Switch" → selector switch head, "16A Single Switched Socket" → industrial panel socket, "Data Socket (CAT6)" and "Floor Box Socket" → 16A power wall socket)
- Verdict: new-pattern
- Status: applied v3 — only protective devices are quoted; sockets/switches open until ranges are mapped
- Also open: "MCB 63A 3P 6kA" gets no quote — most list descriptions do not state kA, so a stated kA filters everything out; needs kA per range
