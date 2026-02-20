"""
AfriPlan Electrical v4.2 - Smart Upload (Simplified)

Single-page workflow: Upload → Extract → View Results → Export
No editing - contractor edits prices in exported Excel file.
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header

# Import agent components
PIPELINE_AVAILABLE = False

try:
    from agent import (
        AfriPlanPipeline,
        SimplifiedResult,
        create_pipeline,
        ServiceTier,
        ExtractionResult,
        ValidationResult,
        PricingResult,
    )
    from exports.excel_bq import export_professional_bq, HAS_OPENPYXL
    from exports.pdf_summary import generate_pdf_summary
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_IMPORT_ERROR = str(e)
    HAS_OPENPYXL = False

    # Fallback ServiceTier so the file can load and show the error
    from enum import Enum
    class ServiceTier(Enum):
        RESIDENTIAL = "residential"
        COMMERCIAL = "commercial"
        MAINTENANCE = "maintenance"
        UNKNOWN = "unknown"

    # Dummy classes so type hints don't fail
    SimplifiedResult = None


# Load API keys from secrets
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

    # Check for provider override
    if "LLM_PROVIDER" in st.secrets:
        provider = st.secrets["LLM_PROVIDER"]
        if provider == "groq" and "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
        elif provider == "grok" and "XAI_API_KEY" in st.secrets:
            api_key = st.secrets["XAI_API_KEY"]
        elif provider == "gemini" and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        elif provider == "claude" and "ANTHROPIC_API_KEY" in st.secrets:
            api_key = st.secrets["ANTHROPIC_API_KEY"]

    return provider, api_key


# Load API keys
LLM_PROVIDER, LLM_API_KEY = load_api_keys()

# Tier display info
TIER_DISPLAY = {
    ServiceTier.RESIDENTIAL: {"icon": "🏡", "name": "Residential", "color": "#22C55E"},
    ServiceTier.COMMERCIAL: {"icon": "🏢", "name": "Commercial", "color": "#3B82F6"},
    ServiceTier.MAINTENANCE: {"icon": "🔧", "name": "Maintenance", "color": "#F59E0B"},
    ServiceTier.UNKNOWN: {"icon": "❓", "name": "Unknown", "color": "#64748b"},
}

# Provider labels
PROVIDER_LABELS = {
    "groq": ("Groq Llama 4", "100% FREE"),
    "grok": ("xAI Grok", "$25 FREE"),
    "gemini": ("Google Gemini", "FREE"),
    "claude": ("Claude", "Paid"),
}

# Apply custom styling
inject_custom_css()

# Page Header
page_header(
    title="Smart Upload",
    subtitle="Upload → Extract → Export"
)


def get_confidence_color(confidence: float) -> str:
    """Return color based on confidence level."""
    if confidence >= 0.70:
        return "#22C55E"  # Green
    elif confidence >= 0.40:
        return "#F59E0B"  # Yellow
    else:
        return "#EF4444"  # Red


def render_summary_metrics(result: SimplifiedResult):
    """Render extraction summary metrics."""
    extraction = result.extraction

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Building Blocks",
            len(extraction.building_blocks) if extraction else 0
        )
    with col2:
        st.metric(
            "Distribution Boards",
            extraction.total_dbs if extraction else 0
        )
    with col3:
        st.metric(
            "Circuits",
            extraction.total_circuits if extraction else 0
        )
    with col4:
        st.metric(
            "Total Points",
            extraction.total_points if extraction else 0
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Light Fittings", result.total_lights)
    with col2:
        st.metric("Socket Outlets", result.total_sockets)
    with col3:
        st.metric("Switches", result.total_switches)
    with col4:
        st.metric("Cable Runs", len(extraction.site_cable_runs) if extraction else 0)


def render_compliance_summary(result: SimplifiedResult):
    """Render SANS 10142 compliance summary."""
    validation = result.validation

    if not validation:
        st.info("Validation not run")
        return

    score = validation.compliance_score
    score_color = get_confidence_color(score / 100)

    st.markdown(f"""
    <div style="background: {score_color}15; border: 1px solid {score_color}40;
                border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 0.9rem; color: #94a3b8;">SANS 10142-1 Compliance</div>
                <div style="font-size: 2rem; font-weight: 700; color: {score_color};">{score:.0f}%</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.85rem; color: #94a3b8;">
                    ✓ {validation.passed} passed |
                    ✗ {validation.failed} critical |
                    ⚠ {validation.warnings} warnings
                </div>
                <div style="font-size: 0.85rem; color: #22C55E;">
                    🔧 {validation.auto_corrections} auto-corrected
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show critical failures and auto-corrections
    if validation.flags:
        with st.expander("View Compliance Details", expanded=False):
            for flag in validation.flags:
                if not flag.passed:
                    severity_icon = "🔴" if flag.severity.value == "critical" else "🟡"
                    auto_fix = f" → {flag.corrected_value}" if flag.auto_corrected else ""

                    st.markdown(f"""
                    <div style="background: rgba(17,24,39,0.5); border-radius: 8px;
                                padding: 0.75rem; margin: 0.5rem 0; font-size: 0.9rem;">
                        {severity_icon} <strong>{flag.rule_name}</strong>: {flag.message}
                        <span style="color: #22C55E;">{auto_fix}</span>
                        <div style="font-size: 0.75rem; color: #64748b;">{flag.standard_ref or ''}</div>
                    </div>
                    """, unsafe_allow_html=True)


def render_detailed_extraction(result: SimplifiedResult):
    """Render detailed extraction view with validation checklist."""
    extraction = result.extraction

    if not extraction or not extraction.building_blocks:
        st.info("No extraction data available")
        return

    # v5.0: Import and run extraction checklist validation
    try:
        from agent.extraction_checklist import (
            create_model_checklist, validate_extraction, ChecklistCategory
        )
        checklist = create_model_checklist()
        checklist = validate_extraction(extraction, checklist)

        # Show overall extraction rate
        rate = checklist.extraction_rate
        rate_color = "#22C55E" if rate >= 70 else "#F59E0B" if rate >= 40 else "#EF4444"

        st.markdown(f"""
        <div style="background: {rate_color}15; border: 1px solid {rate_color}40;
                    border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
            <div style="font-size: 1.2rem; font-weight: 700; color: {rate_color};">
                BOQ Extraction Rate: {rate:.0f}%
            </div>
            <div style="font-size: 0.85rem; color: #94a3b8;">
                {checklist.extracted_items} of {checklist.total_items} checklist items extracted
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show checklist by category
        for category in ChecklistCategory:
            cat_items = checklist.items_by_category(category)
            extracted = sum(1 for item in cat_items if item.extracted)

            # Color based on completion
            if extracted == len(cat_items):
                cat_color = "#22C55E"
                cat_icon = "✓"
            elif extracted > 0:
                cat_color = "#F59E0B"
                cat_icon = "◐"
            else:
                cat_color = "#EF4444"
                cat_icon = "✗"

            with st.expander(f"{cat_icon} {category.value} — {extracted}/{len(cat_items)}", expanded=False):
                for item in cat_items:
                    status_icon = "✓" if item.extracted else "✗"
                    status_color = "#22C55E" if item.extracted else "#6B7280"
                    qty_text = f" ({item.extracted_qty:.0f} {item.expected_unit})" if item.extracted and item.extracted_qty > 0 else ""

                    st.markdown(f"""
                    <div style="display: flex; align-items: center; padding: 0.3rem 0; border-bottom: 1px solid #1f2937;">
                        <span style="color: {status_color}; margin-right: 0.5rem;">{status_icon}</span>
                        <span style="flex: 1;">{item.name}{qty_text}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">{item.source if item.extracted else 'Not found'}</span>
                    </div>
                    """, unsafe_allow_html=True)

    except ImportError:
        # Fallback to old view if checklist module not available
        pass

    # Also show building block summary
    st.markdown("---")
    st.markdown("### Building Blocks")

    for block in extraction.building_blocks:
        with st.expander(f"🏢 {block.name} — {len(block.rooms)} rooms, {len(block.distribution_boards)} DBs", expanded=False):
            # Distribution Boards
            if block.distribution_boards:
                st.markdown("**Distribution Boards:**")
                for db in block.distribution_boards:
                    st.markdown(f"""
                    - **{db.name}**: {db.total_ways}-way, {db.main_breaker_a}A main,
                      ELCB: {'✓' if db.earth_leakage else '✗'},
                      Surge: {'✓' if db.surge_protection else '✗'}
                    """)

                    if db.circuits:
                        circuit_summary = ", ".join([
                            f"{c.id}" for c in db.circuits[:5]
                        ])
                        if len(db.circuits) > 5:
                            circuit_summary += f" +{len(db.circuits) - 5} more"
                        st.caption(f"  Circuits: {circuit_summary}")

            # Rooms with fixture counts
            if block.rooms:
                st.markdown("**Rooms:**")
                for room in block.rooms[:10]:
                    f = room.fixtures
                    lights = f.total_lights
                    sockets = f.total_sockets
                    switches = f.total_switches
                    st.markdown(f"- **{room.name}**: {lights} lights, {sockets} sockets, {switches} switches")

                if len(block.rooms) > 10:
                    st.caption(f"... and {len(block.rooms) - 10} more rooms")

    # Site Cable Runs
    if extraction.site_cable_runs:
        with st.expander(f"🔌 Site Cable Runs ({len(extraction.site_cable_runs)})", expanded=False):
            for run in extraction.site_cable_runs:
                trench = "🪓 Trenching" if run.needs_trenching else ""
                st.markdown(f"- {run.from_point} → {run.to_point}: {run.cable_spec}, {run.length_m}m {trench}")


def render_export_section(result: SimplifiedResult, filename: str):
    """Render export buttons."""
    if not result.pricing:
        st.warning("Pricing data not available for export")
        return

    project_name = filename.rsplit(".", 1)[0] if filename else "Project"

    st.markdown("### Export Options")
    st.markdown("Download your Bill of Quantities. Fill in prices in the Excel file.")

    col1, col2 = st.columns(2)

    with col1:
        if HAS_OPENPYXL:
            try:
                # v5.0: Use professional export with 3 sheets (Cover, BOQ, Summary)
                excel_bytes = export_professional_bq(
                    pricing=result.pricing,
                    extraction=result.extraction,  # Pass extraction for metadata
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
                st.caption("3-sheet BOQ: Cover, BOQ (14 sections), Summary")
            except Exception as e:
                st.error(f"Excel export error: {e}")
        else:
            st.warning("Excel export requires openpyxl: `pip install openpyxl`")

    with col2:
        try:
            pdf_bytes = generate_pdf_summary(
                result.pricing,
                result.extraction,
                result.validation,
                project_name,
                result.tier,
            )
            st.download_button(
                label="📄 Download PDF Summary",
                data=pdf_bytes,
                file_name=f"{project_name}_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption("Scope summary + compliance status")
        except Exception as e:
            st.error(f"PDF export error: {e}")

    # BQ Stats
    if result.pricing:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("BQ Line Items", result.bq_items_count)
        with col2:
            extracted_pct = (result.pricing.items_from_extraction / max(1, result.pricing.total_items)) * 100
            st.metric("From Drawings", f"{extracted_pct:.0f}%")
        with col3:
            st.metric("Estimated Items", result.pricing.items_estimated)


# Check availability
if not PIPELINE_AVAILABLE:
    st.error(f"""
    **Pipeline Unavailable**

    Required modules could not be loaded.

    **Error:** `{PIPELINE_IMPORT_ERROR}`

    Please ensure all dependencies are installed:
    ```
    pip install anthropic PyMuPDF openpyxl fpdf2 pydantic groq
    ```
    """)
    st.stop()


# Sidebar
with st.sidebar:
    st.markdown("### Pipeline Status")

    if LLM_API_KEY:
        provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
        st.success(f"✓ {provider_name} ({provider_cost})")

        # Masked key
        masked_key = f"{LLM_API_KEY[:8]}...{LLM_API_KEY[-4:]}"
        st.caption(f"Key: {masked_key}")

        # Clear results button
        if "result" in st.session_state:
            if st.button("🔄 Clear & Start New", use_container_width=True):
                for key in ["result", "filename"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    else:
        st.error("No API Key")
        st.caption("Add GROQ_API_KEY to secrets.toml")

    st.markdown("---")
    st.markdown("### Supported Files")
    st.markdown("""
    - **PDF** - Electrical drawings
    - **PNG/JPG** - Floor plans, photos
    """)


# ============================================================================
# MAIN CONTENT
# ============================================================================

# Check if we have results
if "result" in st.session_state and st.session_state.result:
    result: SimplifiedResult = st.session_state.result
    filename = st.session_state.get("filename", "Document")

    # Results Header
    tier_info = TIER_DISPLAY.get(result.tier, TIER_DISPLAY[ServiceTier.UNKNOWN])
    conf_color = get_confidence_color(result.confidence)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid {tier_info['color']}40; border-radius: 16px;
                padding: 1.5rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="font-size: 2.5rem;">{tier_info['icon']}</span>
                <div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: {tier_info['color']};">
                        {tier_info['name']} Project
                    </div>
                    <div style="font-size: 0.9rem; color: #94a3b8;">{filename}</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.8rem; color: #64748b;">Confidence</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: {conf_color};">
                    {result.confidence*100:.0f}%
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary Metrics
    section_header("Extraction Summary", "Quantities extracted from drawings")
    render_summary_metrics(result)

    st.markdown("---")

    # Compliance
    section_header("SANS 10142-1 Compliance", "Automatic validation")
    render_compliance_summary(result)

    st.markdown("---")

    # Detailed View (Collapsible)
    section_header("Detailed Extraction", "Read-only view of extracted data")
    render_detailed_extraction(result)

    st.markdown("---")

    # Export
    render_export_section(result, filename)

else:
    # Upload Section
    section_header("Upload Document", "PDF or image of electrical drawings")

    # API Status Banner
    if LLM_API_KEY:
        provider_name, provider_cost = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05));
                    border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 1rem;
                    margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <div>
                    <div style="font-weight: 600; color: #22C55E;">
                        AI Ready — {provider_name} ({provider_cost})
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Upload electrical drawings to extract quantities
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("No API key configured. Add GROQ_API_KEY to .streamlit/secrets.toml")
        st.stop()

    # Accuracy Mode
    if LLM_PROVIDER == "groq":
        mode_options = ["Standard (Llama 4 Scout)", "High Accuracy (Llama 4 Maverick)"]
        high_accuracy_label = "High Accuracy (Llama 4 Maverick)"
    elif LLM_PROVIDER == "grok":
        mode_options = ["Standard (Grok Vision)", "High Accuracy (Grok Vision)"]
        high_accuracy_label = "High Accuracy (Grok Vision)"
    elif LLM_PROVIDER == "gemini":
        mode_options = ["Standard (Flash)", "High Accuracy (Pro)"]
        high_accuracy_label = "High Accuracy (Pro)"
    else:
        mode_options = ["Standard (Sonnet)", "High Accuracy (Opus)"]
        high_accuracy_label = "High Accuracy (Opus)"

    accuracy_mode = st.radio(
        "Accuracy Mode",
        options=mode_options,
        horizontal=True,
        index=0,
    )
    use_high_accuracy = accuracy_mode == high_accuracy_label

    # File Uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Upload electrical drawings, floor plans, or DB board photos",
        label_visibility="collapsed"
    )

    if uploaded_file:
        # File Preview
        col1, col2 = st.columns([2, 1])

        with col1:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            else:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                            border: 1px solid rgba(0,212,255,0.2); border-radius: 12px;
                            padding: 3rem; text-align: center;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
                    <div style="font-size: 1.2rem; color: #f1f5f9;">{uploaded_file.name}</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("**File Details**")
            st.markdown(f"**Name:** {uploaded_file.name[:30]}...")
            st.markdown(f"**Type:** {uploaded_file.type}")
            st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")

        st.markdown("---")

        # Extract Button
        if st.button("🚀 Extract Quantities", type="primary", use_container_width=True):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()

            with status_placeholder:
                provider_name, _ = PROVIDER_LABELS.get(LLM_PROVIDER, ("Unknown", ""))
                st.info(f"Starting extraction using {provider_name}...")

            try:
                # Create pipeline and run simplified extraction
                pipeline = create_pipeline(
                    api_key=LLM_API_KEY,
                    provider=LLM_PROVIDER
                )

                with st.spinner("Processing... This may take 30-60 seconds."):
                    result = pipeline.run_simplified(
                        files=[(uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)],
                        use_high_accuracy=use_high_accuracy
                    )

                # Store result
                st.session_state.result = result
                st.session_state.filename = uploaded_file.name

                with status_placeholder:
                    if result.success:
                        st.success(f"Extraction complete! Confidence: {result.confidence*100:.0f}%")
                    else:
                        st.error(f"Extraction failed: {result.error}")

                st.rerun()

            except Exception as e:
                with status_placeholder:
                    st.error(f"Error: {str(e)}")

    else:
        # Empty state
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.5), rgba(15,23,42,0.3));
                    border: 2px dashed rgba(0,212,255,0.3); border-radius: 16px;
                    padding: 4rem 2rem; text-align: center; margin-top: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📁</div>
            <div style="font-size: 1.2rem; color: #94a3b8;">
                Drag and drop your document here
            </div>
            <div style="font-size: 12px; color: #64748b; margin-top: 0.5rem;">
                Electrical drawings, floor plans, SLDs
            </div>
        </div>
        """, unsafe_allow_html=True)
