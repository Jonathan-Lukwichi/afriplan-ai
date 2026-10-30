---
name: writing-sa-bill-lines
description: Use when writing or changing the description, unit, section, order, numbering or supply/install form of any BoQ line AfriPlan emits (agent/shared/pricing.py, agent/shared/boq.py, both assemble.py, api/exports/excel_boq.py and pdf_boq.py), when laying out a tender bill (P&G, per-building bills, provisional sums, collections, summary, VAT), or when parsing a human South African bill into a reference.
---

# Writing South African bill lines

## Overview
An SA bill is one small set of templates used over and over: each **family** has a fixed description
shape, one unit, a supply/install form and a place in a fixed document order. Readers (the reference
parser) and writers (the exports) should both follow it. Python fills every slot and number (ADR-0002);
`BillOfQuantities`/`BQSection` are public (ask first); the taxonomy is frozen (ADR-0003).

## LN-1 Line grammar
```
VERB  OBJECT  ATTRIBUTES  [complete with INCLUSIONS]  [as per drawings / as specified]
      [(X measured elsewhere)]  [or equivalent and approved]
```
- VERB: "Supply and install" (default) · "Supply, deliver and install" · "Install only" (free issue) · "Supply only".
- An INCLUSION must not also be its own line; "measured elsewhere" must point to a line that exists.
- A brand or range named → "or equivalent and approved" (6/8 bills; no AfriPlan code writes it yet).
- Standard where the family has one: SANS 164 (sockets), SANS 1507 (cables), COC to SANS 10142-1.

## LN-2 Header → variant → role
A section = one **header** row (shared spec, no qty) → **variant** rows (only the slot that varies) →
**role** rows (Supply / Install / Terminate / Join) with equal qty. The Install row carries the method
("in sleeves and trench", "recessed"). In flat output keep the identity in the text
("Supply 16 mm² x 4-core PVC/SWA/PVC cable"). Parsing: always pass the header —
`taxonomy.classify_item(description, parent=header, unit=unit)`.

## LN-3 Units by family (no exceptions in 8 bills)
length → **m** (cable, wire, conduit, trunking, tray, sleeve, tape, draw wire) · counted → **No** (devices,
boxes, lids, terminations, joints, boards — one row per named board, qty 1; "ea" only if the whole bill
uses it; never "each") · earthworks priced by volume → **m³** · lump obligations → **Sum** (P&G, earthing,
testing, COC, as-built, provisional) · time-related P&G → **mths** · P&A → **%**.
Today the code mixes "each" (`boq.py`), "Ea" and "Sum" for boards (`pricing.py`) — normalise when touched.

## LN-4 Required slots per family
| Family | Required slots | Section |
|---|---|---|
| Distribution board | **name**, phases, main A, kA, ways (+spare), mounting | DISTRIBUTION |
| Switchgear | MCB/MCCB/ELU, poles, A, kA, curve | DISTRIBUTION |
| SWA cable / termination / joint | mm², cores, PVC/SWA/PVC (ECC), 600/1000 V, laying method | SUBMAIN_CABLES |
| Trench / sleeve | depth × width (soil class if m³) / Ø, material | UNDERGROUND |
| Conduit / boxes | Ø, PVC / galvanised / flexible; box size 100×50 / 100×100 / round | CONTAINMENT |
| GP wire | mm², conductor or earth, colour | FINAL_CABLES |
| Trunking / tray | range, compartments / width, duty, support | CONTAINMENT |
| Socket outlet | 16 A, single/double, normal/dedicated, mounting, IP | POWER_OUTLETS |
| Isolator | **A, poles, IP, equipment served** | POWER_OUTLETS |
| Light switch / sensor | 16 A, levers, ways, IP | **LIGHTING** (4/5 trade-grouped bills) |
| Luminaire | **Type tag**, W, form, size, IP, colour temperature | LIGHTING |
| Emergency variant | "as Type A with 1 h battery back-up" | LIGHTING |
| Earthing / testing | "complete installation to SANS 10142-1" | EARTHING / TESTING |

Known gap: the PDF engine files switches under POWER_OUTLETS (`pdf_pipeline/passes/assemble.py`) while
`agent/shared/symbol_catalogue.py` and the taxonomy say lighting — make both engines agree.

## LN-5 Supply/install: one estimate, three presentations
Split rows (3/7 bills) · split rate columns Supply|Install or Material|Labour (2/7) · one all-in rate (2/7).
Produce the split **in the exports only** from `build_rate(...)` supply/install rates; default = the
client bill's own form. Do not add Supply/Install findings.

## LN-6 Document order (SA tender layout)
Cover → **Preamble** (rates all-in, excl. VAT, remeasurable families, or-equivalent — from the scope
modifiers) → **P&G** (fixed / value-related / time-related) → LV network bill → **one bill per
building, same template** → specialist bills (lightning, generator) → provisional sums (each + P&A %)
and contingency → collection per bill → summary → VAT 15 % **once**.
Inside a building bill: wireways (conduit → round boxes → lids → wall boxes) → trunking/tray → conductors
(GP wire → earth wire) → appliances (sockets → switches → isolators → engraving → draw wire) →
luminaires by Type → sensors → closing items (earthing → test & COC → as-built). Infrastructure first,
devices after — the reverse of take-off order.
Today: one flat list, PRELIMS last, no preamble or collections (`agent/shared/boq.py`, `exports/`). Add the
layout as an **export option** grouped by `building_block`; keep `BQSection` as is.

## LN-7 Parsing a human bill
Carry the nearest header to every child and the bill/building name to every line; strip page tokens
("carried forward", "brought forward", "carried to collection"); join wrapped descriptions; keep
"Rate Only" rows as qty 0 (deliberate placeholders); key on position, not item number (spreadsheets turn
"1.10" into "1,1"). Never commit a parsed client bill (ADR-0005).

## Procedure when you touch a line generator
1. Find the family in LN-4; failing test first (skill `tdd`): slots present, unit = family unit, section
   agrees in both engines, equivalence clause when a brand is named.
2. Build descriptions in ONE pure function per family in `agent/shared/`; quantities never come from it.
3. `$PY -m pytest -q -p no:warnings`; re-score Wedela — a wording change should not move RS; if it does,
   the taxonomy matched something else: investigate and report.
4. Open the exported Excel/PDF from the running app (`python scripts/dev.py start`) and read it like a tender.
5. Log what you learned in `FEEDBACK.md`; run `improving-boq-skills`.

## Version
v1 · 2026-10-29 · from the CNN (templates) and transformer (grammar) studies.
