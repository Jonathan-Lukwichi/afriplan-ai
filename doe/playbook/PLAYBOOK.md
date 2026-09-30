# AfriPlan DOE — Layer 1: the Playbook (Direction)

The playbook says **what** we do and **what good looks like**. It never computes a number.
The brain (layer 2, `doe/brain/BRAIN.md`) reads it and decides the next step; the execution
layer (layer 3, `doe/execution/`) does the work with deterministic Python.

> The web app is a separate product and is not touched by this system. Both share the same
> engines (`api/`), read-only.

---

## 1. The job
Turn an electrical drawing set (DWG/DXF and/or PDF) into a **priced Bill of Quantities**
(Excel + PDF) that a South African contractor can tender with, and say honestly **how
reliable it is**.

## 2. Inputs
| What | Where | Needed? |
|---|---|---|
| DWG/DXF drawings (SLDs, layouts, site plan) | `data/projects/<project>/raw/` | best source — free, exact |
| PDF drawings | same folder | adds what CAD cannot show; costs AI unless re-used |
| Real priced bill (only for reference projects) | same folder | only to evaluate |
| Manifest (which file is which) | `data/projects/<project>/manifest.json` | yes |

## 3. The procedure (every run, in this order)
1. **Check the inputs** — the raw files must match the manifest's checksums. If not: STOP.
2. **Read the DWG set** — boards and breakers from the SLDs, cable routes and trench from
   the site plan, fittings from the layouts. Re-use remembered AI symbol names (free).
3. **Read the PDF set** — re-use the last saved PDF reading (R 0) unless the drawings changed
   or a fresh read is asked for (then use the AI provider in `api/.env`; Gemini is free).
4. **Combine** — pair each PDF page with its DWG sheet by the words both print; keep the
   stronger evidence: *measured > counted > written > seen > assumed*; keep what only one
   source saw; list every disagreement as a "thing to check". Never count a thing twice.
5. **Price once** — deterministic rate model: material × 1.3 markup + crew × hours labour;
   boards from their SLD contents; trench built up (dig, sand, backfill, reinstate).
6. **Write the documents** — tender Excel + PDF in the house style, with the source of every
   line in plain words and the "Things to check" list.
7. **Evaluate** (reference projects only) — score DWG alone, PDF alone and combined against
   the real bill with the frozen scorer.
8. **Report** — e-mail the Excel + PDF and the evaluation to the owner.
9. **Learn** — write what surprised us into `doe/playbook/LESSONS.md` (new drawing
   conventions, wrong matches, missing items). Never tune prices to one project.

## 4. Hard rules
- **The AI reads and names; Python counts, measures and prices.** No AI-invented numbers.
- **Never silent:** every guessed quantity is marked "Guessed — check" with its reason.
- **Never double-count:** a sheet read from DWG is not counted again from its PDF.
- **Client data stays private:** outputs go to `runs/doe/` (never committed, never
  published); e-mail only to the owner's address.
- **Generalise:** a fix must work on other consultants' drawings, not only on Wedela.
- **Don't change the scorer** to make a number look better.

## 5. What the scores mean and when we call it reliable
| Score | Plain meaning |
|---|---|
| **Reproduction Score (RS)** — the headline | share of the real bill's value reproduced with the right quantities |
| Coverage | share of the real bill's value we found at all |
| Precision | share of what we priced that really belongs in the bill (low = invented/double) |
| Qty accuracy | for what we found, how close the quantities are |
| Rate accuracy | for what we found, how close our unit prices are |
| Total off by | how far our bill total is from the real total |

| Level | Condition (all must hold) | Use |
|---|---|---|
| Useful draft | RS ≥ 60 %, precision ≥ 90 % | saves hours; a person checks every line |
| Reliable assistant | RS ≥ 75 %, precision ≥ 90 %, total within ±15 % | tender prep; a person checks "Things to check" |
| Near-estimator quality | RS ≥ 85 %, precision ≥ 90 %, total within ±10 % | quick quotes; a person signs off |

**Proof rule:** a level counts only when it holds on **3–5 different projects, including one
we never tuned on**. Today we have one project (Wedela), so no level is proven yet.

## 6. When to stop and ask the owner
- Inputs don't match the manifest; a drawing can't be opened.
- The AI provider has no key or no credit and a fresh PDF read was asked for.
- A score drops compared with the last run of the same inputs (something broke).
- More than 5 "high" things to check about boards or feeders (the supply is unclear).
