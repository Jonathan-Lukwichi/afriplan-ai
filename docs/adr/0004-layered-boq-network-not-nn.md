# ADR-0004: A layered, explainable BOQ network — not a trained ANN/CNN (yet)

- **Status:** accepted
- **Date:** 2026-09-23

## Context
The goal: understand how a BOQ is truly reproduced from drawings, build a baseline
model and metric, and know which drawings a complete BOQ needs. An ANN/CNN approach
was proposed. We hold exactly one fully labelled project (Wedela: 7 building bills,
~350 lines). A neural network trained on it would memorise Wedela and report flattering
in-sample accuracy that does not transfer to the next project.

## Decision
1. Model the BOQ as an explicit **layered network** — drawings → evidence →
   quantities (primary + derived) → priced lines → totals (`api/evaluation/network.py`).
   This is the ANN idea made explicit: layers, edges, weights — but every edge is
   named and inspectable.
2. Learn the network's **weights** — ratios from primary to derived items — by least
   squares on the reference and report **leave-one-building-out** error for each
   (`api/evaluation/ratios.py`). The completer uses only ratios with LOO error ≤ 35 %.
3. Prepare for a CNN now at zero labelling cost: `api/ml/symbol_dataset.py` renders every
   DWG and projects its classified blocks into YOLO boxes. Train a detector only once
   5–10 reference projects exist, validated leave-one-project-out.

## Consequences
- Every number is explainable to a contractor ("1.16 chases per outlet, ±32 %").
- Generalisation claims are honest (held-out error, never training error).
- The CNN path is ready but blocked on data, not code; `api/ml/DATASET_CARD.md` reports how
  many labels the CAD actually yields (exploded Revit line-work yields few).
