# Feedback log — deriving-companion-items

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

### 2026-10-29 · skill test (synthetic Building A bill, with-skill vs baseline agent) · CO-C4, CO-C9
- Observed: the baseline agent (no skills) missed dome lids and the earth ÷ conductor ratio; the agent with the skills caught both
- Expected: CO-C4, CO-C9
- Evidence: planted-error test, 11/11 found with skills vs 9/11 without
- Verdict: confirms
- Status: applied v1 (no change needed)

### 2026-10-29 · skill test · CO-F4
- Observed: unclear in which bill the supply-end termination goes when a feeder crosses from the LV network bill to a building bill
- Verdict: unclear
- Status: applied v2 — both terminations billed with the cable

### 2026-10-29 · skill test · CO-B1–B4
- Observed: closing items tagged PROVISIONAL read as contractual provisional sums, so CO-B4 seemed to demand a P&A line for each
- Verdict: unclear
- Status: applied v2 — CO-B1–B3 are priced Sums tagged ASSUMED; CO-B4 only for the bill's own provisional/PC sums

### 2026-10-29 · skill test · CO-C4
- Observed: "Σ conductors ÷ 2" did not say per size or in total
- Status: applied v2 — per size

### 2026-10-29 · skill test · CO-F9
- Observed: "excavations by builder" switched off warning tape too, but laying tape is often still the electrician's scope
- Verdict: unclear (one test, no bill evidence yet)
- Status: applied v2 — tape stays ASSUMED + GapItem unless a note names it; conf unchanged (M)

### 2026-10-29 · skill test · CO-C15, CO-F6, CO-F11
- Observed: chasing has no definition of a "drop" or the height bands; straight joints have no trigger (e.g. run longer than a drum); unclear whether sleeve seals go when sleeves are excluded
- Verdict: unclear
- Status: open — needs evidence from a bill that prices chasing / joints

### 2026-10-30 · Wedela DXF re-score (route take-off task 1, branch feat/route-takeoff) · CO-C1, CO-C3
- Observed: CO-C1 with R = the DXF's measured wiring (per circuit) gave conduit ≈ 2.85 × the bill's
  `conduit|20mm`; RS unchanged (44.8 %), coverage +1.9 pts, precision +0.4, quantity accuracy −2.2.
  In the bill, `gp_wire` (1.5 + 2.5 mm²) ≈ 5.0 × `conduit|20mm`; our drawn route ≈ 0.57 × the bill's GP wire.
- Expected: CO-C3 says GP conductors ≈ 2.0–2.2 × conduit.
- Evidence: Wedela's bill also prices trunking, so part of the wiring runs in trunking, not conduit:
  conduit ≠ every route, and GP wire ÷ conduit is inflated. The DXF's drawn wiring is neither the conduit
  route nor the conductor length. Also a code fault: DXF `WireFinding.building` holds the circuit label,
  so drops (wall points, filed by building) never matched — D was 0.
- Verdict: contradicts (CO-C3 ratio where trunking carries part of the wiring) · code (building field)
- Status: open — before CO-C1/C3 can be used: (1) DXF wires carry the real building; (2) split the route
  by containment (conduit vs trunking/tray) from the drawing's layers/legend; (3) re-score. CO-C3's ratio
  should state "conduit-only installations".

### 2026-10-30 · Wedela DXF re-score (route take-off step 2) · CO-C1
- Observed: Wedela draws wiring on one layer, mostly as point-to-point arcs (about 3 arcs per line), with no
  trunking layer, so a containment split by layer is not possible there. Measuring the route as straight
  chords (BOQ_KNOWLEDGE §4) and leaving out sheets read or titled as an SLD: conduit ≈ 1.6 × the bill's
  `conduit|20mm` (was 2.85 ×); project RS 44.8 % → 45.6 %, quantity accuracy 70.9 % → 72.0 %, precision 89.2 %.
- Expected: CO-C1 = R + D, with R the straight route.
- Evidence: per sheet, arcs are 1.2–2.0 × their chords; one sheet titled SLD carried ~18 % of the drawn wiring.
- Verdict: confirms (CO-C1 with R as straight runs) · code (route measured as drawn; SLD lines counted)
- Status: applied in feat/route-takeoff (not yet in main). Remaining excess (~1.6 ×) unexplained — candidates:
  drops over-counted, routes shared by circuits counted per circuit, part of the wiring in trunking.

### 2026-11-02 · Rules audit before bill completion · emission rule, CO-C2, CO-F6, CO-B5
- Observed: the skill said L rules only flag, yet CO-C2 and CO-F6 emitted lines; H closing items were tagged ASSUMED while the skill called sums PROVISIONAL; CO-B5 was an M rule tagged INFERRED.
- Expected: one rule for whether a line is emitted, one for its tag.
- Evidence: RULES.md, `api/agent/shared/companions.py`, confidence table in `improving-boq-skills`.
- Verdict: unclear (the rules contradicted each other; no project evidence involved)
- Status: applied v3 — H and M emit, L only flags; the tag follows what the quantity rests on.

### 2026-11-02 · Rules audit before bill completion · CO-C1, CO-C3, CO-C5, CO-C7, CO-C9, CO-C10, CO-C11
- Observed: H needs 3 or more independent sources; these rows cite fewer.
- Expected: conf follows the source count.
- Evidence: each row's own sources. CO-C5 and CO-C15 gain the Wedela bill as a source. CO-C1 gains the manual method study.
- Verdict: unclear (recount, no rule's quantity disproved)
- Status: applied v3 — all to M. CO-C1 now emits ASSUMED, test first. Other H rows short of sources (CO-F7, CO-F12, CO-C16, CO-C17, CO-C19) are not used by the next step and stay open.

### 2026-11-02 · Rules audit · CO-C3 and waste
- Observed: CO-C3's 2.2 carried PTC's 10 % waste in the quantity, against "Never in the quantity"; BOQ_KNOWLEDGE wrote conduit as R + D (+ waste).
- Expected: quantities are net, waste in the rate (UNP p1, PTC Part 4 §15).
- Evidence: PTC p9 (2 × 10 %).
- Verdict: contradicts
- Status: applied v3 — CO-C3 is 2.0 × conduit in conduit-only installations.

### 2026-11-02 · Rules audit · CO-C10, CO-C11 and SM-8
- Observed: both rows still gated on `included:boxes`; SM-8 was narrowed so a note covers only the item it names.
- Verdict: unclear (two skills disagreed)
- Status: applied v3 — gates are `included:boxes@switches` and `included:boxes@sockets`.

### 2026-11-02 · Wedela drawings vs bill · CO-C1, CO-C3 (containment split)
- Observed: with the arc fix and one conduit line per building, our conduit is about 1.48 × all the bill's conduit, and about 1.14 × its conduit plus trunking. No text or layer on any sheet mentions trunking.
- Expected: the route is one figure for all containment.
- Evidence: bill items `conduit`, `trunking`; a total only. One trunk can carry several circuits, so this suggests a cause without proving it.
- Verdict: unclear
- Status: open. Trunking is a question for the person, not a reading.

### 2026-11-02 · Wedela Small Guard House, hand measurement from the drawing · CO-C1, CO-C3, CO-C4
- Observed: measured point to point, conductors per run from how the circuits are wired: wire ÷ conduit about 2.2 on lighting and 2.0 on power; earth = conduit.
- Expected: CO-C3 2.0 × conduit; CO-C4 earth = conductors ÷ 2.
- Evidence: hand sheet (local, `data/takeoff_tests/wedela-small-guard-house/raw/`). A measurement that does not start from any bill. A person has not checked it yet.
- Verdict: confirms (pending the person's check)
- Status: open. Not a third source until a person checks it.

### 2026-11-02 · Wedela Small Guard House · CO-C1 (conduit against the bill)
- Observed: the bill's conduit is about 2.4 × the hand figure at a 3 m ceiling, 1.9 × at 4 m, in a very small building. The bill's wire is 2.0 × its conduit and its earth equals its conduit: internally exact, so it looks like an allowance taken through these ratios, not a measurement.
- Expected: the guard houses at under half the bill looked like a shortfall of ours.
- Evidence: hand sheet, bill lines for that building. Only this building was measured.
- Verdict: bill-vs-drawing
- Status: open; a rule does not change. Small buildings may be billed by allowance, which a person should confirm.

### 2026-11-02 · Wedela, all layouts · code (label bubbles counted as wiring)
- Observed: the small loops drawn around tags such as a board and circuit label sit on the wiring layer, so they are measured as cable and as conduit route. On the Small Guard House sheets they are about 30 % of the route. Across the project, closed loops under 2 m wide are about 19 % of measured wiring, an estimate: checked by eye on one building only.
- Expected: R = the route between points.
- Evidence: hand sheet; a count of loops left after pruning loose ends. Without them our conduit would be about 0.95 × the bill's conduit plus trunking, estimated, not run.
- Verdict: code
- Status: open, next change to the reader.
