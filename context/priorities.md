# Priorities

Updated: 2026-11-02. Review monthly.

**Current aim: a COMPLETE BILL a contractor can review and send** (owner's decision, 2026-11-02).
**Reading accuracy** (`evaluation/reading.py`) stays as a guard: a change must not lower it. Details
and numbers: `context/current-state.md`.

Order set by the owner, 2026-11-02:
1. Re-run the combined result on the current code, to know if combined still beats CAD alone.
2. Fix the plug-sheet conduit attribution, the waste and emission contradictions in the rules, and
   the rules step 5 will use.
3. An answer on each thing to check, stored with the bill, that updates it, with its rand impact.
4. Measure one guard house by hand, a person checks it: the one check independent of the bill.
5. Complete the bill: conduit labour, wire by size, boxes, chasing, draw wire, marked allowances,
   sleeves, manholes, trench rate. A feeder with no route keeps its cable; its trench is an open
   question with a rand value, outside the total until answered.
6. An optional P&G calculator from the engineer's own inputs: no project's rates as defaults.
7. Scope notes from the page reading.
8. Circuit tracing, only if a gap remains after 4 and 5.

Biggest risk: every reader rule so far was tuned on Wedela alone.
- **A second reference project** (`issues/014-second-reference-project.md`), as soon as data exists.

Other candidates, not ranked:
- **Building attribution** in the PDF pipeline (`issues/008-pdf-building-attribution.md`).
- **A drawing ground truth:** hand counts and measured metres on reference drawings (the
  playbook's 5–10 drawing test set; plan in `docs/accuracy-metrics.md` §2c).
- **Tag→symbol attribution** on site plans (leader lines).
- **Site-lighting double counts** across PDF sheets (flagged, not yet merged).

Open questions (not engineering):
- Using the DOE workflow (Claude Code on the subscription) for paying customers: check
  Anthropic's current terms first.
- Pilot "done", sign-off person and POPIA wording (`context/about-project.md`).

Not now (parked): real user accounts; a trained CNN (ADR-0004).
