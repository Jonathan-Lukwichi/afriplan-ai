"""
AfriPlan Electrical v4.11 - Guided Upload

Interactive step-by-step extraction with user validation at each stage.
Target: 70%+ extraction rate through human-in-the-loop validation.

Each step asks for the specific document needed:
1. Upload COVER PAGE → Extract project info
2. Confirm project info
3. Upload SLD PAGES → Detect DBs
4. Extract DB Schedules (loop)
5. Upload LAYOUT PAGES → Detect rooms
6. Extract Room Fixtures (loop)
7. Cable Routes (from SLD)
8. Review & Export
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
    """Initialize all session state variables."""
    defaults = {
        # Navigation
        "guided_step": 1,
        "max_completed_step": 0,

        # Document pages by type
        "cover_pages": [],
        "sld_pages": [],
        "layout_pages": [],

        # Pipeline instance
        "interactive_pipeline": None,

        # Extraction results
        "project_info": {},
        "detected_dbs": [],
        "db_schedules": {},
        "detected_rooms": [],
        "room_fixtures": {},
        "cable_routes": [],

        # Loop indices
        "current_db_index": 0,
        "current_room_index": 0,

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


def render_progress_indicator():
    """Render 8-step progress indicator."""
    step = st.session_state.guided_step
    max_step = st.session_state.max_completed_step

    steps = [
        ("1", "Cover"),
        ("2", "Project"),
        ("3", "SLD"),
        ("4", "Schedules"),
        ("5", "Layouts"),
        ("6", "Fixtures"),
        ("7", "Cables"),
        ("8", "Export"),
    ]

    cols = st.columns(8)
    for i, (num, name) in enumerate(steps):
        step_num = i + 1
        with cols[i]:
            if step_num == step:
                st.markdown(f"**:blue[{num}. {name}]**")
            elif step_num <= max_step:
                st.markdown(f":green[✓ {name}]")
            else:
                st.markdown(f":gray[{num}. {name}]")

    st.markdown("---")


def render_confidence_badge(confidence: float, label: str = "Confidence"):
    """Render confidence indicator."""
    if confidence >= 0.70:
        st.success(f"✅ {label}: {confidence*100:.0f}% - High confidence")
    elif confidence >= 0.40:
        st.warning(f"⚠️ {label}: {confidence*100:.0f}% - Please review")
    else:
        st.error(f"❌ {label}: {confidence*100:.0f}% - Manual input needed")


# ============================================================================
# STEP 1: UPLOAD COVER PAGE
# ============================================================================

def render_step_1_cover_upload():
    """Step 1: Upload cover page to extract project info."""
    section_header("Step 1: Upload Cover Page", "Upload the cover/title page of your electrical drawings")

    st.info("📋 **What to upload:** The cover page or title block that contains project name, client, date, etc.")

    uploaded_file = st.file_uploader(
        "📤 Upload Cover Page (PDF or Image)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="cover_uploader"
    )

    if uploaded_file:
        with st.spinner("Processing cover page..."):
            pages = process_uploaded_file(uploaded_file)
            if pages:
                st.session_state.cover_pages = pages
                st.success(f"✅ Cover page loaded ({len(pages)} page(s))")

                # Show thumbnail
                if pages[0].image_base64:
                    st.image(
                        f"data:image/png;base64,{pages[0].image_base64}",
                        caption="Cover Page Preview",
                        width=400
                    )

    # Navigation
    st.markdown("")
    col1, col2 = st.columns(2)

    with col2:
        if st.session_state.cover_pages:
            if st.button("Extract Project Info →", type="primary", use_container_width=True):
                # Initialize pipeline
                pipeline = init_pipeline()
                if pipeline:
                    st.session_state.interactive_pipeline = pipeline
                    st.session_state.guided_step = 2
                    st.session_state.max_completed_step = 1
                    st.rerun()
                else:
                    st.error("Failed to initialize AI. Check API key.")
        else:
            st.button("Extract Project Info →", type="primary", use_container_width=True, disabled=True)
            st.caption("Upload a cover page first")


# ============================================================================
# STEP 2: CONFIRM PROJECT INFO
# ============================================================================

def render_step_2_project_info():
    """Step 2: Extract and confirm project information."""
    section_header("Step 2: Project Information", "Extracted from cover page - verify and edit")

    pipeline = st.session_state.interactive_pipeline

    # Run extraction if not done
    if not st.session_state.project_info:
        if st.session_state.cover_pages:
            with st.spinner("AI is extracting project information..."):
                result = pipeline.run_project_info_pass(st.session_state.cover_pages)
                if result.success:
                    st.session_state.project_info = result.display_data
                else:
                    st.session_state.project_info = {}

    # Show confidence
    confidence = 0.85 if st.session_state.project_info.get("project_name") else 0.3
    render_confidence_badge(confidence, "Extraction")

    # Editable form
    with st.form("project_info_form"):
        st.markdown("##### Edit extracted values:")

        project_name = st.text_input(
            "Project Name",
            value=st.session_state.project_info.get("project_name", ""),
            placeholder="e.g., NewMark Commercial Building"
        )
        client_name = st.text_input(
            "Client Name",
            value=st.session_state.project_info.get("client_name", ""),
            placeholder="e.g., ABC Properties (Pty) Ltd"
        )
        consultant = st.text_input(
            "Consultant/Engineer",
            value=st.session_state.project_info.get("consultant_name", ""),
            placeholder="e.g., Electro-Tech Consulting"
        )

        col1, col2 = st.columns(2)
        with col1:
            date = st.text_input(
                "Date",
                value=st.session_state.project_info.get("date", ""),
                placeholder="e.g., 2024-01-15"
            )
        with col2:
            revision = st.text_input(
                "Revision",
                value=st.session_state.project_info.get("revision", ""),
                placeholder="e.g., Rev 3"
            )

        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("← Back", use_container_width=True)
        with col2:
            confirm = st.form_submit_button("✓ Confirm & Continue →", type="primary", use_container_width=True)

        if back:
            st.session_state.guided_step = 1
            st.rerun()

        if confirm:
            st.session_state.project_info = {
                "project_name": project_name,
                "client_name": client_name,
                "consultant_name": consultant,
                "date": date,
                "revision": revision,
            }
            pipeline.apply_project_info(st.session_state.project_info)
            st.session_state.guided_step = 3
            st.session_state.max_completed_step = 2
            st.rerun()


# ============================================================================
# STEP 3: UPLOAD SLD PAGES
# ============================================================================

def render_step_3_sld_upload():
    """Step 3: Upload SLD pages to detect distribution boards."""
    section_header("Step 3: Upload SLD Pages", "Upload Single Line Diagram pages")

    st.info("⚡ **What to upload:** Single Line Diagram (SLD) pages showing distribution boards, circuits, and electrical layout.")

    uploaded_file = st.file_uploader(
        "📤 Upload SLD Pages (PDF or Images)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="sld_uploader"
    )

    if uploaded_file:
        with st.spinner("Processing SLD pages..."):
            pages = process_uploaded_file(uploaded_file)
            if pages:
                st.session_state.sld_pages = pages
                st.success(f"✅ SLD loaded ({len(pages)} page(s))")

                # Show thumbnails
                cols = st.columns(min(3, len(pages)))
                for i, page in enumerate(pages[:3]):
                    if page.image_base64:
                        with cols[i]:
                            st.image(
                                f"data:image/png;base64,{page.image_base64}",
                                caption=f"Page {i+1}",
                                use_container_width=True
                            )

    # Navigation
    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to Project Info", use_container_width=True):
            st.session_state.guided_step = 2
            st.rerun()

    with col2:
        if st.session_state.sld_pages:
            if st.button("Detect Distribution Boards →", type="primary", use_container_width=True):
                st.session_state.guided_step = 4
                st.session_state.max_completed_step = 3
                st.rerun()
        else:
            st.button("Detect Distribution Boards →", type="primary", use_container_width=True, disabled=True)
            st.caption("Upload SLD pages first")


# ============================================================================
# STEP 4: DETECT & EXTRACT DB SCHEDULES
# ============================================================================

def render_step_4_db_extraction():
    """Step 4: Detect DBs and extract schedules one by one."""
    pipeline = st.session_state.interactive_pipeline

    # First, detect DBs if not done
    if not st.session_state.detected_dbs:
        section_header("Step 4: Detect Distribution Boards", "AI scanning SLD pages...")

        with st.spinner("Detecting distribution boards from SLD..."):
            result = pipeline.run_db_detection_pass(st.session_state.sld_pages)
            if result.success:
                st.session_state.detected_dbs = [
                    db["name"] for db in result.display_data.get("dbs", [])
                ]
                pipeline.apply_detected_dbs(st.session_state.detected_dbs)
            else:
                st.session_state.detected_dbs = []

        if st.session_state.detected_dbs:
            st.success(f"✅ Found {len(st.session_state.detected_dbs)} distribution boards")
            st.rerun()
        else:
            st.warning("No DBs detected. Add manually:")
            new_db = st.text_input("DB Name", placeholder="e.g., DB-MAIN, DB-S1")
            if st.button("Add DB") and new_db:
                st.session_state.detected_dbs.append(new_db)
                pipeline.apply_detected_dbs(st.session_state.detected_dbs)
                st.rerun()
        return

    # Then process each DB
    detected_dbs = st.session_state.detected_dbs
    current_idx = st.session_state.current_db_index

    if current_idx >= len(detected_dbs):
        # All done, move to next step
        pipeline.mark_db_schedules_complete()
        st.session_state.guided_step = 5
        st.session_state.max_completed_step = 4
        st.rerun()
        return

    current_db = detected_dbs[current_idx]
    section_header(f"Step 4: Extract DB Schedule", f"DB {current_idx + 1} of {len(detected_dbs)}")

    st.info(f"📊 **Processing: {current_db}**")
    st.progress((current_idx + 1) / len(detected_dbs))

    # Extract schedule if not done
    if current_db not in st.session_state.db_schedules:
        with st.spinner(f"Extracting circuits from {current_db}..."):
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
        main_breaker = st.number_input("Main Breaker (A)", value=schedule.get("main_breaker_a", 0), key=f"mb_{current_db}")
    with col2:
        supply_from = st.text_input("Supply From", value=schedule.get("supply_from", ""), key=f"sf_{current_db}")
    with col3:
        total_ways = st.number_input("Total Ways", value=schedule.get("total_ways", 0), key=f"tw_{current_db}")

    # Circuits table
    st.markdown("##### Circuits")
    circuits = schedule.get("circuits", [])
    if circuits:
        import pandas as pd
        df = pd.DataFrame(circuits)
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key=f"circuits_{current_db}")
        circuits = edited_df.to_dict('records')
    else:
        st.info("No circuits extracted. Skip or add manually.")

    # Navigation
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back", key="back_db"):
            if current_idx > 0:
                st.session_state.current_db_index -= 1
            else:
                st.session_state.guided_step = 3
            st.rerun()
    with col2:
        if st.button("⏭ Skip DB", key="skip_db"):
            st.session_state.current_db_index += 1
            st.rerun()
    with col3:
        if st.button("✓ Confirm & Next →", type="primary", key="confirm_db"):
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


# ============================================================================
# STEP 5: UPLOAD LAYOUT PAGES
# ============================================================================

def render_step_5_layout_upload():
    """Step 5: Upload layout pages to detect rooms."""
    section_header("Step 5: Upload Layout Pages", "Upload lighting and power layout drawings")

    st.info("🏠 **What to upload:** Floor plan layouts showing lighting fixtures, power points, and room names.")

    uploaded_file = st.file_uploader(
        "📤 Upload Layout Pages (PDF or Images)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="layout_uploader"
    )

    if uploaded_file:
        with st.spinner("Processing layout pages..."):
            pages = process_uploaded_file(uploaded_file)
            if pages:
                st.session_state.layout_pages = pages
                st.success(f"✅ Layouts loaded ({len(pages)} page(s))")

                # Show thumbnails
                cols = st.columns(min(3, len(pages)))
                for i, page in enumerate(pages[:3]):
                    if page.image_base64:
                        with cols[i]:
                            st.image(
                                f"data:image/png;base64,{page.image_base64}",
                                caption=f"Page {i+1}",
                                use_container_width=True
                            )

    # Navigation
    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to DB Schedules", use_container_width=True):
            st.session_state.guided_step = 4
            st.session_state.current_db_index = len(st.session_state.detected_dbs) - 1
            st.rerun()

    with col2:
        if st.session_state.layout_pages:
            if st.button("Detect Rooms →", type="primary", use_container_width=True):
                st.session_state.guided_step = 6
                st.session_state.max_completed_step = 5
                st.rerun()
        else:
            st.button("Detect Rooms →", type="primary", use_container_width=True, disabled=True)
            st.caption("Upload layout pages first")


# ============================================================================
# STEP 6: DETECT & EXTRACT ROOM FIXTURES
# ============================================================================

def render_step_6_room_extraction():
    """Step 6: Detect rooms and extract fixtures one by one."""
    pipeline = st.session_state.interactive_pipeline

    # First, detect rooms if not done
    if not st.session_state.detected_rooms:
        section_header("Step 6: Detect Rooms", "AI scanning layout pages...")

        with st.spinner("Detecting rooms from layouts..."):
            result = pipeline.run_room_detection_pass(st.session_state.layout_pages)
            if result.success:
                st.session_state.detected_rooms = [
                    room["name"] for room in result.display_data.get("rooms", [])
                ]
                pipeline.apply_detected_rooms(st.session_state.detected_rooms)
            else:
                st.session_state.detected_rooms = []

        if st.session_state.detected_rooms:
            st.success(f"✅ Found {len(st.session_state.detected_rooms)} rooms")
            st.rerun()
        else:
            st.warning("No rooms detected. Add manually:")
            new_room = st.text_input("Room Name", placeholder="e.g., Office 1, Kitchen")
            if st.button("Add Room") and new_room:
                st.session_state.detected_rooms.append(new_room)
                pipeline.apply_detected_rooms(st.session_state.detected_rooms)
                st.rerun()
        return

    # Then process each room
    detected_rooms = st.session_state.detected_rooms
    current_idx = st.session_state.current_room_index

    if current_idx >= len(detected_rooms):
        # All done, move to next step
        pipeline.mark_room_fixtures_complete()
        st.session_state.guided_step = 7
        st.session_state.max_completed_step = 6
        st.rerun()
        return

    current_room = detected_rooms[current_idx]
    section_header(f"Step 6: Extract Room Fixtures", f"Room {current_idx + 1} of {len(detected_rooms)}")

    st.info(f"💡 **Processing: {current_room}**")
    st.progress((current_idx + 1) / len(detected_rooms))

    # Extract fixtures if not done
    if current_room not in st.session_state.room_fixtures:
        with st.spinner(f"Extracting fixtures for {current_room}..."):
            result = pipeline.run_room_fixtures_pass(current_room, st.session_state.layout_pages)
            if result.success:
                st.session_state.room_fixtures[current_room] = result.display_data.get("fixtures", {})
            else:
                st.session_state.room_fixtures[current_room] = {}

    fixtures = st.session_state.room_fixtures.get(current_room, {})
    confidence = 0.70 if fixtures else 0.3
    render_confidence_badge(confidence, "Fixtures")

    # Editable fields
    st.markdown("##### Lighting")
    col1, col2, col3 = st.columns(3)
    with col1:
        led_panel = st.number_input("LED Panel 600x1200", value=fixtures.get("recessed_led_600x1200", 0), min_value=0, key=f"led_{current_room}")
    with col2:
        downlight = st.number_input("Downlights", value=fixtures.get("downlight", 0), min_value=0, key=f"dl_{current_room}")
    with col3:
        surface = st.number_input("Surface Mount", value=fixtures.get("surface_mount_led", 0), min_value=0, key=f"sm_{current_room}")

    st.markdown("##### Power Points")
    col1, col2, col3 = st.columns(3)
    with col1:
        socket_300 = st.number_input("Double @300mm", value=fixtures.get("double_socket_300", 0), min_value=0, key=f"s300_{current_room}")
    with col2:
        socket_1100 = st.number_input("Double @1100mm", value=fixtures.get("double_socket_1100", 0), min_value=0, key=f"s1100_{current_room}")
    with col3:
        data_point = st.number_input("Data Points", value=fixtures.get("data_point_cat6", 0), min_value=0, key=f"dp_{current_room}")

    st.markdown("##### Switches")
    col1, col2 = st.columns(2)
    with col1:
        switch_1 = st.number_input("1-Lever", value=fixtures.get("switch_1lever", 0), min_value=0, key=f"sw1_{current_room}")
    with col2:
        switch_2 = st.number_input("2-Lever", value=fixtures.get("switch_2lever", 0), min_value=0, key=f"sw2_{current_room}")

    # Navigation
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back", key="back_room"):
            if current_idx > 0:
                st.session_state.current_room_index -= 1
            else:
                st.session_state.guided_step = 5
            st.rerun()
    with col2:
        if st.button("⏭ Skip Room", key="skip_room"):
            st.session_state.current_room_index += 1
            st.rerun()
    with col3:
        if st.button("✓ Confirm & Next →", type="primary", key="confirm_room"):
            st.session_state.room_fixtures[current_room] = {
                "recessed_led_600x1200": led_panel,
                "downlight": downlight,
                "surface_mount_led": surface,
                "double_socket_300": socket_300,
                "double_socket_1100": socket_1100,
                "data_point_cat6": data_point,
                "switch_1lever": switch_1,
                "switch_2lever": switch_2,
            }
            pipeline.apply_room_fixtures(current_room, st.session_state.room_fixtures[current_room])
            st.session_state.current_room_index += 1
            st.rerun()


# ============================================================================
# STEP 7: CABLE ROUTES
# ============================================================================

def render_step_7_cable_routes():
    """Step 7: Extract cable routes from SLD."""
    section_header("Step 7: Cable Routes", "Extracted from SLD pages")

    pipeline = st.session_state.interactive_pipeline

    # Extract if not done
    if not st.session_state.cable_routes:
        with st.spinner("Extracting cable routes..."):
            result = pipeline.run_cable_routes_pass(st.session_state.sld_pages)
            if result.success:
                st.session_state.cable_routes = result.display_data.get("routes", [])

    routes = st.session_state.cable_routes
    if routes:
        st.success(f"✅ {len(routes)} cable routes found")
        import pandas as pd
        df = pd.DataFrame(routes)
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        st.session_state.cable_routes = edited_df.to_dict('records')
    else:
        st.info("No cable routes extracted. You can skip this step.")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Room Fixtures", use_container_width=True):
            st.session_state.guided_step = 6
            st.session_state.current_room_index = len(st.session_state.detected_rooms) - 1
            st.rerun()
    with col2:
        if st.button("🎯 Generate BOQ →", type="primary", use_container_width=True):
            pipeline.apply_cable_routes(st.session_state.cable_routes)
            st.session_state.guided_step = 8
            st.session_state.max_completed_step = 7
            st.rerun()


# ============================================================================
# STEP 8: REVIEW & EXPORT
# ============================================================================

def render_step_8_export():
    """Step 8: Review and export BOQ."""
    section_header("Step 8: Review & Export", "Final extraction summary")

    pipeline = st.session_state.interactive_pipeline

    # Build final result
    if st.session_state.final_extraction is None:
        with st.spinner("Building BOQ..."):
            st.session_state.final_extraction = pipeline.build_final_result()
            validation, _ = validate(st.session_state.final_extraction)
            st.session_state.final_validation = validation
            pricing, _ = price(st.session_state.final_extraction, validation, None, None)
            st.session_state.final_pricing = pricing

    extraction = st.session_state.final_extraction
    validation = st.session_state.final_validation
    pricing = st.session_state.final_pricing
    stats = pipeline.get_statistics()

    # Success
    st.success("🎉 **Extraction Complete!**")

    # Stats
    st.markdown("### Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("DBs", stats["db_schedules_extracted"])
    with col2:
        total_circuits = sum(len(s.get("circuits", [])) for s in st.session_state.db_schedules.values())
        st.metric("Circuits", total_circuits)
    with col3:
        st.metric("Rooms", stats["room_fixtures_extracted"])
    with col4:
        st.metric("Cables", stats["cable_routes"])

    # Compliance
    if validation:
        st.markdown("### SANS 10142-1 Compliance")
        score = validation.compliance_score
        if score >= 70:
            st.success(f"✅ Score: {score:.0f}%")
        elif score >= 40:
            st.warning(f"⚠️ Score: {score:.0f}%")
        else:
            st.error(f"❌ Score: {score:.0f}%")

    # API cost
    st.markdown("### API Usage")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tokens", f"{stats['total_tokens']:,}")
    with col2:
        st.metric("Cost", f"R{stats['total_cost_zar']:.2f}")

    # Export
    st.markdown("### Export")
    col1, col2 = st.columns(2)
    with col1:
        if HAS_OPENPYXL and pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                excel_bytes = export_professional_bq(pricing, extraction, project_name)
                st.download_button(
                    "📥 Download Excel BOQ",
                    data=excel_bytes,
                    file_name=f"{project_name}_BOQ.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Export error: {e}")

    with col2:
        if pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                pdf_bytes = generate_pdf_summary(pricing, extraction, validation, project_name, ServiceTier.COMMERCIAL)
                st.download_button(
                    "📄 Download PDF Summary",
                    data=pdf_bytes,
                    file_name=f"{project_name}_Summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF error: {e}")

    # Start over
    st.markdown("---")
    if st.button("🔄 Start New Extraction", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("guided_") or key in [
                "cover_pages", "sld_pages", "layout_pages",
                "interactive_pipeline", "project_info",
                "detected_dbs", "db_schedules", "detected_rooms", "room_fixtures",
                "cable_routes", "current_db_index", "current_room_index",
                "final_extraction", "final_validation", "final_pricing"
            ]:
                del st.session_state[key]
        st.rerun()


# ============================================================================
# MAIN PAGE
# ============================================================================

inject_custom_css()
init_session_state()

page_header(
    title="⚡ Guided Upload",
    subtitle="Step-by-step document upload • 70%+ accuracy target"
)

if not PIPELINE_AVAILABLE:
    st.error(f"Pipeline not available: {PIPELINE_IMPORT_ERROR}")
    st.stop()

if not LLM_API_KEY:
    st.error("No API key configured. Add GROQ_API_KEY to secrets.toml")
    st.stop()

# Sidebar
st.sidebar.markdown("### AI Status")
provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
st.sidebar.success(f"✓ {provider_name} ({provider_cost})")

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Upload documents step-by-step:**
1. Cover page → Project info
2. SLD pages → DB schedules
3. Layout pages → Room fixtures
4. Review & Export BOQ
""")

# Progress
render_progress_indicator()

# Render current step
step = st.session_state.guided_step

if step == 1:
    render_step_1_cover_upload()
elif step == 2:
    render_step_2_project_info()
elif step == 3:
    render_step_3_sld_upload()
elif step == 4:
    render_step_4_db_extraction()
elif step == 5:
    render_step_5_layout_upload()
elif step == 6:
    render_step_6_room_extraction()
elif step == 7:
    render_step_7_cable_routes()
elif step == 8:
    render_step_8_export()
