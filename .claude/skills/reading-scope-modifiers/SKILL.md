---
name: reading-scope-modifiers
description: Use when reading a drawing set's notes, legend, register, specification or scope pages (DOE estimate-project, the readers' context pass), when a client supplies a tender BoQ template or preamble, or when deciding which items, variants or sections a bill must carry from project facts — outdoor/IP, fault level, ECC cable, underground runs and road crossings, wall and ceiling type, renovation, emergency fittings, lightning, provisional sums, P&G, VAT.
---

# Reading scope modifiers (context first, then gates)

## Overview
A QS reads the scope, preamble and general notes **before** counting one symbol: one sentence there
decides whether dozens of later lines exist, how they are measured and what their rate includes.
AfriPlan keeps notes as free text (`ProjectContext.notes`, `pdf_pipeline/passes/facts.py`) and acts only
on `free_issue_items` (`passes/assemble.py`). The eyes copy each modifier **verbatim** with its sheet;
Python applies its effect (ADR-0002).

## Where context lives (read in this order)
1. Tender documents: scope of works, BoQ preamble / general notes, specification, drawing schedule.
2. Drawing set: register/cover, legend sheet(s), GENERAL NOTES blocks, keyed notes, fitting schedule,
   DB schematic and cable schedule notes. Legends and notes are often on **another sheet** than the
   layout they govern — search the whole set.
3. Bill headers in a client template ("…terminations and earth measured elsewhere").

## SM — modifiers (wording → effect)
| ID | Kind | Typical wording | Effect | Conf |
|---|---|---|---|---|
| SM-1 | `free_issue` | owner/client furnished, free issue | install-only lines (exists) | H |
| SM-2 | `rates_all_in` | rate includes materials, labour, profit, transport | no separate labour/transport/consumable lines | H |
| SM-3 | `supply_install_split` | separate rates for supply and installation | Supply + Install rows, equal qty | H |
| SM-4 | `vat_excluded` | rates exclude VAT; VAT in final summary | VAT once, on the summary | H |
| SM-5 | `remeasurable` | cable/earth/route quantities remeasured, paid as installed | feeder, earth, trench lines PROVISIONAL + preamble note | H |
| SM-6 | `ecc_cable` | PVC/PVC/SWA/**ECC**/PVC | no separate earth for those feeders (CO-F2 off) | H |
| SM-7 | `measured_elsewhere:<family>` | boxes / terminations / excavations measured elsewhere | that companion line **must** exist | H |
| SM-8 | `included:<companion>@<primary>` | "socket outlets complete with flush boxes and cover plates" | that companion is **not** a separate line — **for the named primary only** (switch boxes stay when only sockets say so) | H |
| SM-9 | `wiring_method` | GP wire in conduit / surfix / trunking | which final-circuit families exist (BOQ_KNOWLEDGE §3–5) | H |
| SM-10 | `mounting_height` | switches 1 200 mm, sockets 300/500 mm, ceiling height | drop lengths in the route take-off | M |
| SM-11 | `spare_capacity` | allow 30 % spare ways | DB ways (default 15 %, `core/standards.py`) | M |
| SM-12 | `plug_and_cabtyre` | fittings with 5 A plug and 3 m cabtyre | CO-C14 on | M |
| SM-13 | `excluded:<scope>` | excavations and sleeves by builder; data by others | drop only the families the note names + GapItem (severity medium) "excluded by note"; companions it does not name stay (see CO-F9) | H |
| SM-14 | `provisional_sum` | allow a provisional sum of … | Sum line + its own P&A % line (CO-B4) | H |
| SM-15 | `or_equivalent` | brand names | descriptions end "or equivalent and approved" | H |
| SM-16 | `conflict_order` | specification > schedule > drawings; do not scale | which source wins; note it in things to check | H |

Anything that changes quantity, presence or basis and is not listed → record as `other` with the
snippet, raise it to the owner, and log it as `NEW` in `FEEDBACK.md`. Never invent an effect.

## SM-G — gates (project fact → items on/off)
| ID | Fact (where read) | Default if unknown (+ GapItem) | Effect |
|---|---|---|---|
| SM-G1 | outdoors / wet area (layout, room name) | indoor | IP65 fittings and boards, IP66 isolators, weatherproof boxes |
| SM-G2 | fault level kA (SLD, spec) | 5 kA | ≥ 10 kA → type-tested board + certificate (UNP p1) |
| SM-G3 | breaker / board size (SLD) | — | > 63 A → MCCB; ≥ 49 ways or ≥ 200 A → floor-standing (`core/rate_model.py`) |
| SM-G4 | cable buried (site plan) | buried if outside a building | trench set CO-F7–F9 |
| SM-G5 | road/paving crossings (site plan) | 0 | sleeve set CO-F11 |
| SM-G6 | wall type (architecture, spec) | masonry | masonry → chasing; drywall → dry-wall boxes, no chasing; RC slab → coring |
| SM-G7 | ceiling type | plastered | grid/recessed → CO-C14 |
| SM-G8 | renovation ("existing" on drawings, scope) | new build | decommission, make safe, removal, lamp-disposal certificate (VUT p3) |
| SM-G9 | emergency variants in legend | off | separate battery-backup lines per type |
| SM-G10 | lightning drawing / spec | off | designed → CO-C20; not designed → PROVISIONAL per m² roof |
| SM-G11 | unmeasurable scope (bulk connection, CCTV, PA) | — | provisional sum + P&A |
| SM-G12 | contract months | one P&G sum, PROVISIONAL | fixed + value-related + time-related × months |

## DOE workflow (`estimate-project`)
- Read notes / legend / register pages **first**, before any layout.
- In `read_project_context`, keep `free_issue_items`; put every other modifier in `notes`, one per
  line: `"SM-6 ecc_cable | sheet E-02 | 'PVC/PVC/SWA/ECC/PVC 600/1000V'"` — verbatim snippet, never paraphrased.
- A layout page with its own notes: add them to that page's form (local beats global for that building).
- Report to the owner which modifiers were applied and which were found but are not yet supported.

## Decision rules
- Specific (building/sheet) beats global for that building.
- Follow the document's own conflict clause; if none: specification > schedule > drawings, plus a thing to check.
- A modifier only *seen* by the AI that **removes** a priced family also emits a medium GapItem — removal is the riskiest effect.
- Never carry one project's modifiers into another project.

## Making a modifier typed (code change)
**Ask first** — a field on `ProjectContext`/`Findings` is a public schema change. Proposed shape:
`ScopeModifier(kind, value, snippet, sheet, scope)`. Readers fill it (PDF via strict tool schema; DXF via
a keyword table, no LLM SDK); `api/consolidate/combine.py` merges; `agent/shared/pricing.py` applies it
and appends `"Per note (<sheet>): '<snippet>'"` to each affected line's `assumption`. Failing test first
(skill `tdd`), one synthetic notes page per modifier; re-score; log in `FEEDBACK.md`.

## Version
v1 · 2026-10-29 · from the transformer (context) and ANN (activation) studies.

v2 · 2026-10-29 · first feedback loop: planted-error test (with skills 11/11, baseline 9/11); fixes logged in FEEDBACK.md.
