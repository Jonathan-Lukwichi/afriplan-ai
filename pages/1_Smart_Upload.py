"""
AfriPlan Electrical v1.0 - Smart Upload (Primary Mode)

AI-powered extraction using Claude/Groq/Gemini/Grok vision models.
Circuit-Cluster-First architecture for accurate BOQ extraction.

Document Flow:
1. Cover Page / Drawing Register → Project info
2. SLD / Circuit Schedules → DBs, supply point, circuits, cables
3. Lighting Layout → Legend first → Circuit clusters (e.g., "DB-S3 L2")
4. Power Layout → Legend first → Circuit clusters (e.g., "DB-S1 P1")
5. Review → SLD vs Layout reconciliation with match rate

Key Features:
- Circuit-cluster-first extraction (aligns with how contractors quote)
- Human-in-the-loop validation at each step
- Type-specific point counting (lights, sockets, dedicated)
- Direct SLD reconciliation with match rate scoring

Target: 75%+ extraction accuracy through circuit-label alignment.
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

# Import benchmark validation module
BENCHMARK_AVAILABLE = False
try:
    from benchmark import (
        validate_extraction_against_benchmark,
        render_benchmark_results,
        convert_extraction_for_validation,
        identify_project,
    )
    BENCHMARK_AVAILABLE = True
except ImportError:
    pass


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
    """Initialize all session state variables for v7.0 circuit-cluster-first flow."""
    defaults = {
        # Navigation (5 steps: 4 uploads + 1 review)
        "guided_step": 1,
        "max_completed_step": 0,

        # Document pages by type (4 separate documents)
        "cover_pages": [],
        "sld_pages": [],
        "lighting_pages": [],
        "power_pages": [],

        # Skip tracking (for upload summary)
        "step_1_skipped": False,
        "step_2_skipped": False,
        "step_3_skipped": False,
        "step_4_skipped": False,

        # Pipeline instance (AI-based)
        "interactive_pipeline": None,

        # Step 1: Project Info
        "project_info": {},

        # Step 2: SLD Extraction
        "supply_point": {},
        "detected_dbs": [],
        "db_schedules": {},
        "cable_routes": [],
        "current_db_index": 0,

        # Step 3: Lighting (v7.0 - circuit clusters)
        "lighting_legend": {},
        "detected_rooms": [],       # Secondary - populated from clusters
        "lighting_circuit_clusters": [],  # v7.0 - PRIMARY extraction unit
        "room_lighting": {},        # DEPRECATED - kept for compatibility

        # Step 4: Power (v7.0 - circuit clusters)
        "power_legend": {},
        "power_circuit_clusters": [],     # v7.0 - PRIMARY extraction unit
        "room_power": {},           # DEPRECATED - kept for compatibility

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


def reconcile_sld_with_clusters(db_schedules: dict, layout_clusters: list) -> dict:
    """
    v7.0 SLD Reconciliation: Compare SLD circuit points vs Layout circuit cluster points.

    For each circuit in the SLD schedule, find the matching layout cluster and compare:
    - Lighting circuits: SLD num_points vs cluster total_points (lights only)
    - Power circuits: SLD num_points vs cluster total_points (sockets only)
    - Dedicated (AC, geyser): Both should be 1 point

    Returns:
        {
            "match_rate": 0.0-1.0,
            "matched": int,
            "total_compared": int,
            "by_db": {
                "DB-S3": {
                    "total_circuits": int,
                    "match_count": int,
                    "is_balanced": bool,
                    "circuits": {
                        "L1": {"sld_points": 10, "layout_points": 8, "matched": False, "circuit_type": "lighting"},
                        ...
                    },
                    "discrepancies": ["L1: SLD=10 vs Layout=8", ...]
                }
            }
        }
    """
    from collections import defaultdict

    result = {
        "match_rate": 0.0,
        "matched": 0,
        "total_compared": 0,
        "by_db": {}
    }

    if not db_schedules or not layout_clusters:
        return result

    # Index layout clusters by (db_name, circuit_id)
    cluster_index = {}
    for cluster in layout_clusters:
        key = (cluster.get("db_name", ""), cluster.get("circuit_id", ""))
        if key[0] and key[1]:
            cluster_index[key] = cluster

    # Compare each SLD circuit to its matching layout cluster
    total_compared = 0
    matched = 0

    for db_name, schedule in db_schedules.items():
        db_result = {
            "total_circuits": 0,
            "match_count": 0,
            "is_balanced": True,
            "circuits": {},
            "discrepancies": []
        }

        circuits = schedule.get("circuits", [])
        for circuit in circuits:
            circuit_id = circuit.get("circuit_id", "")
            if not circuit_id:
                continue

            # Skip spare circuits
            circuit_type = circuit.get("circuit_type", "").lower()
            if "spare" in circuit_type or "spare" in circuit_id.lower():
                continue

            db_result["total_circuits"] += 1
            total_compared += 1

            # Get SLD num_points
            sld_points = circuit.get("num_points", 0)
            if isinstance(sld_points, dict):
                sld_points = sld_points.get("value", 0)
            sld_points = int(sld_points) if sld_points else 0

            # Look up matching layout cluster
            lookup_key = (db_name, circuit_id)
            cluster = cluster_index.get(lookup_key)

            if cluster:
                layout_points = cluster.get("total_points", 0)

                # Determine if matched (exact or within tolerance)
                # Allow ±1 point tolerance for minor counting differences
                is_match = abs(sld_points - layout_points) <= 1

                db_result["circuits"][circuit_id] = {
                    "sld_points": sld_points,
                    "layout_points": layout_points,
                    "matched": is_match,
                    "circuit_type": circuit_type
                }

                if is_match:
                    matched += 1
                    db_result["match_count"] += 1
                else:
                    db_result["is_balanced"] = False
                    db_result["discrepancies"].append(
                        f"{circuit_id}: SLD={sld_points} vs Layout={layout_points}"
                    )
            else:
                # No matching cluster found
                db_result["circuits"][circuit_id] = {
                    "sld_points": sld_points,
                    "layout_points": "-",
                    "matched": False,
                    "circuit_type": circuit_type
                }
                db_result["is_balanced"] = False
                db_result["discrepancies"].append(
                    f"{circuit_id}: No matching cluster found in layout"
                )

        result["by_db"][db_name] = db_result

    result["total_compared"] = total_compared
    result["matched"] = matched
    result["match_rate"] = matched / max(1, total_compared)

    return result


# ============================================================================
# STEP 1: COVER PAGE / DRAWING REGISTER
# ============================================================================
# STEP 1: COVER PAGE / DRAWING REGISTER
# ============================================================================

def render_step_1_cover():
    """Step 1: Upload cover page and extract project info."""
    section_header("Step 1: Cover Page / Drawing Register",
                   "Upload the cover page to extract project information")

    st.info("""
    **What to upload:** `01_Cover_Page_Drawing_Register.pdf`

    This document should contain:
    - Project name and description
    - Client name
    - Consultant/Engineer name
    - Drawing register (list of drawings)
    - Date and revision info
    """)

    # File upload - supports multiple files
    uploaded_files = st.file_uploader(
        "Upload Cover Page(s) (PDF or Image) - You can select multiple files",
        type=["pdf", "png", "jpg", "jpeg"],
        key="cover_uploader_v3",
        accept_multiple_files=True
    )

    if uploaded_files:
        all_pages = []
        with st.spinner(f"Processing {len(uploaded_files)} file(s)..."):
            for uploaded_file in uploaded_files:
                pages = process_uploaded_file(uploaded_file)
                if pages:
                    all_pages.extend(pages)
            if all_pages:
                st.session_state.cover_pages = all_pages
                st.success(f"Cover page loaded ({len(all_pages)} page(s) from {len(uploaded_files)} file(s))")
                show_page_thumbnails(all_pages, max_show=2)

    # Skip button
    col_skip, col_spacer = st.columns([1, 3])
    with col_skip:
        if st.button("Skip this step →", key="skip_step_1", help="Skip if you don't have a cover page"):
            st.session_state.guided_step = 2
            st.session_state.max_completed_step = max(1, st.session_state.max_completed_step)
            st.session_state["step_1_skipped"] = True
            st.rerun()

    # If already uploaded, show extraction form
    if st.session_state.cover_pages and not st.session_state.project_info:
        st.markdown("---")
        st.markdown("### Extract Project Information")

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
    section_header("Step 2: SLD & Circuit Schedules",
                   "Upload SLD to extract distribution boards, circuits, and cable routes")

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

        **Tip:** You can upload multiple SLD files if they are split across documents.
        """)

        uploaded_files = st.file_uploader(
            "Upload SLD & Circuit Schedule(s) (PDF) - You can select multiple files",
            type=["pdf", "png", "jpg", "jpeg"],
            key="sld_uploader_v3",
            accept_multiple_files=True
        )

        if uploaded_files:
            all_pages = []
            with st.spinner(f"Processing {len(uploaded_files)} SLD file(s)..."):
                for uploaded_file in uploaded_files:
                    pages = process_uploaded_file(uploaded_file)
                    if pages:
                        all_pages.extend(pages)
                if all_pages:
                    st.session_state.sld_pages = all_pages
                    st.success(f"SLD loaded ({len(all_pages)} page(s) from {len(uploaded_files)} file(s))")
                    show_page_thumbnails(all_pages, max_show=4)

        if st.session_state.sld_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Cover Page", use_container_width=True):
                    st.session_state.guided_step = 1
                    st.rerun()
            with col2:
                if st.button("Detect Distribution Boards", type="primary", use_container_width=True):
                    st.session_state["sld_substep"] = "detect_dbs"
                    st.rerun()
        else:
            # Skip button when no file uploaded
            col_back, col_skip = st.columns(2)
            with col_back:
                if st.button("Back to Cover Page", use_container_width=True):
                    st.session_state.guided_step = 1
                    st.rerun()
            with col_skip:
                if st.button("Skip SLD step →", key="skip_step_2", help="Skip if you don't have SLD documents"):
                    st.session_state.guided_step = 3
                    st.session_state.max_completed_step = max(2, st.session_state.max_completed_step)
                    st.session_state["step_2_skipped"] = True
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
# STEP 3: LIGHTING LAYOUT (v7.0 - Circuit Cluster Extraction)
# ============================================================================

def render_step_3_lighting():
    """Step 3: Upload lighting layout, extract legend, then circuit clusters."""
    section_header("Step 3: Lighting Layout",
                   "Extract legend, then count fixtures by circuit label (e.g., DB-S3 L2)")

    substep = st.session_state.get("lighting_substep", "upload")
    pipeline = st.session_state.interactive_pipeline

    # SUBSTEP: Upload
    if substep == "upload":
        st.info("""
        **What to upload:** `03_Lighting_Layout.pdf`

        This document should contain:
        - Lighting legend (symbol → fixture type)
        - Floor plan with light fixtures
        - Circuit labels (e.g., "DB-S3 L2", "DB-GF L1")

        **Tip:** You can upload multiple lighting layout files (e.g., Ground Floor, First Floor).
        """)

        uploaded_files = st.file_uploader(
            "Upload Lighting Layout(s) (PDF) - You can select multiple files",
            type=["pdf", "png", "jpg", "jpeg"],
            key="lighting_uploader_v3",
            accept_multiple_files=True
        )

        if uploaded_files:
            all_pages = []
            with st.spinner(f"Processing {len(uploaded_files)} lighting file(s)..."):
                for uploaded_file in uploaded_files:
                    pages = process_uploaded_file(uploaded_file)
                    if pages:
                        all_pages.extend(pages)
                if all_pages:
                    st.session_state.lighting_pages = all_pages
                    st.success(f"Lighting layout loaded ({len(all_pages)} page(s) from {len(uploaded_files)} file(s))")
                    show_page_thumbnails(all_pages, max_show=3)

        if st.session_state.lighting_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to SLD", use_container_width=True):
                    st.session_state.guided_step = 2
                    st.session_state["sld_substep"] = "cable_routes"
                    st.rerun()
            with col2:
                if st.button("Extract Lighting Legend", type="primary", use_container_width=True):
                    st.session_state["lighting_substep"] = "legend"
                    st.rerun()
        else:
            # Skip button when no file uploaded
            col_back, col_skip = st.columns(2)
            with col_back:
                if st.button("Back to SLD", use_container_width=True):
                    st.session_state.guided_step = 2
                    st.session_state["sld_substep"] = "cable_routes"
                    st.rerun()
            with col_skip:
                if st.button("Skip Lighting step →", key="skip_step_3", help="Skip if you don't have lighting layouts"):
                    st.session_state.guided_step = 4
                    st.session_state.max_completed_step = max(3, st.session_state.max_completed_step)
                    st.session_state["step_3_skipped"] = True
                    st.rerun()
        return

    # SUBSTEP: Legend extraction
    if substep == "legend":
        st.markdown("### Lighting Legend")
        st.caption("Extract fixture types BEFORE counting circuits for higher accuracy")

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
            if st.button("Extract Circuit Clusters", type="primary", use_container_width=True):
                st.session_state.lighting_legend = {
                    "has_legend": True,
                    "light_types": light_types,
                    "switch_types": switch_types,
                }
                st.session_state["lighting_substep"] = "circuit_clusters"
                st.rerun()
        return

    # SUBSTEP: Circuit Clusters (v7.0 - replaces room-by-room)
    if substep == "circuit_clusters":
        st.markdown("### Lighting Circuit Clusters")
        st.caption("Counting fixtures by circuit label (e.g., 'DB-S3 L2' → 8 downlights)")

        # Extract circuit clusters
        if "lighting_circuit_clusters" not in st.session_state or not st.session_state.lighting_circuit_clusters:
            if not hasattr(pipeline, 'run_circuit_clusters_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()
            with st.spinner("AI extracting lighting circuit clusters..."):
                result = pipeline.run_circuit_clusters_pass(
                    st.session_state.lighting_pages,
                    st.session_state.lighting_legend
                )
                if result.success:
                    st.session_state.lighting_circuit_clusters = result.display_data.get("circuit_clusters", [])
                    st.session_state.detected_rooms = [
                        r.get("name", "") for r in result.display_data.get("rooms_identified", [])
                    ]
                else:
                    st.session_state.lighting_circuit_clusters = []

        clusters = st.session_state.lighting_circuit_clusters

        if clusters:
            # Group by DB
            db_groups = {}
            for cluster in clusters:
                db = cluster.get("db_name", "Unknown")
                if db not in db_groups:
                    db_groups[db] = []
                db_groups[db].append(cluster)

            # Stats
            total_clusters = len(clusters)
            total_points = sum(c.get("total_points", 0) for c in clusters)
            st.success(f"Found **{total_clusters} circuit clusters** with **{total_points} total points**")

            # Show clusters grouped by DB
            for db_name, db_clusters in db_groups.items():
                with st.expander(f"**{db_name}** ({len(db_clusters)} circuits)", expanded=True):
                    import pandas as pd

                    # Build table data
                    table_data = []
                    for c in db_clusters:
                        fixtures_str = ", ".join([f"{k}: {v}" for k, v in c.get("fixtures", {}).items() if v > 0])
                        table_data.append({
                            "Circuit": c.get("circuit_id", ""),
                            "Type": c.get("circuit_type", ""),
                            "Points": c.get("total_points", 0),
                            "Fixtures": fixtures_str[:50] + "..." if len(fixtures_str) > 50 else fixtures_str,
                            "Rooms": ", ".join(c.get("rooms_served", [])),
                            "Confidence": f"{c.get('confidence', 0):.0%}",
                        })

                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            # Show rooms identified
            if st.session_state.detected_rooms:
                st.markdown(f"**Rooms identified:** {', '.join(st.session_state.detected_rooms)}")

        else:
            st.warning("No circuit clusters found. The drawing may not have clear circuit labels.")
            st.info("Circuit labels look like: 'DB-S3 L2', 'DB-GF L1', 'DB-CA P3'")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Legend", use_container_width=True):
                st.session_state["lighting_substep"] = "legend"
                st.rerun()
        with col2:
            if st.button("Continue to Power Layout", type="primary", use_container_width=True):
                st.session_state["lighting_substep"] = "upload"
                st.session_state.guided_step = 4
                st.session_state.max_completed_step = max(3, st.session_state.max_completed_step)
                st.rerun()


# ============================================================================
# STEP 4: POWER LAYOUT
# ============================================================================

def render_step_4_power():
    """Step 4: Upload power layout, extract legend, then circuit clusters.

    v7.0 Circuit-Cluster-First: Extract by circuit labels (DB-S3 P2), not rooms.
    Power circuits: Count socket outlets (double socket = 1 point).
    Dedicated circuits (AC, geyser, isolators): Always 1 point per circuit.
    """
    section_header("Step 4: Power Layout",
                   "Extract power legend, then detect power circuit clusters")

    substep = st.session_state.get("power_substep", "upload")
    pipeline = st.session_state.interactive_pipeline

    # SUBSTEP: Upload
    if substep == "upload":
        st.info("""
        **What to upload:** `04_Power_Layout.pdf`

        This document should contain:
        - Power legend (sockets, data points, isolators)
        - Floor plan with circuit labels (e.g., "DB-S3 P2", "DB-GF P1")
        - Equipment connections (A/C, geyser isolators)

        **Tip:** You can upload multiple power layout files (e.g., Ground Floor, First Floor).
        """)

        uploaded_files = st.file_uploader(
            "Upload Power Layout(s) (PDF) - You can select multiple files",
            type=["pdf", "png", "jpg", "jpeg"],
            key="power_uploader_v3",
            accept_multiple_files=True
        )

        if uploaded_files:
            all_pages = []
            with st.spinner(f"Processing {len(uploaded_files)} power file(s)..."):
                for uploaded_file in uploaded_files:
                    pages = process_uploaded_file(uploaded_file)
                    if pages:
                        all_pages.extend(pages)
                if all_pages:
                    st.session_state.power_pages = all_pages
                    st.success(f"Power layout loaded ({len(all_pages)} page(s) from {len(uploaded_files)} file(s))")
                    show_page_thumbnails(all_pages, max_show=3)

        if st.session_state.power_pages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to Lighting", use_container_width=True):
                    st.session_state.guided_step = 3
                    st.session_state["lighting_substep"] = "circuit_clusters"
                    st.rerun()
            with col2:
                if st.button("Extract Power Legend", type="primary", use_container_width=True):
                    st.session_state["power_substep"] = "legend"
                    st.rerun()
        else:
            # Skip button when no file uploaded
            col_back, col_skip = st.columns(2)
            with col_back:
                if st.button("Back to Lighting", use_container_width=True):
                    st.session_state.guided_step = 3
                    st.session_state["lighting_substep"] = "circuit_clusters"
                    st.rerun()
            with col_skip:
                if st.button("Skip to Review →", key="skip_step_4", help="Skip if you don't have power layouts"):
                    st.session_state.guided_step = 5
                    st.session_state.max_completed_step = max(4, st.session_state.max_completed_step)
                    st.session_state["step_4_skipped"] = True
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
            if st.button("Detect Power Circuits", type="primary", use_container_width=True):
                st.session_state.power_legend = {
                    "has_legend": True,
                    "socket_types": socket_types,
                    "isolator_types": isolator_types,
                }
                st.session_state["power_substep"] = "circuit_clusters"
                st.rerun()
        return

    # SUBSTEP: Circuit clusters (v7.0 - replaces room_sockets)
    if substep == "circuit_clusters":
        st.markdown("### Power Circuit Clusters")
        st.caption("Power circuits: Each socket outlet = 1 point. Dedicated (AC/geyser) = 1 point.")

        # Extract power circuit clusters using legend context
        power_clusters_key = "power_circuit_clusters"
        if power_clusters_key not in st.session_state:
            if not hasattr(pipeline, 'run_circuit_clusters_pass'):
                st.error("App needs reboot. Go to 'Manage app' → 'Reboot app'.")
                st.stop()

            with st.spinner("AI detecting power circuit clusters (DB-XX P1, ISO1, AC1...)..."):
                result = pipeline.run_circuit_clusters_pass(
                    st.session_state.power_pages,
                    st.session_state.power_legend,
                    circuit_type_filter="power"  # Filter for power/isolator circuits
                )
                if result.success:
                    st.session_state[power_clusters_key] = result.display_data.get("clusters", [])
                    # Also capture any rooms mentioned
                    rooms_found = set()
                    for c in st.session_state[power_clusters_key]:
                        rooms_found.update(c.get("rooms_served", []))
                    # Merge with existing detected rooms
                    existing = set(st.session_state.detected_rooms)
                    st.session_state.detected_rooms = list(existing | rooms_found)
                else:
                    st.session_state[power_clusters_key] = []

        clusters = st.session_state.get(power_clusters_key, [])
        total_clusters = len(clusters)
        avg_confidence = sum(c.get("confidence", 0) for c in clusters) / max(1, total_clusters)

        render_confidence_badge(avg_confidence, "Circuits")

        if clusters:
            # Group by DB for display
            from collections import defaultdict
            by_db = defaultdict(list)
            for c in clusters:
                by_db[c.get("db_name", "Unknown")].append(c)

            for db_name, db_clusters in by_db.items():
                with st.expander(f"**{db_name}** ({len(db_clusters)} power circuits)", expanded=True):
                    import pandas as pd
                    table_data = []
                    for c in db_clusters:
                        fixtures = c.get("fixtures", {})
                        fixture_str = ", ".join([f"{k}: {v}" for k, v in fixtures.items() if v > 0])
                        table_data.append({
                            "Circuit": c.get("circuit_id", "?"),
                            "Type": c.get("circuit_type", "power"),
                            "Points": c.get("total_points", 0),
                            "Fixtures": fixture_str or "-",
                            "Rooms": ", ".join(c.get("rooms_served", [])),
                            "Confidence": f"{c.get('confidence', 0):.0%}",
                        })

                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

            # Show total power points for reconciliation
            total_power_points = sum(c.get("total_points", 0) for c in clusters)
            st.info(f"**Total Power Points:** {total_power_points} across {total_clusters} circuits")

        else:
            st.warning("No power circuit clusters found. The drawing may not have clear circuit labels.")
            st.info("Power circuit labels look like: 'DB-S3 P2', 'DB-GF ISO1', 'DB-CA AC1'")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Legend", use_container_width=True):
                st.session_state["power_substep"] = "legend"
                st.rerun()
        with col2:
            if st.button("Continue to Review", type="primary", use_container_width=True):
                st.session_state["power_substep"] = "upload"
                st.session_state.guided_step = 5
                st.session_state.max_completed_step = max(4, st.session_state.max_completed_step)
                st.rerun()


# ============================================================================
# STEP 5: REVIEW & EXPORT
# ============================================================================

def render_step_5_review():
    """Step 5: Final review, SLD reconciliation, and BOQ export.

    v7.0 Circuit-Cluster Reconciliation:
    - Compares SLD circuit points vs Layout circuit cluster points
    - Shows match rate and discrepancies per DB
    """
    section_header("Step 5: Review & Export",
                   "SLD Reconciliation, validation, and BOQ export")

    pipeline = st.session_state.interactive_pipeline

    # Build final result from AI pipeline
    if st.session_state.final_extraction is None:
        with st.spinner("Building final BOQ..."):
            st.session_state.final_extraction = pipeline.build_final_result()
            validation, _ = validate(st.session_state.final_extraction)
            st.session_state.final_validation = validation
            pricing, _ = price(st.session_state.final_extraction, validation, None, None)
            st.session_state.final_pricing = pricing

    extraction = st.session_state.final_extraction
    validation = st.session_state.final_validation
    pricing = st.session_state.final_pricing

    # Get statistics from AI pipeline
    stats = pipeline.get_statistics() if pipeline else {}

    # Calculate accuracy using circuit clusters (v7.0)
    db_count = stats.get("db_schedules_extracted", 0)
    total_sld_circuits = sum(len(s.get("circuits", [])) for s in st.session_state.db_schedules.values())
    cable_count = len(st.session_state.cable_routes)

    # Get circuit clusters from both lighting and power
    lighting_clusters = st.session_state.get("lighting_circuit_clusters", [])
    power_clusters = st.session_state.get("power_circuit_clusters", [])
    all_layout_clusters = lighting_clusters + power_clusters

    # Count total points from clusters
    total_lighting_points = sum(c.get("total_points", 0) for c in lighting_clusters)
    total_power_points = sum(c.get("total_points", 0) for c in power_clusters)

    # Reconciliation: SLD vs Layout
    reconciliation_results = reconcile_sld_with_clusters(
        st.session_state.db_schedules,
        all_layout_clusters
    )
    match_rate = reconciliation_results.get("match_rate", 0)
    matched_circuits = reconciliation_results.get("matched", 0)
    total_compared = reconciliation_results.get("total_compared", 0)

    # Accuracy scoring (v7.0 - circuit cluster based)
    # - DBs: 20% weight (target: 10 DBs for commercial)
    # - SLD Circuits: 15% weight (target: 50+ circuits)
    # - Layout Clusters: 20% weight (target: 30+ clusters)
    # - Cable routes: 15% weight (target: 10 routes)
    # - Match Rate: 30% weight (SLD vs Layout reconciliation)
    db_score = min(100, (db_count / 10) * 100)
    circuit_score = min(100, (total_sld_circuits / 50) * 100)
    cluster_score = min(100, (len(all_layout_clusters) / 30) * 100)
    cable_score = min(100, (cable_count / 10) * 100)
    match_score = match_rate * 100

    accuracy = (db_score * 0.20 + circuit_score * 0.15 + cluster_score * 0.20 +
                cable_score * 0.15 + match_score * 0.30)

    # Success banner with accuracy
    if accuracy >= 75:
        st.success(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Target achieved!")
    elif accuracy >= 60:
        st.warning(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Below 75% target")
    else:
        st.error(f"**Extraction Complete!** Accuracy: **{accuracy:.0f}%** - Needs improvement")

    # Summary metrics (v7.0)
    st.markdown("### Extraction Summary")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("DBs", db_count, help="Distribution boards detected")
    with col2:
        st.metric("SLD Circuits", total_sld_circuits, help="Circuits in SLD schedules")
    with col3:
        st.metric("Layout Clusters", len(all_layout_clusters), help="Circuit clusters from layouts")
    with col4:
        st.metric("Cable Routes", cable_count, help="Sub-main cables between DBs")
    with col5:
        st.metric("Match Rate", f"{match_rate:.0%}", help="SLD vs Layout reconciliation")
    with col6:
        st.metric("Accuracy", f"{accuracy:.0f}%", help="Weighted extraction accuracy")

    # SLD vs Layout Reconciliation (v7.0 - NEW)
    st.markdown("### SLD vs Layout Reconciliation")
    st.caption("Comparing circuit points from SLD schedules against layout circuit clusters")

    if reconciliation_results.get("by_db"):
        for db_name, db_recon in reconciliation_results["by_db"].items():
            status_icon = "✅" if db_recon.get("is_balanced", False) else "⚠️"
            with st.expander(f"{status_icon} **{db_name}** - {db_recon.get('match_count', 0)}/{db_recon.get('total_circuits', 0)} matched", expanded=False):
                import pandas as pd
                table_data = []
                for circuit_id, circuit_recon in db_recon.get("circuits", {}).items():
                    sld_points = circuit_recon.get("sld_points", "-")
                    layout_points = circuit_recon.get("layout_points", "-")
                    match_status = "✅ Match" if circuit_recon.get("matched") else "❌ Mismatch"
                    table_data.append({
                        "Circuit": circuit_id,
                        "Type": circuit_recon.get("circuit_type", "-"),
                        "SLD Points": sld_points,
                        "Layout Points": layout_points,
                        "Status": match_status,
                    })
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Show discrepancies
                discrepancies = db_recon.get("discrepancies", [])
                if discrepancies:
                    st.warning(f"**{len(discrepancies)} discrepancies found:**")
                    for d in discrepancies[:5]:
                        st.markdown(f"- {d}")
    else:
        st.info("No reconciliation data available. Upload both SLD and Layout documents.")

    # Document coverage with upload summary
    st.markdown("### Document Upload Summary")

    # Build detailed status with page counts and skip info
    doc_status = [
        {
            "name": "Cover Page",
            "step": 1,
            "pages": st.session_state.cover_pages,
            "extracted": bool(st.session_state.project_info.get("project_name")),
            "skipped": st.session_state.get("step_1_skipped", False),
        },
        {
            "name": "SLD/Schedules",
            "step": 2,
            "pages": st.session_state.sld_pages,
            "extracted": bool(st.session_state.db_schedules),
            "skipped": st.session_state.get("step_2_skipped", False),
        },
        {
            "name": "Lighting Layout",
            "step": 3,
            "pages": st.session_state.lighting_pages,
            "extracted": bool(st.session_state.lighting_legend.get("has_legend")),
            "skipped": st.session_state.get("step_3_skipped", False),
        },
        {
            "name": "Power Layout",
            "step": 4,
            "pages": st.session_state.power_pages,
            "extracted": bool(st.session_state.power_legend.get("has_legend")),
            "skipped": st.session_state.get("step_4_skipped", False),
        },
    ]

    # Calculate totals
    total_pages = sum(len(d["pages"]) for d in doc_status)
    total_uploaded = sum(1 for d in doc_status if d["pages"])
    total_skipped = sum(1 for d in doc_status if d["skipped"])

    st.info(f"**Total:** {total_pages} pages from {total_uploaded} document type(s) | {total_skipped} step(s) skipped")

    for doc in doc_status:
        page_count = len(doc["pages"])
        doc_name = doc["name"]
        if doc["skipped"]:
            st.markdown(f"- :gray[{doc_name}] - **Skipped** (no file uploaded)")
        elif page_count > 0 and doc["extracted"]:
            st.markdown(f"- :green[{doc_name}] - **{page_count} page(s)** - Extracted")
        elif page_count > 0:
            st.markdown(f"- :orange[{doc_name}] - **{page_count} page(s)** - Partial extraction")
        else:
            st.markdown(f"- :red[{doc_name}] - Not uploaded")

    # Accuracy breakdown (v7.0 - circuit cluster based)
    st.markdown("### Accuracy Breakdown")
    with st.expander("View detailed scoring", expanded=False):
        st.markdown(f"""
        | Component | Extracted | Target | Weight | Score |
        |-----------|-----------|--------|--------|-------|
        | Distribution Boards | {db_count} | 10 | 20% | {db_score:.0f}% |
        | SLD Circuits | {total_sld_circuits} | 50 | 15% | {circuit_score:.0f}% |
        | Layout Clusters | {len(all_layout_clusters)} | 30 | 20% | {cluster_score:.0f}% |
        | Cable Routes | {cable_count} | 10 | 15% | {cable_score:.0f}% |
        | SLD↔Layout Match Rate | {matched_circuits}/{total_compared} | 100% | 30% | {match_score:.0f}% |
        | **Weighted Total** | | | | **{accuracy:.0f}%** |

        **v7.0 Circuit-Cluster Scoring:** Match Rate is now the highest weight (30%) because
        accurate reconciliation between SLD and Layout is the key quality indicator.
        """)

        # Point totals for reference
        st.markdown(f"""
        #### Point Totals
        - **Lighting Points (from clusters):** {total_lighting_points}
        - **Power Points (from clusters):** {total_power_points}
        - **Total Layout Points:** {total_lighting_points + total_power_points}
        """)

        # Critique / improvement suggestions
        st.markdown("#### Areas for Improvement")
        issues = []
        if db_count < 8:
            issues.append("- **DBs:** Some distribution boards may be missing (check for DB-GF, DB-CA variations)")
        if total_sld_circuits < 40:
            issues.append("- **SLD Circuits:** Circuit schedules may be incomplete - review SLD pages manually")
        if len(all_layout_clusters) < 20:
            issues.append("- **Layout Clusters:** Low circuit cluster count - drawings may not have clear circuit labels")
        if cable_count < 5:
            issues.append("- **Cables:** Sub-main cable routes not fully extracted from SLD")
        if match_rate < 0.70:
            issues.append("- **Match Rate:** SLD and Layout don't align well - check circuit references match")

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

    # Benchmark Validation (if project matches known ground truth)
    if BENCHMARK_AVAILABLE:
        project_name = st.session_state.project_info.get("project_name", "")
        project_id = identify_project(project_name)

        if project_id:
            st.markdown("### Benchmark Validation")
            st.caption(f"Comparing extraction against ground truth: **{project_id}**")

            with st.expander("View Benchmark Results", expanded=True):
                try:
                    # Convert session state data for validation
                    validation_data = convert_extraction_for_validation(
                        db_data=st.session_state.db_schedules,
                        cable_routes=st.session_state.cable_routes,
                        legend_data={
                            "lighting": st.session_state.lighting_legend,
                            "power": st.session_state.power_legend,
                        },
                        project_info=st.session_state.project_info
                    )

                    # Add circuit clusters for validation
                    validation_data["lighting_clusters"] = lighting_clusters
                    validation_data["power_clusters"] = power_clusters

                    # Run benchmark validation
                    benchmark_report = validate_extraction_against_benchmark(
                        validation_data,
                        project_id=project_id
                    )

                    if benchmark_report:
                        render_benchmark_results(benchmark_report)
                    else:
                        st.info("Benchmark validation could not be completed.")

                except Exception as e:
                    st.warning(f"Benchmark validation error: {e}")
        else:
            # Show that benchmark is available but project not matched
            st.markdown("### Benchmark Validation")
            st.info(f"Project '{project_name}' not in benchmark database. Benchmark validation skipped.")
            st.caption("Known projects: WEDELA (Recreational Club), EUROBATH (Warehouse), NewMark (Offices)")

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
            # Clear all session state (v7.0 - includes circuit clusters)
            keys_to_clear = [
                "guided_step", "max_completed_step",
                "cover_pages", "sld_pages", "lighting_pages", "power_pages",
                "step_1_skipped", "step_2_skipped", "step_3_skipped", "step_4_skipped",  # Skip flags
                "interactive_pipeline", "project_info",
                "supply_point", "detected_dbs", "db_schedules", "cable_routes",
                "current_db_index", "lighting_legend", "detected_rooms",
                "lighting_circuit_clusters", "room_lighting",  # v7.0: added circuit clusters
                "power_legend", "power_circuit_clusters", "room_power",  # v7.0: added circuit clusters
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
    title="Smart Upload",
    subtitle="Upload your drawings, get your BOQ"
)

# Check if pipeline is available
if not PIPELINE_AVAILABLE:
    st.error("Pipeline not available. Check imports.")
    st.stop()

if not LLM_API_KEY:
    st.error("No API key configured. Add GROQ_API_KEY, XAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY to secrets.")
    st.stop()

# Sidebar: Simple help
st.sidebar.markdown("### Need Help?")
st.sidebar.info("Upload your electrical drawings step by step. The AI will extract quantities for your BOQ.")

# Render the 4-step guided upload
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
