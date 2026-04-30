# AfriPlan Electrical · v6.1

**Independent dual-pipeline electrical Bill-of-Quantities extractor for South African contractors.**

Upload an electrical PDF, a DXF, or both. Each pipeline runs independently and produces its own Excel/PDF BoQ. When both run, a read-only comparison layer shows where they agree, where they disagree, and which one matches a hand-validated baseline more closely.

The architecture is shaped by [the v6.1 blueprint](AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md) and a single rule:

> **Pipelines do not share state. Pipelines do not call each other.**

This makes failure attribution trivial (the wrong line item is in one of two places), makes either input optional (you get a BoQ from whichever you have), and makes head-to-head comparison a research-grade artefact.

---

## What runs

```
┌─── PDF ────┐                     ┌─── DXF ────┐
│ rasterise  │ Haiku  / Sonnet     │ ezdxf      │ no LLM
│ classify   │  + Opus escalation  │ patterns   │ deterministic
│ extract    │ via tool_use        │ extract    │ exact counts
│ evaluate   │ confidence + MAPE   │ evaluate   │ coverage + MAPE
│ generate   │ BoQ                 │ generate   │ BoQ
└────────────┘                     └────────────┘
       │                                  │
       └──────────────┬───────────────────┘
                      ▼
           Cross-pipeline comparison
           (read-only, never gates)
```

| | PDF pipeline | DXF pipeline |
|---|---|---|
| Cost / run | ≈ R 3 – R 8 | R 0 |
| Time / run | ≤ 60 s for 10 pages | ≤ 5 s |
| Determinism | Stochastic (LLM) | Deterministic |
| Strengths | Schedules, notes, multi-DB SLDs | Exact counts, exact lengths, exact coordinates |
| Weaknesses | Hallucination, variance | No schedule data, no metadata |
| Gate criterion | MAPE ≤ 20 % vs baseline | Coverage ≥ 0.80 |

---

## Running it

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Optional: provide an Anthropic API key for the PDF pipeline
echo 'ANTHROPIC_API_KEY = "sk-ant-..."' > .streamlit/secrets.toml

# 3. Launch
streamlit run app.py
```

Without `ANTHROPIC_API_KEY` only the DXF pipeline is functional — the UI flags this and lets you run on DXF alone.

---

## Repository layout

```
afriplan-ai/
├── app.py                       single-page entry
├── pages/1_Upload.py            two-column UI + comparison panel
├── ui/                          shared UI primitives (no business logic)
│
├── agent/
│   ├── shared/                  types used by BOTH pipelines (BoQ, Project, etc.)
│   ├── pdf_pipeline/            STRICT INDEPENDENCE — see agent/pdf_pipeline/README.md
│   ├── dxf_pipeline/            STRICT INDEPENDENCE — see agent/dxf_pipeline/README.md
│   └── comparison/              read-only cross-pipeline diff
│
├── core/
│   ├── config.py                model registry, per-pipeline thresholds
│   ├── constants.py             SA unit prices (shared)
│   ├── standards.py             SANS 10142-1 helpers
│   └── layer_aliases.py         DXF layer-name normalisation
│
├── exports/
│   ├── excel_boq.py             BillOfQuantities → .xlsx
│   └── pdf_boq.py               BillOfQuantities → .pdf
│
├── baselines/                   hand-validated ground truth per project
├── scripts/build_baselines.py   author baselines interactively or from a DXF run
├── runs/                        gitignored run logs (per pipeline + comparison)
│
└── tests/
    ├── architecture/            CI-enforced independence rules
    ├── dxf_pipeline/            no Anthropic, no network
    ├── pdf_pipeline/            mocked LLM, no network
    └── comparison/              integration only
```

The **architecture/** test suite enforces the independence rule by grepping the source tree on every CI run:

* `agent/pdf_pipeline/` may not import from `agent/dxf_pipeline/`
* `agent/dxf_pipeline/` may not import from `agent/pdf_pipeline/`
* `agent/dxf_pipeline/` may not import any LLM SDK
* Neither pipeline may import `agent/comparison/`
* `agent/pdf_pipeline/` may not contain `parse_json_safely(` (use `tool_use` schemas)

If those tests pass, the architecture is sound; if any of them fail, the rebuild has regressed.

---

## Tests

```bash
pytest tests/dxf_pipeline/   # deterministic, ~3 s
pytest tests/pdf_pipeline/   # mocked LLM, ~12 s
pytest tests/comparison/     # integration, ~1 s
pytest tests/architecture/   # static checks, ~1 s
```

CI runs each suite as a separate GitHub Actions job (see `.github/workflows/ci.yml`). Total wall-clock is < 4 minutes by design.

---

## Research angle

The dual-pipeline shape exists for both product *and* research reasons. After 30 production runs you have the dataset for a thesis chapter:

> *"Vision Language Models versus Deterministic CAD Parsing for Bill-of-Quantities Generation in Electrical Engineering: A Comparative Field Study."*

Each project produces:

* `runs/pdf/<run_id>.json` — full PDF run, including stage-level token costs
* `runs/dxf/<run_id>.json` — full DXF run
* `runs/comparison/<run_id>.json` — diff
* `baselines/<project>.json` — hand-validated ground truth (one per project)

Aggregate over N projects → mean MAPE per pipeline per BoQ section, cost per correct line item, categories where one pipeline systematically beats the other.

---

## License & support

Author: **Hervé / JLWanalytics**
Issues: https://github.com/Jonathan-Lukwichi/afriplan-ai/issues

Built around the [v6.1 dual-pipeline blueprint](AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md). Fully traceable from contract → implementation → test for every stage of both pipelines.
