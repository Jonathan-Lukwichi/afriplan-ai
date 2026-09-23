# AfriPlan — Professional Restructure + BOQ Evaluation Framework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn AfriPlan into a reproducible, transferable Claude-Code project and give it a real evaluation metric, drawing-sufficiency model and BOQ audit engine, grounded in the Wedela reference project.

**Architecture:** Keep the two independent pipelines untouched. Add two top-level read-only packages — `evaluation/` (ground-truth parsing, item taxonomy, layered BOQ network, fitted ratios, frozen scorer) and `audit/` (BOQ rule audit, drawing sufficiency, BOQ completer) — that consume `agent.shared.BillOfQuantities` and never get imported by a pipeline. Project context follows the Agent Workflow Kit: lean `CLAUDE.md` router, `context.md` glossary, ADRs, project skills, review prompt, AutoResearch program with a frozen scorer.

**Tech Stack:** Python 3.14 (CI 3.11), pydantic v2, openpyxl, ezdxf + LibreDWG, numpy, opencv-python-headless, pytest, Streamlit.

**Spec:** `docs/specs/2026-09-23-restructure-and-evaluation-design.md`

## Global Constraints

- Pipelines do not share state and do not call each other; `agent/pdf_pipeline` ↔ `agent/dxf_pipeline` never import each other; neither imports `agent.comparison`, `evaluation`, `audit`, `sourcing`, `scoring`.
- No LLM SDK import in `agent/dxf_pipeline/`, `evaluation/`, `audit/`.
- `evaluation/metrics.py` is the frozen scorer — no optimisation loop may edit it.
- Model IDs hard-coded only in `core/config.py`.
- Tests never hit the network; tests depending on the Wedela raw files `pytest.skip` when `data/projects/wedela/raw/` is absent.
- Client data (`data/**/raw/`) is gitignored; only manifests and derived JSON are committed.
- Every estimated quantity is visible: tagged `INFERRED`/`ASSUMED`/`PROVISIONAL` and carries an `assumption` string.
- Commit after every task, message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Full suite (`python -m pytest -q`) must stay green after every task (baseline: 259 passed).

---

## File structure (created / moved)

```
CLAUDE.md                          rewritten: lean router (PUSH context)
context.md                         NEW glossary (ubiquitous language)
README.md                          rewritten: quickstart + reproduce-the-baseline
pyproject.toml                     NEW pytest + project metadata
requirements.txt / requirements-dev.txt
.claude/settings.json              NEW hook: architecture tests after edits in agent/
.claude/skills/{evaluate-boq,add-reference-project,audit-boq,tdd,karpathy-coding-discipline}/SKILL.md
prompts/review.md                  fresh-context reviewer prompt
autoresearch/program.md            goal/metric/rules; scorer = evaluation/metrics.py
docs/adr/0001..0006-*.md           decision records
docs/architecture.md               the system in one page
docs/blueprints/                   moved: AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md, PROMPT-ENGINEERING-BLUEPRINT*.md
docs/specs/, docs/superpowers/plans/
issues/NNN-*.md                    backlog of known defects with evidence
data/projects/wedela/manifest.json committed; raw/ gitignored
data/projects/wedela/reference_boq.json   derived ground truth (committed)
data/projects/wedela/ratio_model.json     fitted ratios (committed)
evaluation/{__init__,taxonomy,reference,network,ratios,metrics,report}.py
audit/{__init__,lines,boq_rules,sufficiency,completer}.py
ml/symbol_dataset.py               DWG → labelled symbol-image dataset generator
scripts/{verify_data,build_reference,evaluate,audit_boq,run_baseline,build_symbol_dataset}.py
reports/baselines/                 committed baseline score reports
tests/evaluation_layer/, tests/audit_layer/, tests/ml_layer/
```

---

### Task 0: Safety checkpoint

**Files:** none created.

- [ ] **Step 1:** Run `python -m pytest -q` → expect `259 passed`.
- [ ] **Step 2:** `git add -A` (gitignore already excludes runs/, client folders) then `git status --short` and confirm no file > 5 MB and no secrets are staged.
- [ ] **Step 3:** Commit `chore: checkpoint v2 estimators, LDSE, sourcing, scoring before restructure`.

---

### Task 1: Reproducible reference dataset

**Files:**
- Create: `data/projects/wedela/manifest.json`, `data/README.md`, `scripts/verify_data.py`, `evaluation/__init__.py`, `evaluation/dataset.py`
- Modify: `.gitignore` (add `data/**/raw/`)
- Test: `tests/evaluation_layer/__init__.py`, `tests/evaluation_layer/test_dataset.py`

**Interfaces — Produces:**
```python
# evaluation/dataset.py
class DatasetFile(BaseModel):
    path: str            # relative to the project dir, e.g. "raw/Wedela Electrical/WD-AB-01-SLD 050425.dwg"
    sha256: str
    role: str            # "reference_boq" | "sld" | "lighting_layout" | "plug_layout" | "architectural" | "pdf_sld" | "pdf_layouts"
    building: str = ""   # canonical building name as in the BOQ summary ("" = whole project)
class ProjectManifest(BaseModel):
    project: str; description: str; buildings: List[str]
    building_codes: Dict[str, str]   # "AB" -> "Ablution Retail Block"
    files: List[DatasetFile]
def project_dir(project: str) -> Path                  # data/projects/<project>
def load_manifest(project: str) -> ProjectManifest
def verify_manifest(manifest, root: Path) -> List[str]  # list of problems; [] = OK
def sha256_file(path: Path) -> str
```

- [ ] **Step 1: Write failing tests** — `test_dataset.py`: (a) `verify_manifest` returns `[]` for a tmp dir whose file matches its sha; (b) returns a "checksum mismatch" problem when content changes; (c) returns "missing" when file absent; (d) `load_manifest("wedela")` parses and lists 7 buildings.
- [ ] **Step 2:** Run `python -m pytest tests/evaluation_layer/test_dataset.py -q` → FAIL (module missing).
- [ ] **Step 3:** Copy `Downloads/wetransfer_4-autocad-drawings-client_2026-08-25_1003/*` into `data/projects/wedela/raw/` (exclude `.bak/.dwl/.dwl2/plot.log`). Implement `evaluation/dataset.py`. Generate `manifest.json` with a one-off `scripts/verify_data.py --write wedela` mode that hashes files and assigns role/building from the file-name convention `WD-<CODE>-01-<ROLE>`: AB=Ablution Retail Block, ECH=Existing Community Hall, LGH=Large Guard House, SGH=Small Guard House, PB=Swimming Pool, KIOSK=Main Kiosk, OL=Swimming Pool (outdoor lighting SLD — site/pool lighting is billed on the Swimming Pool sheet).
- [ ] **Step 4:** Tests pass; `python scripts/verify_data.py wedela` prints `OK — 28 files verified`.
- [ ] **Step 5:** Commit `feat(data): reproducible Wedela reference dataset with checksummed manifest`.

---

### Task 2: Tooling, dependencies, CI

**Files:** Create `pyproject.toml`, `requirements-dev.txt`; Modify `requirements.txt`, `.github/workflows/ci.yml`.

- [ ] **Step 1:** `pyproject.toml` with `[project] name="afriplan-electrical" version="6.2.0" requires-python=">=3.11"` and `[tool.pytest.ini_options] testpaths=["tests"] addopts="-q" filterwarnings=["ignore::DeprecationWarning:agent.*"]`.
- [ ] **Step 2:** `requirements.txt` += `opencv-python-headless>=4.8` (already used by `agent/dxf_pipeline/passes/template_count.py`). `requirements-dev.txt` = `-r requirements.txt` + `pytest>=8`.
- [ ] **Step 3:** CI: DXF job installs `-r requirements.txt` (it currently misses numpy/opencv needed by DXF tests); add an `evaluation-audit` job running `pytest tests/evaluation_layer tests/audit_layer tests/ml_layer tests/shared tests/eval tests/sourcing_layer`.
- [ ] **Step 4:** `python -m pytest` → 259+ passed (the new dataset tests included).
- [ ] **Step 5:** Commit `build: pyproject, dev requirements, CI installs full deps + evaluation job`.

---

### Task 3: Item taxonomy (ItemKey)

**Files:** Create `evaluation/taxonomy.py`; Test `tests/evaluation_layer/test_taxonomy.py`.

**Interfaces — Produces:**
```python
class ItemKey(NamedTuple):
    family: str      # e.g. "swa_cable", "bcew", "termination", "trench", "warning_tape", "sleeve",
                     # "manhole", "db", "cable_tray", "wire_basket", "trunking", "trunking_cover",
                     # "trunking_bend", "trunking_tee", "round_box", "plug_top", "gp_wire", "surfix",
                     # "socket_double", "socket_single", "isolator", "wall_box", "extension_box",
                     # "waterproof_box", "chasing", "conduit", "draw_wire", "light_panel", "light_flood",
                     # "light_vapour_proof", "light_bulkhead", "light_downlight", "light_pole",
                     # "light_solar_post", "switch", "day_night_switch", "kiosk", "plinth", "breaker",
                     # "connection_fee", "coc", "prelims", "other"
    spec: str        # size/variant, e.g. "95mm2|4c", "600x1200", "1lever|1way", "20mm", "4m"; "" if none
def classify_item(description: str, *, parent: str = "") -> ItemKey
def line_role(description: str) -> str      # "supply" | "install" | "combined"
BILL_SECTION_FAMILIES: Dict[str, str]       # family -> Wedela section letter "A"|"B"|"C"|"D"|"F"|"P"
```

Ordered regex rules, first match wins; `parent` is the header row above a Supply/Install child (e.g. parent `"95mm2 x 4C PVC SWA PVC 600-1000V Cable"`, description `"Supply"`).

- [ ] **Step 1: Failing tests** with real Wedela strings (≥ 20 cases): `classify_item("Supply", parent="95mm2 x 4C PVC SWA PVC 600-1000V Cable") == ItemKey("swa_cable","95mm2|4c")`; `"35mm2 BCEW "` → `("bcew","35mm2")`; `"Trenching and re-instatement for 450mm x 650mm..."` → `("trench","")`; `"110 mm diameter flexible PVC cable sleeves."` → `("sleeve","110mm")`; `"P8000 Trunking Covers"` → `("trunking_cover","p8000")`; `"P8000 Trunking Horizontal Bend"` → `("trunking_bend","p8000")`; `"1.5mm2 GP wire Black"` → `("gp_wire","1.5mm2")`; `"1.5 mm2 BCEW "` → `("bcew","1.5mm2")`; `"WHITE, 100X100, 16 Ampere, ... double switched socket outlet"` → `("socket_double","16a")`; `"WHITE, 100X50 ,30 Ampere, double pole isolator..."` → `("isolator","30a")`; `"100x100 Wall box"` → `("wall_box","100x100")`; `"100 x 50 mm Wall box"` → `("wall_box","100x50")`; `"Chasing for 4 m (height) for 20 mm conduit"` → `("chasing","4m|20mm")`; `"20mm diameter PVC conduits with accessories"` and `"20 mm dia PVC conduit"` → `("conduit","20mm")`; `"600x1200 Recessed 3x18watt Led..."` → `("light_panel","600x1200")`; `"30watt led flood light"` → `("light_flood","30w")`; `"2x24watt double vapor proof..."` → `("light_vapour_proof","2x24w")`; `"1 Lever light switch 1 way"` → `("switch","1lever|1way")`; `"Day Night switch"` → `("day_night_switch","")`; `"Main DB 1: 3 phase+N+E..."` → `("db","")`. Also our pipeline strings: `"Supply 95mm² x4C SWA feeder MSB→DB1"` → `("swa_cable","95mm2|4c")`, `"Terminate 50mm² SWA (both ends)"` → `("termination","50mm2")`, `"16A double switched socket — Office"` → `("socket_double","16a")`, `"1-lever 1-way switch"` → `("switch","1lever|1way")`. `line_role("Supply")=="supply"`, `line_role("Install 95mm²...")=="install"`, `line_role("Chasing...")=="combined"`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement (normalise `²`→`2`, collapse spaces, lowercase; size regex `(\d+(?:\.\d+)?)\s*mm\s*2`).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat(evaluation): ItemKey taxonomy normalising reference and pipeline descriptions`.

---

### Task 4: Reference BOQ parser (ground truth)

**Files:** Create `evaluation/reference.py`, `scripts/build_reference.py`, `data/projects/wedela/reference_boq.json`; Test `tests/evaluation_layer/test_reference.py`.

**Interfaces — Produces:**
```python
class RefLine(BaseModel):
    sheet: str; building: str; bill_section: str   # "A".."D","F","P"
    code: str; description: str; parent: str = ""
    unit: str; qty: float; rate: Optional[float]; total: Optional[float]
    key_family: str; key_spec: str; role: str      # from taxonomy
    raw_row: int
    @property value -> float                       # total if not None else qty*(rate or 0)
class RefBuilding(BaseModel):
    name: str; sheet: str; lines: List[RefLine]
    section_totals: Dict[str, float]; contingency: float; total_excl_vat: float
    in_summary: bool; errors: List[str]            # e.g. "#REF! in A-TOTAL"
class ReferenceBoq(BaseModel):
    project: str; buildings: List[RefBuilding]
    summary_total_excl_vat: float; vat: float; total_incl_vat: float
    prelims: List[RefLine]                         # P&Gs
    def building(self, name) -> Optional[RefBuilding]
    def all_lines(self) -> List[RefLine]
def parse_reference_xlsx(path: Path, *, project: str) -> ReferenceBoq
```

Parsing rules: a sheet is a **building bill** if it contains a header row `('ITEM NO','DESCRIPTION','UOM','QTY','RATE','SUB TOTAL')`; section letter = the most recent row whose col-A is a single letter with a title in col-B; a row whose col-D (qty) is empty but col-B is a spec title becomes the `parent` of following `Supply`/`Install` rows; rows with qty `None` or `0` are dropped (recorded count in `errors` only if they have a total); `#REF!` values → recorded in `errors`; `in_summary` from matching the sheet name to Summary-sheet descriptions (case/space-insensitive); Main Kiosk & minisub parsed with bill section `F`; P&Gs into `prelims`; Installation Rate / Cable Termination material / Provisional Sum ignored (rate sources, not bill lines).

- [ ] **Step 1: Failing tests:** (a) synthetic workbook built in-test with openpyxl (one building sheet with A/B sections, a Supply/Install pair under a parent, a zero-qty row, a `#REF!` total, plus Summary) → assert parent inheritance, role, dropped zero row, error captured, `in_summary`; (b) real file (skip if absent): 7 buildings in summary + `Pool-Heat Pumps` with `in_summary=False`; `summary_total_excl_vat` equals the Summary sheet total; Existing Community Hall has a line with `key_family=="swa_cable"`, `key_spec=="50mm2|4c"`, `role=="supply"`, `qty==50`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement + `scripts/build_reference.py wedela` writes `reference_boq.json`. **Step 4:** PASS. **Step 5:** Commit `feat(evaluation): parse reference BOQ workbook into typed ground truth`.

---

### Task 5: The layered BOQ network (drawing → evidence → item)

**Files:** Create `evaluation/network.py`; Test `tests/evaluation_layer/test_network.py`.

**Interfaces — Produces:**
```python
class DrawingType(str, Enum):
    SLD="sld"; LIGHTING="lighting_layout"; PLUGS="plug_layout"; SITE="site_plan"
    SCHEDULE="schedule"; LEGEND="legend"; REGISTER="register"; ARCHITECTURAL="architectural"
class Method(str, Enum):
    COUNT="count"; LENGTH="length"; DERIVED="derived"; PROVISIONAL="provisional"; PRELIMS="prelims"
class ItemNode(BaseModel):
    family: str; method: Method
    requires: List[List[DrawingType]]   # OR of AND-groups: [[SLD],[SCHEDULE]] = SLD or schedule
    derived_from: List[str] = []        # primary families feeding a DERIVED item
    note: str = ""
NETWORK: Dict[str, ItemNode]            # one node per taxonomy family
def reproducible(family: str, uploaded: Set[DrawingType]) -> bool
def reproducible_families(uploaded: Set[DrawingType]) -> Set[str]
def requirements_matrix() -> Dict[str, List[str]]   # family -> human readable requirement
def missing_for(families: Iterable[str], uploaded) -> Dict[DrawingType, List[str]]  # drawing -> families it would unlock
```

Key edges: `db`,`breaker` ← SLD|SCHEDULE (count); `swa_cable`,`bcew` ← SLD (length; site plan improves) ; `termination` DERIVED from `swa_cable`,`bcew` (2 per run); `trench`,`warning_tape`,`sleeve`,`manhole` ← SITE (length) else DERIVED from feeder length; `light_*`,`switch`,`day_night_switch` ← LIGHTING (count); `socket_*`,`isolator` ← PLUGS (count); `wall_box`,`chasing`,`conduit`,`round_box`,`draw_wire`,`gp_wire`,`trunking*`,`cable_tray`,`wire_basket`,`extension_box`,`waterproof_box` DERIVED from outlet/light/switch counts (need the layout that holds the primary); `kiosk`,`plinth`,`connection_fee`,`coc` ← SLD (KIOSK SLD) ; `prelims` PRELIMS (never from drawings).

- [ ] **Step 1: Failing tests:** every taxonomy family (from Task 3) has a node; `reproducible("socket_double",{PLUGS})` True, `{LIGHTING}` False; `reproducible("wall_box",{PLUGS})` True (derived from sockets); `reproducible("prelims", all)` False; `missing_for(["socket_double","db"], {LIGHTING})` → `{PLUGS:["socket_double"], SLD:["db"]}` (SCHEDULE alternative listed as SLD first).
- [ ] **Steps 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(evaluation): layered BOQ network mapping drawings to evidence to items`.

---

### Task 6: Fitted ratios ("weights") with leave-one-building-out validation

**Files:** Create `evaluation/ratios.py`, `data/projects/wedela/ratio_model.json`; Test `tests/evaluation_layer/test_ratios.py`.

**Interfaces — Produces:**
```python
class Ratio(BaseModel):
    target: str               # "wall_box|100x100"   (family|spec of the derived item)
    inputs: List[str]         # ["socket_double|*","socket_single|*","isolator|*"]  (* = any spec)
    weight: float             # least squares through origin: qty_target ≈ weight * Σ inputs
    n: int                    # buildings used
    loo_mape: Optional[float] # leave-one-building-out mean abs % error (None if n<3)
    unit: str
class RatioModel(BaseModel):
    project_sources: List[str]; ratios: List[Ratio]
    def predict(self, primary_counts: Dict[str, float]) -> Dict[str, float]
DEFAULT_RATIO_SPECS: List[Tuple[str, List[str]]]
def building_quantities(b: RefBuilding) -> Dict[str, float]  # "family|spec" -> summed qty (supply+combined only)
def fit_ratios(ref: ReferenceBoq, specs=DEFAULT_RATIO_SPECS) -> RatioModel
```

`DEFAULT_RATIO_SPECS` (target ← inputs): wall_box|100x100 ← sockets+isolators; wall_box|100x50 ← switches+day_night; chasing|* ← sockets+isolators+switches; conduit|20mm ← all lights+sockets+switches; gp_wire|1.5mm2 ← lights; gp_wire|2.5mm2 ← sockets; bcew|1.5mm2 ← lights; round_box|* ← lights; draw_wire|* ← sockets; termination|* ← feeder runs (2 each); trench|* , warning_tape|* ← feeder metres.

- [ ] **Step 1: Failing tests:** synthetic ReferenceBoq with 4 buildings where target = exactly 2×input → `weight==2.0`, `loo_mape==0`; building lacking the input is excluded from n; `predict({"socket_double|16a":5,"isolator|30a":1})["wall_box|100x100"] == 12.0` for weight 2; real Wedela (skip if absent): wall_box|100x100 weight within 0.8–1.2.
- [ ] **Steps 2–4.** Script `scripts/build_reference.py wedela` also writes `ratio_model.json`. **Step 5:** Commit `feat(evaluation): fit derived-quantity ratios with leave-one-building-out error`.

---

### Task 7: The frozen scorer

**Files:** Create `evaluation/metrics.py`; Test `tests/evaluation_layer/test_metrics.py`.

**Interfaces — Produces:**
```python
class PredLine(BaseModel):          # adapter so any BOQ can be scored
    building: str; family: str; spec: str; role: str; qty: float; rate: float; total: float; description: str
def pred_lines_from_boq(boq: BillOfQuantities, *, building: str) -> List[PredLine]
class ItemScore(BaseModel):
    building: str; key: str; role: str
    ref_qty: float; pred_qty: float; ref_rate: float; pred_rate: float; ref_value: float; pred_value: float
    matched: bool; qty_acc: float; rate_acc: float; in_scope: bool
class Scorecard(BaseModel):
    project: str; pipeline: str; uploaded: List[str]
    items: List[ItemScore]
    coverage: float; precision: float; qty_accuracy: float; rate_accuracy: float
    total_accuracy: float; reproduction_score: float
    scoped: Dict[str, float]                  # same metrics restricted to in_scope items
    per_building: Dict[str, Dict[str, float]]
    unmatched_reference: List[str]            # "Swimming Pool | chasing|4m|20mm | combined | R …"
    unmatched_predicted: List[str]
def score(pred: List[PredLine], ref: ReferenceBoq, *, uploaded: Set[DrawingType], pipeline: str = "") -> Scorecard
```

Matching key `(building, family|spec, role)`; quantities of duplicates summed on both sides; building-level `pred` lines with building `""` are matched at project level (key without building) and scored against the summed reference. Accuracy `max(0,1-|p-a|/a)`; value weights = reference value.

- [ ] **Step 1: Failing tests:** perfect prediction (reference → PredLine) → all metrics 1.0; drop one line of value 10 % → coverage 0.9, RS 0.9; qty 50 % high on a line of value 100 % → qty_acc 0.5; extra predicted line not in reference → precision < 1, coverage unchanged; scoped metrics with `uploaded={PLUGS}` include only socket/isolator/derived-from-plugs items; header says `FROZEN SCORER — do not edit inside an optimisation loop`.
- [ ] **Steps 2–4. Step 5:** Commit `feat(evaluation): frozen reproduction scorer (coverage, precision, qty/rate/total accuracy, RS)`.

---

### Task 8: Report + evaluate CLI

**Files:** Create `evaluation/report.py`, `scripts/evaluate.py`; Test `tests/evaluation_layer/test_report.py`.

**Interfaces:** `render_markdown(card: Scorecard, *, top_n: int = 25) -> str`; CLI `python scripts/evaluate.py --project wedela (--run runs/<p>/<id>.json | --boq file.json | --self-test) [--building NAME] [--uploaded sld,lighting_layout,plug_layout] [--out reports/x.md]`. `--self-test` scores the reference against itself and must print `RS 100.0%`.

- [ ] Steps: failing test (markdown contains headline table + "Not produced by the pipeline" section) → implement → PASS → `python scripts/evaluate.py --project wedela --self-test` prints RS 100.0% → Commit `feat(evaluation): markdown report and evaluate CLI with self-test`.

---

### Task 9: BOQ audit rules

**Files:** Create `audit/__init__.py`, `audit/lines.py`, `audit/boq_rules.py`, `scripts/audit_boq.py`; Test `tests/audit_layer/__init__.py`, `tests/audit_layer/test_boq_rules.py`.

**Interfaces — Produces:**
```python
class AuditFinding(BaseModel):
    rule: str; severity: Literal["critical","high","medium","low"]
    building: str; location: str; message: str; value_at_risk_zar: float = 0.0; suggested_action: str
def audit_reference(ref: ReferenceBoq) -> List[AuditFinding]
def audit_boq(boq: BillOfQuantities, *, building: str = "") -> List[AuditFinding]
```
Rules: `ARITH` qty×rate vs total (>1 % and >R1); `NO_RATE` qty>0, rate None/0; `DUPLICATE` same description+qty+rate in one building; `COMPANION` swa_cable supply without matching install / bcew / 2 terminations / trench when trench exists elsewhere in bill; `ROLLUP` Σ lines of a section vs stated section total; `CONTINGENCY` stated contingency ≠ 5 % of Σ sections; `NOT_IN_SUMMARY` building sheet excluded from project summary; `ERROR_CELL` `#REF!` etc.

- [ ] Steps: failing tests on synthetic ReferenceBoq for each rule (one positive + one negative case each) and a real-file test (skip if absent) asserting at least `NOT_IN_SUMMARY` for Pool-Heat Pumps, `DUPLICATE` for Swimming Pool DB CR, `NO_RATE` for guard-house lights → implement → PASS → `python scripts/audit_boq.py --project wedela --out reports/audits/wedela-reference-audit.md` → Commit `feat(audit): BOQ rule audit (arithmetic, missing rates, duplicates, companions, roll-ups)`.

---

### Task 10: Drawing-sufficiency audit (complete vs partial BOQ)

**Files:** Create `audit/sufficiency.py`; Test `tests/audit_layer/test_sufficiency.py`.

**Interfaces:**
```python
class SufficiencyReport(BaseModel):
    building: str; uploaded: List[str]
    reproducible_families: List[str]; not_reproducible: List[str]
    coverage_possible_zar: float; coverage_possible_pct: float   # vs reference value, when a reference exists
    requests: Dict[str, List[str]]    # drawing type -> families it would unlock
def sufficiency(uploaded: Set[DrawingType], *, building: str = "", ref: Optional[ReferenceBoq] = None) -> SufficiencyReport
def uploaded_from_manifest(manifest: ProjectManifest, building: str) -> Set[DrawingType]
```
- [ ] Steps: failing tests (only LIGHTING → requests include PLUGS & SLD; with a synthetic ref, coverage_possible_pct equals value share of lighting families) → implement → PASS → `scripts/audit_boq.py --sufficiency` prints the per-building table for Wedela → Commit `feat(audit): drawing sufficiency report for complete vs partial BOQ`.

---

### Task 11: BOQ completer (fill what pipelines never calculate)

**Files:** Create `audit/completer.py`; Test `tests/audit_layer/test_completer.py`.

**Interfaces:**
```python
def complete_boq(boq: BillOfQuantities, model: RatioModel, *, building: str = "") -> BillOfQuantities
```
Returns a **clone**; reads primary counts via `pred_lines_from_boq`; for every ratio target whose family is absent from the bill adds a `BQLineItem(source=INFERRED, assumption=f"Fitted ratio {w:.2f} × {inputs} (LOO error {mape:.0%}, n={n}) — verify", section=<mapped>)` priced from the ratio model's median reference rate; adds one `GapItem(severity="low")` per inferred line; re-totals with contingency/VAT exactly like `agent/pdf_pipeline/passes/assemble.py::_finalise_totals`.
- [ ] Steps: failing tests (original not mutated; wall_box line added with qty = weight × sockets; existing family not duplicated; totals recomputed) → implement → PASS → Commit `feat(audit): ratio-driven BOQ completer for derived items`.

---

### Task 12: Architecture test extension

**Files:** Modify `tests/architecture/test_independence.py`.
- [ ] Add: no module under `agent/` imports `evaluation`, `audit`, `scoring`, `sourcing`, `ml`; no module under `evaluation/`/`audit/` imports `anthropic`. Run → PASS. Commit `test(architecture): pipelines may not import evaluation/audit/ml`.

---

### Task 13: Baseline runs on Wedela (DXF free, PDF paid)

**Files:** Create `scripts/run_baseline.py`, `reports/baselines/2026-09-23-wedela-dxf.md`, `reports/baselines/2026-09-23-wedela-pdf.md`, `reports/baselines/README.md`.

`run_baseline.py --project wedela --pipeline dxf|pdf [--complete]`: for each building, run the pipeline on that building's files from the manifest (DXF: each LIGHTING/PLUG/SLD dwg → `run_dxf_estimator`, lines tagged with the building; PDF: whole set → `run_pdf_estimator` once, building assignment via `building_block`), persist runs, score with `uploaded` from the manifest, optionally score again after `complete_boq`, write the report.
- [ ] Step 1: DXF baseline → report committed. Step 2: DXF + completer → delta recorded in the same report. Step 3: PDF baseline (API key from env/secrets; if missing, stop and tell the user) → report. Step 4: `reports/baselines/README.md` table of the headline numbers. Commit `docs(reports): first honest Wedela baselines for DXF and PDF pipelines`.

---

### Task 14: CNN symbol-dataset generator (future-proofing the model)

**Files:** Create `ml/__init__.py`, `ml/symbol_dataset.py`, `scripts/build_symbol_dataset.py`, `ml/DATASET_CARD.md`; Test `tests/ml_layer/__init__.py`, `tests/ml_layer/test_symbol_dataset.py`.

**Interfaces:**
```python
class SymbolLabel(BaseModel): cls: str; x0: int; y0: int; x1: int; y1: int; source: str  # "block"|"template"
class SheetSample(BaseModel): image_path: str; width: int; height: int; labels: List[SymbolLabel]; source_dwg: str
def render_sheet(doc, *, px_per_unit: float, out_png: Path) -> Tuple[int,int,Callable]   # returns size + world->pixel fn
def labels_from_doc(doc, legend, to_px) -> List[SymbolLabel]  # INSERT blocks classified by patterns/legend, + template-count hits
def build_dataset(manifest, out_dir: Path) -> List[SheetSample]   # writes images/ + labels/*.txt (YOLO) + samples.jsonl
```
- [ ] Steps: failing test on a synthetic ezdxf doc with 3 socket blocks → 3 labels with pixel boxes inside the image and YOLO lines normalised to [0,1] → implement → PASS → run on Wedela (output to `data/ml/symbols/`, gitignored), write `DATASET_CARD.md` with real counts per class and the honest limitation (exploded Revit line-work yields few block labels) → Commit `feat(ml): DWG to labelled symbol-image dataset generator + dataset card`.

---

### Task 15: Professional project context (the Claude project layer)

**Files:** Rewrite `CLAUDE.md`, `README.md`; Create `context.md`, `docs/architecture.md`, `docs/adr/0001-pipeline-independence.md`, `0002-llm-eyes-python-brain.md`, `0003-evaluation-frozen-scorer.md`, `0004-layered-boq-network-not-nn.md`, `0005-reference-data-management.md`, `0006-top-level-read-only-layers.md`, `docs/adr/ADR-TEMPLATE.md`; move blueprints to `docs/blueprints/`; `issues/001..NNN-*.md`; `.claude/skills/*/SKILL.md`; `.claude/settings.json`; `prompts/review.md`; `autoresearch/program.md`.

- [ ] `CLAUDE.md` ≤ 150 lines: what it is, where things live (map table), how to work (read context.md, TDD, surgical changes), feedback-loop commands, hard rules (the independence rules + frozen scorer + data), guardrails ALWAYS / ASK FIRST / NEVER, pointers to skills/ADRs/issues.
- [ ] `context.md`: glossary terms — BOQ, Bill, Building bill, Bill section (A–D,F,P), Line, Supply/Install/Combined, ItemKey (family|spec), Primary item, Derived item, Evidence, Drawing type, Point method, Feeder, BCEW, Termination, DB, SLD, Legend/LDSE, Gap, Provisional, Reference BOQ, Reproduction Score, Coverage, Scope/Scoped metrics, Sufficiency, Completer, Run, Baseline — plus "terms to avoid".
- [ ] Skills: `evaluate-boq` (run evaluate CLI, read report, never edit metrics.py), `add-reference-project` (copy raw → manifest → build_reference → verify → self-test → baseline), `audit-boq`, `tdd`, `karpathy-coding-discipline` (copied from the Agent Workflow Kit).
- [ ] `.claude/settings.json`: `PostToolUse` hook on `Edit|Write` running `python -m pytest tests/architecture -q` so the independence rule is enforced by tooling, not prose.
- [ ] `issues/`: 001 page-3 double markup, 002 Live Pricing page not registered, 003 v2 runs have no quality gate, 004 cross-page merge double counting, 005 DXF fitting install ignores crew/params, 006 switch section inconsistency, 007 upload page still says ODA, 008 utcnow deprecation — each with file:line evidence and acceptance criteria.
- [ ] Verify: `python -m pytest` green; `python scripts/evaluate.py --project wedela --self-test` → RS 100.0 %. Commit `docs: professional Claude project layer (CLAUDE.md router, glossary, ADRs, skills, issues, hooks)`.

---

### Task 16: Close-out

- [ ] Full suite green; update memory (`project` memory: evaluation framework + baselines); final summary to user with the baseline numbers, the reference-BOQ audit findings, and the drawing-requirements matrix.
