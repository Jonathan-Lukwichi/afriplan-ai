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
