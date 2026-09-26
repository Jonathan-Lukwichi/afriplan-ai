# context.md — the ubiquitous language

One glossary, used identically in conversation, plans, code, reports and the UI.
If a word here is used differently anywhere, fix the usage, not the glossary
(or change the glossary deliberately and say so).

## What this repo is
Software that reads South African electrical drawings and produces the priced
Bill of Quantities a contractor tenders with — and measures, honestly, how close
that bill is to one a human estimator priced from the same drawings.

---

## The deliverable

### BOQ / Bill of Quantities
The priced list of every item needed to build the electrical installation. In code:
`agent.shared.BillOfQuantities`. A **project** may have several **building bills**
plus a **summary** that rolls them up, plus **P&Gs**.

### Building bill
One sheet of a project BOQ covering one building (Wedela: "Existing Community Hall",
"Swimming Pool" …). Organised in **bill sections**.

### Bill section (A–D, F, P)
The SA building-bill layout observed on real bills:
**A** distribution boards / excavations / main cables · **B** trunking, wiring &
trays · **C** general-purpose outlets · **D** general lighting · **E** contingency ·
**F** bulk power (kiosk / minisub) · **P** P&Gs. Distinct from the 14 `BQSection`
values our pipelines emit (a presentation taxonomy); `evaluation.taxonomy.BILL_SECTION_OF`
maps item families to letters.

### Line
One row of a bill: description, unit, quantity, rate, total. A line has a **role**.

### Role — Supply / Install / Combined
SA bills split cables (and terminations) into a **Supply** line (material) and an
**Install** line (labour), each with the same quantity. Fittings are one
**Combined** line. The scorer treats a Supply+Install pair and a Combined line for
the same item as the same item.

### P&Gs (Preliminaries & General)
Time-based site costs (site manager, containers, plant). Never derived from drawings;
excluded from reproduction scoring.

### Contingency
A percentage (5 % on Wedela) added to a building's section totals.

---

## Item identity

### ItemKey (`family|spec`)
The normalised identity of a line, whoever wrote it: `swa_cable|95mm2|4c`,
`wall_box|100x100`, `socket_double`. **Family** = what the item is; **spec** = the
variant that changes price or quantity (cable size + cores, conduit size, trunking
type, switch levers). Spec is deliberately empty where pipelines cannot see the
variant (socket amps, light wattage). Defined in `api/evaluation/taxonomy.py`.

### Primary item
An item counted or measured directly from a drawing: sockets, lights, switches,
isolators, DBs, feeder cable length.

### Derived item
An item an estimator infers from primary items because it is never drawn as a
symbol: flush wall boxes, chasing, conduit, GP wire, round boxes, terminations,
trench, warning tape.

### Ratio (fitted)
`qty(derived) ≈ weight × Σ qty(primary inputs)`, fitted by least squares on a
reference project, reported with its **LOO error**. The "weights" of the layered BOQ
network. `api/evaluation/ratios.py`.

### LOO error
Leave-one-building-out mean absolute % error of a ratio: fit on all buildings but
one, predict the held-out building, average. The honest "does this generalise"
number. Ratios above 35 % are not used by the completer.

---

## Drawings and evidence

### Drawing type
`sld` (single-line diagram) · `lighting_layout` · `plug_layout` · `site_plan` ·
`schedule` · `legend` · `register` · `architectural`. `evaluation.network.DrawingType`.

### SLD (single-line diagram)
The drawing that shows distribution boards, their circuits, and the feeder cables
between them. Carries the highest-value evidence of a bill.

### Evidence
What an estimator reads off a drawing to quantify an item (a count, a length, a DB
list).

### Layered BOQ network
The explicit graph drawing → evidence → quantity → priced line → total
(`api/evaluation/network.py`). Each item family declares its **method** (`count`,
`length`, `derived`, `provisional`, `prelims`) and which drawing types carry its
evidence. It is *not* a trained neural network (ADR-0004).

### Legend / LDSE
A drawing's own symbol key. Legend-Driven Symbol Extraction reads it as ground
truth for that drawing (`api/agent/shared/legend.py`).

### Feeder
A sub-main cable run between two nodes (kiosk → DB, DB → sub-DB). Every feeder
implies an earth (**BCEW**), two **terminations**, and — underground — trench +
warning tape.

### BCEW
Bare copper earth wire, run alongside a feeder (large sizes) or as a circuit earth
(1.5 mm² in section B).

### DB
Distribution board. Priced per board as a "Sum" line.

### Point method
Reticulation wire allowance per point (short/medium/long/axis) — `api/core/rate_model.py`.

---

## Evaluation and audit

### Reference project / reference BOQ
A real project whose drawings and human-priced BOQ we hold. Lives in
`data/projects/<project>/`. The reference BOQ is ground truth — but it is audited too;
it is not assumed perfect.

### Manifest
`data/projects/<p>/manifest.json`: every input file with SHA-256, role, building.
What makes an evaluation reproducible.

### Superseded
An older revision of a drawing in the same set. Never used (double counting).

### Reproduction Score (RS)
The headline metric: Σ reference value × matched × quantity accuracy ÷ Σ reference
value. "What share of the bill's value did we reproduce, discounted by how wrong the
quantities were." `api/evaluation/metrics.py`.

### Coverage · Precision · Quantity accuracy · Rate accuracy · Total accuracy
Coverage = value share of reference items predicted at all. Precision = value share of
predicted items that exist in the reference. Quantity/rate accuracy =
value-weighted `max(0, 1 − |p − a|/a)` over matched items.

### Scoped metrics
The same metrics restricted to items **reproducible** from the drawing types
actually uploaded. Full minus scoped = what the missing drawings cost.

### Sufficiency / coverage ceiling
For a building and an upload: the share of the reference value the available drawing
types can reproduce at all. No pipeline can beat it. `api/audit/sufficiency.py`.

### Complete BOQ / partial BOQ
Complete: every drawable item family is reproducible from the upload. Partial: some are
not — those become PROVISIONAL gaps, never silent omissions.

### Completer
`api/audit/completer.py`: adds derived items to a pipeline bill using fitted ratios,
tagged `INFERRED`, with the ratio and LOO error in the assumption.

### Audit finding
A rule violation in a bill with a severity and rand **value at risk**: ARITH,
UNTOTALLED, NO_RATE, DUPLICATE, REPEATED, ROLLUP, CONTINGENCY, TOTAL,
NOT_IN_SUMMARY, SUMMARY, ERROR_CELL, COMPANION. `api/audit/boq_rules.py`.

### Baseline
A committed, dated score report of a pipeline on a reference project
(`reports/baselines/`). Improvements are claimed only against a baseline.

### Gap
`GapItem` — something estimated or unverifiable, listed for the human to check.

### Provenance tags
`EXTRACTED` (read from drawing) · `INFERRED` (derived deterministically / by fitted
ratio) · `ASSUMED` (documented assumption) · `PROVISIONAL` (allowance) · `MANUAL`
(contractor / live supplier price) · `ESTIMATED` (legacy guess).

### Run
One pipeline execution; persisted to `runs/<pipeline>/<run_id>.json` when `persist=True`.

---

## Terms to avoid / disambiguate
- **"accuracy"** alone → say which: Reproduction Score, coverage, quantity accuracy.
- **"the model"** → say *ratio model*, *LLM (Sonnet/Haiku/Opus)*, or *layered BOQ network*.
- **"ANN/CNN model"** → we have none trained. Say *layered BOQ network* (explicit graph)
  or *CNN symbol dataset* (training data only).
- **"section"** → say *bill section (A–D)* or *BQSection (1–14)*.
- **"baseline"** (old `baselines/*.json`) → that is the legacy totals file; the ground
  truth is now the *reference BOQ* in `data/projects/`.
- **"building_block"** in `BQLineItem` holds DB or room names in pipeline output — not a
  reference building name. Map before scoring.
