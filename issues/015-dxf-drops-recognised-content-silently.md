# 015 — DXF engine drops recognised symbols and cable without a gap

> **Status:** OPEN (found 2026-10-29 by `/check-takeoff` on the synthetic sample)

**Priority:** P1 — breaks hard rule 7 ("never silent") · **Opened:** 2026-10-29

**Evidence.** `python scripts/check_takeoff.py` on the synthetic sample (no client data):
- `recognise()` finds all **27 symbols** (11 `LIGHT_DOWNLIGHT`, 13 `SOCKET_DOUBLE`, 1 `DB_MAIN`,
  2 `MYSTERY_SYMBOL`, all on electrical layers) and **34.25 m** of cable on `E-CABLE-2.5`,
  exactly the hand count.
- `findings_from_recognition()` then yields 0 items, 0 boards, 0 feeders, 0 wires and **0 gaps**,
  so the bill is empty and the run fails "No electrical content recognised in the DXF".
- `classify_block_name()` returns `None` for all four block names, so every symbol becomes the
  unclassified-electrical fallback; the cable has no circuit tag.

**Why it matters.** A drafter whose block names AfriPlan does not know gets an empty bill and a
message that is untrue (content *was* recognised), with nothing listed for the estimator to check.

**Acceptance criteria.**
1. Recognised-but-unclassified symbols and untagged cable reach the bill or the gap list: never
   neither (hard rule 7). Unclassified symbols as gaps naming the block and count; measured cable
   as a line or a gap with its metres.
2. Common descriptive block names (`LIGHT_DOWNLIGHT`, `SOCKET_DOUBLE`, `DB_MAIN`) classify, or the
   decision not to is recorded.
3. `tests/scripts_layer/test_check_takeoff.py::test_the_sample_drawing_take_off_matches_its_hand_counts`
   passes, and its `xfail` marker is removed (it is strict, so it fails loudly once fixed).

**Where.** `api/agent/dxf_pipeline/patterns.py` (`classify_block_name`),
`api/agent/dxf_pipeline/passes/assemble.py` (`findings_from_recognition`), `passes/run.py`.
