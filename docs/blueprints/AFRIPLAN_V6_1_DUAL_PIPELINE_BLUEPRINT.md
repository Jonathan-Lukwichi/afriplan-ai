# AfriPlan Electrical — v6.1 Rebuild Blueprint
## Dual Independent Pipelines (PDF + DXF) with Per-Pipeline Evaluation

> **Supersedes** the v6.0 blueprint dated 29 April 2026. The fused-pipeline architecture in v6.0 is replaced by two **fully independent pipelines** — one for PDF, one for DXF — each with its own extraction, evaluation, and BOQ generation. A cross-comparison layer sits on top as an optional research metric only; it does not gate either pipeline.

> **Author intent.** Hervé / AfriPlan AI — South African electrical quotation automation, designed to support both production use *and* the comparative ML research that motivates the work (Industrial Engineering Master's, ML applied to engineering documents).

---

## 0. The single most important rule

> **Pipelines do not share state. Pipelines do not call each other. Each pipeline is a standalone product.**

A change in the PDF extraction prompts does not affect the DXF tests.
A `pyautocad` / `ezdxf` upgrade does not break PDF tests.
Each pipeline can be deployed, evaluated, and reasoned about in isolation.

Everything below follows from this rule.

---

## 1. Why two pipelines (and not one)

### 1.1 Three problems with the fused design

| Problem | Fused (v6.0) | Independent (v6.1) |
|---|---|---|
| **Failure attribution** | When BOQ is wrong, root cause is buried in fusion logic | Each pipeline emits its own BOQ — failure is locatable in one of two places |
| **Input optionality** | Both inputs required or pipeline breaks | Either input alone produces a valid BOQ |
| **Comparative research** | DXF and PDF outputs are merged before they can be compared | Each pipeline produces its own deliverable; head-to-head comparison is trivial |

### 1.2 The research angle

An independent two-pipeline design is the natural shape of a comparative experiment. With it, you can answer questions like:

- For a given building type, which pipeline achieves lower MAPE against the human BOQ?
- How does each pipeline scale with drawing complexity (page count, fixture count)?
- What is the cost-per-correct-line-item for each? (DXF pipeline cost ≈ R 0; PDF pipeline cost ≈ R 5 per project — but PDF captures things DXF can't.)
- On what categories does each pipeline systematically fail?

These are publishable questions. They require the architecture below.

### 1.3 The product angle

A consultant who only has a PDF still gets a BOQ. A consultant who only has a DXF still gets a BOQ. A consultant with both gets two BOQs and a comparison report. **No upload combination ever produces zero output.**

---

## 2. Architecture

### 2.1 The full picture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         AFRIPLAN v6.1                                │
│                                                                      │
│   ┌─── 1A. PDF UPLOAD ───┐         ┌─── 1B. DXF UPLOAD ───┐          │
│   │ wedela_full_set.pdf  │         │ wedela_layout.dxf    │          │
│   └──────────┬───────────┘         └──────────┬───────────┘          │
│              │                                │                      │
│              ▼                                ▼                      │
│  ┌─────────────────────────┐    ┌─────────────────────────┐          │
│  │   PDF PIPELINE          │    │   DXF PIPELINE          │          │
│  │   ────────────          │    │   ────────────          │          │
│  │   • PDF Ingest          │    │   • DXF Ingest          │          │
│  │   • Page Classify       │    │   • Layer Analysis      │          │
│  │   • LLM Extract         │    │   • Block Extract       │          │
│  │     (tool_use, Sonnet)  │    │     (ezdxf, Python)     │          │
│  │   • PDF Evaluate        │    │   • DXF Evaluate        │          │
│  │     (LLM-aware metrics) │    │     (deterministic)     │          │
│  │   • PDF BOQ Generate    │    │   • DXF BOQ Generate    │          │
│  └────────────┬────────────┘    └────────────┬────────────┘          │
│               │                              │                       │
│               ▼                              ▼                       │
│  ┌─────────────────────────┐    ┌─────────────────────────┐          │
│  │  PDF BOQ (Excel + PDF)  │    │  DXF BOQ (Excel + PDF)  │          │
│  │  + pdf_eval.json        │    │  + dxf_eval.json        │          │
│  └────────────┬────────────┘    └────────────┬────────────┘          │
│               │                              │                       │
│               └──────────────┬───────────────┘                       │
│                              ▼                                       │
│              ┌──────────────────────────────────┐                    │
│              │   3. CROSS-COMPARISON LAYER      │                    │
│              │   (optional, research-grade)     │                    │
│              │   • Field-by-field agreement     │                    │
│              │   • Per-section MAPE between     │                    │
│              │     PDF-BOQ and DXF-BOQ          │                    │
│              │   • Cost / accuracy trade-off    │                    │
│              └──────────────────────────────────┘                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Key property: the dashed line between the two pipelines and the
cross-comparison is one-way. The comparison reads the outputs.
The pipelines never read each other.
```

### 2.2 What each pipeline owns

|  | PDF Pipeline | DXF Pipeline |
|---|---|---|
| **Input** | Single PDF (multi-page) | Single DXF |
| **Primary technology** | Vision LLM via Anthropic `tool_use` | `ezdxf` library (pure Python) |
| **Determinism** | Stochastic (LLM) | Deterministic |
| **Cost per run** | ≈ R 3 – R 8 | R 0 |
| **Strengths** | Reads schedules, notes, title blocks, multi-DB SLDs | Exact counts, exact lengths, exact coordinates |
| **Weaknesses** | Hallucination, variance, slower | No schedule data, no project metadata |
| **Output** | `pdf_boq.xlsx` + `pdf_boq.pdf` + `pdf_eval.json` | `dxf_boq.xlsx` + `dxf_boq.pdf` + `dxf_eval.json` |
| **Test methodology** | Mocked LLM responses, ≥3 runs for variance | Direct equality assertions, single run |
| **CI gate criterion** | Mean BOQ MAPE ≤ 15% across baselines | Exact match on counts where ground truth exists |

---

## 3. PDF Pipeline — Detailed Spec

### 3.1 Stages

`agent/pdf_pipeline/`

```
PDF File
   │
   ▼
┌──────────────────────────┐
│ STAGE P1: INGEST         │  PyMuPDF rasterise pages at 200 DPI
│  ingest.py               │  Cap at 30 pages, hash inputs
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE P2: CLASSIFY       │  Haiku 4.5 classifies each page:
│  classify.py             │  register | sld | lighting_layout |
│                          │  plugs_layout | schedule | notes
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE P3: EXTRACT        │  Sonnet 4.5 with tool_use,
│  extract.py              │  schema-enforced. Per page-type prompt.
│                          │  Retry-with-error-feedback on validation fail.
│                          │  Escalate to Opus only if retry fails.
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE P4: EVALUATE       │  LLM-pipeline-specific evaluation:
│  evaluate.py             │  • per-field confidence
│                          │  • cross-page consistency (same DB on
│                          │    register + SLD agree?)
│                          │  • baseline regression (vs Wedela/Trichard)
│                          │  • SANS 10142-1 compliance
└────────────┬─────────────┘
             ▼
        passed?
       ┌──┴──┐
   yes │     │ no
       ▼     ▼
┌─────────┐ ┌──────────────────┐
│ P5: GEN │ │ P5b: REVIEW UI   │
│         │ │ (PDF-specific:   │
│         │ │ shows confidence │
│         │ │ heatmap on each  │
│         │ │ rasterised page) │
└─────────┘ └──────────────────┘
```

### 3.2 PDF pipeline data contract

```python
# agent/pdf_pipeline/models.py

class PdfPipelineRun(BaseModel):
    run_id: str
    timestamp: datetime
    input_file: str
    input_sha256: str
    page_count: int
    page_classifications: list[PageClassification]
    extraction: PdfExtraction
    evaluation: PdfEvaluation
    boq: BillOfQuantities | None = None     # None if evaluation failed
    cost_zar: float
    duration_s: float

class PdfExtraction(BaseModel):
    """Everything extracted from the PDF — confidence-scored."""
    project: ProjectMetadata
    distribution_boards: list[DistributionBoard]   # from SLD pages
    schedules: list[CircuitSchedule]               # from schedule pages
    fixtures_per_room: dict[str, FixtureCounts]    # from layout pages
    legends: dict[str, str]
    notes: list[str]
    per_field_confidence: dict[str, float]
    extraction_warnings: list[str]

class PdfEvaluation(BaseModel):
    """Methodology specific to LLM pipelines."""
    # 1. LLM-internal confidence aggregation
    mean_confidence: float
    min_confidence: float
    low_confidence_fields: list[str]         # below 0.6

    # 2. Cross-page consistency
    cross_page_agreements: int               # e.g. DB-PFA referenced on 3 pages, all agreed
    cross_page_disagreements: list[CrossPageDisagreement]
    consistency_score: float

    # 3. Baseline regression
    baseline_project: str | None
    baseline_mape: float | None

    # 4. SANS compliance
    sans_violations: list[ComplianceFlag]
    sans_warnings: list[ComplianceFlag]

    # Composite gate
    passed: bool
    overall_score: float
    failure_reasons: list[str]
```

### 3.3 PDF pipeline evaluation methodology

PDF evaluation must account for **LLM stochasticity**. This is qualitatively different from how you evaluate the DXF pipeline.

| Concern | Approach |
|---|---|
| **Output variability between runs** | Run extraction 3× per page in CI; report mean + standard deviation |
| **Hallucinated DBs / fixtures** | Cross-page consistency check (a DB mentioned on a layout but not on any SLD = hallucination flag) |
| **Schema drift on prompt change** | `tool_use` schema versioning; semver bump = full regression run |
| **Cost regression** | Track per-run token cost; alert if it climbs >20% vs rolling baseline |
| **Confidence calibration** | Quarterly review: do fields with confidence > 0.9 actually have <5% error rate? If not, recalibrate |

### 3.4 PDF pipeline acceptance criteria

The PDF pipeline ships when:

1. Running it on the Wedela PDFs alone produces an Excel BOQ within 20% MAPE of the Wedela ground-truth BOQ (sections A–F, ignoring G/H/I).
2. Running it on the Trichard `_ST` PDFs alone produces an Excel BOQ within 20% MAPE of the Trichard ground-truth BOQ.
3. Three repeat runs on the same input produce BOQs whose grand totals agree within ±5%.
4. `parse_json_safely()` does not exist anywhere in `agent/pdf_pipeline/`.
5. Mean cost per run is below R 8.00.
6. Mean wall-clock time is below 60 seconds for 10-page PDFs.

---

## 4. DXF Pipeline — Detailed Spec

### 4.1 Stages

`agent/dxf_pipeline/`

```
DXF File
   │
   ▼
┌──────────────────────────┐
│ STAGE D1: INGEST         │  ezdxf.readfile(), verify open,
│  ingest.py               │  detect units, hash file
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE D2: LAYER ANALYSIS │  Identify electrical layers,
│  layers.py               │  detect building blocks from layer
│                          │  names, build layer index
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE D3: EXTRACT        │  Pure Python deterministic extraction:
│  extract.py              │  • INSERT block references → fixtures
│                          │  • TEXT/MTEXT → labels, schedules
│                          │  • LINE/LWPOLYLINE → cable lengths
│                          │  • CIRCLE on Layer 0 → flagged unknowns
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ STAGE D4: EVALUATE       │  Deterministic-pipeline evaluation:
│  evaluate.py             │  • coverage check (% of blocks recognised)
│                          │  • baseline regression
│                          │  • SANS compliance (where applicable)
│                          │  • orphan-circle warning (Layer 0)
└────────────┬─────────────┘
             ▼
        passed?
       ┌──┴──┐
   yes │     │ no
       ▼     ▼
┌─────────┐ ┌──────────────────┐
│ D5: GEN │ │ D5b: REVIEW UI   │
│         │ │ (DXF-specific:   │
│         │ │ shows unrecog-   │
│         │ │ nised block      │
│         │ │ names so user    │
│         │ │ can extend the   │
│         │ │ pattern dict)    │
└─────────┘ └──────────────────┘
```

### 4.2 DXF pipeline data contract

```python
# agent/dxf_pipeline/models.py

class DxfPipelineRun(BaseModel):
    run_id: str
    timestamp: datetime
    input_file: str
    input_sha256: str
    drawing_units: str
    extraction: DxfExtraction
    evaluation: DxfEvaluation
    boq: BillOfQuantities | None = None
    cost_zar: float = 0.0                    # always 0
    duration_s: float                        # typically <2s

class DxfExtraction(BaseModel):
    """Deterministic extraction. No confidence scores by design —
    every value here is exact unless ezdxf raised an error."""
    layers: list[LayerInfo]
    blocks: list[DxfBlock]                   # one per INSERT
    texts: list[DxfText]
    polylines: list[DxfPolyline]             # for cable run lengths
    circles_layer_0: list[DxfCircle]         # potential mis-blocked lights
    block_counts_by_type: dict[str, int]
    raw_block_names_unrecognised: list[str]  # tells us what to add to ELECTRICAL_BLOCK_PATTERNS
    extraction_warnings: list[str]

class DxfEvaluation(BaseModel):
    """Methodology specific to deterministic pipelines."""
    # 1. Coverage — what fraction of blocks did we successfully classify?
    total_blocks: int
    recognised_blocks: int
    coverage_score: float                    # recognised / total

    # 2. Baseline regression
    baseline_project: str | None
    baseline_mape: float | None

    # 3. SANS compliance (limited — DXF rarely has electrical data
    #    needed for full SANS check)
    sans_violations: list[ComplianceFlag]
    sans_warnings: list[ComplianceFlag]

    # 4. Anomaly flags
    orphan_layer_0_circles: int              # warns of unblocked lights
    layers_named_electrical_with_no_blocks: list[str]
    suspiciously_long_polylines_m: list[float]  # e.g. >500m cable run

    passed: bool
    overall_score: float
    failure_reasons: list[str]
```

### 4.3 DXF pipeline evaluation methodology

DXF evaluation is fundamentally simpler because outputs are deterministic. The same DXF always produces exactly the same `DxfExtraction`. This permits a stricter test regime.

| Concern | Approach |
|---|---|
| **Block pattern coverage** | Track `coverage_score` over time; alert if it drops below 0.80 (most blocks unrecognised → patterns need extending) |
| **Layer naming variation** | Maintain `core/layer_aliases.py`; CI fails if a known layer alias is removed |
| **Geometric drift** | Polyline lengths must match annotated cable lengths within 5% on the baseline files |
| **Schema stability** | Pure equality assertions in tests — `assert extraction.block_counts_by_type == EXPECTED` |
| **Cost** | Always zero. CI fails if any LLM call appears in the DXF pipeline. |

### 4.4 DXF pipeline acceptance criteria

The DXF pipeline ships when:

1. Running it on a reference DXF produces a `DxfExtraction` whose `block_counts_by_type` matches a hand-counted baseline exactly.
2. `coverage_score >= 0.80` on both reference DXFs (≥80% of blocks recognised).
3. Polyline-derived cable lengths match annotated cable lengths in the source schedule within ±5%.
4. No file in `agent/dxf_pipeline/` imports `anthropic`, `openai`, or any LLM SDK.
5. End-to-end run on the largest reference DXF completes in under 5 seconds.

---

## 5. Cross-Comparison Layer (Research Grade, Optional)

`agent/comparison/`

This is **read-only**. It consumes the outputs of both pipelines and emits a comparison report. It can be disabled entirely without affecting either pipeline.

### 5.1 Why it's separate

A research-grade comparison should not influence either pipeline's gate decision. If it did, the two pipelines would no longer be independent — the PDF pipeline's pass/fail would depend on what the DXF pipeline did, and vice versa, which is exactly the coupling we're trying to avoid.

The comparison layer answers:
- **For this project, do the two BOQs agree?**
- **Across many projects, which pipeline is more accurate?**
- **What categories of items does each pipeline systematically miss?**

These are observations, not gates.

### 5.2 Data contract

```python
# agent/comparison/models.py

class PipelineComparison(BaseModel):
    project_name: str
    pdf_run_id: str
    dxf_run_id: str

    # Per-section agreement
    section_agreements: dict[str, SectionAgreement]   # A..L

    # Field-level diff
    field_disagreements: list[FieldDiscrepancy]
    agreement_score: float                  # 0..1

    # Cost / accuracy
    pdf_cost_zar: float
    dxf_cost_zar: float
    pdf_total_excl_vat: float
    dxf_total_excl_vat: float
    total_difference_pct: float

    # Vs ground truth (if baseline exists)
    pdf_vs_baseline_mape: float | None
    dxf_vs_baseline_mape: float | None
    winner_vs_baseline: Literal["pdf", "dxf", "tie", "no_baseline"] | None

class SectionAgreement(BaseModel):
    section: str
    pdf_subtotal: float
    dxf_subtotal: float
    delta_zar: float
    delta_pct: float
    items_only_in_pdf: list[str]
    items_only_in_dxf: list[str]
    items_in_both: int
```

### 5.3 What the comparison report looks like (UI)

Shown only when both pipelines have produced BOQs:

```
╔══════════════════════════════════════════════════════════════╗
║              CROSS-PIPELINE COMPARISON                       ║
╚══════════════════════════════════════════════════════════════╝

Project       Wedela Recreational Club
PDF Pipeline  R 7,612,400 (vs baseline: 2.4% under)
DXF Pipeline  R 7,891,200 (vs baseline: 1.2% over)
Difference    R   278,800 (3.7%)
Winner vs ground truth: DXF (lower MAPE)

Section-by-section
  A Distribution / Cables    PDF R 1,240k  DXF R 1,310k  Δ +5.6%
  B Trunking / Wiring        PDF R   612k  DXF R   598k  Δ -2.3%
  C General Outlets          PDF R   210k  DXF R   215k  Δ +2.4%
  D General Lighting         PDF R   480k  DXF R   492k  Δ +2.5%
  E Data                     PDF R   180k  DXF R     0   Δ -100%   ← only PDF caught this
  F Bulk Power               PDF R   720k  DXF R   720k  Δ  0.0%

Items only in PDF BOQ (16):
  • Network Cabinet 18U Wall Mount
  • Cat 6 Network Cable (1000m)
  • 48 Port Network Switch
  • Wifi Extenders (3)
  ...
  → DXF doesn't see these because the data layer wasn't in the
    drawing. Expected.

Items only in DXF BOQ (4):
  • Layer-0 circle near Pool Pump #2 (likely missed light)
  • Polyline 47m on layer ELECTRICAL_NEW (uncatalogued cable)
  ...
  → PDF didn't catch these because the schedule didn't list them.

Cost / accuracy summary
  PDF   R 4.20 cost   2.4% MAPE vs baseline   45 s runtime
  DXF   R 0.00 cost   1.2% MAPE vs baseline    1.4 s runtime
  → DXF outperforms on cost AND accuracy for this project,
    but misses the entire Data section (PDF advantage).
```

This view alone is the kind of evidence a thesis chapter is built on.

---

## 6. UI Redesign — Two Independent Result Columns

### 6.1 Layout

The page has **three vertical sections** in a single Streamlit page:

```
┌─────────────────────────────────────────────────────────────────┐
│                  AfriPlan Electrical v6.1                       │
│       Independent PDF and DXF Pipelines + Comparison            │
└─────────────────────────────────────────────────────────────────┘

┌─── 1. UPLOAD ───────────────────────────────────────────────────┐
│                                                                  │
│   📐 PDF (optional)                  📐 DXF (optional)           │
│   ┌─────────────────┐                ┌─────────────────┐         │
│   │ Drop or browse  │                │ Drop or browse  │         │
│   └─────────────────┘                └─────────────────┘         │
│                                                                  │
│   ▸ Project details (auto-detected from inputs)                  │
│   ▸ Site conditions   ▸ Contractor profile                       │
│                                                                  │
│              ┌─────────────────────────────┐                     │
│              │  ▶  Run pipelines           │                     │
│              └─────────────────────────────┘                     │
│   Note: each pipeline runs independently. Upload only what       │
│   you have — at least one of the two is required.                │
└──────────────────────────────────────────────────────────────────┘

┌─── 2. RESULTS — TWO COLUMNS ────────────────────────────────────┐
│                                                                  │
│   ┌──────────────────────────┐  ┌──────────────────────────┐    │
│   │     PDF PIPELINE         │  │     DXF PIPELINE         │    │
│   │     ───────────          │  │     ───────────          │    │
│   │  ⠋ Extracting page 7/24  │  │  ✓ Done (1.4s)           │    │
│   │                          │  │                          │    │
│   │  Score:    81%   ✓ PASS  │  │  Score:    93%   ✓ PASS  │    │
│   │   confidence  87%        │  │   coverage   91%         │    │
│   │   consistency 79%        │  │   regression 96%         │    │
│   │   regression  78%        │  │   anomalies  100%        │    │
│   │   SANS       100%        │  │                          │    │
│   │                          │  │                          │    │
│   │  Total ex VAT R 7,612k   │  │  Total ex VAT R 7,891k   │    │
│   │                          │  │                          │    │
│   │  📥 Excel  📥 PDF        │  │  📥 Excel  📥 PDF        │    │
│   │  📋 Eval JSON            │  │  📋 Eval JSON            │    │
│   └──────────────────────────┘  └──────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘

┌─── 3. COMPARISON (only if both pipelines ran) ──────────────────┐
│                                                                  │
│   Difference between PDF and DXF BOQs:  3.7%                     │
│   Winner vs Wedela ground truth:        DXF (1.2% MAPE)          │
│                                                                  │
│   [▼ Section-by-section breakdown]                               │
│   [▼ Items only in PDF / only in DXF]                            │
│                                                                  │
│   📥 Comparison Report (.pdf)   📋 Comparison JSON               │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Behavioural rules

- **Pipelines run in parallel** (`asyncio.gather`), not sequentially. The DXF column finishes well before the PDF column.
- **Each column updates live** — the user sees DXF complete in 2 seconds while PDF is still on page 7.
- **Each column's download buttons appear independently** as soon as that pipeline completes.
- **The comparison section is hidden** unless both pipelines completed successfully.
- **A pipeline's failure does not block the other pipeline.** If the PDF pipeline crashes, the DXF column still produces its BOQ and download buttons.

---

## 7. File Structure

```
afriplan-ai/
├── README.md
├── BLUEPRINT.md                            ← this document
├── app.py                                  ← entry: 20 lines, just navigation
├── requirements.txt
│
├── agent/
│   ├── __init__.py
│   ├── pdf_pipeline/                       ◄── COMPLETE INDEPENDENCE
│   │   ├── __init__.py
│   │   ├── pipeline.py                     ← orchestrator for PDF only
│   │   ├── models.py                       ← PdfPipelineRun, PdfExtraction, PdfEvaluation
│   │   ├── llm.py                          ← Anthropic client + tool_use + retry-w-feedback
│   │   ├── stages/
│   │   │   ├── ingest.py
│   │   │   ├── classify.py
│   │   │   ├── extract.py
│   │   │   ├── evaluate.py
│   │   │   └── generate.py
│   │   └── prompts/
│   │       ├── system_prompt.py
│   │       ├── classify_prompt.py
│   │       ├── sld_prompt.py
│   │       ├── lighting_layout_prompt.py
│   │       ├── plugs_layout_prompt.py
│   │       ├── schedule_prompt.py
│   │       ├── notes_prompt.py
│   │       └── tool_schemas.py             ← strict JSON schemas for tool_use
│   │
│   ├── dxf_pipeline/                       ◄── COMPLETE INDEPENDENCE
│   │   ├── __init__.py
│   │   ├── pipeline.py                     ← orchestrator for DXF only
│   │   ├── models.py                       ← DxfPipelineRun, DxfExtraction, DxfEvaluation
│   │   ├── patterns.py                     ← ELECTRICAL_BLOCK_PATTERNS dict
│   │   └── stages/
│   │       ├── ingest.py
│   │       ├── layers.py
│   │       ├── extract.py
│   │       ├── evaluate.py
│   │       └── generate.py
│   │
│   ├── comparison/                         ◄── READ-ONLY, OPTIONAL
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── compare.py                      ← reads PdfPipelineRun + DxfPipelineRun
│   │   └── report.py                       ← generates comparison PDF
│   │
│   └── shared/                             ← only truly shared types
│       ├── __init__.py
│       ├── boq.py                          ← BillOfQuantities, BQLineItem (used by both)
│       ├── project.py                      ← ProjectMetadata, ContractorProfile
│       └── compliance.py                   ← ComplianceFlag (used by both)
│
├── core/
│   ├── __init__.py
│   ├── config.py                           ← thresholds (per pipeline), model names
│   ├── constants.py                        ← unit prices (shared)
│   ├── standards.py                        ← SANS rules (shared)
│   └── layer_aliases.py                    ← DXF-only: layer-name normalisations
│
├── exports/
│   ├── __init__.py
│   ├── excel_bq.py                         ← takes a BillOfQuantities, emits .xlsx
│   ├── pdf_boq.py                          ← takes a BillOfQuantities, emits .pdf
│   └── comparison_pdf.py                   ← takes a PipelineComparison, emits .pdf
│
├── pages/
│   └── 1_Upload.py                         ← THE ONLY PAGE
│
├── ui/
│   ├── components.py
│   ├── pipeline_column.py                  ← renders one pipeline's status + downloads
│   ├── comparison_panel.py
│   └── styles.py
│
├── baselines/
│   ├── wedela.json
│   └── trichard.json
│
├── scripts/
│   ├── build_baselines.py
│   └── seed_block_patterns.py
│
├── runs/                                   ← gitignored
│   ├── pdf/
│   ├── dxf/
│   └── comparison/
│
└── tests/                                  ◄── COMPLETELY SEPARATE TEST SUITES
    ├── pdf_pipeline/
    │   ├── conftest.py                     ← MockAnthropic fixture
    │   ├── unit/
    │   │   ├── test_classify.py
    │   │   ├── test_extract.py             ← uses mocked LLM responses
    │   │   ├── test_evaluate.py
    │   │   └── test_models.py
    │   └── eval/
    │       ├── fixtures/                   ← only the PDF files
    │       │   ├── wedela/
    │       │   └── trichard/
    │       ├── expected/
    │       └── test_pdf_extraction.py      ← runs 3× per fixture for variance
    │
    ├── dxf_pipeline/
    │   ├── conftest.py                     ← no LLM fixtures
    │   ├── unit/
    │   │   ├── test_layers.py
    │   │   ├── test_extract.py             ← deterministic equality assertions
    │   │   ├── test_evaluate.py
    │   │   └── test_patterns.py
    │   └── eval/
    │       ├── fixtures/                   ← only the DXF files
    │       │   ├── wedela/
    │       │   └── trichard/
    │       ├── expected/
    │       └── test_dxf_extraction.py      ← single run, exact equality
    │
    ├── comparison/
    │   └── test_compare.py
    │
    └── shared/
        ├── test_boq_models.py
        └── test_compliance.py
```

### 7.1 Why this layout matters

`agent/pdf_pipeline/` has zero imports from `agent/dxf_pipeline/` and vice versa. CI can verify this with a one-line `grep`. If someone accidentally couples them, the test suite catches it.

`tests/pdf_pipeline/` and `tests/dxf_pipeline/` are runnable independently:

```bash
pytest tests/pdf_pipeline/      # only LLM-mock tests, no DXF dependency
pytest tests/dxf_pipeline/      # only deterministic tests, no Anthropic dependency
pytest tests/comparison/        # integration only
```

This is the structural enforcement of the independence rule.

---

## 8. Build Phases for Claude Code

The two pipelines can be built **in parallel by separate agents** if you want, because they don't share code paths. The order below assumes a single agent.

### Phase 0 — Repo cleanup (½ day)
Remove all v3/v4/v5 docs and `app_backup.py`. Keep `agent/models.py` and `core/` for now — they'll be split.

### Phase 1 — Shared models and config (1 day)
Create `agent/shared/`, `core/config.py`. Migrate `BillOfQuantities`, `BQLineItem`, `ProjectMetadata`, `ContractorProfile`, `ComplianceFlag` from existing `agent/models.py` into the new location. Delete the old `agent/models.py`.

### Phase 2 — Baseline builder (1 day)
Build `scripts/build_baselines.py` per §5.2 of the v6.0 blueprint (unchanged). Output `baselines/wedela.json`, `baselines/trichard.json`.

### Phase 3 — DXF pipeline end-to-end (3 days)
Build `agent/dxf_pipeline/` complete — all stages, models, tests. Acceptance: `pytest tests/dxf_pipeline/` passes; running on Wedela DXF produces a BOQ in <5 seconds with exact block count match.

> **Build DXF pipeline first.** It's deterministic, faster to test, and gives you a working end-to-end product on day 3 even before any LLM work begins. This is also good for morale on a long rebuild.

### Phase 4 — PDF pipeline end-to-end (5 days)
Build `agent/pdf_pipeline/` complete. Use `tool_use` with strict schemas. Implement retry-with-error-feedback. Mock-tested in unit, real-API-tested in eval. Acceptance: `pytest tests/pdf_pipeline/` passes; running on Wedela PDFs produces a BOQ within 20% MAPE.

### Phase 5 — UI with two-column layout (2 days)
`pages/1_Upload.py` per §6. Async parallel execution. Each column updates independently.

### Phase 6 — Comparison layer (1 day)
`agent/comparison/` reads both runs, emits report. UI section appears only when both available.

### Phase 7 — Observability and CI (1 day)
Persist `RunLog` per pipeline to `runs/{pipeline}/{run_id}.json`. GitHub Actions: separate jobs for PDF tests, DXF tests, comparison tests. PDF job uses recorded LLM responses (vcr-style) so it doesn't burn API budget on every PR.

### Phase 8 — Polishing and docs (1 day)
README. Per-pipeline README inside `agent/pdf_pipeline/` and `agent/dxf_pipeline/` (the kind of READMEs that survive the next 3 years).

**Total: ~14 working days.** Same as v6.0 but split across two clean tracks.

---

## 9. Acceptance criteria — overall product

The rebuild is complete when **all** of the following hold:

### Architectural enforcement
1. `grep -r "from agent.pdf_pipeline" agent/dxf_pipeline/` returns nothing.
2. `grep -r "from agent.dxf_pipeline" agent/pdf_pipeline/` returns nothing.
3. `grep -r "anthropic\|openai" agent/dxf_pipeline/` returns nothing.

### Functional behaviour
4. Uploading only a PDF runs the PDF pipeline and produces a PDF BOQ in `<60 seconds`. The DXF column shows "no input."
5. Uploading only a DXF runs the DXF pipeline and produces a DXF BOQ in `<5 seconds`. The PDF column shows "no input."
6. Uploading both runs both in parallel; comparison panel appears.
7. A failure in the PDF pipeline (e.g. API timeout) does not affect the DXF column.

### Quality
8. PDF pipeline MAPE ≤ 20% vs Wedela and Trichard baselines.
9. DXF pipeline `coverage_score >= 0.80` on both reference files.
10. Three repeat PDF runs on Wedela inputs produce grand totals within ±5%.

### CI
11. `pytest tests/pdf_pipeline/` passes (with LLM responses replayed from cassettes).
12. `pytest tests/dxf_pipeline/` passes (no network access at all).
13. Both test jobs run in parallel in GitHub Actions; total CI time ≤ 4 minutes.

---

## 10. Open questions for Hervé (revised)

Same as v6.0 §9, plus:

7. **Run isolation.** When both pipelines run on a single submission, do they share a `submission_id` for joining in analytics, or do they each have fully independent `run_id`s? Recommend: independent `run_id`s, optional `submission_id` link in metadata only.
8. **Default-on policy for comparison.** When both inputs are uploaded, should the comparison panel appear automatically or behind a "Compare" button? Recommend: automatic — the user uploaded both for a reason.
9. **Handling DXF without PDF for tender.** A DXF-only BOQ will lack the Data section, project metadata, and SLD-derived DB schedules. The output PDF should clearly state these limitations on its cover page. Confirm that's acceptable.

---

## 11. Out of scope (unchanged from v6.0)

Same list. Specifically: no FastAPI/Next.js migration, no auth, no marketplace, no DWG support — DXF only.

---

## Appendix A — How this enables your Master's research

The dual-pipeline design isn't only a product decision; it's a research instrument. With it, every project run by any user becomes a data point in a comparative study you can publish.

```
For each project P:
   Run PDF pipeline   → BOQ_pdf, cost_pdf, time_pdf, mape_pdf
   Run DXF pipeline   → BOQ_dxf, cost_dxf, time_dxf, mape_dxf
   Compare            → agreement(P), category-wise win-loss

Aggregate over N projects:
   - Mean MAPE per pipeline per BOQ section
   - Cost-per-correct-line-item per pipeline
   - Categories where one pipeline systematically beats the other
   - Failure modes of each (false positives, hallucinations, missed items)
```

After 30 production runs you have the dataset for a paper titled something like:

> *"Vision Language Models versus Deterministic CAD Parsing for Bill-of-Quantities Generation in Electrical Engineering: A Comparative Field Study."*

The architecture below puts you one good dataset away from publishing. That's the point.

---

*End of revised blueprint. v6.1 — last updated 29 April 2026.*
