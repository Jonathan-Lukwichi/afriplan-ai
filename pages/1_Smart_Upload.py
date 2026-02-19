"""
AfriPlan Electrical v4.1 - Smart Document Upload
7-stage AI pipeline with confidence visualization and contractor review

Supports both Google Gemini (FREE) and Claude (paid) as LLM providers.
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

# Import agent components (v4.1)
PIPELINE_AVAILABLE = False

try:
    from agent import (
        AfriPlanPipeline,
        create_pipeline,
        PipelineResult,
        StageResult,
        PipelineStage,
        ServiceTier,
        ExtractionResult,
    )
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_IMPORT_ERROR = str(e)

# Load API keys from secrets and set environment variables
def load_api_keys():
    """Load API keys from Streamlit secrets and set as environment variables."""
    provider = None
    api_key = None

    # Try Grok first ($25 free credits/month!)
    if "XAI_API_KEY" in st.secrets:
        os.environ["XAI_API_KEY"] = st.secrets["XAI_API_KEY"]
        provider = "grok"
        api_key = st.secrets["XAI_API_KEY"]

    # Try Gemini (FREE tier)
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
        if provider is None:  # Only use Gemini if Grok not available
            provider = "gemini"
            api_key = st.secrets["GEMINI_API_KEY"]

    # Fall back to Claude (paid)
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
        if provider is None:  # Only use Claude if others not available
            provider = "claude"
            api_key = st.secrets["ANTHROPIC_API_KEY"]

    # Check for provider override
    if "LLM_PROVIDER" in st.secrets:
        provider = st.secrets["LLM_PROVIDER"]
        if provider == "grok" and "XAI_API_KEY" in st.secrets:
            api_key = st.secrets["XAI_API_KEY"]
        elif provider == "gemini" and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        elif provider == "claude" and "ANTHROPIC_API_KEY" in st.secrets:
            api_key = st.secrets["ANTHROPIC_API_KEY"]

    return provider, api_key

# Load API keys
LLM_PROVIDER, LLM_API_KEY = load_api_keys()

# Tier display info (inline, no legacy dependency)
TIER_DISPLAY = {
    ServiceTier.RESIDENTIAL: {"icon": "🏡", "name": "Residential", "color": "#22C55E", "description": "Houses, flats, domestic installations"},
    ServiceTier.COMMERCIAL: {"icon": "🏢", "name": "Commercial", "color": "#3B82F6", "description": "Offices, retail, hospitality"},
    ServiceTier.MAINTENANCE: {"icon": "🔧", "name": "Maintenance", "color": "#F59E0B", "description": "COC inspections, repairs"},
    ServiceTier.UNKNOWN: {"icon": "❓", "name": "Unknown", "color": "#64748b", "description": "Classification needed"},
}

# Apply custom styling
inject_custom_css()

# Page Header
page_header(
    title="Smart Document Upload",
    subtitle="v4.1 AI Pipeline - 7-stage analysis"
)


# Pipeline stage configuration (v4.1 - 7 stages)
STAGE_CONFIG = {
    "INGEST": {"icon": "📄", "name": "Ingest", "desc": "Document processing"},
    "CLASSIFY": {"icon": "🏷️", "name": "Classify", "desc": "Tier detection"},
    "DISCOVER": {"icon": "🔍", "name": "Discover", "desc": "Data extraction"},
    "REVIEW": {"icon": "✏️", "name": "Review", "desc": "Contractor edit"},
    "VALIDATE": {"icon": "✅", "name": "Validate", "desc": "SANS 10142 check"},
    "PRICE": {"icon": "💰", "name": "Price", "desc": "BQ generation"},
    "OUTPUT": {"icon": "📊", "name": "Output", "desc": "Final result"},
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
        # Claude models
        "claude-3-5-haiku-20241022": ("Haiku", "#00D4FF", "Fast"),
        "claude-sonnet-4-20250514": ("Sonnet", "#8B5CF6", "Standard"),
        "claude-opus-4-20250514": ("Opus", "#F59E0B", "Premium"),
        # Gemini models
        "gemini-2.0-flash": ("Gemini 2.0", "#4285F4", "FREE"),
        "gemini-1.5-pro-latest": ("Gemini Pro", "#34A853", "FREE"),
        # Grok models
        "grok-2-vision-1212": ("Grok Vision", "#1DA1F2", "$25 FREE"),
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


# Initialize v4.1 pipeline with caching based on API key
def get_pipeline_key():
    """Generate a cache key based on current API config."""
    return f"{LLM_PROVIDER}_{LLM_API_KEY[:10] if LLM_API_KEY else 'none'}"

@st.cache_resource
def get_pipeline(_cache_key: str):
    """Get cached AfriPlan v4.1 pipeline instance."""
    if PIPELINE_AVAILABLE and LLM_API_KEY:
        try:
            return create_pipeline(api_key=LLM_API_KEY, provider=LLM_PROVIDER)
        except Exception as e:
            st.warning(f"Pipeline initialization failed: {e}")
            return None
    return None


# Check availability
if not PIPELINE_AVAILABLE:
    st.error(f"""
    **v4.1 Pipeline Unavailable**

    Required modules could not be loaded.

    Please ensure all dependencies are installed:
    ```
    pip install anthropic PyMuPDF
    ```
    """)
    st.stop()

pipeline = get_pipeline(get_pipeline_key())
pipeline_available = pipeline is not None


# Sidebar with info
with st.sidebar:
    st.markdown("### v4.1 AI Pipeline")
    st.markdown("""
    Upload documents for automatic:
    - **Classification** - Tier detection
    - **Extraction** - Quantity take-off
    - **Review** - You verify & correct
    - **Validation** - SANS 10142 compliance
    - **Pricing** - Dual BQ generation
    """)

    st.markdown("---")
    st.markdown("### Pipeline Status")

    if pipeline and pipeline_available:
        provider_labels = {
            "grok": "Grok ($25 FREE)",
            "gemini": "Gemini (FREE)",
            "claude": "Claude"
        }
        provider_label = provider_labels.get(LLM_PROVIDER, "Unknown")
        st.success(f"v4.1 Pipeline Active ({provider_label})")
        st.caption("7-stage processing available")

        # Show current API key (masked)
        if LLM_API_KEY:
            masked_key = f"{LLM_API_KEY[:8]}...{LLM_API_KEY[-4:]}"
            st.caption(f"Key: {masked_key}")

        # API test button
        if st.button("🧪 Test API", key="test_api"):
            with st.spinner("Testing API connection..."):
                try:
                    if LLM_PROVIDER == "grok":
                        # Grok API test (OpenAI-compatible)
                        test_response = pipeline.client.chat.completions.create(
                            model="grok-2-vision-1212",
                            max_tokens=50,
                            messages=[{"role": "user", "content": "Reply with just 'OK'"}]
                        )
                        st.success(f"Grok API working! Response: {test_response.choices[0].message.content}")
                    elif LLM_PROVIDER == "gemini":
                        # Gemini API test
                        gemini_model = pipeline.client.GenerativeModel("gemini-2.0-flash")
                        test_response = gemini_model.generate_content("Reply with just 'OK'")
                        st.success(f"Gemini API working! Response: {test_response.text}")
                    else:
                        # Claude API test
                        test_response = pipeline.client.messages.create(
                            model="claude-3-5-haiku-20241022",
                            max_tokens=50,
                            messages=[{"role": "user", "content": "Reply with just 'OK'"}]
                        )
                        st.success(f"Claude API working! Response: {test_response.content[0].text}")
                except Exception as e:
                    st.error(f"API Error: {str(e)}")

        # Clear cache button
        if st.button("🔄 Clear Cache", key="clear_cache"):
            st.cache_resource.clear()
            st.rerun()
    else:
        st.error("API Not Configured")
        st.caption("Add XAI_API_KEY (Grok), GEMINI_API_KEY (free), or ANTHROPIC_API_KEY")

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
    if pipeline_available:
        provider_badges = {
            "grok": "🆓 Grok $25 FREE",
            "gemini": "🆓 Gemini FREE",
            "claude": "Claude"
        }
        provider_badge = provider_badges.get(LLM_PROVIDER, "Unknown")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05));
                    border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 1rem;
                    margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #22C55E;">
                        v4.1 AI Pipeline Ready — {provider_badge}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        7-stage processing with contractor review
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
                        Add XAI_API_KEY (Grok), GEMINI_API_KEY (FREE), or ANTHROPIC_API_KEY
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("How to enable AI analysis"):
            st.markdown("""
            Add your API key via Streamlit secrets:

            **Option 1: xAI Grok ($25 free credits/month!)**
            1. Get key at: https://console.x.ai/
            2. Add to `.streamlit/secrets.toml`:
            ```toml
            XAI_API_KEY = "xai-..."
            LLM_PROVIDER = "grok"
            ```

            **Option 2: Google Gemini (FREE tier)**
            1. Get key at: https://aistudio.google.com/
            2. Add to `.streamlit/secrets.toml`:
            ```toml
            GEMINI_API_KEY = "AIza..."
            LLM_PROVIDER = "gemini"
            ```

            **Option 3: Anthropic Claude (paid)**
            ```toml
            ANTHROPIC_API_KEY = "sk-ant-api03-..."
            LLM_PROVIDER = "claude"
            ```
            """)

    # Accuracy mode selection (provider-aware labels)
    if LLM_PROVIDER == "grok":
        mode_options = ["Standard (Grok Vision)", "Maximum Accuracy (Grok Vision)"]
        mode_help = "Grok Vision is fast and accurate. Uses your $25 free monthly credits."
        high_accuracy_label = "Maximum Accuracy (Grok Vision)"
        high_accuracy_info = "🎯 **Maximum Accuracy Mode** - Uses Grok Vision with extended analysis. Same model but more thorough extraction."
    elif LLM_PROVIDER == "gemini":
        mode_options = ["Standard (Flash)", "Maximum Accuracy (Pro)"]
        mode_help = "Pro is slower but more accurate. Both are FREE with Gemini."
        high_accuracy_label = "Maximum Accuracy (Pro)"
        high_accuracy_info = "🎯 **Maximum Accuracy Mode** - Uses Gemini Pro for initial extraction. Still FREE but slower and more accurate."
    else:
        mode_options = ["Standard (Sonnet)", "Maximum Accuracy (Opus)"]
        mode_help = "Opus is slower but more accurate. Use for critical quotations."
        high_accuracy_label = "Maximum Accuracy (Opus)"
        high_accuracy_info = "🎯 **Maximum Accuracy Mode** - Uses Opus for initial extraction. Higher cost (~R8/doc) but significantly more accurate."

    accuracy_mode = st.radio(
        "Extraction Mode",
        options=mode_options,
        horizontal=True,
        index=0,
        help=mode_help
    )
    use_opus = accuracy_mode == high_accuracy_label

    if use_opus:
        st.info(high_accuracy_info)

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

            if pipeline_available and LLM_API_KEY:
                # v4.1 7-stage pipeline (stages 1-3: INGEST, CLASSIFY, DISCOVER)
                with status_placeholder:
                    provider_names = {
                        "grok": "xAI Grok ($25 FREE)",
                        "gemini": "Google Gemini (FREE)",
                        "claude": "Claude"
                    }
                    provider_name = provider_names.get(LLM_PROVIDER, "Unknown")
                    st.info(f"Starting v4.1 AI pipeline using {provider_name}...")

                try:
                    # Create fresh pipeline instance for this run
                    run_pipeline = create_pipeline(
                        api_key=LLM_API_KEY,
                        provider=LLM_PROVIDER
                    )

                    # Process document (runs INGEST → CLASSIFY → DISCOVER)
                    # Pass accuracy mode to use Opus for initial extraction if selected
                    extraction, confidence = run_pipeline.process_documents(
                        files=[(uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type)],
                        use_opus_directly=use_opus
                    )

                    # Store results in session state for v4.1 flow
                    st.session_state.pipeline = run_pipeline  # Keep pipeline for later stages
                    st.session_state.extraction = extraction
                    st.session_state.extraction_confidence = confidence
                    st.session_state.detected_tier = run_pipeline.tier
                    st.session_state.uploaded_filename = uploaded_file.name
                    st.session_state.stages_completed = run_pipeline.stages

                    with status_placeholder:
                        tier_info = TIER_DISPLAY.get(run_pipeline.tier, TIER_DISPLAY[ServiceTier.UNKNOWN])
                        if confidence >= 0.70:
                            st.success(f"Extraction complete! {tier_info['icon']} {tier_info['name']} ({confidence*100:.0f}% confidence)")
                        elif confidence >= 0.40:
                            st.warning(f"Extraction complete with medium confidence: {confidence*100:.0f}%")
                        else:
                            st.error(f"Extraction complete with low confidence: {confidence*100:.0f}%")

                            # Show diagnostic info for low confidence
                            with st.expander("🔧 Diagnostic Info", expanded=True):
                                st.markdown("**Stage Results:**")
                                for stage in run_pipeline.stages:
                                    status_icon = "✅" if stage.success else "❌"
                                    st.markdown(f"- {stage.stage.name}: {status_icon} (conf: {stage.confidence*100:.0f}%)")
                                    if stage.errors:
                                        for err in stage.errors:
                                            st.error(f"  Error: {err}")

                    st.info("Check the **Pipeline** and **Extraction** tabs, then continue to **Review & Edit**.")

                except Exception as e:
                    with status_placeholder:
                        st.error(f"Pipeline error: {str(e)}")

            elif not LLM_API_KEY:
                st.error("No API key configured. Add XAI_API_KEY (Grok), GEMINI_API_KEY (free), or ANTHROPIC_API_KEY to .streamlit/secrets.toml")
            else:
                st.error("Pipeline not available. Check the installation.")
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
    section_header("Pipeline Progress", "7-stage AI processing")

    if "stages_completed" in st.session_state and st.session_state.stages_completed:
        stages = st.session_state.stages_completed
        confidence = st.session_state.get("extraction_confidence", 0.0)

        # Pipeline visualization
        render_pipeline_progress(current_stage="DISCOVER")  # Show stages 1-3 complete

        st.markdown("---")
        st.markdown("### Stage Details (1-3 of 7)")

        for stage_result in stages:
            stage_name = stage_result.stage.name
            config = STAGE_CONFIG.get(stage_name, {"icon": "❓", "name": stage_name})

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

        # Total cost so far
        st.markdown("---")
        total_cost = sum(getattr(s, 'cost_zar', 0) or 0 for s in stages)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pipeline Cost (so far)", f"R{total_cost:.2f}")
        with col2:
            st.metric("Extraction Confidence", f"{confidence*100:.0f}%")

        st.info("Stages 4-7 (REVIEW, VALIDATE, PRICE, OUTPUT) run after you review the extraction.")

    else:
        st.info("Upload and analyze a document to see pipeline progress.")
        render_pipeline_progress()


with tab3:
    section_header("Extraction Preview", "View AI extraction summary")

    if "extraction" not in st.session_state or st.session_state.extraction is None:
        st.info("Upload and analyze a document to see extraction results.")
    else:
        extraction: ExtractionResult = st.session_state.extraction
        confidence = st.session_state.get("extraction_confidence", 0.0)
        tier = st.session_state.get("detected_tier", ServiceTier.UNKNOWN)
        tier_info = TIER_DISPLAY.get(tier, TIER_DISPLAY[ServiceTier.UNKNOWN])

        # Confidence summary
        col1, col2, col3 = st.columns(3)
        with col1:
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
                            color: {'#22C55E' if confidence >= 0.7 else '#F59E0B' if confidence >= 0.4 else '#EF4444'};">
                    {confidence*100:.0f}%
                </div>
                <div style="color: #94a3b8; font-size: 12px;">Confidence</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            stages = st.session_state.get("stages_completed", [])
            discover_stage = next((s for s in stages if s.stage.name == "DISCOVER"), None)
            if discover_stage and discover_stage.model_used:
                st.markdown(render_model_indicator(discover_stage.model_used), unsafe_allow_html=True)

        st.markdown("---")

        # Summary metrics
        st.markdown("### Extraction Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building Blocks", len(extraction.building_blocks))
        with col2:
            st.metric("Distribution Boards", extraction.total_dbs)
        with col3:
            st.metric("Rooms", len(extraction.all_rooms))
        with col4:
            st.metric("Site Cables", len(extraction.site_cable_runs))

        # Building blocks preview
        if extraction.building_blocks:
            with st.expander("🏢 Building Blocks Preview", expanded=True):
                for block in extraction.building_blocks:
                    st.markdown(f"**{block.name}** — {len(block.rooms)} rooms, {block.total_dbs} DBs, {block.total_points} points")

        # DBs preview
        if any(block.distribution_boards for block in extraction.building_blocks):
            with st.expander("⚡ Distribution Boards Preview", expanded=False):
                for block in extraction.building_blocks:
                    for db in block.distribution_boards:
                        st.markdown(f"**{db.name}** — {db.total_ways} ways, Main {db.main_breaker_a}A")

        # Rooms preview
        if extraction.all_rooms:
            with st.expander("🚿 Rooms Preview", expanded=False):
                for block in extraction.building_blocks:
                    if block.rooms:
                        st.markdown(f"**{block.name}:**")
                        for room in block.rooms[:5]:  # Show first 5
                            st.markdown(f"  • {room.name}: {room.fixtures.total_lights} lights, {room.fixtures.total_sockets} sockets")
                        if len(block.rooms) > 5:
                            st.caption(f"  ... and {len(block.rooms) - 5} more rooms")

        st.markdown("---")
        st.info("**To edit quantities**, click 'Continue to Review' in the next tab. The Review page has detailed editing controls.")


with tab4:
    section_header("SANS 10142 Validation", "Stage 5 - runs after review")

    st.info("""
    **v4.1 Pipeline Flow:**

    In v4.1, SANS 10142 validation happens **after** you review and correct the AI extraction.

    **Current stage:** DISCOVER complete → **REVIEW** next

    The validation stage will check:
    - Max 10 lights/plugs per circuit
    - Mandatory ELCB (30mA)
    - Dedicated circuits for stove, geyser, aircon
    - Voltage drop limits (< 5%)
    - 15% spare DB ways

    Click "Continue to Review" to proceed.
    """)


with tab5:
    section_header("Continue to Review", "v4.1 workflow - Stage 4")

    if "extraction" not in st.session_state or st.session_state.extraction is None:
        st.info("Upload and analyze a document first.")
    else:
        extraction: ExtractionResult = st.session_state.extraction
        confidence = st.session_state.get("extraction_confidence", 0.0)
        tier = st.session_state.get("detected_tier", ServiceTier.UNKNOWN)
        tier_info = TIER_DISPLAY.get(tier, TIER_DISPLAY[ServiceTier.UNKNOWN])

        # Handle uncertain classification
        if tier == ServiceTier.UNKNOWN or confidence < 0.3:
            st.warning("**Classification Uncertain** - Please select manually:")

            manual_tier = st.selectbox(
                "Select Project Tier",
                options=[ServiceTier.RESIDENTIAL, ServiceTier.COMMERCIAL, ServiceTier.MAINTENANCE],
                format_func=lambda x: f"{TIER_DISPLAY[x]['icon']} {TIER_DISPLAY[x]['name']}"
            )
            st.session_state.detected_tier = manual_tier
            tier = manual_tier
            tier_info = TIER_DISPLAY[tier]

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

        # Confidence badge and metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Confidence:** {get_confidence_badge(confidence)}", unsafe_allow_html=True)
        with col2:
            stages = st.session_state.get("stages_completed", [])
            total_cost = sum(getattr(s, 'cost_zar', 0) or 0 for s in stages)
            st.markdown(f"**Pipeline Cost:** R{total_cost:.2f}")
        with col3:
            st.markdown(f"**Items:** {len(extraction.building_blocks)} blocks, {extraction.total_dbs} DBs")

        st.markdown("---")

        # v4.1 workflow explanation
        st.markdown("### v4.1 Workflow")
        st.markdown("""
        1. ✅ **INGEST** - Document processed
        2. ✅ **CLASSIFY** - Tier detected
        3. ✅ **DISCOVER** - Quantities extracted
        4. ⏳ **REVIEW** - You review & correct ← **Next step**
        5. ⏳ **VALIDATE** - SANS 10142 compliance
        6. ⏳ **PRICE** - Dual BQ generation
        7. ⏳ **OUTPUT** - Final result
        """)

        st.markdown("---")

        # Navigation
        if st.button(
            "✏️ Continue to Review & Edit",
            type="primary",
            use_container_width=True
        ):
            # Data is already in session state (extraction, pipeline, etc.)
            st.session_state.from_smart_upload = True
            st.switch_page("pages/6_Review.py")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Analyze Another", use_container_width=True):
                for key in ["extraction", "pipeline", "stages_completed", "extraction_confidence",
                           "detected_tier", "uploaded_filename", "from_smart_upload"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        with col2:
            if st.button("🏠 Return to Welcome", use_container_width=True):
                st.switch_page("pages/0_Welcome.py")
