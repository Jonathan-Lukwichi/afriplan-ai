# Electrical BoQ knowledge — how quantity surveyors prepare, measure and price

Domain knowledge for anyone producing or checking an AfriPlan BoQ (the DOE brain, a developer,
a reviewer). It explains **how a person does the job**, so the machine can do the same and be
judged the same way. Written in our own words from three lecture transcripts (sources at the
end) and compared with the way the South African reference bill (Wedela) measures the same
work. The lectures' example prices (India, Bhutan, Nigeria) are explicitly not current and must
**never** be used as AfriPlan rates — only the methods are kept here. No client quantity or
rand figure appears in this file (ADR-0005).

> **The open problem (2026-10-29).** Final-circuit wiring — wire, earth wire, conduit, boxes,
> chasing — is measured and billed in **several different conventions**, and AfriPlan produces
> it in none of them properly. §3–§6 explain the conventions, the one thing they all derive
> from, and exactly where AfriPlan falls short. Read them before changing any wiring code.

---

## 1. What a BoQ is, and its two kinds
- A **Bill of Quantities** lists every item of the installation with description, unit and
  quantity, and (once priced) a rate and an amount.
- **Supply only** (material delivered) vs **supply + install** — often written **SITC**
  (supply, installation, testing, commissioning). AfriPlan bills are supply + install; the
  Wedela bill even splits many items into a *Supply* line and an *Install* line.
- Columns: item · reference (schedule-of-rates code, if any) · description · unit · quantity ·
  rate · amount · remarks. Some templates carry "quantity as per standard BoQ" and "as per
  design": the estimator fills the **design quantity**.

## 2. Where each quantity comes from (drawing → BoQ line)
| BoQ section | Read it from | How |
|---|---|---|
| Distribution boards and their breakers | **SLD** | One line per board (ways, TPN/SPN, rating). Count every breaker by **rating and poles** (10 A SP MCB, 32 A DP RCCB, 63 A TP MCB…) board by board; a spare way that is fitted is still a breaker. |
| UPS, inverter, main equipment | Equipment / electrical-room layout | Capacity (kVA) and count. |
| Cable tray / trunking | Containment layout | **Running metres per size** (e.g. 300×50, 150×50 perforated GI); supports/accessories as their own line. |
| Sub-mains / feeders | **Cable schedule**, or SLD (size) + site plan (route) | Metres per type, cores and size, board to board. |
| Sockets, switches, isolators | Power / small-power layout | Count each type yourself. |
| Light fittings | Lighting layout + fitting schedule | Count per type, schedule wording. |
| **Final-circuit wiring** | Lighting / power layouts | **See §3–§6** — the hard part. |
| Junction / draw boxes | Conduit layout | Count. |
| Sundries | Specification | As-built drawings, rubber mats, insulating gloves, first-aid box, testing. |

**Never trust a template's quantities.** A standard BoQ can carry wrong counts (one lecture's
template had a socket total that did not match the drawing). Count on *this* project's drawings.

## 3. Final-circuit wiring — four ways to bill the same work
The same physical installation (conduit from the board to every light, switch and socket, with
wires pulled through it and boxes at the ends) is billed in different ways in different places:

| # | Convention | Where seen | What one line means | Unit |
|---|---|---|---|---|
| **A** | **Material by material** | **South Africa — the Wedela reference bill** | Each material on its own: conduit by diameter; **GP wire by size *and colour*** (e.g. 1.5 mm² red / black / white, 2.5 mm² red / black, 4 mm² red); **BCEW earth by size**; flush **wall boxes** (100×50 for switches, 100×100 for sockets); **round / looping boxes**; **chasing per drop by height** (1 m, 2 m); draw wires; a "wiring accessories" sum | m, No, Ea, Sum |
| **B** | **Circuit wiring in metres** | India lecture | Metres of a whole circuit, the description naming its make-up (e.g. "2 × 2.5 + 1 × 1.5 mm²" = two conductors + earth): one metre of line = one metre of route carrying all of them | m |
| **C** | **Point, banded by length** | Bhutan lecture (schedule of rates) | A **point** = the wiring of one outlet, priced by the band of its routed length: short 0–3 m, medium 3–6 m, long 6–10 m; beyond 10 m the **excess** is priced per metre (rate for live + neutral). 2.5 mm² measured from the sub-board to the switch box; 1.5 mm² from the switch box to the fitting. Conduit billed separately in metres. | point, m |
| **D** | **All-in point** | Nigeria lecture | One price per point covering conduit, both conductors, box, consumables and labour, built from a per-metre rate × the **average metres per point** (§5) | point |

**The scorer and our reference bills are South African, so convention A is what AfriPlan must
produce.** B, C and D are useful as *measuring methods* (C's banding and D's average-per-point
both measure the route) but are not the form of a South African bill.

## 4. The one thing to measure: the route
All four conventions are derived from the same physical facts. Measure these and every
convention follows:
1. **Horizontal route** of each circuit's conduit — from the board, through the ceiling void (or
   floor/wall), point to point, **straight runs** (ignore drawn curves).
2. **Drops** — one vertical run per switch / socket / wall point, from the ceiling void to the
   box: **ceiling height − mounting height** (e.g. socket at 500 mm in a 3 m room → **2.5 m**;
   switch at ~1.2–1.4 m → ~1.6–1.8 m). Light points in the ceiling have no drop.
3. **Conductors in each part of the route** — power: live + neutral (+ earth); lighting: the
   feed, the neutral and the **switch wire** between the switch and the light (which is why the
   Wedela bill buys 1.5 mm² in three colours); a 4 mm² run for heavier outlets.
4. **Points and boxes** — every switch, socket, light, isolator, and every looping/junction box.
5. **Looped vs dedicated** — sockets and lights are **looped** from point to point; **AC units,
   geysers/water heaters and cookers/stoves run directly from the board**, one run each (two ACs
   in a room = two runs). Dedicated runs are usually heavier wire.

When runs are not dimensioned (PDF without scale, or no layout), the lectures' fallback is an
**average length per point = total looped metres ÷ number of points**, measured once on a
typical building and re-used (the Nigeria lecture's example averages: ~7 m per point when nothing
is measured, ~8 m for lighting, ~10 m for looped sockets — illustrations, not rules).

## 5. Converting the route into each convention
Let *R* = horizontal route metres, *D* = sum of drop heights, *n* = number of points.

| Convention A line (South Africa) | Quantity |
|---|---|
| PVC conduit (by diameter) | R + D (+ waste) |
| GP wire, each size and colour | metres of route that carry that conductor (R + D on those parts) + tails at each box and the board |
| BCEW earth (final circuits) | route that needs a separate earth (as the specification says) |
| Wall boxes 100×50 / 100×100 | count of switches / sockets |
| Round / looping boxes | count of ceiling points + looping points |
| Chasing (per drop, by height) | count of drops in masonry, banded by height |
| Draw wire, accessories | allowance / sum |

- Convention **B** = route metres per circuit type (R + D), one line per conductor make-up.
- Convention **C** = classify each point's routed length into short / medium / long; add the
  excess over 10 m as metres.
- Convention **D** = rate per metre × average metres per point (+ box + labour), per point.

## 6. Where AfriPlan stands on wiring today (and why it loses points)
| Engine | What it does now | Gap against convention A |
|---|---|---|
| **PDF** (`agent/pdf_pipeline/passes/assemble.py`, `_wiring`) | Per room: points × a fixed allowance (`light_m_per_point = 8`, `power_m_per_point = 10`) → **one** "reticulation wire" line per kind, ASSUMED. The point band is computed but only written into the note. | No conduit, no per-colour GP wire, no BCEW, no boxes, no chasing; the metres are an allowance, not a route. |
| **DWG** (`agent/dxf_pipeline/passes/assemble.py`, `_wiring`) | Per circuit: the length of the wiring polylines drawn on the plan → **one** line per circuit, MEASURED. | Plan length only: **no drops**, **no conductor multiplier** (one run ≠ red + black + white), no conduit/boxes/chasing lines. |
| **Pricing** (`agent/shared/pricing.py`, `_wire_line`) | Prices every wire line as **3-core surfix** per metre. | The reference bills GP wire in conduit by colour, not surfix. |
| **Completer** (`audit/completer.py`) | Adds boxes, chasing, conduit, GP wire, terminations from **fitted ratios** — local only (needs the client ratio model). | Ratios, not measurement; absent online. |

This is what the accuracy report shows on Wedela: GP wire quantities too low, BCEW for final
circuits and 20 mm conduit not produced, chasing and trunking not produced (`docs/accuracy-
metrics.md`, `evaluation/gaps.py`). **The fix is a route take-off (§4) that emits convention-A
lines (§5)**, measured on CAD where the wiring is drawn, and from points × banded allowances
(tagged ASSUMED, with a GapItem) where it is not.

## 7. Building up a rate (from the Nigeria lecture)
1. **Conduit per metre** = bundle price ÷ pieces per bundle ÷ length of a piece (e.g. 25 × 2.1 m).
2. **Wire per metre** = roll price ÷ roll length (e.g. 100 m); **× number of conductors** run.
3. **Box** per point.
4. **Consumables** (bushes, couplings, Y/U-boxes): a **% of the conduit cost** from past
   projects (about **9–10 %**) instead of counting each one.
5. **Transport** about **2 %**; **waste** on wire and conduit about **5 %**.
6. Per point (convention D) = rate per metre × average metres per point + labour per point.
Keep a **unit-rate bank** by trade and refresh it from suppliers; own cost data beats a guess.
AfriPlan's `api/core/rate_model.py` already applies 4–5 (`consumables_pct`, `transport_pct`,
`waste_pct`).

## 8. Writing descriptions
- Full specification: insulation/sheath, armouring, conductor, cores × size, voltage grade,
  standard; for wire, **size and colour**.
- Brands as "**… or equivalent**" — naming one brand alone excludes other suppliers.
- Units match the measure: No./Ea (count), m (length), point, Sum.
- Amounts in international grouping (1 234 567.89), not regional systems (lakh).

## 9. Regional schedules of rates
Some countries publish an official schedule (Bhutan's BSR): *basic rates* (material only) and
*built-up rates* (supply + install) per location, each with a code quoted on the BoQ line. Where
a client requires one, the reference column carries its codes. AfriPlan uses its own
deterministic rate model.

## 10. Already in AfriPlan from these methods
| Knowledge | Code | Status |
|---|---|---|
| Consumables ≈ 9 %, transport ≈ 2 %, waste ≈ 5 % | `core/rate_model.py` | Used in every built-up rate |
| Point bands, routed length, average per point | `rate_model.classify_point`, `routed_length`, `average_length_per_point` | Exist; the PDF engine only notes the band (§6) |
| Boards and breakers counted from the SLD | DXF SLD reader; PDF forms | Used |
| Feeder routes measured on the site plan | `agent/shared/routes.py` | Used; feeder length is still a large Wedela loss |
| Dedicated vs looped runs | — | Not distinguished |
| "or equivalent" wording | Exports | Not checked |

## Sources (local copies, not in the repo)
Transcripts of three training videos, kept by the owner in `Downloads`:
- *Preparing BOQ for Electrical Works* — filling a services BoQ template from the SLD, equipment,
  cable-tray, cable-schedule, power and lighting layouts; circuit wiring in metres (India).
- *BoQ preparation (Electrical Bills of quantities preparation example)* — supply-only BoQ,
  short / medium / long / excess points, schedule of rates (Bhutan, BSR 2018).
- *How to measure/takeoff for electrical work and Rate built up for cables* — routed length with
  drops, average length per point, looped vs dedicated runs, rate build-up (Nigeria).
