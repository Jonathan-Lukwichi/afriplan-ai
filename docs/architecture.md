# Architecture — AfriPlan Electrical (v6.2)

```
                        ┌──────────────── drawings ────────────────┐
                        │   PDF set (SLD, layouts, register)       │   DWG / DXF (CAD)
                        ▼                                          ▼
 ┌──────────── agent/pdf_pipeline/passes ─────────┐   ┌──── agent/dxf_pipeline/passes ────┐
 │ ingest → classify (Haiku) → Passes 1-3 (Sonnet │   │ dwg→dxf (LibreDWG) → recognise    │
 │ "eyes", tool_use) → PdfFacts                   │   │ → legend (LDSE) → spatial → count │
 │ → Passes 4-5 assemble.py (pure Python "brain") │   │ → assemble (pure Python)          │
 └────────────────────────┬───────────────────────┘   └─────────────────┬─────────────────┘
                          │   both emit agent.shared.BillOfQuantities   │
                          └───────────────────┬─────────────────────────┘
                                              │   (pipelines never import each other)
        ┌─────────────────────────────────────┼──────────────────────────────────────────┐
        ▼                                     ▼                                          ▼
  pages/ UI + exports/               READ-ONLY LAYERS (never imported by agent/)     runs/<p>/<id>.json
  (Streamlit, Excel, PDF)            ┌────────────────────────────────────────────┐
                                     │ evaluation/  ground truth + frozen scorer  │
                                     │ audit/       rules · sufficiency · completer│
                                     │ sourcing/    live supplier prices          │
                                     │ ml/          CNN training-data generator   │
                                     │ scoring/     legacy totals scorer          │
                                     └────────────────────────────────────────────┘
```

## The two pipelines

| | PDF (`run_pdf_estimator`) | DXF (`run_dxf_estimator`) |
|---|---|---|
| Input | a SET of PDFs, auto-classified per page | one DXF/DWG |
| Perception | vision LLM, strict `tool_use` schemas, retry-with-feedback | ezdxf geometry, pattern table, legend, OpenCV template match |
| Arithmetic | pure Python (`passes/assemble.py`, `core/rate_model.py`) | pure Python (`passes/assemble.py`) |
| Determinism | facts are stochastic; bill is deterministic given facts | fully deterministic |
| Cost | ≈ R 1.80 / page (Sonnet) | R 0 |

The legacy v1 stage pipelines (`run_pdf_pipeline`, `run_dxf_pipeline`) remain and stay
green, but the UI uses the v2 `passes/` entry points.

## The evaluation layer (what "good" means)

```
data/projects/<p>/raw/*.xlsx ──parse──▶ ReferenceBoq (evaluation/reference.py)
                                          │  every line → ItemKey (evaluation/taxonomy.py)
                                          ▼
        fitted ratios (evaluation/ratios.py) ◀── layered BOQ network (evaluation/network.py)
                                          │
pipeline BOQ ──pred_lines_from_boq──▶ score() (evaluation/metrics.py — FROZEN) ──▶ Scorecard
                                          │
                                          ▼
                           report.py → reports/baselines/*.md
```

The **layered BOQ network** is the explicit model of how a bill is produced:

```
Layer 0 DRAWINGS  → Layer 1 EVIDENCE → Layer 2 QUANTITIES → Layer 3 PRICED LINES → Layer 4 TOTALS
 sld, layouts,       counts, lengths,    primary (counted)     qty × rate           section → building
 site plan…          DB list             + derived (ratios)    (core.rate_model)    → project (+cont., VAT)
```

It answers: *which drawings does a complete BOQ need*, *what can this upload produce*
(partial BOQ), and *what did we never calculate*.

## The audit layer (commercial features)

| Module | Question it answers |
|---|---|
| `audit/boq_rules.py` | Is this bill internally correct? (arithmetic, unpriced lines, duplicates, roll-ups, missing companion items, orphan sheets) |
| `audit/sufficiency.py` | Can these drawings produce a complete BOQ? What should the client send next, and what is it worth? |
| `audit/completer.py` | What derived items (boxes, chasing, conduit, wire, terminations) are missing from a pipeline bill? Adds them, tagged INFERRED. |

## Invariants (CI-enforced in `tests/architecture/`)
- PDF ↔ DXF pipelines never import each other; DXF imports no LLM SDK.
- `agent/` never imports `evaluation`, `audit`, `scoring`, `sourcing`, `ml`, `agent.comparison`.
- `evaluation/` and `audit/` import no pipeline and no LLM SDK (the ruler is independent of what it measures).

## Data flow for a reproducible baseline
```
python scripts/verify_data.py wedela            # inputs byte-identical to manifest
python scripts/build_reference.py wedela        # reference_boq.json + ratio_model.json
python scripts/run_baseline.py --project wedela --pipeline dxf --out reports/baselines/<date>-wedela-dxf.md
python scripts/audit_boq.py --project wedela --out reports/audits/wedela-reference-audit.md
python scripts/audit_boq.py --project wedela --sufficiency --out reports/audits/wedela-drawing-sufficiency.md
```
