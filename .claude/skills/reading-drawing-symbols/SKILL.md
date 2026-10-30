---
name: reading-drawing-symbols
description: Use when reading electrical layout or SLD pages into forms in the DOE workflow (estimate-project, read_layout_takeoff / read_power_spine), when a count looks doubled or a fitting variant was lost, or when changing how symbols are named — api/agent/shared/legend.py, symbol_catalogue.py, the PDF form schema in pdf_pipeline/passes/facts.py and prompts/pass_schemas.py.
---

# Reading drawing symbols

## Overview
Reading a layout is local pattern detection: find a glyph, read its modifiers and tag, look it up in
the legend, count it **once**. Most counting errors come from a handful of local motifs. You only
READ and record — never compute a length, total or price (ADR-0002). Missing → 0 / false / empty plus
a note in `extraction_warnings`. Tutorials in `doe/knowledge/youtube_*` are mostly US: keep the method,
never their sizes or prices.

## Before counting (per sheet)
1. **Find the legend** — this sheet, another sheet, or partly missing. A glyph not in this legend: check
   the other sheets' legends before giving up.
2. **Legend QTY column?** Use the printed counts for the sheet, set `counts_from_legend_schedule: true`
   (LESSONS: legend QTY columns are gold).
3. **Fitting schedule**: each luminaire **Type tag** (Type A, B1, S2B, LF-03) links the symbol to its full
   description (W, form, IP, emergency). The tag is the variant.
4. **Keynotes and general notes** first: they change the item (weatherproof, mounting height), make it
   install-only ("by others" → free issue), or say "typical" (applies to every similar device in the
   area). Scope-wide notes → skill `reading-scope-modifiers`.
5. Lengths are measured by Python on vector sheets (`agent/shared/routes.py`); report only a length
   *written* on the drawing.

## DS — local motifs
| ID | Motif | Rule |
|---|---|---|
| DS-1 | Same base glyph + extra letters (WP, G, E/EM, 1D/2D, "B" battery, D/red dedicated) | a **different item** — never add to the plain glyph's count |
| DS-2 | Same glyph, different Type tag | different variant; keep counts per tag (field, or "Type X: n" in warnings) |
| DS-3 | Emergency version ("Ae", "S2B", "with battery back-up") | counted as emergency, **not** also as the plain type |
| DS-4 | Symbol inside the legend box | not an instance — never count (issue 006) |
| DS-5 | Enlarged plan / detail of an area | count that area once, on one view; note which |
| DS-6 | Board on both lighting and power sheets | the same board — take boards from the SLD/schedule only (issues 005, 011) |
| DS-7 | Building on a lighting sheet and a plug sheet | same `room_name` on both forms so the merge keeps the higher count instead of adding |
| DS-8 | Same site lights on an outline sheet and a building sheet | count once; say which sheet in warnings |
| DS-9 | Circuit tag + arrow (home run) to a named board | tag → `circuit_tags`, board → `served_by_db` (exact SLD spelling) |
| DS-10 | Equipment only in an SLD/schedule (geyser, AC, heat pump) | still needs an isolator + connection → write it in warnings |
| DS-11 | Isolator labelled with rating/equipment ("30A DP – AC") | count it; copy rating + equipment into warnings |
| DS-12 | Switch levers / ways ("2", "2W") | 1-, 2-, 3-lever and 1-lever 2-way are separate fields |
| DS-13 | Words in brackets after equipment ("KIOSK (WD-KIOSK-01)") | describe that equipment |
| DS-14 | Containment, sleeves, draw wire, manholes, trench, tray droppers | usually **not drawn** — do not invent them; Python allows for them |

## SLD (`read_power_spine`)
One entry per board, **name exactly as written**; main switch = the incomer breaker, not the busbar
rating; record kA and voltage; every outgoing way **including spares** (amps, poles, cable size); each
"FED FROM … / incoming cable …" box is a feeder (from → to, mm², cores, **ECC or not**). A board drawn on
a second SLD page is the same board — same name, so the merge dedups it.

## Self-check before saving a form
- [ ] every counted glyph is named in a legend (this sheet or another)
- [ ] modifier variants counted apart; no legend-box symbols; enlargements once
- [ ] boards only from SLD/schedule pages
- [ ] every keynote that changes an item is reflected or written in warnings
- [ ] what the form cannot hold is in warnings, not forced into a wrong field
- [ ] no lengths, totals or prices invented

## When the form keeps losing information (developer path)
The layout form (`TakeoffRoom`, `pdf_pipeline/passes/facts.py`) stores counts per generic category;
real bills key luminaires by Type tag (7/7) and isolators by amps/poles/equipment. If warnings carry the
same kind of information across projects, log it in `FEEDBACK.md`; when two projects show it, propose an
additive optional field (`fitting_types: [{tag, legend_text, count}]`, `isolators_by_rating`). **Ask first**
(public schema; `prompts/system_prompt.py` must stay frozen). Then failing test first, map it in
`assemble.py` with the `writing-sa-bill-lines` templates, keep old counts as fallback, re-score.
Naming rules for modifiers (WP, EM, battery "B") go in `legend.classify_description` with tests —
emergency before generic lighting; the DXF engine reads the same legend spec, so check both engines.

## SA wording (not US)
receptacle → switched socket outlet (SANS 164, 16 A; dedicated = red) · GFCI → earth leakage · panelboard
→ DB · home run → circuit to the DB · AWG → mm² · OFCI → free issue.

## Version
v1 · 2026-10-29 · from the CNN (drawing motifs) study + LESSONS.md.
