# How we measure BoQ accuracy

**Question answered:** how close is the BoQ we produce to the real, human-priced bill for the
same drawings — and where exactly is the difference?

The answer comes from the **frozen scorer** (`api/evaluation/metrics.py`, [ADR-0003](adr/)).
It never changes inside an improvement loop, so every score in `reports/baselines/README.md`
is comparable with every other.

## 1. What is compared

| Side | What it is |
|---|---|
| **Real bill** (reference) | the quantity surveyor's priced Excel BoQ, parsed into lines (`scripts/build_reference.py` → `data/projects/<p>/reference_boq.json`, local only). Only priced **building lines** count — contingency, VAT and P&Gs are excluded. |
| **Our bill** (prediction) | the BoQ a reader produced: CAD alone, PDF alone, or the combined bill we deliver. |

Lines are matched on **(building, ItemKey)**. The ItemKey is the item's *type*, not its wording:
`swa_cable|95mm2|4c`, `db`, `socket_double`, `light_vapour_proof` … (`api/evaluation/taxonomy.py`).
So "95mm² x 4C PVC SWA PVC 600/1000V" and "SWA 95/4" are the same item. A Supply line + an
Install line in the real bill are one item. The project-level view merges all buildings.

## 2. The metrics

Every metric is weighted by the item's **value in the real bill** — an item worth R 100 000
counts 250× more than one worth R 400. That is deliberate: it is how a tender is won or lost.

| Metric | Formula (w = real value of the item) | Read it as |
|---|---|---|
| **Reproduction Score (RS)** — headline | Σ w·matched·qty_acc / Σ w | share of the real bill reproduced *with the right quantity*. 100 % = every item, exact quantities. |
| **Coverage** | Σ w(matched) / Σ w | share of the real bill whose item we produced at all |
| **Precision** | our value on real items / all our value | how much of what we priced belongs in the bill |
| **Quantity accuracy** | Σ w·(1 − \|q̂−q\|/q) / Σ w, matched items | how right our quantities are, where we have the item |
| **Rate accuracy** | same, on unit rates | how right our prices are — **not in RS** |
| **Total accuracy** | 1 − \|T̂−T\|/T | bill total vs real total — can be good **by luck** (misses and extras cancel); never judge on it alone |
| **Scoped** variants | the same, only on items the uploaded drawings *can* show (`evaluation/network.py`) | full ≪ scoped → the problem is missing drawings, not our readers |

**Why RS ignores rates:** rates come from our rate model (crew × hours, supplier prices) —
a pricing policy, not something read off a drawing. RS judges the *take-off* (what and how
much); rate accuracy judges the *pricing*. Both are reported; only RS is the headline.

## 2b. Reading accuracy — the headline for now

The current aim is **reading**: did AfriPlan read what is drawn? Pricing is judged later.
`api/evaluation/reading.py` judges only the items that are **counted or measured on the uploaded
drawings** (network method `count` / `length`, drawing type present). It leaves out, and names:
**derived** items (wire, conduit, trunking, boxes, trench — an estimating rule, not a reading) and
**provisional** items (connection fees, CoC, P&Gs — never on a drawing).

| Reading metric | Meaning |
|---|---|
| **Reading score** | Σ w·found·qty_acc / Σ w on judged items — w is the item's value in the *real* bill (what it is worth to get right); **our rates never enter** |
| Coverage | share of the judged value we read at all |
| Quantity accuracy | how close our counts / lengths are, where we read the item |
| Items found, within ±5 %, within ±10 % | plain counts — how many items, how many close enough |
| Item precision | of the read-type items we produced, the share that are in the real bill (by count — prices not used) |

**Caveat — the reference is a priced bill, not the drawings.** Where the quantity surveyor priced a
different size or grouped boards differently from the drawing, a correct reading still loses points.
Each reading loss is therefore rechecked against the drawing and labelled *our error*, *bill differs
from drawing* or *to verify*. A drawing ground truth (what is drawn, counted and measured by a person)
is the clean reference to build next.

## 3. Where the missing points are — the gap analysis

`api/evaluation/gaps.py` splits the missing score exactly: each real-bill item loses

    points_lost = w · (1 − matched · qty_acc) / Σ w

and the points lost add up to **100 − RS**. Each loss gets:

- a **cause** — `not_produced` (absent from our bill), `qty_low`, `qty_high`;
- a **bill section** — A: DBs, main cables, trenching · B: trunking, wiring · C: outlets ·
  D: lighting · F: bulk supply (kiosk);
- a **method** — how the item is obtained: `count` (symbols), `length` (measured runs),
  `derived` (follows from other items: wire, conduit, boxes, trench), `provisional`
  (never on a drawing: connection fees, CoC);
- the **kind of fix** it needs, e.g. *"length too short — measure the route on the site plan"*,
  *"never on a drawing — add it as a rule"*, *"the uploaded drawings cannot show it — needs a
  site_plan drawing"*.

It also lists **rate errors** (with their effect on our total) and **extras** (items we priced
that the real bill does not have — they lower precision).

## 4. What determines BoQ accuracy first

Measured on the reference project (Wedela, 7 buildings) — percentages only:

1. **The value is in Section A** — DBs, main SWA feeders, trenching and earth: about **60 %**
   of the real bill. Lighting (D) is about 21 %, wiring/trunking (B) 10 %, outlets (C) 4 %.
   A perfect symbol counter alone would score below 10 %.
2. So the first things to get right are, in order: **feeder cable sizes and lengths**
   (from the SLD + the site plan), **the number of boards** (one per board, never duplicated
   across sheets), **trench length**; then **derived installation material** (trunking,
   conduit, wire, BCEW) which together are about 29 % of the value and are mostly *not
   produced* today; then counts of fittings and outlets.
3. Provisional items (connection fees) cannot be read from any drawing — they need a rule.

## 5. How to produce the report

DOE workflow (free, no AI cost on a re-run):

```bash
$PY doe/execution/project.py finish "<project folder>" --reference <reference project>
```

writes `accuracy_report.md` (to read) and `accuracy_report.json` (to compare runs) into
`<folder>/AfriPlan_Output/`, plus a dated copy in `reports/accuracy/`. Both quote the real
bill's items and rand values — **client data, gitignored** (ADR-0005). The committed record of
progress is the percentage table in `reports/baselines/README.md`.

App runs (DXF / PDF) are scored with `scripts/run_baseline.py` / `scripts/evaluate.py`
(skill `evaluate-boq`).
