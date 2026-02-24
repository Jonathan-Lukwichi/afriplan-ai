"""
AfriPlan Electrical v4.11 - Guided Upload

Interactive step-by-step extraction with user validation at each stage.
Target: 70%+ extraction rate through human-in-the-loop validation.

8-Step Wizard:
1. Upload & Categorize Pages
2. Extract Project Info
3. Detect Distribution Boards
4. Extract DB Schedules (loop)
5. Detect Rooms
6. Extract Room Fixtures (loop)
7. Extract Cable Routes
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

# Page categories for user tagging
PAGE_CATEGORIES = ["Cover", "SLD", "Lighting", "Power", "Legend", "Other"]

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

    # Try Groq first (100% FREE!)
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
        provider = "groq"
        api_key = st.secrets["GROQ_API_KEY"]

    # Try xAI Grok
    if "XAI_API_KEY" in st.secrets:
        os.environ["XAI_API_KEY"] = st.secrets["XAI_API_KEY"]
        if provider is None:
            provider = "grok"
            api_key = st.secrets["XAI_API_KEY"]

    # Try Gemini
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
        if provider is None:
            provider = "gemini"
            api_key = st.secrets["GEMINI_API_KEY"]

    # Fall back to Claude
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
        if provider is None:
            provider = "claude"
            api_key = st.secrets["ANTHROPIC_API_KEY"]

    return provider, api_key


LLM_PROVIDER, LLM_API_KEY = load_api_keys()

# Provider labels
PROVIDER_LABELS = {
    "groq": ("Groq Llama 4", "100% FREE"),
    "grok": ("xAI Grok", "$25 FREE"),
    "gemini": ("Google Gemini", "FREE"),
    "claude": ("Claude", "Paid"),
}

# Model names by provider
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

        # Document data
        "guided_doc_set": None,
        "guided_pages": [],
        "guided_filename": "",

        # Page categorization (Step 1)
        "page_categories": {},

        # Pipeline instance
        "interactive_pipeline": None,

        # Extraction results (populated step by step)
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

def map_page_type_to_category(page_type) -> str:
    """Map PageType enum to category string."""
    if not PIPELINE_AVAILABLE:
        return "Other"

    mapping = {
        PageType.REGISTER: "Cover",
        PageType.SLD: "SLD",
        PageType.SCHEDULE: "SLD",
        PageType.LAYOUT_LIGHTING: "Lighting",
        PageType.LAYOUT_PLUGS: "Power",
        PageType.LAYOUT_COMBINED: "Lighting",
        PageType.OUTSIDE_LIGHTS: "Lighting",
        PageType.DETAIL: "Other",
        PageType.PHOTO: "Other",
        PageType.SPECIFICATION: "Other",
        PageType.UNKNOWN: "Other",
    }
    return mapping.get(page_type, "Other")


def get_categorized_pages(category: str) -> List:
    """Get pages matching a category."""
    pages = []
    for page in st.session_state.guided_pages:
        if st.session_state.page_categories.get(page.page_number) == category:
            pages.append(page)
    return pages


def get_confidence_color(confidence: float) -> str:
    """Return color based on confidence level."""
    if confidence >= 0.70:
        return "#22C55E"  # Green
    elif confidence >= 0.40:
        return "#F59E0B"  # Yellow
    else:
        return "#EF4444"  # Red


def render_confidence_badge(confidence: float):
    """Render a confidence score badge."""
    color = get_confidence_color(confidence)
    if confidence >= 0.70:
        label = "High"
    elif confidence >= 0.40:
        label = "Medium"
    else:
        label = "Low"

    st.markdown(f"""
    <div style="display: inline-block; padding: 4px 12px; border-radius: 12px;
                background: {color}20; border: 1px solid {color}40; margin-bottom: 1rem;">
        <span style="color: {color}; font-weight: 600;">
            {label} Confidence: {confidence*100:.0f}%
        </span>
    </div>
    """, unsafe_allow_html=True)


def render_progress_indicator():
    """Render the 8-step progress indicator."""
    step = st.session_state.guided_step
    max_step = st.session_state.max_completed_step

    steps = [
        ("1", "Upload"),
        ("2", "Project"),
        ("3", "DBs"),
        ("4", "Schedules"),
        ("5", "Rooms"),
        ("6", "Fixtures"),
        ("7", "Cables"),
        ("8", "Export"),
    ]

    cols = st.columns(8)
    for i, (num, name) in enumerate(steps):
        step_num = i + 1
        with cols[i]:
            if step_num == step:
                color = "#00D4FF"
                icon = "●"
            elif step_num <= max_step:
                color = "#22C55E"
                icon = "✓"
            else:
                color = "#64748b"
                icon = "○"

            st.markdown(f"""
            <div style="text-align: center;">
                <div style="color: {color}; font-size: 1.2rem; font-weight: bold;">{icon}</div>
                <div style="color: {color}; font-size: 0.7rem;">{name}</div>
            </div>
            """, unsafe_allow_html=True)


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
            st.error(f"Unsupported provider: {provider}")
            return None

        pipeline = InteractivePipeline(client, model, provider)

        # Set categorized pages
        categorized = {}
        for cat in PAGE_CATEGORIES:
            categorized[cat] = get_categorized_pages(cat)
        pipeline.set_categorized_pages(categorized)

        return pipeline

    except Exception as e:
        st.error(f"Error initializing pipeline: {e}")
        return None


# ============================================================================
# STEP 1: UPLOAD & CATEGORIZE PAGES
# ============================================================================

def render_step_1_upload_categorize():
    """Step 1: Upload document and categorize pages."""
    section_header("Step 1: Upload & Categorize Pages", "Tag each page by type")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload electrical drawing (PDF, PNG, JPG)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="guided_uploader"
    )

    if uploaded_file and not st.session_state.guided_pages:
        # Process upload
        with st.spinner("Processing document..."):
            doc_set, result = ingest([
                (uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)
            ])

            if result.success:
                st.session_state.guided_doc_set = doc_set
                # Flatten all pages from all documents
                all_pages = []
                for doc in doc_set.documents:
                    all_pages.extend(doc.pages)
                st.session_state.guided_pages = all_pages
                st.session_state.guided_filename = uploaded_file.name

                # Initialize categories based on auto-detection
                for page in all_pages:
                    category = map_page_type_to_category(page.page_type)
                    st.session_state.page_categories[page.page_number] = category

                st.rerun()
            else:
                st.error(f"Error processing file: {result.errors}")

    # Display page thumbnails if we have pages
    if st.session_state.guided_pages:
        st.success(f"**{len(st.session_state.guided_pages)} pages** loaded from {st.session_state.guided_filename}")

        st.markdown("### Categorize Each Page")
        st.markdown("*The AI auto-detected categories. Review and correct if needed.*")

        # 3-column grid
        cols = st.columns(3)

        for i, page in enumerate(st.session_state.guided_pages):
            col_idx = i % 3

            with cols[col_idx]:
                # Container for each page
                with st.container():
                    # Thumbnail
                    if page.image_base64:
                        st.image(
                            f"data:image/png;base64,{page.image_base64}",
                            caption=f"Page {page.page_number}",
                            width=200
                        )
                    else:
                        st.markdown(f"**Page {page.page_number}**")

                    # Category selector
                    current_cat = st.session_state.page_categories.get(
                        page.page_number, "Other"
                    )
                    new_cat = st.selectbox(
                        f"Category for Page {page.page_number}",
                        PAGE_CATEGORIES,
                        index=PAGE_CATEGORIES.index(current_cat) if current_cat in PAGE_CATEGORIES else 5,
                        key=f"cat_{page.page_number}",
                        label_visibility="collapsed"
                    )
                    st.session_state.page_categories[page.page_number] = new_cat

        # Category summary
        st.markdown("---")
        st.markdown("### Category Summary")
        summary_cols = st.columns(6)
        for i, cat in enumerate(PAGE_CATEGORIES):
            count = sum(1 for v in st.session_state.page_categories.values() if v == cat)
            with summary_cols[i]:
                color = "#22C55E" if count > 0 else "#64748b"
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem; border-radius: 8px;
                            background: {color}15; border: 1px solid {color}40;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{count}</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">{cat}</div>
                </div>
                """, unsafe_allow_html=True)

        # Continue button
        st.markdown("---")
        if st.button("Continue to Extraction →", type="primary", use_container_width=True):
            # Initialize pipeline with categorized pages
            pipeline = init_pipeline()
            if pipeline:
                st.session_state.interactive_pipeline = pipeline
                st.session_state.guided_step = 2
                st.session_state.max_completed_step = 1
                st.rerun()
            else:
                st.error("Failed to initialize pipeline. Check API key configuration.")


# ============================================================================
# STEP 2: EXTRACT PROJECT INFO
# ============================================================================

def render_step_2_project_info():
    """Step 2: Extract and validate project information."""
    section_header("Step 2: Extract Project Information", "From cover page")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Run extraction if not already done
    if not st.session_state.project_info:
        cover_pages = get_categorized_pages("Cover")
        if cover_pages:
            with st.spinner("Extracting project information from cover page..."):
                result = pipeline.run_project_info_pass(cover_pages)

                if result.success:
                    st.session_state.project_info = result.display_data
                else:
                    st.warning("Could not extract project info. Please fill in manually.")
                    st.session_state.project_info = {
                        "project_name": "",
                        "client_name": "",
                        "consultant_name": "",
                        "date": "",
                        "revision": "",
                    }
        else:
            st.warning("No cover pages found. Please fill in manually.")
            st.session_state.project_info = {
                "project_name": "",
                "client_name": "",
                "consultant_name": "",
                "date": "",
                "revision": "",
            }

    # Display editable fields
    confidence = 0.85 if st.session_state.project_info.get("project_name") else 0.3
    render_confidence_badge(confidence)

    with st.form("project_info_form"):
        st.markdown("**Edit the extracted values if needed:**")

        project_name = st.text_input(
            "Project Name",
            value=st.session_state.project_info.get("project_name", "")
        )
        client_name = st.text_input(
            "Client Name",
            value=st.session_state.project_info.get("client_name", "")
        )
        consultant_name = st.text_input(
            "Consultant/Engineer",
            value=st.session_state.project_info.get("consultant_name", "")
        )

        col1, col2 = st.columns(2)
        with col1:
            date = st.text_input(
                "Date",
                value=st.session_state.project_info.get("date", "")
            )
        with col2:
            revision = st.text_input(
                "Revision",
                value=st.session_state.project_info.get("revision", "")
            )

        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("← Back", use_container_width=True)
        with col2:
            confirm = st.form_submit_button("Confirm & Continue →", type="primary", use_container_width=True)

        if back:
            st.session_state.guided_step = 1
            st.rerun()

        if confirm:
            # Save validated data
            validated_data = {
                "project_name": project_name,
                "client_name": client_name,
                "consultant_name": consultant_name,
                "date": date,
                "revision": revision,
            }
            st.session_state.project_info = validated_data
            pipeline.apply_project_info(validated_data)

            st.session_state.guided_step = 3
            st.session_state.max_completed_step = 2
            st.rerun()


# ============================================================================
# STEP 3: DETECT DISTRIBUTION BOARDS
# ============================================================================

def render_step_3_db_detection():
    """Step 3: Detect and validate distribution boards."""
    section_header("Step 3: Detect Distribution Boards", "From SLD pages")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Run detection if not already done
    if not st.session_state.detected_dbs:
        sld_pages = get_categorized_pages("SLD")
        if sld_pages:
            with st.spinner("Detecting distribution boards from SLD pages..."):
                result = pipeline.run_db_detection_pass(sld_pages)

                if result.success:
                    st.session_state.detected_dbs = [
                        db["name"] for db in result.display_data.get("dbs", [])
                    ]
                    st.success(f"Found {len(st.session_state.detected_dbs)} distribution boards")
                else:
                    st.warning("No DBs detected. Add them manually below.")
                    st.session_state.detected_dbs = []
        else:
            st.warning("No SLD pages found. Add DBs manually.")
            st.session_state.detected_dbs = []

    # Display with checkboxes
    confidence = 0.92 if st.session_state.detected_dbs else 0.3
    render_confidence_badge(confidence)

    st.markdown(f"**{len(st.session_state.detected_dbs)} DBs detected.** Select which ones to process:")

    # Checkbox for each DB
    selected_dbs = []
    for db_name in st.session_state.detected_dbs:
        if st.checkbox(db_name, value=True, key=f"db_select_{db_name}"):
            selected_dbs.append(db_name)

    # Add new DB
    st.markdown("---")
    st.markdown("**Add Missing DB:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_db_name = st.text_input("DB Name (e.g., DB-S5)", key="new_db_input", label_visibility="collapsed")
    with col2:
        if st.button("Add", use_container_width=True):
            if new_db_name and new_db_name not in st.session_state.detected_dbs:
                st.session_state.detected_dbs.append(new_db_name)
                st.rerun()

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.guided_step = 2
            st.rerun()

    with col2:
        if st.button("Confirm & Continue →", type="primary", use_container_width=True):
            if selected_dbs:
                pipeline.apply_detected_dbs(selected_dbs)
                st.session_state.detected_dbs = selected_dbs
                st.session_state.current_db_index = 0
                st.session_state.guided_step = 4
                st.session_state.max_completed_step = 3
                st.rerun()
            else:
                st.error("Please select at least one DB or add one manually.")


# ============================================================================
# STEP 4: EXTRACT DB SCHEDULES (LOOP)
# ============================================================================

def render_step_4_db_schedules():
    """Step 4: Extract DB schedules one at a time."""
    pipeline: InteractivePipeline = st.session_state.interactive_pipeline
    detected_dbs = st.session_state.detected_dbs
    current_idx = st.session_state.current_db_index

    if current_idx >= len(detected_dbs):
        # All DBs processed, move to next step
        pipeline.mark_db_schedules_complete()
        st.session_state.guided_step = 5
        st.session_state.max_completed_step = 4
        st.rerun()
        return

    current_db = detected_dbs[current_idx]
    section_header(f"Step 4: Extract DB Schedule ({current_idx + 1}/{len(detected_dbs)})", f"Processing {current_db}")

    # Check if we already have this DB's schedule
    if current_db not in st.session_state.db_schedules:
        sld_pages = get_categorized_pages("SLD")
        with st.spinner(f"Extracting circuit schedule for {current_db}..."):
            result = pipeline.run_db_schedule_pass(current_db, sld_pages)

            if result.success:
                st.session_state.db_schedules[current_db] = result.display_data
            else:
                st.warning(f"Could not extract schedule for {current_db}. Fill in manually or skip.")
                st.session_state.db_schedules[current_db] = {
                    "db_name": current_db,
                    "main_breaker_a": 0,
                    "supply_from": "",
                    "circuits": [],
                    "schedule_found": False,
                }

    schedule = st.session_state.db_schedules.get(current_db, {})
    confidence = 0.78 if schedule.get("schedule_found") else 0.3
    render_confidence_badge(confidence)

    # Display editable fields
    st.markdown("**DB Header Information:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        main_breaker = st.number_input("Main Breaker (A)", value=schedule.get("main_breaker_a", 0), key=f"mb_{current_db}")
    with col2:
        supply_from = st.text_input("Supply From", value=schedule.get("supply_from", ""), key=f"sf_{current_db}")
    with col3:
        total_ways = st.number_input("Total Ways", value=schedule.get("total_ways", 0), key=f"tw_{current_db}")

    # Circuits table
    st.markdown("**Circuits:**")
    circuits = schedule.get("circuits", [])
    if circuits:
        # Create editable dataframe
        import pandas as pd
        df = pd.DataFrame(circuits)
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key=f"circuits_{current_db}"
        )
        circuits = edited_df.to_dict('records')
    else:
        st.info("No circuits extracted. Add manually if needed.")

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back", use_container_width=True):
            if current_idx > 0:
                st.session_state.current_db_index = current_idx - 1
            else:
                st.session_state.guided_step = 3
            st.rerun()

    with col2:
        if st.button("Skip DB", use_container_width=True):
            # Remove from schedules and move to next
            if current_db in st.session_state.db_schedules:
                del st.session_state.db_schedules[current_db]
            st.session_state.current_db_index = current_idx + 1
            st.rerun()

    with col3:
        if st.button("Confirm DB & Continue →", type="primary", use_container_width=True):
            # Save updated schedule
            updated_schedule = {
                "db_name": current_db,
                "main_breaker_a": main_breaker,
                "supply_from": supply_from,
                "total_ways": total_ways,
                "circuits": circuits,
                "schedule_found": True,
            }
            st.session_state.db_schedules[current_db] = updated_schedule
            pipeline.apply_db_schedule(current_db, updated_schedule)
            st.session_state.current_db_index = current_idx + 1
            st.rerun()


# ============================================================================
# STEP 5: DETECT ROOMS
# ============================================================================

def render_step_5_room_detection():
    """Step 5: Detect rooms from layout pages."""
    section_header("Step 5: Detect Rooms & Areas", "From layout pages")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Run detection if not already done
    if not st.session_state.detected_rooms:
        lighting_pages = get_categorized_pages("Lighting")
        power_pages = get_categorized_pages("Power")
        layout_pages = lighting_pages + power_pages

        if layout_pages:
            with st.spinner("Detecting rooms from layout pages..."):
                result = pipeline.run_room_detection_pass(layout_pages)

                if result.success:
                    st.session_state.detected_rooms = [
                        room["name"] for room in result.display_data.get("rooms", [])
                    ]
                    st.success(f"Found {len(st.session_state.detected_rooms)} rooms")
                else:
                    st.warning("No rooms detected. Add them manually below.")
                    st.session_state.detected_rooms = []
        else:
            st.warning("No layout pages found. Add rooms manually.")
            st.session_state.detected_rooms = []

    # Display with checkboxes
    confidence = 0.88 if st.session_state.detected_rooms else 0.3
    render_confidence_badge(confidence)

    st.markdown(f"**{len(st.session_state.detected_rooms)} rooms detected.** Select which ones to process:")

    # Show in 2 columns
    col1, col2 = st.columns(2)
    selected_rooms = []
    for i, room_name in enumerate(st.session_state.detected_rooms):
        with col1 if i % 2 == 0 else col2:
            if st.checkbox(room_name, value=True, key=f"room_select_{room_name}"):
                selected_rooms.append(room_name)

    # Add new room
    st.markdown("---")
    st.markdown("**Add Missing Room:**")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_room_name = st.text_input("Room Name", key="new_room_input", label_visibility="collapsed")
    with col2:
        if st.button("Add", key="add_room_btn", use_container_width=True):
            if new_room_name and new_room_name not in st.session_state.detected_rooms:
                st.session_state.detected_rooms.append(new_room_name)
                st.rerun()

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back", key="back_step5", use_container_width=True):
            st.session_state.guided_step = 4
            st.session_state.current_db_index = len(st.session_state.detected_dbs) - 1
            st.rerun()

    with col2:
        if st.button("Confirm & Continue →", key="confirm_step5", type="primary", use_container_width=True):
            if selected_rooms:
                pipeline.apply_detected_rooms(selected_rooms)
                st.session_state.detected_rooms = selected_rooms
                st.session_state.current_room_index = 0
                st.session_state.guided_step = 6
                st.session_state.max_completed_step = 5
                st.rerun()
            else:
                st.error("Please select at least one room or add one manually.")


# ============================================================================
# STEP 6: EXTRACT ROOM FIXTURES (LOOP)
# ============================================================================

def render_step_6_room_fixtures():
    """Step 6: Extract room fixtures one at a time."""
    pipeline: InteractivePipeline = st.session_state.interactive_pipeline
    detected_rooms = st.session_state.detected_rooms
    current_idx = st.session_state.current_room_index

    if current_idx >= len(detected_rooms):
        # All rooms processed, move to next step
        pipeline.mark_room_fixtures_complete()
        st.session_state.guided_step = 7
        st.session_state.max_completed_step = 6
        st.rerun()
        return

    current_room = detected_rooms[current_idx]
    section_header(f"Step 6: Extract Room Fixtures ({current_idx + 1}/{len(detected_rooms)})", f"Processing {current_room}")

    # Check if we already have this room's fixtures
    if current_room not in st.session_state.room_fixtures:
        lighting_pages = get_categorized_pages("Lighting")
        power_pages = get_categorized_pages("Power")
        layout_pages = lighting_pages + power_pages

        with st.spinner(f"Extracting fixtures for {current_room}..."):
            result = pipeline.run_room_fixtures_pass(current_room, layout_pages)

            if result.success:
                st.session_state.room_fixtures[current_room] = result.display_data.get("fixtures", {})
            else:
                st.warning(f"Could not extract fixtures for {current_room}. Fill in manually or skip.")
                st.session_state.room_fixtures[current_room] = {}

    fixtures = st.session_state.room_fixtures.get(current_room, {})
    confidence = 0.72 if fixtures else 0.3
    render_confidence_badge(confidence)

    # Display editable fixture counts
    st.markdown("**Lights:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        led_panel = st.number_input("LED Panel 600x1200", value=fixtures.get("recessed_led_600x1200", 0), key=f"led_{current_room}")
    with col2:
        downlight = st.number_input("Downlights", value=fixtures.get("downlight", 0), key=f"dl_{current_room}")
    with col3:
        surface = st.number_input("Surface Mount", value=fixtures.get("surface_mount_led", 0), key=f"sm_{current_room}")

    st.markdown("**Sockets:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        socket_300 = st.number_input("Double @300mm", value=fixtures.get("double_socket_300", 0), key=f"s300_{current_room}")
    with col2:
        socket_1100 = st.number_input("Double @1100mm", value=fixtures.get("double_socket_1100", 0), key=f"s1100_{current_room}")
    with col3:
        data_point = st.number_input("Data Points", value=fixtures.get("data_point_cat6", 0), key=f"dp_{current_room}")

    st.markdown("**Switches:**")
    col1, col2 = st.columns(2)
    with col1:
        switch_1 = st.number_input("1-Lever Switch", value=fixtures.get("switch_1lever", 0), key=f"sw1_{current_room}")
    with col2:
        switch_2 = st.number_input("2-Lever Switch", value=fixtures.get("switch_2lever", 0), key=f"sw2_{current_room}")

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back", key="back_step6", use_container_width=True):
            if current_idx > 0:
                st.session_state.current_room_index = current_idx - 1
            else:
                st.session_state.guided_step = 5
            st.rerun()

    with col2:
        if st.button("Skip Room", key="skip_room", use_container_width=True):
            if current_room in st.session_state.room_fixtures:
                del st.session_state.room_fixtures[current_room]
            st.session_state.current_room_index = current_idx + 1
            st.rerun()

    with col3:
        if st.button("Confirm Room & Continue →", key="confirm_room", type="primary", use_container_width=True):
            # Save updated fixtures
            updated_fixtures = {
                "recessed_led_600x1200": led_panel,
                "downlight": downlight,
                "surface_mount_led": surface,
                "double_socket_300": socket_300,
                "double_socket_1100": socket_1100,
                "data_point_cat6": data_point,
                "switch_1lever": switch_1,
                "switch_2lever": switch_2,
            }
            st.session_state.room_fixtures[current_room] = updated_fixtures
            pipeline.apply_room_fixtures(current_room, updated_fixtures)
            st.session_state.current_room_index = current_idx + 1
            st.rerun()


# ============================================================================
# STEP 7: EXTRACT CABLE ROUTES
# ============================================================================

def render_step_7_cable_routes():
    """Step 7: Extract cable routes."""
    section_header("Step 7: Extract Cable Routes", "Between distribution boards")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Run extraction if not already done
    if not st.session_state.cable_routes:
        sld_pages = get_categorized_pages("SLD")
        if sld_pages:
            with st.spinner("Extracting cable routes from SLD pages..."):
                result = pipeline.run_cable_routes_pass(sld_pages)

                if result.success:
                    st.session_state.cable_routes = result.display_data.get("routes", [])
                else:
                    st.session_state.cable_routes = []
        else:
            st.session_state.cable_routes = []

    confidence = 0.85 if st.session_state.cable_routes else 0.4
    render_confidence_badge(confidence)

    st.markdown(f"**{len(st.session_state.cable_routes)} cable routes detected.**")

    # Display as editable table
    if st.session_state.cable_routes:
        import pandas as pd
        df = pd.DataFrame(st.session_state.cable_routes)
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key="cable_routes_editor"
        )
        st.session_state.cable_routes = edited_df.to_dict('records')
    else:
        st.info("No cable routes extracted. You can add them manually in the table editor.")

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back", key="back_step7", use_container_width=True):
            st.session_state.guided_step = 6
            st.session_state.current_room_index = len(st.session_state.detected_rooms) - 1
            st.rerun()

    with col2:
        if st.button("Finalize Extraction →", key="finalize", type="primary", use_container_width=True):
            pipeline.apply_cable_routes(st.session_state.cable_routes)
            st.session_state.guided_step = 8
            st.session_state.max_completed_step = 7
            st.rerun()


# ============================================================================
# STEP 8: REVIEW & EXPORT
# ============================================================================

def render_step_8_review_export():
    """Step 8: Review and export final results."""
    section_header("Step 8: Review & Export", "Final extraction summary")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Build final extraction result
    if st.session_state.final_extraction is None:
        with st.spinner("Building final extraction result..."):
            st.session_state.final_extraction = pipeline.build_final_result()

            # Run validation
            validation, _ = validate(st.session_state.final_extraction)
            st.session_state.final_validation = validation

            # Run pricing
            pricing, _ = price(st.session_state.final_extraction, validation, None, None)
            st.session_state.final_pricing = pricing

    extraction = st.session_state.final_extraction
    validation = st.session_state.final_validation
    pricing = st.session_state.final_pricing

    # Statistics
    stats = pipeline.get_statistics()

    st.markdown("### Extraction Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("DBs Extracted", stats["db_schedules_extracted"])
    with col2:
        total_circuits = sum(
            len(s.get("circuits", [])) for s in st.session_state.db_schedules.values()
        )
        st.metric("Total Circuits", total_circuits)
    with col3:
        st.metric("Rooms Processed", stats["room_fixtures_extracted"])
    with col4:
        st.metric("Cable Routes", stats["cable_routes"])

    # Compliance score
    if validation:
        st.markdown("### SANS 10142-1 Compliance")
        score = validation.compliance_score
        color = get_confidence_color(score / 100)
        st.markdown(f"""
        <div style="background: {color}15; border: 1px solid {color}40;
                    border-radius: 12px; padding: 1rem; margin: 1rem 0;">
            <div style="font-size: 2rem; font-weight: bold; color: {color};">{score:.0f}%</div>
            <div style="color: #94a3b8;">Compliance Score</div>
        </div>
        """, unsafe_allow_html=True)

    # Cost summary
    st.markdown("### API Usage")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")
    with col2:
        st.metric("Estimated Cost", f"R{stats['total_cost_zar']:.2f}")

    # Export buttons
    st.markdown("---")
    st.markdown("### Export Options")

    col1, col2 = st.columns(2)

    with col1:
        if HAS_OPENPYXL and pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                excel_bytes = export_professional_bq(
                    pricing=pricing,
                    extraction=extraction,
                    project_name=project_name,
                )
                st.download_button(
                    label="📥 Download Professional Excel BQ",
                    data=excel_bytes,
                    file_name=f"{project_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as e:
                st.error(f"Excel export error: {e}")
        else:
            st.warning("Excel export not available.")

    with col2:
        if pricing:
            try:
                project_name = st.session_state.project_info.get("project_name", "Project")
                pdf_bytes = generate_pdf_summary(
                    pricing,
                    extraction,
                    validation,
                    project_name,
                    ServiceTier.COMMERCIAL,
                )
                st.download_button(
                    label="📄 Download PDF Summary",
                    data=pdf_bytes,
                    file_name=f"{project_name}_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF export error: {e}")

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to Edit", key="back_step8", use_container_width=True):
            st.session_state.final_extraction = None
            st.session_state.final_validation = None
            st.session_state.final_pricing = None
            st.session_state.guided_step = 7
            st.rerun()

    with col2:
        if st.button("Start New Extraction", key="start_new", use_container_width=True):
            # Clear all state
            for key in list(st.session_state.keys()):
                if key.startswith("guided_") or key in [
                    "page_categories", "interactive_pipeline", "project_info",
                    "detected_dbs", "db_schedules", "detected_rooms", "room_fixtures",
                    "cable_routes", "current_db_index", "current_room_index",
                    "final_extraction", "final_validation", "final_pricing"
                ]:
                    del st.session_state[key]
            init_session_state()
            st.rerun()


# ============================================================================
# MAIN PAGE
# ============================================================================

# Apply custom styling
inject_custom_css()

# Initialize session state
init_session_state()

# Page header
page_header(
    title="Guided Upload",
    subtitle="Step-by-step extraction with validation"
)

# Check if pipeline is available
if not PIPELINE_AVAILABLE:
    st.error(f"Pipeline not available: {PIPELINE_IMPORT_ERROR}")
    st.stop()

if not LLM_API_KEY:
    st.error("No API key configured. Add GROQ_API_KEY to secrets.toml")
    st.stop()

# Provider info
provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
st.sidebar.markdown("### Pipeline Status")
st.sidebar.success(f"✓ {provider_name} ({provider_cost})")

# Progress indicator
render_progress_indicator()
st.markdown("---")

# Render current step
step = st.session_state.guided_step

if step == 1:
    render_step_1_upload_categorize()
elif step == 2:
    render_step_2_project_info()
elif step == 3:
    render_step_3_db_detection()
elif step == 4:
    render_step_4_db_schedules()
elif step == 5:
    render_step_5_room_detection()
elif step == 6:
    render_step_6_room_fixtures()
elif step == 7:
    render_step_7_cable_routes()
elif step == 8:
    render_step_8_review_export()
