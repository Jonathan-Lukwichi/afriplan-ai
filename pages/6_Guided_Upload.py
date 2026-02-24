"""
AfriPlan Electrical v5.0 - Guided Upload (4-Step Document Flow)

Redesigned for higher accuracy by matching document types:
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
        # Navigation (5 steps: 4 uploads + 1 review)
        "guided_step": 1,
        "max_completed_step": 0,

        # Document pages by type (4 separate documents)
        "cover_pages": [],
        "sld_pages": [],
        "lighting_pages": [],
        "power_pages": [],

        # Pipeline instance
        "interactive_pipeline": None,

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


def map_fixture_to_standard_key(name: str) -> str:
    """Map a legend fixture name to a standard key for build_extraction_result."""
    name_lower = name.lower()

    # Lighting fixtures
    if "600x1200" in name_lower or "1200" in name_lower or "panel" in name_lower:
        return "recessed_led_600x1200"
    if "600x600" in name_lower:
        return "recessed_led_600x600"
    if "downlight" in name_lower or "down light" in name_lower:
        return "downlight"
    if "surface" in name_lower or "ceiling" in name_lower:
        return "surface_mount_led"
    if "vapor" in name_lower or "vapour" in name_lower:
        return "vapor_proof"
    if "bulkhead" in name_lower or "wall" in name_lower:
        return "bulkhead"
    if "flood" in name_lower or "outdoor" in name_lower:
        return "flood_light"
    if "emergency" in name_lower:
        return "emergency_light"

    # Switches
    if "1-lever" in name_lower or "1 lever" in name_lower or "single" in name_lower:
        if "2-way" in name_lower or "2 way" in name_lower:
            return "switch_2way"
        return "switch_1lever"
    if "2-lever" in name_lower or "2 lever" in name_lower:
        return "switch_2lever"
    if "day" in name_lower and "night" in name_lower:
        return "switch_daynight"

    # Sockets
    if "double" in name_lower:
        if "1100" in name_lower or "worktop" in name_lower:
            return "double_socket_1100"
        if "water" in name_lower or "ip" in name_lower:
            return "waterproof_socket"
        return "double_socket_300"
    if "single" in name_lower:
        return "single_socket"
    if "data" in name_lower or "cat" in name_lower:
        return "data_point_cat6"
    if "floor" in name_lower and "box" in name_lower:
        return "floor_box"

    # Isolators
    if "isolator" in name_lower or "iso" in name_lower:
        return "isolator"
    if "a/c" in name_lower or "air con" in name_lower:
        return "ac_isolator"

    # Default: use normalized name
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

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Cover Page (PDF or Image)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="cover_uploader_v2"
    )

    if uploaded_file:
        with st.spinner("Processing cover page..."):
            pages = process_uploaded_file(uploaded_file)
            if pages:
                st.session_state.cover_pages = pages
                st.success(f"Cover page loaded ({len(pages)} page(s))")
                show_page_thumbnails(pages, max_show=2)

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
        """)

        uploaded_file = st.file_uploader(
            "Upload SLD & Circuit Schedule (PDF)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="sld_uploader_v2"
        )

        if uploaded_file:
            with st.spinner("Processing SLD pages..."):
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
                if st.button("Detect Distribution Boards", type="primary", use_container_width=True):
                    st.session_state["sld_substep"] = "detect_dbs"
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
    section_header("Step 3: Lighting Layout",
                   "Extract lighting legend, then count fixtures per room")

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
                    st.session_state["sld_substep"] = "cable_routes"
                    st.rerun()
            with col2:
                if st.button("Extract Lighting Legend", type="primary", use_container_width=True):
                    st.session_state["lighting_substep"] = "legend"
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
                    st.session_state.room_lighting[current_room] = result.display_data.get("fixtures", {})
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
    section_header("Step 4: Power Layout",
                   "Extract power legend, then count sockets per room")

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
                    st.session_state["lighting_substep"] = "room_fixtures"
                    st.session_state.current_lighting_room_index = len(st.session_state.detected_rooms) - 1
                    st.rerun()
            with col2:
                if st.button("Extract Power Legend", type="primary", use_container_width=True):
                    st.session_state["power_substep"] = "legend"
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
                    st.session_state.room_power[current_room] = result.display_data.get("fixtures", {})
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
    section_header("Step 5: Review & Export",
                   "Validate extraction and download BOQ")

    pipeline = st.session_state.interactive_pipeline

    # Build final result
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
    stats = pipeline.get_statistics()

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
                "interactive_pipeline", "project_info",
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
    title="Guided Upload v2.0",
    subtitle="4-step document flow | Legend-based extraction | 75%+ accuracy target"
)

if not PIPELINE_AVAILABLE:
    st.error(f"Pipeline not available: {PIPELINE_IMPORT_ERROR}")
    st.stop()

if not LLM_API_KEY:
    st.error("No API key configured. Add GROQ_API_KEY, XAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY to secrets.")
    st.stop()

# Sidebar info
st.sidebar.markdown("### AI Provider")
provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
st.sidebar.success(f"{provider_name} ({provider_cost})")

st.sidebar.markdown("---")
st.sidebar.markdown("""
**4-Step Document Flow:**

1. **Cover Page** → Project info
2. **SLD + Schedules** → DBs, circuits, cables
3. **Lighting Layout** → Legend → Fixtures
4. **Power Layout** → Legend → Sockets

**Key Improvement:** Extract legends BEFORE counting fixtures for higher accuracy.
""")

# Progress indicator
render_progress_indicator()

# Render current step
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
