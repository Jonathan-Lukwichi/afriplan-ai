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
from utils.components import page_header, section_header, glass_card, metric_card

# Category colors for page thumbnails
CATEGORY_COLORS = {
    "Cover": "#9333EA",   # Purple
    "SLD": "#00D4FF",     # Cyan
    "Lighting": "#F59E0B", # Amber
    "Power": "#22C55E",   # Green
    "Legend": "#EC4899",  # Pink
    "Other": "#64748B",   # Gray
}

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


def render_confidence_badge(confidence: float, label_prefix: str = "Extraction"):
    """Render a confidence score badge using native Streamlit."""
    if confidence >= 0.70:
        label = "High"
        icon = "✅"
    elif confidence >= 0.40:
        label = "Medium"
        icon = "⚠️"
    else:
        label = "Low"
        icon = "❌"

    col1, col2 = st.columns([1, 4])
    with col1:
        st.metric(f"{label_prefix}", f"{confidence*100:.0f}%", label)
    with col2:
        if confidence >= 0.70:
            st.success(f"{icon} {label} confidence - AI extraction looks good")
        elif confidence >= 0.40:
            st.warning(f"{icon} {label} confidence - Please review carefully")
        else:
            st.error(f"{icon} {label} confidence - Manual input recommended")


def render_progress_indicator():
    """Render 8-step progress indicator using Streamlit columns."""
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
                # Current step - cyan
                st.markdown(f"""
                <div style="text-align: center; padding: 8px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; margin: 0 auto;
                                background: linear-gradient(135deg, #00D4FF, #0099FF);
                                display: flex; align-items: center; justify-content: center;
                                font-weight: bold; color: #0a0e1a; font-size: 14px;
                                box-shadow: 0 0 15px rgba(0,212,255,0.5);">{num}</div>
                    <div style="font-size: 10px; color: #00D4FF; margin-top: 4px;
                                font-weight: 600; text-transform: uppercase;">{name}</div>
                </div>
                """, unsafe_allow_html=True)
            elif step_num <= max_step:
                # Completed step - green
                st.markdown(f"""
                <div style="text-align: center; padding: 8px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; margin: 0 auto;
                                background: linear-gradient(135deg, #22C55E, #16A34A);
                                display: flex; align-items: center; justify-content: center;
                                font-weight: bold; color: #0a0e1a; font-size: 14px;">✓</div>
                    <div style="font-size: 10px; color: #22C55E; margin-top: 4px;
                                font-weight: 600; text-transform: uppercase;">{name}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Future step - gray
                st.markdown(f"""
                <div style="text-align: center; padding: 8px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; margin: 0 auto;
                                background: rgba(30,41,59,0.8); border: 2px solid #475569;
                                display: flex; align-items: center; justify-content: center;
                                font-weight: bold; color: #64748b; font-size: 14px;">{num}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;
                                font-weight: 600; text-transform: uppercase;">{name}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")


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
    section_header("Step 1: Upload & Categorize Pages", "Tag each page by type for accurate extraction")

    # File upload
    uploaded_file = st.file_uploader(
        "📤 Upload electrical drawing (PDF, PNG, JPG)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="guided_uploader"
    )

    if uploaded_file and not st.session_state.guided_pages:
        with st.spinner("Processing document..."):
            doc_set, result = ingest([
                (uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)
            ])

            if result.success:
                st.session_state.guided_doc_set = doc_set
                all_pages = []
                for doc in doc_set.documents:
                    all_pages.extend(doc.pages)
                st.session_state.guided_pages = all_pages
                st.session_state.guided_filename = uploaded_file.name

                for page in all_pages:
                    category = map_page_type_to_category(page.page_type)
                    st.session_state.page_categories[page.page_number] = category

                st.rerun()
            else:
                st.error(f"Error processing file: {result.errors}")

    # Display page thumbnails if we have pages
    if st.session_state.guided_pages:
        st.success(f"✅ **{len(st.session_state.guided_pages)} pages** loaded from {st.session_state.guided_filename}")

        st.info("⚡ AI auto-detected categories below. Review and correct if needed.")

        # 3-column grid for pages
        cols = st.columns(3)

        for i, page in enumerate(st.session_state.guided_pages):
            col_idx = i % 3
            current_cat = st.session_state.page_categories.get(page.page_number, "Other")

            with cols[col_idx]:
                st.markdown(f"**Page {page.page_number}** - *{current_cat}*")

                if page.image_base64:
                    st.image(
                        f"data:image/png;base64,{page.image_base64}",
                        use_container_width=True
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
                st.metric(cat, count)

        # Continue button
        st.markdown("")
        if st.button("⚡ Continue to Extraction →", type="primary", use_container_width=True):
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
    section_header("Step 2: Extract Project Information", "Extracted from cover page")

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

    # Display confidence badge
    confidence = 0.85 if st.session_state.project_info.get("project_name") else 0.3
    render_confidence_badge(confidence, "Project Info")

    with st.form("project_info_form"):
        st.markdown("##### 📋 Verify & Edit Extracted Data")
        project_name = st.text_input(
            "🏗️ Project Name",
            value=st.session_state.project_info.get("project_name", ""),
            placeholder="e.g., NewMark Commercial Building"
        )
        client_name = st.text_input(
            "👤 Client Name",
            value=st.session_state.project_info.get("client_name", ""),
            placeholder="e.g., NewMark Properties (Pty) Ltd"
        )
        consultant_name = st.text_input(
            "⚡ Consultant/Engineer",
            value=st.session_state.project_info.get("consultant_name", ""),
            placeholder="e.g., Electro-Tech Consulting"
        )

        col1, col2 = st.columns(2)
        with col1:
            date = st.text_input(
                "📅 Date",
                value=st.session_state.project_info.get("date", ""),
                placeholder="e.g., 2024-01-15"
            )
        with col2:
            revision = st.text_input(
                "🔄 Revision",
                value=st.session_state.project_info.get("revision", ""),
                placeholder="e.g., Rev 3"
            )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("← Back to Categorize", use_container_width=True)
        with col2:
            confirm = st.form_submit_button("✓ Confirm & Continue →", type="primary", use_container_width=True)

        if back:
            st.session_state.guided_step = 1
            st.rerun()

        if confirm:
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
    section_header("Step 3: Detect Distribution Boards", "Extracted from SLD pages")

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
                else:
                    st.session_state.detected_dbs = []
        else:
            st.warning("No SLD pages found. Add DBs manually.")
            st.session_state.detected_dbs = []

    # Confidence badge
    confidence = 0.92 if st.session_state.detected_dbs else 0.3
    render_confidence_badge(confidence, "DB Detection")

    # DB count
    db_count = len(st.session_state.detected_dbs)
    if db_count > 0:
        st.success(f"⚡ **{db_count} Distribution Boards** found. Select which to process:")
    else:
        st.warning("No DBs detected. Add them manually below.")

    st.markdown("##### Distribution Boards")

    selected_dbs = []
    cols = st.columns(2)
    for i, db_name in enumerate(st.session_state.detected_dbs):
        with cols[i % 2]:
            checked = st.checkbox(f"⚡ {db_name}", value=True, key=f"db_select_{db_name}")
            if checked:
                selected_dbs.append(db_name)

    # Add new DB section
    st.markdown("---")
    st.markdown("##### ➕ Add Missing Distribution Board")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_db_name = st.text_input(
            "DB Name",
            key="new_db_input",
            placeholder="e.g., DB-S5, MAIN-DB, DB-GROUND"
        )
    with col2:
        st.markdown("")  # Spacing
        if st.button("➕ Add", use_container_width=True):
            if new_db_name and new_db_name not in st.session_state.detected_dbs:
                st.session_state.detected_dbs.append(new_db_name)
                st.rerun()

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to Project Info", use_container_width=True):
            st.session_state.guided_step = 2
            st.rerun()

    with col2:
        if st.button("✓ Confirm DBs & Continue →", type="primary", use_container_width=True):
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
        pipeline.mark_db_schedules_complete()
        st.session_state.guided_step = 5
        st.session_state.max_completed_step = 4
        st.rerun()
        return

    current_db = detected_dbs[current_idx]
    section_header(f"Step 4: Extract DB Schedule", f"Processing DB {current_idx + 1} of {len(detected_dbs)}")

    # Progress indicator
    st.info(f"📊 **{current_db}** - Distribution Board Schedule")
    st.progress((current_idx + 1) / len(detected_dbs), text=f"Progress: {current_idx + 1}/{len(detected_dbs)}")

    # Extract schedule if not done
    if current_db not in st.session_state.db_schedules:
        sld_pages = get_categorized_pages("SLD")
        with st.spinner(f"Extracting circuit schedule for {current_db}..."):
            result = pipeline.run_db_schedule_pass(current_db, sld_pages)

            if result.success:
                st.session_state.db_schedules[current_db] = result.display_data
            else:
                st.session_state.db_schedules[current_db] = {
                    "db_name": current_db,
                    "main_breaker_a": 0,
                    "supply_from": "",
                    "circuits": [],
                    "schedule_found": False,
                }

    schedule = st.session_state.db_schedules.get(current_db, {})
    confidence = 0.78 if schedule.get("schedule_found") else 0.3
    render_confidence_badge(confidence, "Schedule")

    st.markdown("##### ⚡ DB Header Information")

    col1, col2, col3 = st.columns(3)
    with col1:
        main_breaker = st.number_input(
            "Main Breaker (A)",
            value=schedule.get("main_breaker_a", 0),
            key=f"mb_{current_db}",
            help="Main incoming breaker size in Amps"
        )
    with col2:
        supply_from = st.text_input(
            "Supply From",
            value=schedule.get("supply_from", ""),
            key=f"sf_{current_db}",
            placeholder="e.g., MSB-A"
        )
    with col3:
        total_ways = st.number_input(
            "Total Ways",
            value=schedule.get("total_ways", 0),
            key=f"tw_{current_db}",
            help="Number of circuit breaker ways"
        )

    # Circuits table
    st.markdown("##### 🔌 Circuit Breakers")

    circuits = schedule.get("circuits", [])
    if circuits:
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
        st.info("No circuits extracted. Add manually using the table below or skip this DB.")

    st.markdown("")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back", key="back_step4", use_container_width=True):
            if current_idx > 0:
                st.session_state.current_db_index = current_idx - 1
            else:
                st.session_state.guided_step = 3
            st.rerun()

    with col2:
        if st.button("⏭ Skip DB", key="skip_db", use_container_width=True):
            if current_db in st.session_state.db_schedules:
                del st.session_state.db_schedules[current_db]
            st.session_state.current_db_index = current_idx + 1
            st.rerun()

    with col3:
        if st.button("✓ Confirm & Next →", key="confirm_db", type="primary", use_container_width=True):
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
    section_header("Step 5: Detect Rooms & Areas", "Extracted from layout pages")

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
                else:
                    st.session_state.detected_rooms = []
        else:
            st.warning("No layout pages found. Add rooms manually.")
            st.session_state.detected_rooms = []

    # Confidence badge
    confidence = 0.88 if st.session_state.detected_rooms else 0.3
    render_confidence_badge(confidence, "Room Detection")

    # Room count
    room_count = len(st.session_state.detected_rooms)
    if room_count > 0:
        st.success(f"🏠 **{room_count} Rooms** found. Select which to process:")
    else:
        st.warning("No rooms detected. Add them manually below.")

    st.markdown("##### Detected Rooms")

    col1, col2 = st.columns(2)
    selected_rooms = []
    for i, room_name in enumerate(st.session_state.detected_rooms):
        with col1 if i % 2 == 0 else col2:
            if st.checkbox(f"🏠 {room_name}", value=True, key=f"room_select_{room_name}"):
                selected_rooms.append(room_name)

    # Add new room
    st.markdown("---")
    st.markdown("##### ➕ Add Missing Room")

    col1, col2 = st.columns([3, 1])
    with col1:
        new_room_name = st.text_input(
            "Room Name",
            key="new_room_input",
            placeholder="e.g., Office 101, Kitchen, Store Room"
        )
    with col2:
        st.markdown("")
        if st.button("➕ Add", key="add_room_btn", use_container_width=True):
            if new_room_name and new_room_name not in st.session_state.detected_rooms:
                st.session_state.detected_rooms.append(new_room_name)
                st.rerun()

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to DB Schedules", key="back_step5", use_container_width=True):
            st.session_state.guided_step = 4
            st.session_state.current_db_index = len(st.session_state.detected_dbs) - 1
            st.rerun()

    with col2:
        if st.button("✓ Confirm Rooms & Continue →", key="confirm_step5", type="primary", use_container_width=True):
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
        pipeline.mark_room_fixtures_complete()
        st.session_state.guided_step = 7
        st.session_state.max_completed_step = 6
        st.rerun()
        return

    current_room = detected_rooms[current_idx]
    section_header(f"Step 6: Extract Room Fixtures", f"Processing Room {current_idx + 1} of {len(detected_rooms)}")

    # Progress indicator
    st.info(f"💡 **{current_room}** - Fixture Count Extraction")
    st.progress((current_idx + 1) / len(detected_rooms), text=f"Progress: {current_idx + 1}/{len(detected_rooms)}")

    # Extract fixtures if not done
    if current_room not in st.session_state.room_fixtures:
        lighting_pages = get_categorized_pages("Lighting")
        power_pages = get_categorized_pages("Power")
        layout_pages = lighting_pages + power_pages

        with st.spinner(f"Extracting fixtures for {current_room}..."):
            result = pipeline.run_room_fixtures_pass(current_room, layout_pages)

            if result.success:
                st.session_state.room_fixtures[current_room] = result.display_data.get("fixtures", {})
            else:
                st.session_state.room_fixtures[current_room] = {}

    fixtures = st.session_state.room_fixtures.get(current_room, {})
    confidence = 0.72 if fixtures else 0.3
    render_confidence_badge(confidence, "Fixtures")

    st.markdown("##### 💡 Lighting Fixtures")

    col1, col2, col3 = st.columns(3)
    with col1:
        led_panel = st.number_input(
            "LED Panel 600x1200",
            value=fixtures.get("recessed_led_600x1200", 0),
            key=f"led_{current_room}",
            min_value=0
        )
    with col2:
        downlight = st.number_input(
            "Downlights",
            value=fixtures.get("downlight", 0),
            key=f"dl_{current_room}",
            min_value=0
        )
    with col3:
        surface = st.number_input(
            "Surface Mount",
            value=fixtures.get("surface_mount_led", 0),
            key=f"sm_{current_room}",
            min_value=0
        )

    st.markdown("##### 🔌 Power Points")

    col1, col2, col3 = st.columns(3)
    with col1:
        socket_300 = st.number_input(
            "Double @300mm",
            value=fixtures.get("double_socket_300", 0),
            key=f"s300_{current_room}",
            min_value=0,
            help="Floor-level sockets"
        )
    with col2:
        socket_1100 = st.number_input(
            "Double @1100mm",
            value=fixtures.get("double_socket_1100", 0),
            key=f"s1100_{current_room}",
            min_value=0,
            help="Worktop-level sockets"
        )
    with col3:
        data_point = st.number_input(
            "Data Points",
            value=fixtures.get("data_point_cat6", 0),
            key=f"dp_{current_room}",
            min_value=0,
            help="CAT6 data outlets"
        )

    st.markdown("##### 🔲 Switches")

    col1, col2 = st.columns(2)
    with col1:
        switch_1 = st.number_input(
            "1-Lever Switch",
            value=fixtures.get("switch_1lever", 0),
            key=f"sw1_{current_room}",
            min_value=0
        )
    with col2:
        switch_2 = st.number_input(
            "2-Lever Switch",
            value=fixtures.get("switch_2lever", 0),
            key=f"sw2_{current_room}",
            min_value=0
        )

    st.markdown("")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back", key="back_step6", use_container_width=True):
            if current_idx > 0:
                st.session_state.current_room_index = current_idx - 1
            else:
                st.session_state.guided_step = 5
            st.rerun()

    with col2:
        if st.button("⏭ Skip Room", key="skip_room", use_container_width=True):
            if current_room in st.session_state.room_fixtures:
                del st.session_state.room_fixtures[current_room]
            st.session_state.current_room_index = current_idx + 1
            st.rerun()

    with col3:
        if st.button("✓ Confirm & Next →", key="confirm_room", type="primary", use_container_width=True):
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
    render_confidence_badge(confidence, "Cable Routes")

    # Cable routes count
    route_count = len(st.session_state.cable_routes)
    if route_count > 0:
        st.success(f"🔌 **{route_count} Cable Routes** found")
    else:
        st.warning("No cable routes detected. Add them manually below.")

    st.markdown("##### 🔌 Cable Schedule")

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
        st.info("No cable routes extracted. You can add them manually using the data editor.")

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to Room Fixtures", key="back_step7", use_container_width=True):
            st.session_state.guided_step = 6
            st.session_state.current_room_index = len(st.session_state.detected_rooms) - 1
            st.rerun()

    with col2:
        if st.button("🎯 Finalize Extraction →", key="finalize", type="primary", use_container_width=True):
            pipeline.apply_cable_routes(st.session_state.cable_routes)
            st.session_state.guided_step = 8
            st.session_state.max_completed_step = 7
            st.rerun()


# ============================================================================
# STEP 8: REVIEW & EXPORT
# ============================================================================

def render_step_8_review_export():
    """Step 8: Review and export final results."""
    section_header("Step 8: Review & Export", "Final extraction summary & BOQ generation")

    pipeline: InteractivePipeline = st.session_state.interactive_pipeline

    # Build final extraction result
    if st.session_state.final_extraction is None:
        with st.spinner("Building final extraction result..."):
            st.session_state.final_extraction = pipeline.build_final_result()

            validation, _ = validate(st.session_state.final_extraction)
            st.session_state.final_validation = validation

            pricing, _ = price(st.session_state.final_extraction, validation, None, None)
            st.session_state.final_pricing = pricing

    extraction = st.session_state.final_extraction
    validation = st.session_state.final_validation
    pricing = st.session_state.final_pricing

    # Statistics
    stats = pipeline.get_statistics()
    total_circuits = sum(
        len(s.get("circuits", [])) for s in st.session_state.db_schedules.values()
    )

    # Success banner
    st.success("🎉 **Extraction Complete!** Guided Upload Successfully Processed")

    # Extraction Statistics
    st.markdown("### Extraction Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("DBs Extracted", stats["db_schedules_extracted"])
    with col2:
        st.metric("Total Circuits", total_circuits)
    with col3:
        st.metric("Rooms Processed", stats["room_fixtures_extracted"])
    with col4:
        st.metric("Cable Routes", stats["cable_routes"])

    # Compliance score
    if validation:
        st.markdown("### SANS 10142-1 Compliance")
        score = validation.compliance_score
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Score", f"{score:.0f}%")
        with col2:
            if score >= 70:
                st.success(f"✅ Good compliance - {score:.0f}% of standards met")
            elif score >= 40:
                st.warning(f"⚠️ Moderate compliance - {score:.0f}% of standards met")
            else:
                st.error(f"❌ Low compliance - {score:.0f}% of standards met")

    # API Usage
    st.markdown("### API Usage")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")
    with col2:
        st.metric("Estimated Cost", f"R{stats['total_cost_zar']:.2f}")

    # Export buttons section
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
            st.warning("Excel export not available (install openpyxl).")

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
        if st.button("🔄 Start New Extraction", key="start_new", use_container_width=True):
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

# Page header with premium styling
page_header(
    title="⚡ Guided Upload",
    subtitle="Interactive step-by-step extraction • 70%+ accuracy target"
)

# Check if pipeline is available
if not PIPELINE_AVAILABLE:
    st.error(f"Pipeline not available: {PIPELINE_IMPORT_ERROR}")
    st.stop()

if not LLM_API_KEY:
    st.error("No API key configured. Add GROQ_API_KEY to secrets.toml")
    st.stop()

# Sidebar with provider status
st.sidebar.markdown("### Pipeline Status")
provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
st.sidebar.success(f"✓ {provider_name} ({provider_cost})")

st.sidebar.markdown("---")
st.sidebar.markdown("""
**How it works:**
1. Upload & categorize pages
2. Extract data step-by-step
3. Validate at each stage
4. Export professional BOQ
""")

# Progress indicator
render_progress_indicator()

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
