# Design — Professional project structure + BOQ evaluation framework

- **Date:** 2026-09-23
- **Status:** accepted (user choices recorded below)
- **Author:** Claude (Opus 5.5) with Jonathan Lukwichi

## 1. Problem

AfriPlan produces a Bill of Quantities (BOQ) from electrical drawings, but:

1. **No true evaluation.** The existing `scoring/harness.py` compares only totals and a
   few fixture counts. We cannot say *which* BOQ lines we reproduce, how accurately, or
   what we never produce at all.
2. **No drawing-sufficiency model.** We cannot tell a user which drawings are needed for a
   complete BOQ, or what a partial upload can honestly produce.
3. **No audit.** Neither our output nor a human-made BOQ is checked for arithmetic errors,
   missing companion items (feeder without terminations), or items never measured.
4. **Project hygiene.** CLAUDE.md describes an architecture that no longer matches the
   code; there is no glossary, no decision records, no reproducible dataset, CI misses
   dependencies. The project is not transferable.

## 2. Ground truth available

The Wedela Recreation Centre project (client handover, 2026-08-25):

| Asset | Content |
|---|---|
| `Wedela BOQ Rev01 141125.xlsx` | 14 sheets; 7 building bills (A–D sections + 5% contingency), minisub, Main Kiosk, P&Gs, Installation Rate, Cable Termination material, Provisional Sum. |
| `Wedela SLD 260525.pdf` | 8 pages, A3 SLDs |
| `Wedela Lighting&Plugs 260525.pdf` | 10 pages, lighting & plug layouts |
| `Wedela Electrical/*.dwg` | 18 electrical DWGs: per building `-LIGHTING`, `-PLUG`, `-SLD` (AB, ECH, LGH, PB, SGH, KIOSK, OL) |
| `4.Autocad drawings Client/*.dwg` | 7 architectural DWGs (site plan, per-building floor plans) |

Observed structure of a real SA building bill (every building sheet):

- **A** Distribution boards / excavations / main cables — trench m, warning tape m,
  sleeves m (110/75/50 mm), manholes, DBs (Sum), feeder cable Supply/Install m, BCEW
  earth Supply/Install m, terminations Supply/Install Ea.
- **B** Trunking, wiring & cable trays — tray/basket m, P9000/P8000/P2000 trunking m,
  bends/T-pieces No, round boxes No, GP wire per colour m, BCEW m.
- **C** General purpose outlets — sockets, isolators, wall boxes, chasing (No),
  conduit 20/25/32 mm (m), draw wire.
- **D** General lighting — light fittings, switches, conduit m, wall boxes.
- **E** Contingency 5 %.

Our pipelines today emit DBs, feeders, fittings and reticulation wire only. **All of
section B, the chasing/conduit/wall-box parts of C and D, sleeves and manholes are never
produced.** This is the largest systematic gap and it is invisible in the current scorer.

The reference bill itself contains defects (found by manual inspection, to be confirmed
by the audit engine): an unpriced sheet with `#REF!` (Pool-Heat Pumps) excluded from the
summary, a DB line repeated three times (Swimming Pool), install lines with no subtotal,
lights with quantity but no rate (guard houses), a GP-wire line with rate 0.

## 3. Decisions (user-confirmed 2026-09-23)

| # | Decision |
|---|---|
| D1 | Git: commit current work as a checkpoint, then one commit per task. |
| D2 | **No neural-network training on one project.** Model the BOQ as an explainable *layered network* (drawings → evidence → quantities → priced lines → totals). Its "weights" are ratios fitted from the reference by least squares and validated leave-one-building-out. Build a DWG → labelled-image dataset generator so a CNN symbol detector can be trained once 5–10 projects exist. |
| D3 | Run both pipelines (DXF free, PDF paid ≈ R30–50) on Wedela for the starting baseline. |
| D4 | Copy reference files into `data/projects/wedela/raw/` (gitignored); commit a `manifest.json` with SHA-256 checksums. |

## 4. The layered BOQ network (the "ANN view")

```
Layer 0  DRAWINGS      sld · lighting_layout · plug_layout · site_plan · schedule · legend
            │  (which drawing carries the evidence)
Layer 1  EVIDENCE      db_list · feeder(size,len) · light counts · socket counts ·
                       switch counts · isolator counts · route lengths · building list
            │  (count / measure — pipelines do this)
Layer 2  QUANTITIES    primary items (counted/measured)  +  derived items (fitted ratios:
                       wall boxes, chasing, conduit m, GP wire m, round boxes, terminations,
                       trench, tape, sleeves, earth)
            │  (× rate — core.rate_model)
Layer 3  PRICED LINES  Supply / Install / Combined lines with ItemKey
            │  (Σ)
Layer 4  TOTALS        section A–D → building → project (+contingency, +VAT, P&Gs)
```

Each Layer-2 item family declares (a) the drawing types that provide its evidence, (b) its
measurement method: `count`, `length`, `derived`, `provisional`, `prelims`. This one table
answers three product questions:

- *What drawings do I need for a complete BOQ?* → union of Layer-0 requirements.
- *What can I produce from what was uploaded?* → items whose requirements ⊆ uploaded
  (partial BOQ; everything else is PROVISIONAL + gap).
- *What did we fail to calculate?* → reference items with no predicted counterpart.

Derived-item ratios are **fitted, not assumed**: e.g. `wall_box_100x100 ≈ w·(sockets +
isolators)`, with leave-one-building-out error reported so the accuracy claim is honest.

## 5. The metric (frozen scorer)

Lines are matched on `(building, ItemKey, role)` where ItemKey is a normalised item
identity (e.g. `swa_cable|95mm2|4c`) and role ∈ {supply, install, combined}.

| Metric | Definition |
|---|---|
| **Coverage** (value-weighted recall) | Σ reference value of matched keys ÷ Σ reference value |
| **Precision** | Σ predicted value on keys that exist in the reference ÷ Σ predicted value |
| **Quantity accuracy** | value-weighted mean of `max(0, 1 − |q̂−q|/q)` over matched keys |
| **Rate accuracy** | value-weighted mean of `max(0, 1 − |r̂−r|/r)` over matched keys |
| **Total accuracy** | `max(0, 1 − |T̂−T|/T)` per building and project |
| **Reproduction Score (RS)** | Σ value_i · matched_i · qty_acc_i ÷ Σ value_i — the headline number |

Every metric is reported **twice**: against the full reference and against the *scoped*
reference (only items reproducible from the uploaded drawing types). A partial upload is
therefore scored fairly, and the difference between the two numbers *is* the "what the
missing drawings cost you" figure.

`evaluation/metrics.py` is the frozen scorer (AutoResearch `prepare.py` role): nothing in
an optimisation loop may edit it (enforced by a hook).

## 6. Audit engine

- **BOQ audit** (any bill, ours or human): arithmetic (qty×rate≠total), quantity without
  rate, duplicate lines, missing companions (feeder ⇒ earth + 2 terminations + trench +
  tape when underground), section roll-up mismatch, contingency ≠ declared %, sheets not
  rolled into the summary, `#REF!`/error cells.
- **Sufficiency audit**: per building, which drawing types are present, which BOQ
  sections are reproducible, which drawings to request.
- **Completer**: adds fitted derived lines (section B/C/D items) to a pipeline BOQ, tagged
  `INFERRED` with the ratio and its LOO error as the assumption — never silent.

## 7. Independence

`evaluation/` and `audit/` are top-level packages (like `sourcing/`, `scoring/`). They may
import `agent.shared` and `core`; the pipelines never import them. The architecture test
suite is extended to enforce this.

## 8. Out of scope (logged as issues, not done here)

Fixing the page-3 double markup, registering the Live Pricing page, v2 quality gates,
cross-page double counting. They are recorded in `issues/` with evidence.
