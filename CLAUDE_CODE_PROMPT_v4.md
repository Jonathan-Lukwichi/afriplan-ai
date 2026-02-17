# CLAUDE_CODE_PROMPT.md — AfriPlan Electrical v4.0 Build Instructions

## Pre-requisite
Read `CLAUDE.md` and `agent/models.py` first. These are the blueprint and data contract. Every file you create must import from `agent/models.py` — never define data shapes inline.

---

## Phase 1: Agent Infrastructure

### 1.1 agent/utils.py

```python
"""Utility functions shared across all pipeline stages."""

import json
import re
import base64
import time
from pathlib import Path
from typing import Any, Optional


def parse_json_safely(text: str) -> Optional[dict]:
    """
    Parse JSON from Claude's response. Handles common issues:
    - Strips markdown backticks (```json ... ```)
    - Removes trailing commas before } or ]
    - Handles single quotes → double quotes
    - Returns None on failure (never raises)
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Strip markdown code fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    # Remove trailing commas (common Claude mistake)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    # Try parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: try array
    match = re.search(r'\[[\s\S]*\]', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def estimate_cost_zar(
    model: str,
    input_tokens: int,
    output_tokens: int,
    usd_to_zar: float = 18.50
) -> float:
    """Estimate API cost in ZAR."""
    rates = {
        "claude-haiku-4-5-20251001": (1.0, 5.0),
        "claude-sonnet-4-20250514": (3.0, 15.0),
        "claude-opus-4-20250514": (15.0, 75.0),
    }
    input_rate, output_rate = rates.get(model, (3.0, 15.0))
    cost_usd = (input_tokens / 1_000_000 * input_rate +
                output_tokens / 1_000_000 * output_rate)
    return round(cost_usd * usd_to_zar, 4)


class Timer:
    """Context manager for timing operations."""
    def __init__(self):
        self.elapsed_ms = 0
    def __enter__(self):
        self._start = time.monotonic()
        return self
    def __exit__(self, *args):
        self.elapsed_ms = int((time.monotonic() - self._start) * 1000)
```

### 1.2 agent/prompts/system_prompt.py

Create the system prompt that gives Claude SA electrical domain context. Include:
- SANS 10142-1 overview
- NRS 034 ADMD values
- Standard cable sizes and ampacities (from CLAUDE.md cable capacity table)
- Common fixture types and their symbols
- SA-specific terminology (DB = distribution board, ELCB = earth leakage, etc.)
- Load calculation defaults (50W per light point, 250W per socket)

The system prompt is sent with EVERY API call. Keep it under 800 tokens.

### 1.3 agent/prompts/schemas.py

Create JSON schema strings that match the Pydantic models. These get appended to prompts.

Required schemas:
- `REGISTER_SCHEMA` → matches `ProjectMetadata`
- `SLD_SCHEMA` → matches `{"distribution_boards": [DistributionBoard...]}`
- `LIGHTING_LAYOUT_SCHEMA` → matches `{"rooms": [Room...], "legend": BuildingLegend}`
- `PLUGS_LAYOUT_SCHEMA` → similar to lighting but focused on sockets/switches
- `OUTSIDE_LIGHTS_SCHEMA` → matches `{"cable_runs": [SiteCableRun...], "fixtures": FixtureCounts}`
- `CLASSIFY_SCHEMA` → matches `{"tier": str, "mode": str, "blocks": [str]}`

Each schema should be a JSON example (not JSON Schema format). Claude performs better with examples.

### 1.4 agent/prompts/ — Individual prompt files

Create each prompt file as described in CLAUDE.md:

- `register_prompt.py` — extract project metadata from drawing register
- `sld_prompt.py` — **MOST CRITICAL** — extract DBs + circuits from SLDs (see CLAUDE.md detailed spec)
- `lighting_layout_prompt.py` — extract rooms with light fixtures from lighting layouts
- `plugs_layout_prompt.py` — extract rooms with sockets/switches from plugs layouts
- `outside_lights_prompt.py` — extract site cable runs and external fixtures
- `classify_prompt.py` — classify tier/mode (used as Haiku fallback)
- `residential_prompt.py` — estimate fixtures from residential floor plan
- `maintenance_prompt.py` — identify defects from photos

Each prompt file exports a function: `def get_prompt(pages: List[PageInfo]) -> str`

---

## Phase 2: Pipeline Stages

### 2.1 agent/stages/ingest.py

```python
"""INGEST stage: PDF → typed pages with building block assignments."""

import fitz  # PyMuPDF
from agent.models import (
    PageInfo, PageType, DocumentInfo, DocumentSet
)
from agent.utils import encode_image_to_base64


def classify_page_type(text: str, drawing_number: str) -> tuple[PageType, float]:
    """Classify page type from text content and drawing number. Returns (type, confidence)."""

    text_lower = text.lower()
    dwg_upper = drawing_number.upper()

    # Drawing number patterns (highest confidence)
    if "-SLD" in dwg_upper:
        return PageType.SLD, 0.95

    if "-LIGHTING" in dwg_upper or "-LIGHTS" in dwg_upper:
        return PageType.LAYOUT_LIGHTING, 0.95

    if "-PLUG" in dwg_upper:
        return PageType.LAYOUT_PLUGS, 0.95

    if "-OL-" in dwg_upper or "OUTSIDE" in dwg_upper:
        return PageType.OUTSIDE_LIGHTS, 0.90

    # Text content patterns
    if "drawing register" in text_lower or "transmittal" in text_lower:
        return PageType.REGISTER, 0.90

    if "circuit no" in text_lower and "wattage" in text_lower:
        return PageType.SLD, 0.85

    if "lighting layout" in text_lower or "lights layout" in text_lower:
        return PageType.LAYOUT_LIGHTING, 0.80

    if "plugs layout" in text_lower or "power layout" in text_lower:
        return PageType.LAYOUT_PLUGS, 0.80

    return PageType.UNKNOWN, 0.30


def detect_building_block(text: str, drawing_number: str) -> str:
    """Detect which building block a page belongs to."""

    text_lower = text.lower()
    dwg_upper = drawing_number.upper()

    patterns = [
        (["WD-AB-", "ABLUTION RETAIL", "ablution retail"], "Ablution Retail Block"),
        (["WD-ECH-", "COMMUNITY HALL", "community hall", "MULTI PURPOSE"], "Existing Community Hall"),
        (["WD-LGH-", "LARGE GUARD", "large guard"], "Large Guard House"),
        (["WD-SGH-", "SMALL GUARD", "small guard"], "Small Guard House"),
        (["WD-PB-", "POOL BLOCK", "pool block", "POOL PUMP"], "Pool Block"),
        (["WD-KIOSK-", "KIOSK"], "Site Infrastructure"),
        (["WD-OL-", "OUTSIDE LIGHT"], "Site Infrastructure"),
        (["TJM-", "NEWMARK", "newmark", "PROPOSED NEW OFFICES"], "NewMark Office Building"),
    ]

    for keywords, block_name in patterns:
        for kw in keywords:
            if kw in dwg_upper or kw.lower() in text_lower:
                return block_name

    return "Unclassified"


def extract_drawing_number(text: str) -> str:
    """Extract drawing number from page text (usually in title block)."""
    # Look for common patterns: TJM-SLD-001, WD-PB-01-LIGHTING, etc.
    patterns = [
        r'(TJM-[\w-]+)',
        r'(WD-[\w-]+)',
        r'([A-Z]{2,4}-[A-Z]{2,4}-\d{2}-[\w]+)',
    ]
    for pattern in patterns:
        import re
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def ingest_documents(files: list) -> DocumentSet:
    """
    Process uploaded PDF files into a typed DocumentSet.

    Args:
        files: List of Streamlit UploadedFile objects

    Returns:
        DocumentSet with all pages classified and assigned to blocks
    """
    doc_set = DocumentSet()
    total_pages = 0

    for uploaded_file in files:
        if total_pages >= 30:
            break

        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        doc_info = DocumentInfo(
            filename=uploaded_file.name,
            mime_type="application/pdf",
            num_pages=min(doc.page_count, 10),
            file_size_bytes=len(pdf_bytes),
        )

        for page_num in range(min(doc.page_count, 10)):
            if total_pages >= 30:
                break

            page = doc[page_num]

            # Extract text
            text = page.get_text()

            # Render to image at 200 DPI
            mat = fitz.Matrix(200/72, 200/72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # Classify
            drawing_number = extract_drawing_number(text)
            page_type, confidence = classify_page_type(text, drawing_number)
            block = detect_building_block(text, drawing_number)

            page_info = PageInfo(
                page_number=page_num + 1,
                page_type=page_type,
                image_base64=encode_image_to_base64(img_bytes),
                text_content=text,
                width_px=pix.width,
                height_px=pix.height,
                classification_confidence=confidence,
                drawing_number=drawing_number,
                building_block=block,
                source_document=uploaded_file.name,
            )
            doc_info.pages.append(page_info)
            total_pages += 1

        doc.close()
        doc_set.documents.append(doc_info)

    # Update aggregates
    doc_set.total_pages = total_pages
    all_pages = doc_set.all_pages
    doc_set.num_sld_pages = sum(1 for p in all_pages if p.page_type == PageType.SLD)
    doc_set.num_lighting_pages = sum(1 for p in all_pages if p.page_type == PageType.LAYOUT_LIGHTING)
    doc_set.num_plugs_pages = sum(1 for p in all_pages if p.page_type == PageType.LAYOUT_PLUGS)
    doc_set.num_register_pages = sum(1 for p in all_pages if p.page_type == PageType.REGISTER)
    doc_set.num_outside_light_pages = sum(1 for p in all_pages if p.page_type == PageType.OUTSIDE_LIGHTS)
    doc_set.building_blocks_detected = list(set(
        p.building_block for p in all_pages if p.building_block != "Unclassified"
    ))

    return doc_set
```

### 2.2 agent/stages/classify.py

Implement tier and mode classification. Use heuristics first, Haiku fallback.
Import from `agent/models.py`: `ServiceTier`, `ExtractionMode`.

Key logic:
```python
def classify_project(doc_set: DocumentSet) -> tuple[ServiceTier, ExtractionMode, float]:
    # Multiple blocks → MIXED tier
    if len(doc_set.building_blocks_detected) > 2:
        tier = ServiceTier.MIXED

    # Has SLDs → AS_BUILT mode
    if doc_set.num_sld_pages > 0 and doc_set.num_lighting_pages > 0:
        mode = ExtractionMode.AS_BUILT

    # Only layouts, no SLDs → ESTIMATION mode
    elif doc_set.num_lighting_pages > 0 and doc_set.num_sld_pages == 0:
        mode = ExtractionMode.ESTIMATION

    # ... etc
```

### 2.3 agent/stages/discover.py — **THE CORE**

This is the most complex stage. Implementation outline:

```python
"""DISCOVER stage: Send page-type-specific prompts to Claude, merge results."""

import anthropic
from agent.models import *
from agent.utils import parse_json_safely, estimate_cost_zar, Timer
from agent.prompts import (
    system_prompt, register_prompt, sld_prompt,
    lighting_layout_prompt, plugs_layout_prompt,
    outside_lights_prompt, schemas
)


def discover(
    doc_set: DocumentSet,
    extraction_mode: ExtractionMode,
    model: str = "claude-sonnet-4-20250514"
) -> tuple[ExtractionResult, StageResult]:
    """
    Extract data from all pages using targeted prompts.

    Strategy:
    1. Group pages by (building_block, page_type)
    2. Send each group with appropriate prompt
    3. Parse responses into Pydantic models
    4. Merge results per building block
    5. Build supply hierarchy from SLD data
    """

    client = anthropic.Anthropic()
    result = ExtractionResult(extraction_mode=extraction_mode)
    stage = StageResult(stage=PipelineStage.DISCOVER)
    total_tokens = 0
    total_cost = 0.0

    # Step 1: Group pages
    page_groups = {}
    for page in doc_set.all_pages:
        key = (page.building_block, page.page_type)
        page_groups.setdefault(key, []).append(page)

    # Step 2: Process register pages first (metadata)
    register_pages = [p for p in doc_set.all_pages if p.page_type == PageType.REGISTER]
    if register_pages:
        metadata = _extract_register(client, register_pages, model)
        if metadata:
            result.metadata = metadata

    # Step 3: Process SLD pages per block
    blocks_data = {}  # block_name → BuildingBlock
    for (block_name, page_type), pages in page_groups.items():
        if page_type == PageType.SLD:
            dbs = _extract_sld(client, pages, block_name, model)
            if block_name not in blocks_data:
                blocks_data[block_name] = BuildingBlock(name=block_name)
            blocks_data[block_name].distribution_boards.extend(dbs)
            # Extract heavy equipment from pump/heat pump circuits
            for db in dbs:
                equipment = _identify_heavy_equipment(db, block_name)
                blocks_data[block_name].heavy_equipment.extend(equipment)

    # Step 4: Process lighting layout pages per block
    for (block_name, page_type), pages in page_groups.items():
        if page_type == PageType.LAYOUT_LIGHTING:
            rooms = _extract_lighting_layout(client, pages, block_name, model)
            if block_name not in blocks_data:
                blocks_data[block_name] = BuildingBlock(name=block_name)
            blocks_data[block_name].rooms.extend(rooms)

    # Step 5: Process plugs layout pages per block — MERGE with existing rooms
    for (block_name, page_type), pages in page_groups.items():
        if page_type == PageType.LAYOUT_PLUGS:
            plug_rooms = _extract_plugs_layout(client, pages, block_name, model)
            if block_name in blocks_data:
                _merge_plug_data(blocks_data[block_name], plug_rooms)
            else:
                blocks_data[block_name] = BuildingBlock(name=block_name)
                blocks_data[block_name].rooms.extend(plug_rooms)

    # Step 6: Process outside lights
    ol_pages = [p for p in doc_set.all_pages if p.page_type == PageType.OUTSIDE_LIGHTS]
    if ol_pages:
        cable_runs, fixtures = _extract_outside_lights(client, ol_pages, model)
        result.site_cable_runs = cable_runs
        result.outside_lights = fixtures

    # Step 7: Assemble building blocks
    result.building_blocks = list(blocks_data.values())

    # Step 8: Build supply hierarchy from DB supply_from fields
    result.supply_points = _build_supply_hierarchy(result)

    return result, stage


def _extract_sld(client, pages, block_name, model):
    """Send SLD pages to Claude with sld_prompt. Returns List[DistributionBoard]."""
    # Build message with all SLD page images for this block
    content = []
    for page in pages:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": page.image_base64}
        })
    content.append({
        "type": "text",
        "text": sld_prompt.get_prompt(pages) + "\n\n" + schemas.SLD_SCHEMA
    })

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8192,  # SLD extraction can be long (many circuits)
            temperature=0,
            system=system_prompt.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )
        raw_text = response.content[0].text
        data = parse_json_safely(raw_text)
        if data and "distribution_boards" in data:
            dbs = []
            for db_data in data["distribution_boards"]:
                db = DistributionBoard(**db_data, building_block=block_name,
                                        page_source=pages[0].drawing_number)
                dbs.append(db)
            return dbs
    except Exception as e:
        # Log error, return empty
        pass
    return []


def _merge_plug_data(block: BuildingBlock, plug_rooms: list):
    """Merge socket/switch data from plugs layout into existing rooms from lighting layout."""
    existing = {r.name.strip().lower(): r for r in block.rooms}
    for pr in plug_rooms:
        key = pr.name.strip().lower()
        if key in existing:
            room = existing[key]
            # Add socket counts
            room.fixtures.double_socket_300 += pr.fixtures.double_socket_300
            room.fixtures.single_socket_300 += pr.fixtures.single_socket_300
            room.fixtures.double_socket_1100 += pr.fixtures.double_socket_1100
            room.fixtures.single_socket_1100 += pr.fixtures.single_socket_1100
            room.fixtures.double_socket_waterproof += pr.fixtures.double_socket_waterproof
            room.fixtures.double_socket_ceiling += pr.fixtures.double_socket_ceiling
            room.fixtures.data_points_cat6 += pr.fixtures.data_points_cat6
            room.fixtures.floor_box += pr.fixtures.floor_box
            # Add switch counts
            room.fixtures.switch_1lever_1way += pr.fixtures.switch_1lever_1way
            room.fixtures.switch_2lever_1way += pr.fixtures.switch_2lever_1way
            room.fixtures.switch_1lever_2way += pr.fixtures.switch_1lever_2way
            room.fixtures.isolator_30a += pr.fixtures.isolator_30a
            room.fixtures.isolator_20a += pr.fixtures.isolator_20a
            room.fixtures.day_night_switch += pr.fixtures.day_night_switch
            room.fixtures.master_switch += pr.fixtures.master_switch
            # Add circuit refs
            room.circuit_refs.extend(pr.circuit_refs)
            # Add AC/geyser flags
            room.has_ac = room.has_ac or pr.has_ac
            room.has_geyser = room.has_geyser or pr.has_geyser
        else:
            # Room only appears on plugs layout
            block.rooms.append(pr)


# Implement similar _extract_register, _extract_lighting_layout,
# _extract_plugs_layout, _extract_outside_lights functions
# following the same pattern.
```

### 2.4 agent/stages/validate.py

Implement SANS 10142-1 rules + cross-page validation as specified in CLAUDE.md.

Key function signature:
```python
def validate(extraction: ExtractionResult) -> ValidationResult:
    """Run all validation rules against extracted data."""
```

Must implement:
1. Per-circuit rules (max points, cable capacity, breaker matching)
2. Per-DB rules (ELCB, spare ways, surge protection)
3. Cross-reference validation (SLD circuits vs layout circuit refs)
4. Cross-block validation (sub-board feeds match child DBs)

### 2.5 agent/stages/price.py

Implement the pricing engine as specified in CLAUDE.md sections A through L.

Key function signature:
```python
def price(
    extraction: ExtractionResult,
    validation: ValidationResult,
    margin_pct: float = 20.0,
    contingency_pct: float = 5.0,
    complexity_factor: float = 1.0,
) -> PricingResult:
    """Generate Bill of Quantities from extracted and validated data."""
```

Must iterate:
1. Per building block → per DB → per circuit → price cables + breakers
2. Per building block → per room → per fixture type → price fittings
3. Per heavy equipment item → price equipment + connection
4. Per site cable run → price cable + trenching
5. Add compliance items from validation
6. Add labour per circuit/point/DB
7. Add provisional sums
8. Calculate subtotals, contingency, margin, VAT

### 2.6 agent/stages/output.py

Assemble final PipelineResult with weighted confidence calculation.

### 2.7 agent/pipeline.py

Orchestrator class:
```python
class AfriPlanAgent:
    def process_documents(self, files: list) -> PipelineResult:
        """Run the complete 6-stage pipeline on uploaded files."""
        result = PipelineResult()

        # Stage 1: INGEST
        try:
            doc_set = ingest.ingest_documents(files)
            result.document_set = doc_set
            # ... add StageResult
        except Exception as e:
            result.errors.append(f"INGEST failed: {str(e)}")
            return result  # Can't continue without documents

        # Stage 2: CLASSIFY
        # Stage 3: DISCOVER
        # Stage 4: VALIDATE
        # Stage 5: PRICE
        # Stage 6: OUTPUT

        return result
```

---

## Phase 3: Core Business Logic

### 3.1 core/standards.py
Move SANS 10142-1 rules into importable constants:
```python
CABLE_CAPACITY_A = {1.5: 14.5, 2.5: 20, 4: 27, 6: 35, 10: 48, 16: 64, 25: 84, 35: 104, 50: 126, 70: 159, 95: 193}
MAX_LIGHTING_POINTS = 10
MAX_POWER_POINTS = 10
MIN_SPARE_WAYS_PCT = 15
# etc.
```

### 3.2 core/pricing_engine.py
Pricing lookup tables matching CLAUDE.md price lists. Import from here in `agent/stages/price.py`.

---

## Phase 4: Frontend Updates

### 4.1 pages/1_Smart_Upload.py — COMPLETE REWRITE

```python
"""Smart Upload — Multi-document AI Pipeline"""
import streamlit as st
from agent.pipeline import AfriPlanAgent
from agent.models import *

st.set_page_config(page_title="AfriPlan - Smart Upload", layout="wide")

# Multi-file upload
uploaded_files = st.file_uploader(
    "Upload electrical drawings",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files and st.button("Run AI Pipeline", type="primary"):
    agent = AfriPlanAgent()

    # Progress bar for 6 stages
    progress = st.progress(0)
    status = st.empty()

    result = agent.process_documents(uploaded_files)

    if result.success:
        # Show tabs
        tab_overview, tab_blocks, tab_validation, tab_bq, tab_export = st.tabs([
            "Overview", "Building Blocks", "Validation", "Bill of Quantities", "Export"
        ])

        with tab_overview:
            # Project name, blocks, confidence, cost
            st.metric("Building Blocks", result.num_building_blocks)
            st.metric("Distribution Boards", result.extraction.total_dbs)
            st.metric("Confidence", f"{result.overall_confidence:.0%}")
            st.metric("API Cost", f"R{result.total_cost_zar:.2f}")

        with tab_blocks:
            # Expandable section per building block
            for block in result.extraction.building_blocks:
                with st.expander(f"{block.name} — {block.total_dbs} DBs, {len(block.rooms)} rooms"):
                    # DB table
                    for db in block.distribution_boards:
                        st.subheader(f"📦 {db.name}")
                        # Circuit table (editable via st.data_editor)
                    # Room table
                    # Equipment list

        with tab_validation:
            # Compliance flags table
            # Cross-reference results

        with tab_bq:
            # BQ grouped by section
            # Per-block subtotals
            # Project total

        with tab_export:
            # PDF download
            # Excel download
            # Continue to detailed page
```

---

## Phase 5: Tests

### tests/test_models.py
- Test all Pydantic models can be instantiated with defaults
- Test computed fields (total_lights, total_sockets, etc.)
- Test ExtractionResult.all_distribution_boards aggregation
- Test FixtureCounts.total_light_wattage calculation

### tests/test_ingest.py
- Test page classification keywords
- Test building block detection
- Test drawing number extraction

### tests/test_validation.py
- Test cable capacity checks
- Test max points per circuit
- Test ELCB detection

### tests/test_pricing.py
- Test BQ line item generation for known fixtures
- Test subtotal calculations
- Test VAT calculation

---

## Verification: The Wedela Test

After building all phases, upload all 3 Wedela PDFs simultaneously.

### Expected INGEST output:
- 25 total pages (7 + 10 + 8)
- Building blocks: NewMark Office, Ablution Retail Block, Existing Community Hall, Large Guard House, Small Guard House, Pool Block, Site Infrastructure
- Page types: 1 register, ~8 SLDs, ~8 lighting layouts, ~6 plugs layouts, 1 outside lights, 1 kiosk SLD

### Expected DISCOVER output:
- ≥15 distribution boards with circuit data
- ≥20 rooms with fixture counts
- 8 pool pumps + 9 heat pumps as HeavyEquipment
- Site cable runs with distances (110m, 35m, 50m, etc.)
- 2 supply points (Eskom Kiosk for NewMark, Existing Mini Sub for Wedela)

### Expected VALIDATE output:
- Cross-reference match rate >80%
- ELCB warnings where missing
- Spare ways warnings

### Expected PRICE output:
- BQ with all sections A-L populated
- Per-block subtotals
- Site works section with trenching costs
- Heavy equipment section with pump/heat pump pricing
- Total in R500k-R1.5M range for a project of this scale

If the pipeline produces a BQ with at least 100 line items across all sections, it's working correctly.

---

## Usage Instructions

```bash
# 1. Copy all files to project
cp CLAUDE.md /path/to/afriplan-ai/CLAUDE.md
cp -r agent/ /path/to/afriplan-ai/agent/

# 2. Install dependencies
pip install anthropic pydantic pymupdf streamlit

# 3. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Open in Claude Code
cd /path/to/afriplan-ai
claude

# 5. Build in phases
# Phase 1: "Read CLAUDE.md and agent/models.py. Build agent/utils.py and all prompt files."
# Phase 2: "Build all pipeline stages: ingest, classify, discover, validate, price, output."
# Phase 3: "Build core/standards.py and core/pricing_engine.py."
# Phase 4: "Rewrite pages/1_Smart_Upload.py with multi-file upload."
# Phase 5: "Create tests and run them."

# 6. Test
streamlit run app.py
# Upload all 3 Wedela PDFs → verify pipeline output
```
