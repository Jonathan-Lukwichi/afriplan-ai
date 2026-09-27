# 011 — PDF fact merging double-counts boards and rooms seen on two sheets

**Priority:** P2 · **Opened:** 2026-09-23 · **Status:** ✅ fixed 2026-09-27 (site lighting flagged, not merged)

**Evidence.** `api/agent/pdf_pipeline/passes/orchestrator.py:118` and `:129` extend lists without
de-duplication; conflicting values across pages are never surfaced.

**Acceptance.** Merge by DB / room name; conflicts recorded as gaps; test with two
overlapping page facts.

## Resolution
`_merge_spine` / `_merge_takeoff` (orchestrator.py), tests in
`tests/pdf_pipeline/unit/test_merge_dedup.py`:
- boards merge by name, spacing/hyphens ignored (`DB-1` = `DB1`); the fuller circuit list
  wins, a missing rating is filled from the other sheet, a conflicting rating is a gap;
- feeders merge by (from, to); a written length beats none; a size conflict is a gap;
- a room read on two different sheets (lighting + plugs) is one room, counts merged field
  by field (higher reading, disagreements are gaps); same-named rooms on one sheet stay apart;
- site lighting found on several sheets raises a medium gap — the saved Wedela run's pole
  lights come from six differently named areas, which name matching cannot safely merge.

**Honest result.** Re-merging the saved Wedela PDF run's boards/feeders (free, no new LLM
call) removes the duplicate feeders and moves RS 17.8 % → 17.1 %: each duplicate had added
another assumed 30 m, accidentally closer to the real long routes. The fix is correct; the
PDF's real limit is feeder length (002 — no site plan in the PDF set).
