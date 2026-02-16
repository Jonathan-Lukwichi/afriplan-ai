"""
AfriPlan Electrical v3.0 - Smart Document Upload
6-stage AI pipeline with confidence visualization and editable extraction
"""

import streamlit as st
import sys
import os
import json
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header

# Import agent components (v3.0)
AGENT_AVAILABLE = False
ANALYZER_AVAILABLE = False

try:
    from agent import (
        AfriPlanAgent,
        PipelineResult,
        StageResult,
        PipelineStage,
        ServiceTier,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_IMPORT_ERROR = str(e)

# Fallback to legacy analyzer
try:
    from utils.document_analyzer import (
        DocumentAnalyzer,
        ProjectTier,
        AnalysisResult,
        get_tier_page_path,
        get_tier_display_info,
        ANTHROPIC_AVAILABLE,
        PDF_AVAILABLE
    )
    ANALYZER_AVAILABLE = True
except ImportError as e:
    ANALYZER_IMPORT_ERROR = str(e)

# Apply custom styling
inject_custom_css()

# Page Header
page_header(
    title="Smart Document Upload",
    subtitle="v3.0 AI Pipeline - 6-stage analysis"
)


# Pipeline stage configuration
STAGE_CONFIG = {
    "INGEST": {"icon": "📄", "name": "Ingest", "desc": "Document processing"},
    "CLASSIFY": {"icon": "🏷️", "name": "Classify", "desc": "Tier detection"},
    "DISCOVER": {"icon": "🔍", "name": "Discover", "desc": "Data extraction"},
    "VALIDATE": {"icon": "✅", "name": "Validate", "desc": "SANS 10142 check"},
    "PRICE": {"icon": "💰", "name": "Price", "desc": "Cost calculation"},
    "OUTPUT": {"icon": "📊", "name": "Output", "desc": "Quote generation"},
}

# Confidence colors
CONFIDENCE_COLORS = {
    "HIGH": "#22C55E",
    "MEDIUM": "#F59E0B",
    "LOW": "#EF4444",
}


def get_confidence_badge(confidence: float) -> str:
    """Return HTML badge for confidence level."""
    if confidence >= 0.70:
        level = "HIGH"
        color = CONFIDENCE_COLORS["HIGH"]
    elif confidence >= 0.40:
        level = "MEDIUM"
        color = CONFIDENCE_COLORS["MEDIUM"]
    else:
        level = "LOW"
        color = CONFIDENCE_COLORS["LOW"]

    return f"""
    <span style="background: {color}20; color: {color}; padding: 2px 8px;
                 border-radius: 4px; font-size: 11px; font-weight: 600;">
        {level} ({confidence*100:.0f}%)
    </span>
    """


def render_pipeline_progress(result: Optional[Any] = None, current_stage: str = None):
    """Render 6-stage pipeline progress visualization using st.columns for reliability."""
    stages = list(STAGE_CONFIG.keys())

    # Determine stage statuses
    stage_statuses = {}
    if result and hasattr(result, 'stages'):
        completed_stages = {s.stage.name: s for s in result.stages}
        for stage in stages:
            if stage in completed_stages:
                stage_statuses[stage] = "complete" if completed_stages[stage].success else "error"
            elif stage == current_stage:
                stage_statuses[stage] = "active"
            else:
                stage_statuses[stage] = "pending"
    elif current_stage:
        for i, stage in enumerate(stages):
            if stage == current_stage:
                stage_statuses[stage] = "active"
            elif stages.index(current_stage) > i:
                stage_statuses[stage] = "complete"
            else:
                stage_statuses[stage] = "pending"
    else:
        stage_statuses = {s: "pending" for s in stages}

    # Use st.columns for reliable rendering
    cols = st.columns(len(stages))

    for i, (stage, col) in enumerate(zip(stages, cols)):
        config = STAGE_CONFIG[stage]
        status = stage_statuses[stage]

        if status == "complete":
            bg = "rgba(34, 197, 94, 0.2)"
            border = "#22C55E"
        elif status == "active":
            bg = "rgba(0, 212, 255, 0.2)"
            border = "#00D4FF"
        elif status == "error":
            bg = "rgba(239, 68, 68, 0.2)"
            border = "#EF4444"
        else:
            bg = "rgba(100, 116, 139, 0.1)"
            border = "#64748b"

        with col:
            stage_html = f"""
            <div style="background: {bg}; border: 2px solid {border}; border-radius: 12px;
                        padding: 0.8rem 0.5rem; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{config['icon']}</div>
                <div style="font-size: 11px; font-weight: 600; color: {border};">{config['name']}</div>
                <div style="font-size: 9px; color: #64748b;">{config['desc']}</div>
            </div>
            """
            st.markdown(stage_html, unsafe_allow_html=True)


def render_model_indicator(model_used: str) -> str:
    """Return indicator showing which model was used."""
    model_map = {
        "claude-3-5-haiku-20241022": ("Haiku", "#00D4FF", "Fast"),
        "claude-sonnet-4-20250514": ("Sonnet", "#8B5CF6", "Standard"),
        "claude-opus-4-20250514": ("Opus", "#F59E0B", "Premium"),
    }

    name, color, tier = model_map.get(model_used, ("Unknown", "#64748b", "N/A"))

    return f"""
    <div style="display: inline-flex; align-items: center; gap: 6px;
                background: {color}15; border: 1px solid {color}40;
                padding: 4px 10px; border-radius: 6px;">
        <span style="font-size: 10px; color: {color}; font-weight: 600;">🤖 {name}</span>
        <span style="font-size: 9px; color: #94a3b8;">({tier})</span>
    </div>
    """


def render_validation_report(validation_flags: list):
    """Render SANS 10142 validation results."""
    if not validation_flags:
        st.success("All SANS 10142-1 checks passed")
        return

    # Filter by severity - only show failed checks
    critical = [f for f in validation_flags if f.get("severity") == "critical" and not f.get("passed", True)]
    warnings = [f for f in validation_flags if f.get("severity") == "warning" and not f.get("passed", True)]
    info = [f for f in validation_flags if f.get("severity") == "info" and not f.get("passed", True)]

    if critical:
        st.error(f"**{len(critical)} Critical Issues Found**")
        for flag in critical:
            # Use correct field names: rule_name (not rule), auto_corrected (not auto_fix)
            rule_name = flag.get('rule_name', 'Unknown')
            message = flag.get('message', '')
            auto_corrected = flag.get('auto_corrected', False)
            corrected_value = flag.get('corrected_value', '')

            auto_fix_html = ""
            if auto_corrected:
                auto_fix_html = f"<br><span style='color: #22C55E; font-size: 12px;'>✓ Auto-corrected: {corrected_value}</span>"

            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #EF4444;
                        padding: 0.5rem 1rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0;">
                <strong>{rule_name}</strong>: {message}{auto_fix_html}
            </div>
            """, unsafe_allow_html=True)

    if warnings:
        with st.expander(f"Warnings ({len(warnings)})", expanded=False):
            for flag in warnings:
                st.warning(f"**{flag.get('rule_name', '')}**: {flag.get('message', '')}")

    if info:
        with st.expander(f"Info ({len(info)})", expanded=False):
            for flag in info:
                st.info(f"**{flag.get('rule_name', '')}**: {flag.get('message', '')}")


# Initialize agent/analyzer with caching
@st.cache_resource
def get_agent():
    """Get cached AfriPlan agent instance."""
    if AGENT_AVAILABLE:
        return AfriPlanAgent()
    return None


@st.cache_resource
def get_analyzer():
    """Get cached legacy document analyzer instance."""
    if ANALYZER_AVAILABLE:
        return DocumentAnalyzer()
    return None


# Check availability
if not AGENT_AVAILABLE and not ANALYZER_AVAILABLE:
    st.error("""
    **Document Analysis Unavailable**

    Required modules could not be loaded.

    Please ensure all dependencies are installed:
    ```
    pip install anthropic PyMuPDF
    ```
    """)
    st.stop()

agent = get_agent()
analyzer = get_analyzer()

# Determine API availability
api_available = False
if agent and agent.available:
    api_available = True
elif analyzer and analyzer.available:
    api_available = True


# Sidebar with info
with st.sidebar:
    st.markdown("### v3.0 AI Pipeline")
    st.markdown("""
    Upload documents for automatic:
    - **Classification** - Tier detection
    - **Extraction** - Project details
    - **Validation** - SANS 10142 compliance
    - **Pricing** - Cost estimation
    """)

    st.markdown("---")
    st.markdown("### Pipeline Status")

    if agent and agent.available:
        st.success("Full Pipeline Active")
        st.caption("6-stage processing available")

        # API test button
        if st.button("🧪 Test API", key="test_api"):
            with st.spinner("Testing API connection..."):
                try:
                    test_response = agent.client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=50,
                        messages=[{"role": "user", "content": "Reply with just 'OK'"}]
                    )
                    st.success(f"API working! Response: {test_response.content[0].text}")
                except Exception as e:
                    st.error(f"API Error: {str(e)}")
    elif analyzer and analyzer.available:
        st.warning("Legacy Mode")
        st.caption("Basic analysis only")
    else:
        st.error("API Not Configured")
        st.caption("Add ANTHROPIC_API_KEY")

    st.markdown("---")
    st.markdown("### Supported Formats")
    st.markdown("""
    - **PDF** - Plans, specifications, COC docs
    - **PNG/JPG** - Floor plans, DB board photos
    """)


# Main content with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Upload",
    "⚡ Pipeline",
    "📝 Extraction",
    "✅ Validation",
    "🎯 Continue"
])

with tab1:
    section_header("Upload Document", "PDF, PNG, or JPG files")

    # API status banner
    if api_available:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05));
                    border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 1rem;
                    margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #22C55E;">
                        v3.0 AI Pipeline Ready
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        6-stage processing with confidence scoring
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(245,158,11,0.1), rgba(245,158,11,0.05));
                    border: 1px solid rgba(245,158,11,0.3); border-radius: 12px; padding: 1rem;
                    margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">⚠️</span>
                <div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #F59E0B;">
                        API Not Configured
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Add ANTHROPIC_API_KEY for full analysis
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("How to enable AI analysis"):
            st.markdown("""
            Add your API key via environment variable or Streamlit secrets:

            **Option 1: Environment Variable**
            ```bash
            export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
            ```

            **Option 2: Streamlit Secrets**
            Create `.streamlit/secrets.toml`:
            ```toml
            ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
            ```
            """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Upload plans, specifications, or DB board photos",
        label_visibility="collapsed"
    )

    if uploaded_file:
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
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #f1f5f9;">
                        {uploaded_file.name}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("### File Details")
            st.markdown(f"""
            <div style="background: rgba(17,24,39,0.5); border-radius: 8px; padding: 1rem;">
                <div style="margin-bottom: 0.8rem;">
                    <div style="font-size: 10px; color: #64748b;">FILENAME</div>
                    <div style="color: #f1f5f9; font-size: 13px;">{uploaded_file.name[:25]}...</div>
                </div>
                <div style="margin-bottom: 0.8rem;">
                    <div style="font-size: 10px; color: #64748b;">TYPE</div>
                    <div style="color: #f1f5f9; font-size: 13px;">{uploaded_file.type}</div>
                </div>
                <div>
                    <div style="font-size: 10px; color: #64748b;">SIZE</div>
                    <div style="color: #f1f5f9; font-size: 13px;">{uploaded_file.size / 1024:.1f} KB</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Analysis button
        if st.button("🚀 Run AI Pipeline", type="primary", use_container_width=True):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()

            # Use new agent if available, otherwise legacy
            if agent and agent.available:
                # New 6-stage pipeline
                with status_placeholder:
                    st.info("Starting 6-stage AI pipeline...")

                # Run pipeline with progress updates
                result = agent.process_document(
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                    uploaded_file.name
                )

                # Store result in session state
                st.session_state.pipeline_result = result
                st.session_state.uploaded_filename = uploaded_file.name

                # Convert to legacy format for compatibility
                tier_map = {
                    ServiceTier.RESIDENTIAL: ProjectTier.RESIDENTIAL,
                    ServiceTier.COMMERCIAL: ProjectTier.COMMERCIAL,
                    ServiceTier.MAINTENANCE: ProjectTier.MAINTENANCE,
                }
                legacy_tier = tier_map.get(result.final_tier, ProjectTier.UNKNOWN)

                st.session_state.analysis_result = AnalysisResult(
                    tier=legacy_tier,
                    confidence=result.overall_confidence,
                    subtype=result.extracted_data.get("subtype"),
                    extracted_data=result.extracted_data,
                    reasoning=result.extracted_data.get("notes", []),
                    warnings=result.extracted_data.get("warnings", [])
                )

                with status_placeholder:
                    if result.overall_confidence >= 0.70:
                        st.success(f"Pipeline complete! Confidence: {result.overall_confidence*100:.0f}%")
                    elif result.overall_confidence >= 0.40:
                        st.warning(f"Pipeline complete with medium confidence: {result.overall_confidence*100:.0f}%")
                    else:
                        st.error(f"Pipeline complete with low confidence: {result.overall_confidence*100:.0f}%")

                        # Show diagnostic info for low confidence
                        with st.expander("🔧 Diagnostic Info", expanded=True):
                            st.markdown("**Stage Results:**")
                            for stage in result.stages:
                                status = "✅" if stage.success else "❌"
                                st.markdown(f"- {stage.stage.name}: {status} (conf: {stage.confidence*100:.0f}%)")
                                if stage.errors:
                                    for err in stage.errors:
                                        st.error(f"  Error: {err}")
                                if stage.warnings:
                                    for warn in stage.warnings:
                                        st.warning(f"  Warning: {warn}")

                            if result.errors:
                                st.markdown("**Pipeline Errors:**")
                                for err in result.errors:
                                    st.error(err)

                st.info("Check **Pipeline**, **Extraction**, and **Validation** tabs for details.")

            elif analyzer and analyzer.available:
                # Legacy single-call analysis
                with status_placeholder:
                    st.info("Running legacy analysis...")

                result = analyzer.analyze_document(
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                    uploaded_file.name
                )

                st.session_state.analysis_result = result
                st.session_state.uploaded_filename = uploaded_file.name
                st.session_state.pipeline_result = None  # No pipeline result

                with status_placeholder:
                    tier_info = get_tier_display_info(result.tier)
                    st.success(f"Analysis complete: {tier_info['icon']} {tier_info['name']}")

            else:
                st.error("No analysis method available. Please configure API key.")
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.5), rgba(15,23,42,0.3));
                    border: 2px dashed rgba(0,212,255,0.3); border-radius: 16px;
                    padding: 4rem 2rem; text-align: center; margin-top: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📁</div>
            <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #94a3b8;">
                Drag and drop your document here
            </div>
            <div style="font-size: 12px; color: #64748b; margin-top: 0.5rem;">
                Floor plans, DB board photos, COC documents
            </div>
        </div>
        """, unsafe_allow_html=True)


with tab2:
    section_header("Pipeline Progress", "6-stage AI processing")

    if "pipeline_result" in st.session_state and st.session_state.pipeline_result:
        result = st.session_state.pipeline_result

        # Pipeline visualization
        render_pipeline_progress(result)

        st.markdown("---")
        st.markdown("### Stage Details")

        for stage_result in result.stages:
            stage_name = stage_result.stage.name
            config = STAGE_CONFIG.get(stage_name, {"icon": "❓", "name": stage_name})

            status_color = "#22C55E" if stage_result.success else "#EF4444"
            status_icon = "✓" if stage_result.success else "✗"

            with st.expander(f"{config['icon']} {config['name']} - {status_icon}", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.markdown(f"**Status:** {'Success' if stage_result.success else 'Failed'}")
                    st.markdown(f"**Confidence:** {get_confidence_badge(stage_result.confidence)}",
                               unsafe_allow_html=True)

                with col2:
                    if stage_result.model_used:
                        st.markdown(render_model_indicator(stage_result.model_used),
                                   unsafe_allow_html=True)
                    if stage_result.tokens_used:
                        st.caption(f"Tokens: {stage_result.tokens_used:,}")

                with col3:
                    cost_zar = getattr(stage_result, 'cost_zar', None)
                    if cost_zar:
                        st.metric("Cost", f"R{cost_zar:.2f}")

                # Show stage data summary
                if stage_result.data:
                    if stage_name == "CLASSIFY":
                        tier = stage_result.data.get("tier", "unknown")
                        st.info(f"Detected Tier: **{tier.upper()}**")
                    elif stage_name == "VALIDATE":
                        passed = stage_result.data.get("passed", 0)
                        failed = stage_result.data.get("failed", 0)
                        st.info(f"Checks: {passed} passed, {failed} failed")

        # Total cost
        st.markdown("---")
        total_cost = sum(getattr(s, 'cost_zar', 0) or 0 for s in result.stages)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Pipeline Cost", f"R{total_cost:.2f}")
        with col2:
            st.metric("Overall Confidence", f"{result.overall_confidence*100:.0f}%")

    elif "analysis_result" in st.session_state:
        st.info("Legacy analysis mode - no pipeline details available.")
        render_pipeline_progress()
    else:
        st.info("Upload and analyze a document to see pipeline progress.")
        render_pipeline_progress()


with tab3:
    section_header("Extracted Data", "Review and edit AI extraction")

    if "analysis_result" not in st.session_state:
        st.info("Upload and analyze a document to see extraction results.")
    else:
        result = st.session_state.analysis_result
        extracted = result.extracted_data or {}

        # Confidence summary
        col1, col2, col3 = st.columns(3)
        with col1:
            tier_info = get_tier_display_info(result.tier)
            st.markdown(f"""
            <div style="background: rgba(17,24,39,0.6); border-radius: 10px; padding: 1rem; text-align: center;">
                <div style="font-size: 2rem;">{tier_info['icon']}</div>
                <div style="color: {tier_info['color']}; font-weight: 600;">{tier_info['name']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background: rgba(17,24,39,0.6); border-radius: 10px; padding: 1rem; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700;
                            color: {'#22C55E' if result.confidence >= 0.7 else '#F59E0B' if result.confidence >= 0.4 else '#EF4444'};">
                    {result.confidence*100:.0f}%
                </div>
                <div style="color: #94a3b8; font-size: 12px;">Confidence</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            if "pipeline_result" in st.session_state and st.session_state.pipeline_result:
                pr = st.session_state.pipeline_result
                discover_stage = next((s for s in pr.stages if s.stage.name == "DISCOVER"), None)
                if discover_stage and discover_stage.model_used:
                    st.markdown(render_model_indicator(discover_stage.model_used), unsafe_allow_html=True)

        st.markdown("---")

        # Editable extraction sections
        st.markdown("### Edit Extracted Data")
        st.caption("Correct any AI extraction errors before continuing")

        # Project details
        with st.expander("📋 Project Details", expanded=True):
            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                project_name = st.text_input(
                    "Project Name",
                    value=extracted.get("project_name", ""),
                    key="edit_project_name"
                )

                # For maintenance/COC
                if result.tier == ProjectTier.MAINTENANCE:
                    property_type = st.selectbox(
                        "Property Type",
                        options=["house", "flat", "townhouse", "complex_unit", "commercial"],
                        index=0 if not extracted.get("property", {}).get("type") else
                              ["house", "flat", "townhouse", "complex_unit", "commercial"].index(
                                  extracted.get("property", {}).get("type", "house")
                              )
                    )

            with edit_col2:
                total_area = st.number_input(
                    "Total Area (m²)",
                    value=float(extracted.get("total_area_m2", 0) or extracted.get("gfa_m2", 0) or 0),
                    min_value=0.0,
                    key="edit_total_area"
                )

        # Rooms (for residential)
        if "rooms" in extracted and extracted["rooms"]:
            with st.expander("🏠 Rooms", expanded=True):
                rooms_df = []
                for room in extracted["rooms"]:
                    rooms_df.append({
                        "Name": room.get("name", "Unknown"),
                        "Type": room.get("type", "Unknown"),
                        "Area (m²)": room.get("area_m2") or 16,
                        "Lights": room.get("lights", 2),
                        "Sockets": room.get("sockets", 4)
                    })

                edited_rooms = st.data_editor(
                    rooms_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="edit_rooms"
                )

                # Store edited rooms back
                if edited_rooms:
                    st.session_state.edited_rooms = edited_rooms

        # Areas (for commercial)
        if "areas" in extracted and extracted["areas"]:
            with st.expander("🏢 Areas", expanded=True):
                areas_df = []
                for area in extracted["areas"]:
                    areas_df.append({
                        "Name": area.get("name", "Unknown"),
                        "Type": area.get("type", "Unknown"),
                        "Area (m²)": area.get("area_m2", 0),
                        "Power (W/m²)": area.get("power_density_wm2", 50)
                    })

                edited_areas = st.data_editor(
                    areas_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="edit_areas"
                )

                if edited_areas:
                    st.session_state.edited_areas = edited_areas

        # Defects (for maintenance)
        if "defects" in extracted and extracted["defects"]:
            with st.expander("⚠️ Detected Defects", expanded=True):
                defects_df = []
                for defect in extracted["defects"]:
                    defects_df.append({
                        "Code": defect.get("code", "unknown"),
                        "Description": defect.get("description", ""),
                        "Severity": defect.get("severity", "medium"),
                        "Qty": defect.get("qty", 1)
                    })

                edited_defects = st.data_editor(
                    defects_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="edit_defects"
                )

                if edited_defects:
                    st.session_state.edited_defects = edited_defects

        # Electrical details
        if "electrical_details" in extracted:
            with st.expander("⚡ Electrical Details", expanded=False):
                elec = extracted["electrical_details"]
                st.json(elec)

        # Raw JSON (for debugging)
        with st.expander("🔧 Raw JSON Data", expanded=False):
            st.json(extracted)


with tab4:
    section_header("SANS 10142 Validation", "Compliance check results")

    if "pipeline_result" in st.session_state and st.session_state.pipeline_result:
        result = st.session_state.pipeline_result

        # Find validation stage
        validate_stage = next((s for s in result.stages if s.stage.name == "VALIDATE"), None)

        if validate_stage and validate_stage.data:
            validation_data = validate_stage.data

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                passed = validation_data.get("passed", 0)
                st.metric("Passed", passed, delta_color="off")
            with col2:
                failed = validation_data.get("failed", 0)
                st.metric("Failed", failed, delta_color="inverse" if failed > 0 else "off")
            with col3:
                warnings = validation_data.get("warnings", 0)
                st.metric("Warnings", warnings)
            with col4:
                score = validation_data.get("compliance_score", 100)
                st.metric("Score", f"{score}%")

            st.markdown("---")

            # Validation flags
            flags = validation_data.get("flags", [])
            if flags:
                render_validation_report(flags)
            else:
                st.success("All SANS 10142-1 checks passed")

            # Auto-corrections applied
            corrections = validation_data.get("corrections_applied", [])
            if corrections:
                st.markdown("### Auto-Corrections Applied")
                for correction in corrections:
                    st.info(f"Added: {correction}")
        else:
            st.info("No validation data available.")

    elif "analysis_result" in st.session_state:
        st.info("Legacy analysis - run new pipeline for SANS 10142 validation.")

        # Basic warnings from legacy analysis
        result = st.session_state.analysis_result
        if result.warnings:
            st.markdown("### Warnings from Analysis")
            for warning in result.warnings:
                st.warning(warning)
    else:
        st.info("Upload and analyze a document to see validation results.")


with tab5:
    section_header("Continue to Quotation", "Proceed with extracted data")

    if "analysis_result" not in st.session_state:
        st.info("Upload and analyze a document first.")
    else:
        result = st.session_state.analysis_result
        tier_info = get_tier_display_info(result.tier)

        # Handle uncertain classification
        if result.tier == ProjectTier.UNKNOWN or result.confidence < 0.3:
            st.warning("**Classification Uncertain** - Please select manually:")

            manual_tier = st.selectbox(
                "Select Project Tier",
                options=["residential", "commercial", "maintenance"],
                format_func=lambda x: f"{get_tier_display_info(ProjectTier(x))['icon']} {x.title()}"
            )

            result = AnalysisResult(
                tier=ProjectTier(manual_tier),
                confidence=1.0,
                subtype=None,
                extracted_data=result.extracted_data,
                reasoning="Manually selected",
                warnings=[]
            )
            st.session_state.analysis_result = result
            tier_info = get_tier_display_info(result.tier)

        # Project summary card
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                    border: 1px solid {tier_info['color']}40; border-radius: 16px;
                    padding: 2rem; margin: 1rem 0;">
            <div style="display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem;">
                <div style="font-size: 3rem;">{tier_info['icon']}</div>
                <div>
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 1.5rem;
                                font-weight: 700; color: {tier_info['color']};">{tier_info['name']} Project</div>
                    <div style="font-size: 14px; color: #94a3b8;">{tier_info['description']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Confidence badge
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Confidence:** {get_confidence_badge(result.confidence)}", unsafe_allow_html=True)
        with col2:
            if "pipeline_result" in st.session_state and st.session_state.pipeline_result:
                total_cost = sum(getattr(s, 'cost_zar', 0) or 0 for s in st.session_state.pipeline_result.stages)
                st.markdown(f"**Pipeline Cost:** R{total_cost:.2f}")

        st.markdown("---")

        # Data transfer options
        st.markdown("### Data Transfer")

        transfer_data = st.checkbox(
            "Pre-populate extracted data",
            value=True,
            help="Transfer rooms, areas, and details to quotation page"
        )

        include_validation = st.checkbox(
            "Include validation corrections",
            value=True,
            help="Apply SANS 10142 auto-corrections"
        )

        st.markdown("---")

        # Navigation
        if st.button(
            f"✅ Continue to {tier_info['name']} Quotation",
            type="primary",
            use_container_width=True
        ):
            # Store data in session state
            st.session_state.from_smart_upload = True
            st.session_state.detected_tier = result.tier.value
            st.session_state.detected_subtype = result.subtype
            st.session_state.ai_confidence = result.confidence

            if transfer_data:
                # Use edited data if available
                extracted = result.extracted_data.copy()

                if "edited_rooms" in st.session_state:
                    extracted["rooms"] = [
                        {
                            "name": r["Name"],
                            "type": r["Type"],
                            "area_m2": r["Area (m²)"],
                            "lights": r.get("Lights", 2),
                            "sockets": r.get("Sockets", 4)
                        }
                        for r in st.session_state.edited_rooms
                    ]

                if "edited_areas" in st.session_state:
                    extracted["areas"] = [
                        {
                            "name": a["Name"],
                            "type": a["Type"],
                            "area_m2": a["Area (m²)"],
                            "power_density_wm2": a.get("Power (W/m²)", 50)
                        }
                        for a in st.session_state.edited_areas
                    ]

                if "edited_defects" in st.session_state:
                    extracted["defects"] = [
                        {
                            "code": d["Code"],
                            "description": d["Description"],
                            "severity": d["Severity"],
                            "qty": d["Qty"]
                        }
                        for d in st.session_state.edited_defects
                    ]

                st.session_state.extracted_data = extracted

                # Pre-populate tier-specific session state
                if result.tier == ProjectTier.RESIDENTIAL and "rooms" in extracted:
                    rooms = []
                    for r in extracted["rooms"]:
                        area = r.get("area_m2", 16) or 16
                        rooms.append({
                            "name": r.get("name", "Room"),
                            "type": r.get("type", "Living Room"),
                            "w": (area ** 0.5),
                            "h": (area ** 0.5)
                        })
                    if rooms:
                        st.session_state.residential_rooms = rooms

            # Store validation report if available
            if include_validation and "pipeline_result" in st.session_state:
                pr = st.session_state.pipeline_result
                validate_stage = next((s for s in pr.stages if s.stage.name == "VALIDATE"), None)
                if validate_stage:
                    st.session_state.validation_report = validate_stage.data

            # Navigate
            target_page = get_tier_page_path(result.tier)
            st.switch_page(target_page)

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Analyze Another", use_container_width=True):
                for key in ["analysis_result", "pipeline_result", "uploaded_filename",
                           "from_smart_upload", "edited_rooms", "edited_areas", "edited_defects"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        with col2:
            if st.button("🏠 Return to Welcome", use_container_width=True):
                st.switch_page("pages/0_Welcome.py")
