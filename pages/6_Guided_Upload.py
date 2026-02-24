"""
AfriPlan Electrical v5.1 - Guided Upload (4-Step Document Flow + Local Mode)

Supports TWO extraction modes:
1. **AI-Based** (Cloud) - Uses Groq/Grok/Gemini/Claude for intelligent extraction
2. **Local (No AI)** - Deterministic pipeline using regex, keywords, and OpenCV

Document Flow:
1. Cover Page / Drawing Register → Project info
2. SLD / Circuit Schedules → DBs, supply point, circuits, cables
3. Lighting Layout → Legend first → Light fixtures per room
4. Power Layout → Legend first → Sockets per room

Target: 75%+ extraction rate through legend-based fixture counting.
"""

import streamlit as st
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header

# Import pipeline components
PIPELINE_AVAILABLE = False
DETERMINISTIC_AVAILABLE = False

try:
    from agent.stages.ingest import ingest
    from agent.stages.interactive_passes import InteractivePipeline, InteractivePassResult
    from agent.stages.validate import validate
    from agent.stages.price import price
    from agent.models import PageInfo, ExtractionResult, ServiceTier, PageType
    from exports.excel_bq import export_professional_bq, HAS_OPENPYXL
    from exports.pdf_summary import generate_pdf_summary
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_IMPORT_ERROR = str(e)
    HAS_OPENPYXL = False

# Import deterministic pipeline (local-only, no AI)
try:
    from agent.deterministic_pipeline import (
        DeterministicPipeline,
        DeterministicPipelineResult,
        run_deterministic_pipeline_bytes,
        quick_extract,
    )
    from agent.models import PipelineConfig
    DETERMINISTIC_AVAILABLE = True
except ImportError as e:
    DETERMINISTIC_IMPORT_ERROR = str(e)
    DETERMINISTIC_AVAILABLE = False


# ============================================================================
# API KEY LOADING
# ============================================================================

def load_api_keys():
    """Load API keys from Streamlit secrets."""
    provider = None
    api_key = None

    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
        provider = "groq"
        api_key = st.secrets["GROQ_API_KEY"]

    if "XAI_API_KEY" in st.secrets:
        os.environ["XAI_API_KEY"] = st.secrets["XAI_API_KEY"]
        if provider is None:
            provider = "grok"
            api_key = st.secrets["XAI_API_KEY"]

    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
        if provider is None:
            provider = "gemini"
            api_key = st.secrets["GEMINI_API_KEY"]

    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
        if provider is None:
            provider = "claude"
            api_key = st.secrets["ANTHROPIC_API_KEY"]

    return provider, api_key


LLM_PROVIDER, LLM_API_KEY = load_api_keys()

PROVIDER_LABELS = {
    "groq": ("Groq Llama 4", "100% FREE"),
    "grok": ("xAI Grok", "$25 FREE"),
    "gemini": ("Google Gemini", "FREE"),
    "claude": ("Claude", "Paid"),
}

PROVIDER_MODELS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "grok": "grok-2-vision-1212",
    "gemini": "gemini-2.0-flash",
    "claude": "claude-sonnet-4-20250514",
}


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables for 4-step flow."""
    defaults = {
        # Extraction mode: "ai" or "local"
        "extraction_mode": "ai",

        # Upload mode: "guided" (4-step) or "quick" (single upload)
        "upload_mode": "guided",

        # Navigation (5 steps: 4 uploads + 1 review)
        "guided_step": 1,
        "max_completed_step": 0,

        # Document pages by type (4 separate documents)
        "cover_pages": [],
        "sld_pages": [],
        "lighting_pages": [],
        "power_pages": [],

        # Raw file bytes (for deterministic pipeline)
        "cover_bytes": None,
        "sld_bytes": None,
        "lighting_bytes": None,
        "power_bytes": None,

        # Quick upload - single combined document
        "combined_bytes": None,
        "quick_upload_result": None,

        # Pipeline instances
        "interactive_pipeline": None,  # AI-based
        "deterministic_pipeline": None,  # Local-only

        # Deterministic pipeline results
        "deterministic_result": None,

        # Step 1: Project Info
        "project_info": {},

        # Step 2: SLD Extraction
        "supply_point": {},
        "detected_dbs": [],
        "db_schedules": {},
        "cable_routes": [],
        "current_db_index": 0,

        # Step 3: Lighting
        "lighting_legend": {},
        "detected_rooms": [],
        "room_lighting": {},
        "current_lighting_room_index": 0,

        # Step 4: Power
        "power_legend": {},
        "room_power": {},
        "current_power_room_index": 0,

        # Final results
        "final_extraction": None,
        "final_validation": None,
        "final_pricing": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def process_uploaded_file(uploaded_file):
    """Process an uploaded file and return pages."""
    if not uploaded_file:
        return []

    doc_set, result = ingest([
        (uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)
    ])

    if result.success:
        all_pages = []
        for doc in doc_set.documents:
            all_pages.extend(doc.pages)
        return all_pages
    else:
        st.error(f"Error processing file: {result.errors}")
        return []


def process_with_deterministic_pipeline(file_bytes: bytes, filename: str):
    """
    Process a PDF file using the deterministic (local-only) pipeline.
    Returns structured extraction results without any AI/cloud calls.
    """
    if not DETERMINISTIC_AVAILABLE:
        st.error("Deterministic pipeline not available")
        return None

    try:
        result = run_deterministic_pipeline_bytes(file_bytes, filename=filename)
        return result
    except Exception as e:
        st.error(f"Deterministic extraction error: {e}")
        return None


def render_deterministic_progress(stage_name: str, progress: float):
    """Render progress indicator for deterministic pipeline stages."""
    stages = ["INGEST", "CLASSIFY", "CROP", "EXTRACT", "MERGE"]
    stage_icons = {
        "INGEST": "📥",
        "CLASSIFY": "🏷️",
        "CROP": "✂️",
        "EXTRACT": "📊",
        "MERGE": "🔗",
    }

    cols = st.columns(5)
    for i, stage in enumerate(stages):
        with cols[i]:
            if stage == stage_name:
                st.markdown(f"**{stage_icons.get(stage, '')} {stage}**")
            elif stages.index(stage) < stages.index(stage_name):
                st.markdown(f":green[{stage_icons.get(stage, '')} {stage}]")
            else:
                st.markdown(f":gray[{stage_icons.get(stage, '')} {stage}]")


def convert_deterministic_to_display(det_result: DeterministicPipelineResult) -> dict:
    """
    Convert DeterministicPipelineResult to display format compatible with session state.
    """
    if not det_result or not det_result.project_result:
        return {}

    project = det_result.project_result
    display = {
        "project_info": {
            "project_name": project.project_name or "",
            "client_name": project.client_name or "",
            "consultant_name": project.consultant_name or "",
            "date": "",
            "revision": "",
        },
        "detected_dbs": [],
        "db_schedules": {},
        "cable_routes": [],
        "rooms": [],
        "room_lighting": {},
        "room_power": {},
    }

    # Extract DB info from SLD pages
    # project.sld_pages is List[SLDExtraction] directly (not PageExtractionResult)
    for sld in project.sld_pages:
        db_name = sld.db_name or f"DB-{len(display['detected_dbs'])+1}"
        if db_name not in display["detected_dbs"]:
            display["detected_dbs"].append(db_name)

        # Build schedule from circuits
        circuits = []
        for circuit in sld.circuits:
            circuits.append({
                "circuit_id": circuit.circuit_id,
                "description": circuit.description,
                "points": circuit.num_points,
                "wattage_w": circuit.wattage_w,
                "breaker_a": circuit.breaker_a,
                "wire_size": circuit.wire_size_mm2,
            })

        display["db_schedules"][db_name] = {
            "db_name": db_name,
            "main_breaker_a": sld.main_breaker_a,
            "supply_from": sld.supply_from,
            "total_ways": sld.total_ways,
            "circuits": circuits,
            "schedule_found": True,
        }

    # Extract room info from layout pages
    # project.lighting_pages/plugs_pages are List[LayoutExtraction] directly
    for layout in project.lighting_pages + project.plugs_pages:
        for room in layout.room_labels:
            if room not in display["rooms"]:
                display["rooms"].append(room)

    # Note: Detailed fixture counts per room would require additional processing
    # The deterministic pipeline extracts at page level, not room level

    return display


def build_extraction_from_session_state():
    """
    Build an ExtractionResult from session state data (fallback for local mode).
    """
    from agent.models import ExtractionResult, DistributionBoard, Circuit, Room, FixtureCounts

    dbs = []
    rooms = []

    # Build DBs from session state
    for db_name, schedule in st.session_state.db_schedules.items():
        circuits = []
        for c in schedule.get("circuits", []):
            circuits.append(Circuit(
                circuit_id=c.get("circuit_id", ""),
                description=c.get("description", ""),
                breaker_a=c.get("breaker_a", 10),
                wire_size_mm2=str(c.get("wire_size", "1.5")),
                points=c.get("points", 0),
            ))
        dbs.append(DistributionBoard(
            name=db_name,
            main_breaker_a=schedule.get("main_breaker_a", 100),
            total_ways=schedule.get("total_ways", 12),
            circuits=circuits,
        ))

    # Build rooms from session state
    for room_name in st.session_state.detected_rooms:
        lighting = st.session_state.room_lighting.get(room_name, {})
        power = st.session_state.room_power.get(room_name, {})

        # Combine lighting and power fixtures
        fixture_data = {**lighting, **power}

        fixtures = FixtureCounts(
            downlight=fixture_data.get("downlight", 0),
            surface_mount_led=fixture_data.get("surface_mount_led", 0),
            recessed_led_600x1200=fixture_data.get("recessed_led_600x1200", 0),
            switch_1lever=fixture_data.get("switch_1lever", 0),
            switch_2lever=fixture_data.get("switch_2lever", 0),
            double_socket_300=fixture_data.get("double_socket_300", 0),
            double_socket_1100=fixture_data.get("double_socket_1100", 0),
            data_point_cat6=fixture_data.get("data_point_cat6", 0),
            isolator_20a=fixture_data.get("isolator_20a", 0),
        )

        rooms.append(Room(
            name=room_name,
            fixtures=fixtures,
        ))

    return ExtractionResult(
        project_name=st.session_state.project_info.get("project_name", "Project"),
        client_name=st.session_state.project_info.get("client_name", ""),
        distribution_boards=dbs,
        rooms=rooms,
    )


def init_pipeline():
    """Initialize the interactive pipeline with API client."""
    if not PIPELINE_AVAILABLE or not LLM_API_KEY:
        return None

    provider = LLM_PROVIDER
    api_key = LLM_API_KEY
    model = PROVIDER_MODELS.get(provider, "claude-sonnet-4-20250514")

    try:
        if provider == "groq":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        elif provider == "grok":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            client = genai
        elif provider == "claude":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        else:
            return None

        return InteractivePipeline(client, model, provider)

    except Exception as e:
        st.error(f"Error initializing pipeline: {e}")
        return None


def normalize_fixture_data(raw_fixtures: dict) -> dict:
    """
    Normalize AI-returned fixture data to standard keys.
    Maps keys like '6w_led_downlight' to 'downlight'.
    """
    if not raw_fixtures:
        return {}

    normalized = {}
    for key, value in raw_fixtures.items():
        if not isinstance(value, (int, float)):
            continue
        std_key = map_fixture_to_standard_key(key)
        # Accumulate if same standard key maps from multiple raw keys
        normalized[std_key] = normalized.get(std_key, 0) + int(value)
    return normalized


def map_fixture_to_standard_key(name: str) -> str:
    """
    Map a legend fixture name to a standard key for build_extraction_result.

    Keys MUST match exactly what build_extraction_result() expects, which are
    based on FixtureCounts model attributes.
    """
    name_lower = name.lower().replace("_", " ").replace("-", " ")

    # === LIGHTING FIXTURES ===
    # Panel/Recessed lights
    if "600x1200" in name_lower or "1200" in name_lower:
        return "recessed_led_600x1200"
    if "600x600" in name_lower:
        return "recessed_led_600x1200"  # Map to 1200 (builder only uses 1200)
    if any(x in name_lower for x in ["panel", "recessed", "led panel"]):
        return "recessed_led_600x1200"

    # Downlights
    if any(x in name_lower for x in ["downlight", "down light", "spotlight", "spot"]):
        return "downlight"

    # Surface mount / ceiling lights
    if any(x in name_lower for x in ["surface", "ceiling light", "batten", "strip"]):
        return "surface_mount_led"

    # Flood lights
    if any(x in name_lower for x in ["200w flood", "flood 200", "high power flood"]):
        return "flood_light_200w"
    if any(x in name_lower for x in ["flood", "floodlight"]):
        return "flood_light_30w"

    # Pool lights
    if any(x in name_lower for x in ["underwater", "pool light", "submerge"]):
        return "pool_underwater_light"
    if "pool" in name_lower and "flood" in name_lower:
        return "pool_flood_light"

    # Vapor proof
    if any(x in name_lower for x in ["vapor 2x24", "vapour 2x24", "24w vapor", "24w vapour"]):
        return "vapor_proof_2x24w"
    if any(x in name_lower for x in ["vapor", "vapour", "waterproof light"]):
        return "vapor_proof_2x18w"

    # Bulkhead
    if any(x in name_lower for x in ["bulkhead 26", "26w bulkhead"]):
        return "bulkhead_26w"
    if any(x in name_lower for x in ["bulkhead", "wall light", "wall mount"]):
        return "bulkhead_24w"

    # Prismatic
    if "prismatic" in name_lower:
        return "prismatic_2x18w"

    # Fluorescent
    if any(x in name_lower for x in ["fluorescent", "5ft", "5 ft"]):
        return "fluorescent_50w_5ft"

    # Pole light
    if any(x in name_lower for x in ["pole light", "pole", "outdoor post"]):
        return "pole_light_60w"

    # Emergency lights (map to surface mount since no dedicated field)
    if "emergency" in name_lower:
        return "surface_mount_led"

    # Generic light catch-all
    if any(x in name_lower for x in ["light", "lamp", "luminaire", "fitting"]) and "switch" not in name_lower:
        return "surface_mount_led"

    # === SWITCHES ===
    # Day/night switch
    if any(x in name_lower for x in ["day", "night", "d/n", "daynight"]):
        return "day_night_switch"

    # Master switch
    if "master" in name_lower:
        return "master_switch"

    # 2-way switch
    if any(x in name_lower for x in ["2 way", "2way", "two way"]):
        return "switch_2way"

    # 2-lever switch
    if any(x in name_lower for x in ["2 lever", "2lever", "two lever"]):
        return "switch_2lever"

    # 1-lever switch (default)
    if any(x in name_lower for x in ["switch", "lever", "1 lever", "1lever"]):
        return "switch_1lever"

    # === SOCKETS ===
    # Ceiling socket
    if "ceiling" in name_lower and "socket" in name_lower:
        return "double_socket_ceiling"

    # Waterproof sockets
    if any(x in name_lower for x in ["waterproof", "wp", "ip44", "ip65", "outdoor socket"]):
        return "waterproof_socket"

    # 1100mm height (worktop)
    if any(x in name_lower for x in ["1100", "worktop", "counter"]):
        if "single" in name_lower or "1 gang" in name_lower:
            return "single_socket_1100"
        return "double_socket_1100"

    # 300mm height (floor level)
    if "single" in name_lower or "1 gang" in name_lower:
        return "single_socket"
    if any(x in name_lower for x in ["double", "twin", "2 gang"]):
        return "double_socket_300"

    # Generic socket catch-all
    if any(x in name_lower for x in ["socket", "plug", "outlet", "receptacle"]):
        return "double_socket_300"

    # === DATA POINTS ===
    if any(x in name_lower for x in ["data", "cat5", "cat6", "rj45", "network", "lan"]):
        return "data_point_cat6"

    # === FLOOR BOX ===
    if any(x in name_lower for x in ["floor box", "floorbox"]):
        return "floor_box"

    # === ISOLATORS ===
    if any(x in name_lower for x in ["30a isolator", "isolator 30", "geyser isolator"]):
        return "isolator_30a"
    if any(x in name_lower for x in ["20a isolator", "isolator 20", "ac isolator"]):
        return "isolator_20a"
    if any(x in name_lower for x in ["isolator", "iso ", "disconnect"]):
        return "isolator_20a"  # Default to 20A

    # === EQUIPMENT ===
    if any(x in name_lower for x in ["a/c", "air con", "aircon", "ac unit", "air condition"]):
        return "ac_units"

    # Default: use normalized name (will likely be ignored by builder)
    return name.replace(" ", "_").replace("-", "_").lower()[:30]


def render_progress_indicator():
    """Render 5-step progress indicator (4 uploads + review)."""
    step = st.session_state.guided_step
    max_step = st.session_state.max_completed_step

    steps = [
        ("1", "Cover Page"),
        ("2", "SLD & Schedules"),
        ("3", "Lighting Layout"),
        ("4", "Power Layout"),
        ("5", "Review & Export"),
    ]

    cols = st.columns(5)
    for i, (num, name) in enumerate(steps):
        step_num = i + 1
        with cols[i]:
            if step_num == step:
                st.markdown(f"**:blue[{num}. {name}]**")
            elif step_num <= max_step:
                st.markdown(f":green[{num}. {name}]")
            else:
                st.markdown(f":gray[{num}. {name}]")

    st.markdown("---")


def render_confidence_badge(confidence: float, label: str = "Confidence"):
    """Render confidence indicator."""
    if confidence >= 0.70:
        st.success(f"{label}: {confidence*100:.0f}% - High confidence")
    elif confidence >= 0.40:
        st.warning(f"{label}: {confidence*100:.0f}% - Please review")
    else:
        st.error(f"{label}: {confidence*100:.0f}% - Manual input needed")


def show_page_thumbnails(pages, max_show=3):
    """Show thumbnails of uploaded pages."""
    if not pages:
        return
    cols = st.columns(min(max_show, len(pages)))
    for i, page in enumerate(pages[:max_show]):
        if page.image_base64:
            with cols[i]:
                st.image(
                    f"data:image/png;base64,{page.image_base64}",
                    caption=f"Page {i+1}",
                    use_container_width=True
                )


# ============================================================================
# QUICK UPLOAD MODE (Single Document - Automatic Split)
# ============================================================================

def render_quick_upload():
    """
    Quick Upload mode: Single combined PDF, automatic page splitting & classification.
    Only available in Local mode (deterministic pipeline).
    """
    section_header("Quick Upload (Local Mode)",
                   "Upload combined PDF - automatic page splitting & classification")

    st.info("""
    **Upload a single PDF** containing all pages (cover, SLD, lighting, power layouts).

    The deterministic pipeline will automatically:
    1. 📥 **INGEST** - Convert PDF to pages
    2. 🏷️ **CLASSIFY** - Detect page types (Register, SLD, Lighting, Plugs)
    3. ✂️ **CROP** - Identify regions (title block, legend, schedule)
    4. 📊 **EXTRACT** - Pull data from each page type
    5. 🔗 **MERGE** - Aggregate to project-level results
    """)

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Combined PDF",
        type=["pdf"],
        key="quick_upload_file"
    )

    if uploaded_file:
        st.session_state.combined_bytes = uploaded_file.getvalue()
        st.success(f"Uploaded: {uploaded_file.name} ({len(st.session_state.combined_bytes) / 1024:.1f} KB)")

    if st.session_state.combined_bytes and not st.session_state.quick_upload_result:
        if st.button("🚀 Process Document (Local)", type="primary", use_container_width=True):
            with st.spinner("Running 5-stage deterministic pipeline..."):
                # Show progress stages
                progress_container = st.empty()

                # Run deterministic pipeline
                det_result = process_with_deterministic_pipeline(
                    st.session_state.combined_bytes,
                    uploaded_file.name if uploaded_file else "document.pdf"
                )

                if det_result:
                    st.session_state.quick_upload_result = det_result
                    st.session_state.deterministic_result = det_result
                    st.rerun()

    # Show results
    if st.session_state.quick_upload_result:
        render_quick_upload_results()


def render_quick_upload_results():
    """Display results from quick upload processing."""
    det_result = st.session_state.quick_upload_result

    if not det_result or not det_result.success:
        st.error("Extraction failed. Try the 4-step guided upload instead.")
        if det_result and det_result.errors:
            for err in det_result.errors[:3]:
                st.error(f"Error: {err}")
        return

    # Success banner
    st.success("✅ Document processed successfully!")

    # Pipeline stages summary
    st.markdown("### Pipeline Stages")
    render_deterministic_progress("MERGE", 1.0)

    # Show stage timings
    if det_result.stage_results:
        cols = st.columns(5)
        for i, stage in enumerate(det_result.stage_results[:5]):
            with cols[i]:
                st.metric(
                    stage.stage_name,
                    f"{stage.processing_time_ms}ms",
                    f"{stage.items_processed} items"
                )

    # Page classification summary
    st.markdown("### Page Classification")
    if det_result.pages:
        page_types = {}
        for page in det_result.pages:
            ptype = page.classification.page_type.value if page.classification else "unknown"
            page_types[ptype] = page_types.get(ptype, 0) + 1

        cols = st.columns(len(page_types))
        for i, (ptype, count) in enumerate(page_types.items()):
            with cols[i]:
                icon = {"register": "📋", "sld": "⚡", "layout_lighting": "💡",
                        "layout_plugs": "🔌", "unknown": "❓"}.get(ptype, "📄")
                st.metric(f"{icon} {ptype.replace('_', ' ').title()}", count)

    # Extraction summary
    st.markdown("### Extraction Summary")
    project = det_result.project_result

    if project:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Project Name", project.project_name or "Not found")
        with col2:
            st.metric("DBs Found", len(project.sld_pages))
        with col3:
            # project.sld_pages is List[SLDExtraction] directly
            total_circuits = sum(
                len(sld.circuits) for sld in project.sld_pages
            )
            st.metric("Circuits", total_circuits)
        with col4:
            # project.lighting_pages/plugs_pages are List[LayoutExtraction] directly
            room_count = sum(
                len(layout.room_labels)
                for layout in project.lighting_pages + project.plugs_pages
            )
            st.metric("Rooms", room_count)

        # Detailed results in expanders
        if project.sld_pages:
            with st.expander("⚡ SLD / Circuit Schedules", expanded=True):
                for sld in project.sld_pages:
                    # sld is SLDExtraction directly, not PageExtractionResult
                    st.markdown(f"**{sld.db_name or 'DB'}** - "
                                f"Main: {sld.main_breaker_a}A, "
                                f"{len(sld.circuits)} circuits")
                    if sld.circuits:
                        import pandas as pd
                        df = pd.DataFrame([{
                            "Circuit": c.circuit_id,
                            "Description": c.description,
                            "Points": c.num_points,
                            "Wattage": c.wattage_w,
                            "Breaker": f"{c.breaker_a}A" if c.breaker_a else "",
                            "Wire": c.wire_size_mm2,
                        } for c in sld.circuits])
                        st.dataframe(df, use_container_width=True)

        if project.lighting_pages:
            with st.expander("💡 Lighting Layout"):
                for i, layout in enumerate(project.lighting_pages):
                    # layout is LayoutExtraction directly
                    st.markdown(f"**Lighting {i+1}** - "
                                f"Rooms: {', '.join(layout.room_labels[:5])}")
                    if layout.legend_items:
                        st.markdown(f"Legend: {', '.join(layout.legend_items[:10])}")

        if project.plugs_pages:
            with st.expander("🔌 Power Layout"):
                for i, layout in enumerate(project.plugs_pages):
                    # layout is LayoutExtraction directly
                    st.markdown(f"**Power {i+1}** - "
                                f"Rooms: {', '.join(layout.room_labels[:5])}")

        # Populate session state for export
        display = convert_deterministic_to_display(det_result)
        st.session_state.project_info = display.get("project_info", {})
        st.session_state.detected_dbs = display.get("detected_dbs", [])
        st.session_state.db_schedules = display.get("db_schedules", {})
        st.session_state.detected_rooms = display.get("rooms", [])

    # Warnings
    if det_result.warnings:
        with st.expander(f"⚠️ Warnings ({len(det_result.warnings)})", expanded=False):
            for warn in det_result.warnings[:10]:
                st.warning(f"{warn.message}")

    # Export buttons
    st.markdown("### Export")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Build extraction result for export
        if st.button("Generate BOQ", type="primary", use_container_width=True):
            st.session_state.final_extraction = build_extraction_from_session_state()
            try:
                validation, _ = validate(st.session_state.final_extraction)
                st.session_state.final_validation = validation
                pricing, _ = price(st.session_state.final_extraction, validation, None, None)
                st.session_state.final_pricing = pricing
                st.success("BOQ generated!")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.session_state.final_pricing and HAS_OPENPYXL:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:50]
                excel_bytes = export_professional_bq(
                    st.session_state.final_pricing,
                    st.session_state.final_extraction,
                    project_name
                )
                st.download_button(
                    "📥 Download Excel BOQ",
                    data=excel_bytes,
                    file_name=f"{safe_name}_BOQ.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Excel error: {e}")

    with col3:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.combined_bytes = None
            st.session_state.quick_upload_result = None
            st.session_state.deterministic_result = None
            st.session_state.final_extraction = None
            st.session_state.final_validation = None
            st.session_state.final_pricing = None
            st.rerun()


# ============================================================================
# STEP 1: COVER PAGE / DRAWING REGISTER
# ============================================================================

def render_step_1_cover():
    """Step 1: Upload cover page and extract project info."""
    is_local_mode = st.session_state.extraction_mode == "local"
    mode_label = "🖥️ Local Mode" if is_local_mode else "☁️ AI Mode"

    section_header("Step 1: Cover Page / Drawing Register",
                   f"Upload the cover page to extract project information ({mode_label})")

    st.info("""
    **What to upload:** `01_Cover_Page_Drawing_Register.pdf`

    This document should contain:
    - Project name and description
    - Client name
    - Consultant/Engineer name
    - Drawing register (list of drawings)
    - Date and revision info
    """)

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Cover Page (PDF or Image)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="cover_uploader_v2"
    )

    if uploaded_file:
        with st.spinner("Processing cover page..."):
            # Store raw bytes for deterministic pipeline
            st.session_state.cover_bytes = uploaded_file.getvalue()
            pages = process_uploaded_file(uploaded_file)
            if pages:
                st.session_state.cover_pages = pages
                st.success(f"Cover page loaded ({len(pages)} page(s))")
                show_page_thumbnails(pages, max_show=2)

    # If already uploaded, show extraction form
    if st.session_state.cover_pages and not st.session_state.project_info:
        st.markdown("---")
        st.markdown("### Extract Project Information")

        if is_local_mode:
            # LOCAL MODE: Use deterministic pipeline
            if st.button("Extract (Local)", type="primary", key="extract_cover_local"):
                with st.spinner("Local extraction (regex + keywords)..."):
                    render_deterministic_progress("INGEST", 0.2)
                    det_result = process_with_deterministic_pipeline(
                        st.session_state.cover_bytes,
                        "cover_page.pdf"
                    )
                    if det_result and det_result.success:
                        st.session_state.deterministic_result = det_result
                        display = convert_deterministic_to_display(det_result)
                        st.session_state.project_info = display.get("project_info", {})
                    else:
                        st.session_state.project_info = {}
                        if det_result:
                            for warn in det_result.warnings[:3]:
                                st.warning(f"⚠️ {warn.message}")
                st.rerun()
        else:
            # AI MODE: Use interactive pipeline
            if st.button("Extract with AI", type="primary", key="extract_cover"):
                pipeline = init_pipeline()
                if pipeline:
                    st.session_state.interactive_pipeline = pipeline
                    with st.spinner("AI extracting project info..."):
                        result = pipeline.run_project_info_pass(st.session_state.cover_pages)
                        if result.success:
                            st.session_state.project_info = result.display_data
                        else:
                            st.session_state.project_info = {}
                    st.rerun()
                else:
                    st.error("Failed to initialize AI. Check API key.")

    # Show editable form if extracted
    if st.session_state.project_info or st.session_state.cover_pages:
        st.markdown("---")
        st.markdown("### Project Details (edit if needed)")

        confidence = 0.85 if st.session_state.project_info.get("project_name") else 0.3
        render_confidence_badge(confidence, "Extraction")

        with st.form("project_info_form_v2"):
            project_name = st.text_input(
                "Project Name",
                value=st.session_state.project_info.get("project_name", ""),
                placeholder="e.g., THE UPGRADING OF WEDELA RECREATIONAL CLUB"
            )
            client_name = st.text_input(
                "Client Name",
                value=st.session_state.project_info.get("client_name", ""),
                placeholder="e.g., ABC Properties (Pty) Ltd"
            )
            consultant = st.text_input(
                "Consultant/Engineer",
                value=st.session_state.project_info.get("consultant_name", ""),
                placeholder="e.g., CHONA MALANGA"
            )

            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input(
                    "Date",
                    value=st.session_state.project_info.get("date", ""),
                    placeholder="e.g., 2024-10-10"
                )
            with col2:
                revision = st.text_input(
                    "Revision",
                    value=st.session_state.project_info.get("revision", ""),
                    placeholder="e.g., Rev 1"
                )

            submitted = st.form_submit_button("Confirm & Continue to SLD", type="primary", use_container_width=True)

            if submitted:
                st.session_state.project_info = {
                    "project_name": project_name,
                    "client_name": client_name,
                    "consultant_name": consultant,
                    "date": date,
                    "revision": revision,
                }
                if st.session_state.interactive_pipeline:
                    st.session_state.interactive_pipeline.apply_project_info(st.session_state.project_info)
                st.session_state.guided_step = 2
                st.session_state.max_completed_step = max(1, st.session_state.max_completed_step)
                st.rerun()


# ============================================================================
# STEP 2: SLD + CIRCUIT SCHEDULES
# ============================================================================

def render_step_2_sld():
    """Step 2: Upload SLD and extract DBs, schedules, supply point, cables."""
    is_local_mode = st.session_state.extraction_mode == "local"
    mode_label = "🖥️ Local Mode" if is_local_mode else "☁️ AI Mode"

    section_header("Step 2: SLD & Circuit Schedules",
                   f"Upload SLD to extract distribution boards, circuits, and cable routes ({mode_label})")

    # Sub-step navigation
    substep = st.session_state.get("sld_substep", "upload")

    # SUBSTEP: Upload
    if substep == "upload":
        st.info("""
        **What to upload:** `02_SLD_Circuit_Schedule.pdf`

        This document should contain:
        - Single Line Diagram (SLD)
        - Circuit schedules for each DB
        - Main supply point / Kiosk metering info
        - Cable routes between DBs
        """)

        uploaded_file = st.file_uploader(
            "Upload SLD & Circuit Schedule (PDF)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="sld_uploader_v2"
        )

        if uploaded_file:
            with st.spinner("Processing SLD pages..."):
                # Store raw bytes for deterministic pipeline
                st.session_state.sld_bytes = uploaded_file.getvalue()
                pages = process_uploaded_file(uploaded_file)
                if pages:
                    st.session_state.sld_pages = pages
                    st.success(f"SLD loaded ({len(pages)} page(s))")
                    show_page_thumbnails(pages, max_show=4)

        if st.session_state.sld_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Cover Page", use_container_width=True):
                    st.session_state.guided_step = 1
                    st.rerun()
            with col2:
                button_label = "Extract (Local)" if is_local_mode else "Detect Distribution Boards"
                if st.button(button_label, type="primary", use_container_width=True):
                    if is_local_mode:
                        # LOCAL MODE: Run full deterministic extraction on SLD
                        st.session_state["sld_substep"] = "local_extract"
                    else:
                        st.session_state["sld_substep"] = "detect_dbs"
                    st.rerun()
        return

    # SUBSTEP: Local extraction (deterministic - all at once)
    if substep == "local_extract":
        st.markdown("### Local Extraction (No AI)")
        render_deterministic_progress("EXTRACT", 0.6)

        if not st.session_state.detected_dbs:
            with st.spinner("Extracting DBs and circuits using regex patterns..."):
                det_result = process_with_deterministic_pipeline(
                    st.session_state.sld_bytes,
                    "sld_schedule.pdf"
                )
                if det_result and det_result.success:
                    st.session_state.deterministic_result = det_result
                    display = convert_deterministic_to_display(det_result)

                    # Update session state with extracted data
                    st.session_state.detected_dbs = display.get("detected_dbs", [])
                    st.session_state.db_schedules = display.get("db_schedules", {})
                    st.session_state.cable_routes = display.get("cable_routes", [])

                    # Show any warnings
                    if det_result.warnings:
                        for warn in det_result.warnings[:3]:
                            st.warning(f"⚠️ {warn.message}")

        if st.session_state.detected_dbs:
            st.success(f"Found {len(st.session_state.detected_dbs)} distribution boards")

            # Show detected DBs
            st.markdown("**Detected DBs:** (edit if needed)")
            for i, db in enumerate(st.session_state.detected_dbs):
                st.markdown(f"- {db}")

            # Show schedules
            if st.session_state.db_schedules:
                with st.expander("View Extracted Schedules", expanded=False):
                    for db_name, schedule in st.session_state.db_schedules.items():
                        st.markdown(f"**{db_name}**")
                        circuits = schedule.get("circuits", [])
                        if circuits:
                            import pandas as pd
                            df = pd.DataFrame(circuits)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.caption("No circuits extracted")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Upload", use_container_width=True):
                    st.session_state["sld_substep"] = "upload"
                    st.rerun()
            with col2:
                if st.button("Continue to Lighting Layout", type="primary", use_container_width=True):
                    st.session_state["sld_substep"] = "upload"  # Reset for next time
                    st.session_state.guided_step = 3
                    st.session_state.max_completed_step = max(2, st.session_state.max_completed_step)
                    st.rerun()
        else:
            st.warning("No DBs detected from SLD. The document may not contain recognizable circuit schedules.")
            st.info("Try uploading a different document or switch to AI mode for better extraction.")

            if st.button("Back to Upload", use_container_width=True):
                st.session_state["sld_substep"] = "upload"
                st.rerun()
        return

    # Initialize pipeline if needed
    pipeline = st.session_state.interactive_pipeline
    if not pipeline:
        pipeline = init_pipeline()
        st.session_state.interactive_pipeline = pipeline

    # SUBSTEP: Detect DBs
    if substep == "detect_dbs":
        st.markdown("### Detecting Distribution Boards")

        if not st.session_state.detected_dbs:
            with st.spinner("AI scanning for distribution boards (including DB-GF, DB-CA, etc.)..."):
                result = pipeline.run_db_detection_pass(st.session_state.sld_pages)
                if result.success:
                    dbs = result.display_data.get("dbs", [])
                    st.session_state.detected_dbs = [db["name"] for db in dbs]
                    pipeline.apply_detected_dbs(st.session_state.detected_dbs)

        if st.session_state.detected_dbs:
            st.success(f"Found {len(st.session_state.detected_dbs)} distribution boards")

            # Show detected DBs with checkboxes
            st.markdown("**Detected DBs:** (uncheck any false positives)")
            valid_dbs = []
            for i, db in enumerate(st.session_state.detected_dbs):
                if st.checkbox(db, value=True, key=f"sld_db_check_{i}"):
                    valid_dbs.append(db)

            # Add manual DB
            new_db = st.text_input("Add DB manually", placeholder="e.g., DB-GF, DB-S5")
            if st.button("+ Add DB") and new_db:
                if new_db not in valid_dbs:
                    valid_dbs.append(new_db)
                    st.session_state.detected_dbs = valid_dbs
                    st.rerun()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Upload", use_container_width=True):
                    st.session_state["sld_substep"] = "upload"
                    st.rerun()
            with col2:
                if st.button("Extract Supply Point", type="primary", use_container_width=True):
                    st.session_state.detected_dbs = valid_dbs
                    pipeline.apply_detected_dbs(valid_dbs)
                    st.session_state["sld_substep"] = "supply_point"
                    st.rerun()
        else:
            st.warning("No DBs detected. Add manually:")
            new_db = st.text_input("DB Name", placeholder="e.g., DB-GF, MSB, DB-S1")
            if st.button("Add DB") and new_db:
                st.session_state.detected_dbs = [new_db]
                st.rerun()
        return

    # SUBSTEP: Supply Point
    if substep == "supply_point":
        st.markdown("### Main Supply Point / Kiosk")

        if not st.session_state.supply_point:
            # Check if method exists (handles Streamlit Cloud caching issue)
            if not hasattr(pipeline, 'run_supply_point_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app' to reload latest code.")
                st.stop()
            with st.spinner("AI extracting supply point info..."):
                result = pipeline.run_supply_point_pass(st.session_state.sld_pages)
                if result.success:
                    st.session_state.supply_point = result.display_data
                else:
                    st.session_state.supply_point = {"supply_found": False}

        supply = st.session_state.supply_point
        confidence = 0.80 if supply.get("supply_found") else 0.3
        render_confidence_badge(confidence, "Supply Point")

        with st.form("supply_form"):
            col1, col2 = st.columns(2)
            with col1:
                supply_name = st.text_input("Supply Name", value=supply.get("name", "Kiosk Metering"))
                main_breaker = st.number_input("Main Breaker (A)", value=supply.get("main_breaker_a", 0))
            with col2:
                meter_type = st.selectbox("Meter Type", ["ct", "direct", "prepaid"],
                                          index=["ct", "direct", "prepaid"].index(supply.get("meter_type", "ct")) if supply.get("meter_type") in ["ct", "direct", "prepaid"] else 0)
                feeds_to = st.text_input("Feeds To", value=supply.get("feeds_to", ""))

            cable_spec = st.text_input("Main Cable Spec", value=supply.get("cable_spec", ""),
                                       placeholder="e.g., 95mm x 4C PVC SWA PVC")

            submitted = st.form_submit_button("Confirm & Extract DB Schedules", type="primary", use_container_width=True)
            if submitted:
                st.session_state.supply_point = {
                    "supply_found": True,
                    "name": supply_name,
                    "main_breaker_a": main_breaker,
                    "meter_type": meter_type,
                    "feeds_to": feeds_to,
                    "cable_spec": cable_spec,
                }
                st.session_state["sld_substep"] = "db_schedules"
                st.session_state.current_db_index = 0
                st.rerun()
        return

    # SUBSTEP: DB Schedules (loop)
    if substep == "db_schedules":
        detected_dbs = st.session_state.detected_dbs
        current_idx = st.session_state.current_db_index

        if current_idx >= len(detected_dbs):
            # All DBs done, move to cable routes
            pipeline.mark_db_schedules_complete()
            st.session_state["sld_substep"] = "cable_routes"
            st.rerun()
            return

        current_db = detected_dbs[current_idx]
        st.markdown(f"### DB Schedule: {current_db} ({current_idx + 1}/{len(detected_dbs)})")
        st.progress((current_idx + 1) / len(detected_dbs))

        # Extract if not done
        if current_db not in st.session_state.db_schedules:
            with st.spinner(f"AI extracting circuits from {current_db}..."):
                result = pipeline.run_db_schedule_pass(current_db, st.session_state.sld_pages)
                if result.success:
                    st.session_state.db_schedules[current_db] = result.display_data
                else:
                    st.session_state.db_schedules[current_db] = {
                        "db_name": current_db,
                        "main_breaker_a": 0,
                        "circuits": [],
                        "schedule_found": False,
                    }

        schedule = st.session_state.db_schedules.get(current_db, {})
        confidence = 0.75 if schedule.get("schedule_found") else 0.3
        render_confidence_badge(confidence, "Schedule")

        # Editable fields
        col1, col2, col3 = st.columns(3)
        with col1:
            main_breaker = st.number_input("Main Breaker (A)", value=schedule.get("main_breaker_a", 0), key=f"mb2_{current_db}")
        with col2:
            supply_from = st.text_input("Supply From", value=schedule.get("supply_from", ""), key=f"sf2_{current_db}")
        with col3:
            total_ways = st.number_input("Total Ways", value=schedule.get("total_ways", 0), key=f"tw2_{current_db}")

        # Circuits table
        st.markdown("##### Circuits")
        circuits = schedule.get("circuits", [])
        if circuits:
            import pandas as pd
            df = pd.DataFrame(circuits)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key=f"circuits2_{current_db}")
            circuits = edited_df.to_dict('records')
        else:
            st.info("No circuits extracted. Add manually or skip.")

        # Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Back", key="back_db2"):
                if current_idx > 0:
                    st.session_state.current_db_index -= 1
                else:
                    st.session_state["sld_substep"] = "supply_point"
                st.rerun()
        with col2:
            if st.button("Skip DB", key="skip_db2"):
                st.session_state.current_db_index += 1
                st.rerun()
        with col3:
            if st.button("Confirm & Next", type="primary", key="confirm_db2"):
                st.session_state.db_schedules[current_db] = {
                    "db_name": current_db,
                    "main_breaker_a": main_breaker,
                    "supply_from": supply_from,
                    "total_ways": total_ways,
                    "circuits": circuits,
                    "schedule_found": True,
                }
                pipeline.apply_db_schedule(current_db, st.session_state.db_schedules[current_db])
                st.session_state.current_db_index += 1
                st.rerun()
        return

    # SUBSTEP: Cable Routes
    if substep == "cable_routes":
        st.markdown("### Cable Routes Between DBs")

        if not st.session_state.cable_routes:
            with st.spinner("AI extracting cable routes..."):
                result = pipeline.run_cable_routes_pass(st.session_state.sld_pages)
                if result.success:
                    st.session_state.cable_routes = result.display_data.get("routes", [])

        routes = st.session_state.cable_routes
        if routes:
            st.success(f"{len(routes)} cable routes found")
            import pandas as pd
            df = pd.DataFrame(routes)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="cable_routes_editor")
            st.session_state.cable_routes = edited_df.to_dict('records')
        else:
            st.info("No cable routes extracted. You can add manually or continue.")
            # Manual add option
            with st.expander("Add Cable Route Manually"):
                col1, col2 = st.columns(2)
                with col1:
                    from_db = st.text_input("From", placeholder="e.g., Kiosk")
                    to_db = st.text_input("To", placeholder="e.g., DB-GF")
                with col2:
                    cable_spec = st.text_input("Cable Spec", placeholder="e.g., 4Cx35mm PVC SWA")
                    length_m = st.number_input("Length (m)", value=0)
                if st.button("Add Route"):
                    st.session_state.cable_routes.append({
                        "from": from_db, "to": to_db,
                        "cable_spec": cable_spec, "length_m": length_m
                    })
                    st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to DB Schedules", use_container_width=True):
                st.session_state["sld_substep"] = "db_schedules"
                st.session_state.current_db_index = len(st.session_state.detected_dbs) - 1
                st.rerun()
        with col2:
            if st.button("Continue to Lighting Layout", type="primary", use_container_width=True):
                pipeline.apply_cable_routes(st.session_state.cable_routes)
                st.session_state["sld_substep"] = "upload"  # Reset for next time
                st.session_state.guided_step = 3
                st.session_state.max_completed_step = max(2, st.session_state.max_completed_step)
                st.rerun()


# ============================================================================
# STEP 3: LIGHTING LAYOUT
# ============================================================================

def render_step_3_lighting():
    """Step 3: Upload lighting layout, extract legend first, then room fixtures."""
    is_local_mode = st.session_state.extraction_mode == "local"
    mode_label = "🖥️ Local Mode" if is_local_mode else "☁️ AI Mode"

    section_header("Step 3: Lighting Layout",
                   f"Extract lighting legend, then count fixtures per room ({mode_label})")

    substep = st.session_state.get("lighting_substep", "upload")
    pipeline = st.session_state.interactive_pipeline

    # SUBSTEP: Upload
    if substep == "upload":
        st.info("""
        **What to upload:** `03_Lighting_Layout.pdf`

        This document should contain:
        - Lighting legend (symbol → fixture type)
        - Floor plan with light fixtures
        - Room names/labels
        - Switch positions
        """)

        uploaded_file = st.file_uploader(
            "Upload Lighting Layout (PDF)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="lighting_uploader_v2"
        )

        if uploaded_file:
            with st.spinner("Processing lighting layout..."):
                # Store raw bytes for deterministic pipeline
                st.session_state.lighting_bytes = uploaded_file.getvalue()
                pages = process_uploaded_file(uploaded_file)
                if pages:
                    st.session_state.lighting_pages = pages
                    st.success(f"Lighting layout loaded ({len(pages)} page(s))")
                    show_page_thumbnails(pages, max_show=3)

        if st.session_state.lighting_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to SLD", use_container_width=True):
                    st.session_state.guided_step = 2
                    if is_local_mode:
                        st.session_state["sld_substep"] = "local_extract"
                    else:
                        st.session_state["sld_substep"] = "cable_routes"
                    st.rerun()
            with col2:
                button_label = "Extract (Local)" if is_local_mode else "Extract Lighting Legend"
                if st.button(button_label, type="primary", use_container_width=True):
                    if is_local_mode:
                        st.session_state["lighting_substep"] = "local_extract"
                    else:
                        st.session_state["lighting_substep"] = "legend"
                    st.rerun()
        return

    # SUBSTEP: Local extraction (deterministic)
    if substep == "local_extract":
        st.markdown("### Local Extraction (No AI)")
        render_deterministic_progress("EXTRACT", 0.6)

        if not st.session_state.lighting_legend.get("has_legend"):
            with st.spinner("Extracting lighting info using regex patterns..."):
                det_result = process_with_deterministic_pipeline(
                    st.session_state.lighting_bytes,
                    "lighting_layout.pdf"
                )
                if det_result and det_result.success:
                    # Extract lighting data from result
                    display = convert_deterministic_to_display(det_result)
                    st.session_state.detected_rooms = display.get("rooms", [])

                    # Build legend from extracted legend items
                    # Use page_results (List[PageExtractionResult]) which has layout_data
                    light_types = []
                    switch_types = []
                    for page_result in det_result.page_results:
                        if page_result.layout_data:
                            for item in page_result.layout_data.legend_items:
                                item_lower = item.lower()
                                if any(x in item_lower for x in ["light", "downlight", "led", "panel", "flood"]):
                                    light_types.append({"name": item, "symbol": "", "wattage_w": 0})
                                elif any(x in item_lower for x in ["switch", "lever"]):
                                    switch_types.append({"name": item, "symbol": ""})

                    st.session_state.lighting_legend = {
                        "has_legend": len(light_types) > 0,
                        "light_types": light_types,
                        "switch_types": switch_types,
                    }

                    if det_result.warnings:
                        for warn in det_result.warnings[:3]:
                            st.warning(f"⚠️ {warn.message}")

        legend = st.session_state.lighting_legend
        rooms = st.session_state.detected_rooms

        st.success(f"Extracted {len(legend.get('light_types', []))} light types, {len(rooms)} rooms")

        # Show legend
        if legend.get("light_types"):
            with st.expander("Light Types", expanded=True):
                import pandas as pd
                df = pd.DataFrame(legend["light_types"])
                st.dataframe(df, use_container_width=True)

        if legend.get("switch_types"):
            with st.expander("Switch Types", expanded=False):
                import pandas as pd
                df = pd.DataFrame(legend["switch_types"])
                st.dataframe(df, use_container_width=True)

        # Show rooms
        if rooms:
            st.markdown(f"**Detected Rooms:** {', '.join(rooms)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Upload", use_container_width=True):
                st.session_state["lighting_substep"] = "upload"
                st.rerun()
        with col2:
            if st.button("Continue to Power Layout", type="primary", use_container_width=True):
                st.session_state["lighting_substep"] = "upload"  # Reset
                st.session_state.guided_step = 4
                st.session_state.max_completed_step = max(3, st.session_state.max_completed_step)
                st.rerun()
        return

    # SUBSTEP: Legend extraction
    if substep == "legend":
        st.markdown("### Lighting Legend")
        st.caption("Extract fixture types BEFORE counting per room for higher accuracy")

        if not st.session_state.lighting_legend:
            if not hasattr(pipeline, 'run_lighting_legend_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()
            with st.spinner("AI extracting lighting legend (symbols, fixture types, wattages)..."):
                result = pipeline.run_lighting_legend_pass(st.session_state.lighting_pages)
                if result.success:
                    st.session_state.lighting_legend = result.display_data
                else:
                    st.session_state.lighting_legend = {"has_legend": False, "light_types": [], "switch_types": []}

        legend = st.session_state.lighting_legend
        confidence = 0.80 if legend.get("has_legend") else 0.3
        render_confidence_badge(confidence, "Legend")

        # Show and edit legend
        st.markdown("##### Light Types")
        light_types = legend.get("light_types", [])
        if light_types:
            import pandas as pd
            df = pd.DataFrame(light_types)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="light_types_editor")
            light_types = edited_df.to_dict('records')
        else:
            st.info("No light types found. Add manually if needed.")

        st.markdown("##### Switch Types")
        switch_types = legend.get("switch_types", [])
        if switch_types:
            import pandas as pd
            df = pd.DataFrame(switch_types)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="switch_types_editor")
            switch_types = edited_df.to_dict('records')

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Upload", use_container_width=True):
                st.session_state["lighting_substep"] = "upload"
                st.rerun()
        with col2:
            if st.button("Detect Rooms", type="primary", use_container_width=True):
                st.session_state.lighting_legend = {
                    "has_legend": True,
                    "light_types": light_types,
                    "switch_types": switch_types,
                }
                st.session_state["lighting_substep"] = "detect_rooms"
                st.rerun()
        return

    # SUBSTEP: Detect rooms
    if substep == "detect_rooms":
        st.markdown("### Detect Rooms from Lighting Layout")

        if not st.session_state.detected_rooms:
            with st.spinner("AI detecting rooms..."):
                result = pipeline.run_room_detection_pass(st.session_state.lighting_pages)
                if result.success:
                    rooms = result.display_data.get("rooms", [])
                    st.session_state.detected_rooms = [r["name"] for r in rooms]
                    pipeline.apply_detected_rooms(st.session_state.detected_rooms)

        if st.session_state.detected_rooms:
            st.success(f"Found {len(st.session_state.detected_rooms)} rooms")

            valid_rooms = []
            for i, room in enumerate(st.session_state.detected_rooms):
                if st.checkbox(room, value=True, key=f"ltg_room_check_{i}"):
                    valid_rooms.append(room)

            new_room = st.text_input("Add room manually", placeholder="e.g., SUITE 5, KITCHEN")
            if st.button("+ Add Room") and new_room:
                valid_rooms.append(new_room)
                st.session_state.detected_rooms = valid_rooms
                st.rerun()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Legend", use_container_width=True):
                    st.session_state["lighting_substep"] = "legend"
                    st.rerun()
            with col2:
                if st.button("Count Fixtures Per Room", type="primary", use_container_width=True):
                    st.session_state.detected_rooms = valid_rooms
                    pipeline.apply_detected_rooms(valid_rooms)
                    st.session_state["lighting_substep"] = "room_fixtures"
                    st.session_state.current_lighting_room_index = 0
                    st.rerun()
        else:
            st.warning("No rooms detected. Add manually:")
            new_room = st.text_input("Room Name", placeholder="e.g., SUITE 1, OFFICE")
            if st.button("Add Room") and new_room:
                st.session_state.detected_rooms = [new_room]
                st.rerun()
        return

    # SUBSTEP: Room fixtures (loop using legend)
    if substep == "room_fixtures":
        rooms = st.session_state.detected_rooms
        current_idx = st.session_state.current_lighting_room_index

        if current_idx >= len(rooms):
            pipeline.mark_room_fixtures_complete()
            st.session_state["lighting_substep"] = "upload"
            st.session_state.guided_step = 4
            st.session_state.max_completed_step = max(3, st.session_state.max_completed_step)
            st.rerun()
            return

        current_room = rooms[current_idx]
        st.markdown(f"### Lighting: {current_room} ({current_idx + 1}/{len(rooms)})")
        st.progress((current_idx + 1) / len(rooms))

        # Extract using legend
        if current_room not in st.session_state.room_lighting:
            if not hasattr(pipeline, 'run_room_fixtures_with_legend_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()
            with st.spinner(f"AI counting lights in {current_room} using legend..."):
                result = pipeline.run_room_fixtures_with_legend_pass(
                    current_room,
                    st.session_state.lighting_pages,
                    st.session_state.lighting_legend
                )
                if result.success:
                    raw_fixtures = result.display_data.get("fixtures", {})
                    # Normalize keys to standard format
                    st.session_state.room_lighting[current_room] = normalize_fixture_data(raw_fixtures)
                else:
                    st.session_state.room_lighting[current_room] = {}

        fixtures = st.session_state.room_lighting.get(current_room, {})
        confidence = 0.70 if fixtures else 0.3
        render_confidence_badge(confidence, "Fixtures")

        # Editable based on legend types
        legend = st.session_state.lighting_legend
        light_types = legend.get("light_types", [])

        st.markdown("##### Light Fixtures")
        light_counts = {}
        cols = st.columns(3)
        for i, lt in enumerate(light_types[:9]):
            name = lt.get("name", f"Light {i+1}")
            std_key = map_fixture_to_standard_key(name)  # Map to standard key
            with cols[i % 3]:
                light_counts[std_key] = st.number_input(
                    name,
                    value=fixtures.get(std_key, 0),
                    min_value=0,
                    key=f"ltg_light_{current_room}_{i}"
                )

        st.markdown("##### Switches")
        switch_types = legend.get("switch_types", [])
        switch_counts = {}
        cols = st.columns(3)
        for i, sw in enumerate(switch_types[:6]):
            name = sw.get("name", f"Switch {i+1}")
            std_key = map_fixture_to_standard_key(name)  # Map to standard key
            with cols[i % 3]:
                switch_counts[std_key] = st.number_input(
                    name,
                    value=fixtures.get(std_key, 0),
                    min_value=0,
                    key=f"ltg_sw_{current_room}_{i}"
                )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Back", key="back_lt_room"):
                if current_idx > 0:
                    st.session_state.current_lighting_room_index -= 1
                else:
                    st.session_state["lighting_substep"] = "detect_rooms"
                st.rerun()
        with col2:
            if st.button("Skip Room", key="skip_lt_room"):
                st.session_state.current_lighting_room_index += 1
                st.rerun()
        with col3:
            if st.button("Confirm & Next", type="primary", key="confirm_lt_room"):
                all_fixtures = {**light_counts, **switch_counts}
                st.session_state.room_lighting[current_room] = all_fixtures
                pipeline.apply_room_fixtures(current_room, all_fixtures)
                st.session_state.current_lighting_room_index += 1
                st.rerun()


# ============================================================================
# STEP 4: POWER LAYOUT
# ============================================================================

def render_step_4_power():
    """Step 4: Upload power layout, extract legend, then room sockets."""
    is_local_mode = st.session_state.extraction_mode == "local"
    mode_label = "🖥️ Local Mode" if is_local_mode else "☁️ AI Mode"

    section_header("Step 4: Power Layout",
                   f"Extract power legend, then count sockets per room ({mode_label})")

    substep = st.session_state.get("power_substep", "upload")
    pipeline = st.session_state.interactive_pipeline

    # SUBSTEP: Upload
    if substep == "upload":
        st.info("""
        **What to upload:** `04_Power_Layout.pdf`

        This document should contain:
        - Power legend (sockets, data points, isolators)
        - Floor plan with socket positions
        - Equipment connections (A/C, etc.)
        """)

        uploaded_file = st.file_uploader(
            "Upload Power Layout (PDF)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="power_uploader_v2"
        )

        if uploaded_file:
            with st.spinner("Processing power layout..."):
                # Store raw bytes for deterministic pipeline
                st.session_state.power_bytes = uploaded_file.getvalue()
                pages = process_uploaded_file(uploaded_file)
                if pages:
                    st.session_state.power_pages = pages
                    st.success(f"Power layout loaded ({len(pages)} page(s))")
                    show_page_thumbnails(pages, max_show=3)

        if st.session_state.power_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Lighting", use_container_width=True):
                    st.session_state.guided_step = 3
                    if is_local_mode:
                        st.session_state["lighting_substep"] = "local_extract"
                    else:
                        st.session_state["lighting_substep"] = "room_fixtures"
                        st.session_state.current_lighting_room_index = len(st.session_state.detected_rooms) - 1
                    st.rerun()
            with col2:
                button_label = "Extract (Local)" if is_local_mode else "Extract Power Legend"
                if st.button(button_label, type="primary", use_container_width=True):
                    if is_local_mode:
                        st.session_state["power_substep"] = "local_extract"
                    else:
                        st.session_state["power_substep"] = "legend"
                    st.rerun()
        return

    # SUBSTEP: Local extraction (deterministic)
    if substep == "local_extract":
        st.markdown("### Local Extraction (No AI)")
        render_deterministic_progress("EXTRACT", 0.6)

        if not st.session_state.power_legend.get("has_legend"):
            with st.spinner("Extracting power info using regex patterns..."):
                det_result = process_with_deterministic_pipeline(
                    st.session_state.power_bytes,
                    "power_layout.pdf"
                )
                if det_result and det_result.success:
                    # Extract power data from result
                    # Use page_results (List[PageExtractionResult]) which has layout_data
                    socket_types = []
                    isolator_types = []
                    for page_result in det_result.page_results:
                        if page_result.layout_data:
                            for item in page_result.layout_data.legend_items:
                                item_lower = item.lower()
                                if any(x in item_lower for x in ["socket", "plug", "outlet", "data", "cat"]):
                                    socket_types.append({"name": item, "symbol": "", "height_mm": 300})
                                elif any(x in item_lower for x in ["isolator", "iso"]):
                                    isolator_types.append({"name": item, "symbol": ""})

                    st.session_state.power_legend = {
                        "has_legend": len(socket_types) > 0,
                        "socket_types": socket_types,
                        "isolator_types": isolator_types,
                    }

                    if det_result.warnings:
                        for warn in det_result.warnings[:3]:
                            st.warning(f"⚠️ {warn.message}")

        legend = st.session_state.power_legend
        st.success(f"Extracted {len(legend.get('socket_types', []))} socket types, {len(legend.get('isolator_types', []))} isolator types")

        # Show legend
        if legend.get("socket_types"):
            with st.expander("Socket Types", expanded=True):
                import pandas as pd
                df = pd.DataFrame(legend["socket_types"])
                st.dataframe(df, use_container_width=True)

        if legend.get("isolator_types"):
            with st.expander("Isolator Types", expanded=False):
                import pandas as pd
                df = pd.DataFrame(legend["isolator_types"])
                st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Upload", use_container_width=True):
                st.session_state["power_substep"] = "upload"
                st.rerun()
        with col2:
            if st.button("Review & Export", type="primary", use_container_width=True):
                st.session_state["power_substep"] = "upload"  # Reset
                st.session_state.guided_step = 5
                st.session_state.max_completed_step = max(4, st.session_state.max_completed_step)
                st.rerun()
        return

    # SUBSTEP: Power legend
    if substep == "legend":
        st.markdown("### Power Legend")

        if not st.session_state.power_legend:
            if not hasattr(pipeline, 'run_power_legend_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()
            with st.spinner("AI extracting power legend (sockets, data, isolators)..."):
                result = pipeline.run_power_legend_pass(st.session_state.power_pages)
                if result.success:
                    st.session_state.power_legend = result.display_data
                else:
                    st.session_state.power_legend = {"has_legend": False, "socket_types": [], "isolator_types": []}

        legend = st.session_state.power_legend
        confidence = 0.80 if legend.get("has_legend") else 0.3
        render_confidence_badge(confidence, "Legend")

        st.markdown("##### Socket Types")
        socket_types = legend.get("socket_types", [])
        if socket_types:
            import pandas as pd
            df = pd.DataFrame(socket_types)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="socket_types_editor")
            socket_types = edited_df.to_dict('records')

        st.markdown("##### Isolator Types")
        isolator_types = legend.get("isolator_types", [])
        if isolator_types:
            import pandas as pd
            df = pd.DataFrame(isolator_types)
            edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="isolator_types_editor")
            isolator_types = edited_df.to_dict('records')

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Upload", use_container_width=True):
                st.session_state["power_substep"] = "upload"
                st.rerun()
        with col2:
            if st.button("Count Sockets Per Room", type="primary", use_container_width=True):
                st.session_state.power_legend = {
                    "has_legend": True,
                    "socket_types": socket_types,
                    "isolator_types": isolator_types,
                }
                st.session_state["power_substep"] = "room_sockets"
                st.session_state.current_power_room_index = 0
                st.rerun()
        return

    # SUBSTEP: Room sockets (loop - reuse rooms from lighting)
    if substep == "room_sockets":
        rooms = st.session_state.detected_rooms  # Reuse from Step 3
        current_idx = st.session_state.current_power_room_index

        if not rooms:
            st.warning("No rooms detected. Go back to Lighting Layout to detect rooms.")
            if st.button("Back to Lighting"):
                st.session_state.guided_step = 3
                st.rerun()
            return

        if current_idx >= len(rooms):
            st.session_state["power_substep"] = "upload"
            st.session_state.guided_step = 5
            st.session_state.max_completed_step = max(4, st.session_state.max_completed_step)
            st.rerun()
            return

        current_room = rooms[current_idx]
        st.markdown(f"### Power: {current_room} ({current_idx + 1}/{len(rooms)})")
        st.progress((current_idx + 1) / len(rooms))

        # Extract using legend
        if current_room not in st.session_state.room_power:
            if not hasattr(pipeline, 'run_room_fixtures_with_legend_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()
            with st.spinner(f"AI counting sockets in {current_room} using legend..."):
                result = pipeline.run_room_fixtures_with_legend_pass(
                    current_room,
                    st.session_state.power_pages,
                    st.session_state.power_legend
                )
                if result.success:
                    raw_fixtures = result.display_data.get("fixtures", {})
                    # Normalize keys to standard format
                    st.session_state.room_power[current_room] = normalize_fixture_data(raw_fixtures)
                else:
                    st.session_state.room_power[current_room] = {}

        fixtures = st.session_state.room_power.get(current_room, {})
        confidence = 0.70 if fixtures else 0.3
        render_confidence_badge(confidence, "Sockets")

        # Editable based on power legend
        legend = st.session_state.power_legend
        socket_types = legend.get("socket_types", [])

        st.markdown("##### Sockets & Data Points")
        socket_counts = {}
        cols = st.columns(3)
        for i, st_type in enumerate(socket_types[:9]):
            name = st_type.get("name", f"Socket {i+1}")
            std_key = map_fixture_to_standard_key(name)  # Map to standard key
            with cols[i % 3]:
                socket_counts[std_key] = st.number_input(
                    name,
                    value=fixtures.get(std_key, 0),
                    min_value=0,
                    key=f"pwr_sock_{current_room}_{i}"
                )

        st.markdown("##### Isolators & Equipment")
        isolator_types = legend.get("isolator_types", [])
        iso_counts = {}
        cols = st.columns(3)
        for i, iso in enumerate(isolator_types[:6]):
            name = iso.get("name", f"Isolator {i+1}")
            std_key = map_fixture_to_standard_key(name)  # Map to standard key
            with cols[i % 3]:
                iso_counts[std_key] = st.number_input(
                    name,
                    value=fixtures.get(std_key, 0),
                    min_value=0,
                    key=f"pwr_iso_{current_room}_{i}"
                )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Back", key="back_pwr_room"):
                if current_idx > 0:
                    st.session_state.current_power_room_index -= 1
                else:
                    st.session_state["power_substep"] = "legend"
                st.rerun()
        with col2:
            if st.button("Skip Room", key="skip_pwr_room"):
                st.session_state.current_power_room_index += 1
                st.rerun()
        with col3:
            if st.button("Confirm & Next", type="primary", key="confirm_pwr_room"):
                all_fixtures = {**socket_counts, **iso_counts}
                st.session_state.room_power[current_room] = all_fixtures
                pipeline.apply_room_fixtures(current_room, all_fixtures)
                st.session_state.current_power_room_index += 1
                st.rerun()


# ============================================================================
# STEP 5: REVIEW & EXPORT
# ============================================================================

def render_step_5_review():
    """Step 5: Final review and BOQ export."""
    is_local_mode = st.session_state.extraction_mode == "local"
    mode_label = "🖥️ Local Mode" if is_local_mode else "☁️ AI Mode"

    section_header("Step 5: Review & Export",
                   f"Validate extraction and download BOQ ({mode_label})")

    pipeline = st.session_state.interactive_pipeline

    # Build final result based on mode
    if st.session_state.final_extraction is None:
        with st.spinner("Building final BOQ..."):
            if is_local_mode:
                # LOCAL MODE: Build result from deterministic pipeline data
                render_deterministic_progress("MERGE", 1.0)

                # Combine all deterministic results
                all_bytes = []
                if st.session_state.cover_bytes:
                    all_bytes.append((st.session_state.cover_bytes, "cover.pdf"))
                if st.session_state.sld_bytes:
                    all_bytes.append((st.session_state.sld_bytes, "sld.pdf"))
                if st.session_state.lighting_bytes:
                    all_bytes.append((st.session_state.lighting_bytes, "lighting.pdf"))
                if st.session_state.power_bytes:
                    all_bytes.append((st.session_state.power_bytes, "power.pdf"))

                # Run combined extraction
                if all_bytes:
                    combined_result = None
                    for file_bytes, filename in all_bytes:
                        result = process_with_deterministic_pipeline(file_bytes, filename)
                        if result and result.success:
                            if combined_result is None:
                                combined_result = result
                            else:
                                # Merge pages from each result
                                combined_result.pages.extend(result.pages)

                    if combined_result and combined_result.project_result:
                        # Build ExtractionResult from deterministic data
                        from agent.models import ExtractionResult, DistributionBoard, Circuit, Room, FixtureCounts

                        project = combined_result.project_result
                        dbs = []
                        rooms = []

                        # Convert SLD data to ExtractionResult format
                        # project.sld_pages is List[SLDExtraction] directly
                        for sld in project.sld_pages:
                            circuits = []
                            for c in sld.circuits:
                                circuits.append(Circuit(
                                    circuit_id=c.circuit_id,
                                    description=c.description,
                                    breaker_a=c.breaker_a or 10,
                                    wire_size_mm2=c.wire_size_mm2 or "1.5",
                                    points=c.num_points or 0,
                                ))
                            dbs.append(DistributionBoard(
                                name=sld.db_name or "DB",
                                main_breaker_a=sld.main_breaker_a or 100,
                                total_ways=sld.total_ways or 12,
                                circuits=circuits,
                            ))

                        # Convert layout data to rooms
                        # project.lighting_pages/plugs_pages are List[LayoutExtraction] directly
                        room_names = set()
                        for layout in project.lighting_pages + project.plugs_pages:
                            room_names.update(layout.room_labels)

                        for room_name in room_names:
                            rooms.append(Room(
                                name=room_name,
                                fixtures=FixtureCounts(),  # Default counts
                            ))

                        st.session_state.final_extraction = ExtractionResult(
                            project_name=project.project_name or st.session_state.project_info.get("project_name", "Project"),
                            client_name=project.client_name or st.session_state.project_info.get("client_name", ""),
                            distribution_boards=dbs,
                            rooms=rooms,
                        )
                    else:
                        # Fallback: Build from session state
                        st.session_state.final_extraction = build_extraction_from_session_state()
                else:
                    st.session_state.final_extraction = build_extraction_from_session_state()

                # Validate and price
                try:
                    validation, _ = validate(st.session_state.final_extraction)
                    st.session_state.final_validation = validation
                    pricing, _ = price(st.session_state.final_extraction, validation, None, None)
                    st.session_state.final_pricing = pricing
                except Exception as e:
                    st.warning(f"Validation/pricing error: {e}")
                    st.session_state.final_validation = None
                    st.session_state.final_pricing = None
            else:
                # AI MODE: Use interactive pipeline
                st.session_state.final_extraction = pipeline.build_final_result()
                validation, _ = validate(st.session_state.final_extraction)
                st.session_state.final_validation = validation
                pricing, _ = price(st.session_state.final_extraction, validation, None, None)
                st.session_state.final_pricing = pricing

    extraction = st.session_state.final_extraction
    validation = st.session_state.final_validation
    pricing = st.session_state.final_pricing

    # Get statistics based on mode
    if is_local_mode:
        stats = {
            "db_schedules_extracted": len(st.session_state.db_schedules),
            "rooms_detected": len(st.session_state.detected_rooms),
        }
    else:
        stats = pipeline.get_statistics() if pipeline else {}

    # Calculate accuracy score
    db_count = stats.get("db_schedules_extracted", 0)
    total_circuits = sum(len(s.get("circuits", [])) for s in st.session_state.db_schedules.values())
    room_count = len(st.session_state.detected_rooms)
    cable_count = len(st.session_state.cable_routes)

    # Count total fixtures extracted
    total_lights = sum(sum(f.values()) for f in st.session_state.room_lighting.values() if isinstance(f, dict))
    total_sockets = sum(sum(f.values()) for f in st.session_state.room_power.values() if isinstance(f, dict))

    # Accuracy scoring (weighted)
    # - DBs: 20% weight (target: 10 DBs for commercial)
    # - Circuits: 20% weight (target: 50+ circuits)
    # - Rooms: 20% weight (target: 15 rooms)
    # - Cable routes: 15% weight (target: 10 routes)
    # - Fixtures: 25% weight (target: 100+ total)
    db_score = min(100, (db_count / 10) * 100)
    circuit_score = min(100, (total_circuits / 50) * 100)
    room_score = min(100, (room_count / 15) * 100)
    cable_score = min(100, (cable_count / 10) * 100)
    fixture_score = min(100, ((total_lights + total_sockets) / 100) * 100)

    accuracy = (db_score * 0.20 + circuit_score * 0.20 + room_score * 0.20 +
                cable_score * 0.15 + fixture_score * 0.25)

    # Success banner with accuracy
    if accuracy >= 75:
        st.success(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Target achieved!")
    elif accuracy >= 60:
        st.warning(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Below 75% target")
    else:
        st.error(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Needs improvement")

    # Summary metrics
    st.markdown("### Extraction Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("DBs", db_count, help="Distribution boards detected")
    with col2:
        st.metric("Circuits", total_circuits, help="Total circuits across all DBs")
    with col3:
        st.metric("Rooms", room_count, help="Rooms detected from layouts")
    with col4:
        st.metric("Cable Routes", cable_count, help="Sub-main cables between DBs")
    with col5:
        st.metric("Accuracy", f"{accuracy:.0f}%", help="Weighted extraction accuracy")

    # Document coverage
    st.markdown("### Document Coverage")
    doc_status = [
        ("Cover Page", bool(st.session_state.cover_pages), bool(st.session_state.project_info.get("project_name"))),
        ("SLD/Schedules", bool(st.session_state.sld_pages), bool(st.session_state.db_schedules)),
        ("Lighting Layout", bool(st.session_state.lighting_pages), bool(st.session_state.lighting_legend.get("has_legend"))),
        ("Power Layout", bool(st.session_state.power_pages), bool(st.session_state.power_legend.get("has_legend"))),
    ]

    for doc_name, uploaded, extracted in doc_status:
        if uploaded and extracted:
            st.markdown(f"- :green[{doc_name}] - Uploaded & Extracted")
        elif uploaded:
            st.markdown(f"- :orange[{doc_name}] - Uploaded (partial extraction)")
        else:
            st.markdown(f"- :red[{doc_name}] - Not uploaded")

    # Accuracy breakdown
    st.markdown("### Accuracy Breakdown")
    with st.expander("View detailed scoring", expanded=False):
        st.markdown(f"""
        | Component | Extracted | Target | Score |
        |-----------|-----------|--------|-------|
        | Distribution Boards | {db_count} | 10 | {db_score:.0f}% |
        | Circuits | {total_circuits} | 50 | {circuit_score:.0f}% |
        | Rooms | {room_count} | 15 | {room_score:.0f}% |
        | Cable Routes | {cable_count} | 10 | {cable_score:.0f}% |
        | Fixtures (lights + sockets) | {total_lights + total_sockets} | 100 | {fixture_score:.0f}% |
        | **Weighted Total** | | | **{accuracy:.0f}%** |

        **Weights:** DBs 20%, Circuits 20%, Rooms 20%, Cables 15%, Fixtures 25%
        """)

        # Critique / improvement suggestions
        st.markdown("#### Areas for Improvement")
        issues = []
        if db_count < 8:
            issues.append("- **DBs:** Some distribution boards may be missing (check for DB-GF, DB-CA variations)")
        if total_circuits < 40:
            issues.append("- **Circuits:** Circuit schedules may be incomplete - review SLD pages manually")
        if total_lights + total_sockets < 50:
            issues.append("- **Fixtures:** Low fixture count - legend extraction or room counting may need improvement")
        if cable_count < 5:
            issues.append("- **Cables:** Sub-main cable routes not fully extracted from SLD")

        if issues:
            for issue in issues:
                st.markdown(issue)
        else:
            st.success("Extraction looks comprehensive!")

    # Compliance score
    if validation:
        st.markdown("### SANS 10142-1 Compliance")
        score = validation.compliance_score
        if score >= 70:
            st.success(f"Score: {score:.0f}%")
        elif score >= 40:
            st.warning(f"Score: {score:.0f}%")
        else:
            st.error(f"Score: {score:.0f}%")

    # Export buttons
    st.markdown("### Export")
    col1, col2 = st.columns(2)

    with col1:
        if HAS_OPENPYXL and pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:50]
                excel_bytes = export_professional_bq(pricing, extraction, project_name)
                st.download_button(
                    "Download Excel BOQ",
                    data=excel_bytes,
                    file_name=f"{safe_name}_BOQ.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Excel export error: {e}")
        else:
            st.info("Excel export not available")

    with col2:
        if pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:50]
                pdf_bytes = generate_pdf_summary(pricing, extraction, validation, project_name, ServiceTier.COMMERCIAL)
                st.download_button(
                    "Download PDF Summary",
                    data=pdf_bytes,
                    file_name=f"{safe_name}_Summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF export error: {e}")

    # Start over
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Power Layout", use_container_width=True):
            st.session_state.guided_step = 4
            st.session_state.final_extraction = None
            st.session_state.final_validation = None
            st.session_state.final_pricing = None
            st.rerun()
    with col2:
        if st.button("Start New Extraction", type="secondary", use_container_width=True):
            # Clear all session state
            keys_to_clear = [
                "guided_step", "max_completed_step",
                "cover_pages", "sld_pages", "lighting_pages", "power_pages",
                "cover_bytes", "sld_bytes", "lighting_bytes", "power_bytes",
                "combined_bytes", "quick_upload_result",
                "interactive_pipeline", "deterministic_pipeline", "deterministic_result",
                "project_info",
                "supply_point", "detected_dbs", "db_schedules", "cable_routes",
                "current_db_index", "lighting_legend", "detected_rooms",
                "room_lighting", "current_lighting_room_index",
                "power_legend", "room_power", "current_power_room_index",
                "final_extraction", "final_validation", "final_pricing",
                "sld_substep", "lighting_substep", "power_substep",
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# ============================================================================
# MAIN PAGE
# ============================================================================

inject_custom_css()
init_session_state()

page_header(
    title="Guided Upload v2.1",
    subtitle="4-step document flow | AI or Local extraction | 75%+ accuracy target"
)

# Check if at least one pipeline is available
if not PIPELINE_AVAILABLE and not DETERMINISTIC_AVAILABLE:
    st.error("No extraction pipeline available")
    st.stop()

# Sidebar: Extraction Mode Selection
st.sidebar.markdown("### 🔧 Extraction Mode")

mode_options = []
mode_labels = {}

if DETERMINISTIC_AVAILABLE:
    mode_options.append("local")
    mode_labels["local"] = "🖥️ Local (No AI)"

if PIPELINE_AVAILABLE and LLM_API_KEY:
    mode_options.append("ai")
    mode_labels["ai"] = "☁️ AI-Based"

if not mode_options:
    st.error("No extraction mode available. Configure API keys or check installation.")
    st.stop()

# Mode selection radio
selected_mode = st.sidebar.radio(
    "Choose extraction method:",
    options=mode_options,
    format_func=lambda x: mode_labels.get(x, x),
    key="extraction_mode_radio",
    help="**Local:** Fast, free, works offline using regex/keywords. **AI:** Higher accuracy using vision models."
)

# Update session state if mode changed
if selected_mode != st.session_state.extraction_mode:
    st.session_state.extraction_mode = selected_mode
    # Reset results when mode changes
    st.session_state.final_extraction = None
    st.session_state.final_validation = None
    st.session_state.final_pricing = None
    st.session_state.deterministic_result = None

# Show mode-specific info and upload mode option
if st.session_state.extraction_mode == "local":
    st.sidebar.info("""
    **Local Mode (No AI)**

    ✅ Free - No API costs
    ✅ Fast - No network latency
    ✅ Private - Data stays local
    ✅ Offline - Works without internet

    **Method:** Regex, keywords, OpenCV
    """)

    # Upload mode selection (only for local mode)
    st.sidebar.markdown("### 📤 Upload Mode")
    upload_mode = st.sidebar.radio(
        "Choose upload style:",
        options=["quick", "guided"],
        format_func=lambda x: "⚡ Quick Upload (Single PDF)" if x == "quick" else "📝 4-Step Guided",
        key="upload_mode_radio",
        help="**Quick:** Upload one combined PDF, auto-split. **Guided:** Upload 4 separate documents."
    )

    if upload_mode != st.session_state.upload_mode:
        st.session_state.upload_mode = upload_mode
        # Reset state when changing upload mode
        st.session_state.quick_upload_result = None
        st.session_state.combined_bytes = None
else:
    # AI mode - only guided upload available
    st.session_state.upload_mode = "guided"

    st.sidebar.markdown("### AI Provider")
    provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
    st.sidebar.success(f"{provider_name} ({provider_cost})")

    st.sidebar.info("""
    **AI Mode (Cloud)**

    ✅ Higher accuracy
    ✅ Better at complex layouts
    ✅ Understands context
    ⚠️ Requires API key
    """)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**4-Step Document Flow:**

1. **Cover Page** → Project info
2. **SLD + Schedules** → DBs, circuits, cables
3. **Lighting Layout** → Legend → Fixtures
4. **Power Layout** → Legend → Sockets

**Key Improvement:** Extract legends BEFORE counting fixtures for higher accuracy.
""")

# Render based on upload mode
if st.session_state.upload_mode == "quick" and st.session_state.extraction_mode == "local":
    # Quick Upload mode - single PDF, automatic processing
    render_quick_upload()
else:
    # Guided 4-step upload mode
    render_progress_indicator()

    step = st.session_state.guided_step

    if step == 1:
        render_step_1_cover()
    elif step == 2:
        render_step_2_sld()
    elif step == 3:
        render_step_3_lighting()
    elif step == 4:
        render_step_4_power()
    elif step == 5:
        render_step_5_review()
