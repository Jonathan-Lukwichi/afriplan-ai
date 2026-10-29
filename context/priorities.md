# Priorities

Updated: 2026-10-29. Review monthly.

**Current aim: READING accuracy** (`evaluation/reading.py`; pricing is judged later). Details and
numbers: `context/current-state.md`.

Candidates for the next piece of work. **Order: owner to set**, so the list is not ranked:
- **DXF engine drops recognised content silently** (`issues/015-dxf-drops-recognised-content-silently.md`):
  found by `/check-takeoff`; breaks hard rule 7.
- **Route take-off** that emits convention-A wiring lines: conduit, GP wire by colour, BCEW,
  boxes, chasing (`doe/knowledge/BOQ_KNOWLEDGE.md` §4–§6).
- **Building attribution** in the PDF pipeline (`issues/008-pdf-building-attribution.md`).
- **A second reference project** (`issues/014-second-reference-project.md`).
- **A drawing ground truth:** hand counts and measured metres on reference drawings (the
  playbook's 5–10 drawing test set; plan in `docs/accuracy-metrics.md` §2c).
- **Tag→symbol attribution** on site plans (leader lines).
- **Site-lighting double counts** across PDF sheets (flagged, not yet merged).

Open questions (not engineering):
- Using the DOE workflow (Claude Code on the subscription) for paying customers: check
  Anthropic's current terms first.
- Pilot "done", sign-off person and POPIA wording (`context/about-project.md`).

Not now (parked): real user accounts; a trained CNN (ADR-0004).
