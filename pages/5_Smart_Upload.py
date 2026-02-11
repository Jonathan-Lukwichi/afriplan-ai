"""
AfriPlan Electrical - Smart Document Upload
AI-powered document analysis and project classification using Claude Vision API
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header

# Import document analyzer components
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
    ANALYZER_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Apply custom styling
inject_custom_css()

# Page Header
page_header(
    title="Smart Document Upload",
    subtitle="AI-powered project analysis and classification"
)


# Initialize analyzer with caching
@st.cache_resource
def get_analyzer():
    """Get cached document analyzer instance."""
    if ANALYZER_AVAILABLE:
        return DocumentAnalyzer()
    return None


# Check if analyzer is available
if not ANALYZER_AVAILABLE:
    st.error(f"""
    **Document Analyzer Unavailable**

    The document analyzer module could not be loaded: {IMPORT_ERROR}

    Please ensure all dependencies are installed:
    ```
    pip install anthropic PyMuPDF
    ```
    """)
    st.stop()

analyzer = get_analyzer()

# Sidebar with info
with st.sidebar:
    st.markdown("### Smart Upload")
    st.markdown("""
    Upload architectural drawings, floor plans, or project documents.

    The AI will analyze your document and:
    - Classify the project type
    - Extract key details
    - Guide you to the correct quotation page
    """)

    st.markdown("---")
    st.markdown("### Supported Formats")
    st.markdown("""
    - **PDF** - Architectural plans, specifications
    - **PNG/JPG** - Scanned drawings, photos
    """)

    st.markdown("---")
    st.markdown("### API Status")

    if analyzer and analyzer.available:
        st.success("Claude Vision API Connected")
    else:
        st.warning("API Not Configured")
        st.caption("Basic analysis available")

# Main content with tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload", "📊 Analysis", "🎯 Continue"])

with tab1:
    section_header("Upload Your Document", "PDF, PNG, or JPG files supported")

    # Show API status banner
    if analyzer and analyzer.available:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05));
                    border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 1rem;
                    margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #22C55E;">
                        AI Analysis Ready
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Claude Vision API connected - full document analysis available
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
                        Limited Analysis Mode
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Configure ANTHROPIC_API_KEY for full AI analysis
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("How to enable full AI analysis"):
            st.markdown("""
            To enable full Claude Vision analysis, add your API key:

            **Option 1: Environment Variable**
            ```bash
            export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
            ```

            **Option 2: Streamlit Secrets**
            Create `.streamlit/secrets.toml`:
            ```toml
            ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"
            ```

            Get your API key at: https://console.anthropic.com/
            """)

    # File uploader
    st.markdown("### Select Document")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Upload architectural drawings, floor plans, electrical layouts, or project specifications",
        label_visibility="collapsed"
    )

    if uploaded_file:
        # File info display
        col1, col2 = st.columns([2, 1])

        with col1:
            # Show preview for images
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            else:
                # PDF preview placeholder
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                            border: 1px solid rgba(0,212,255,0.2); border-radius: 12px;
                            padding: 3rem; text-align: center;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #f1f5f9;">
                        {uploaded_file.name}
                    </div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 0.5rem;">
                        PDF Document
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if not PDF_AVAILABLE:
                    st.warning("PDF processing requires PyMuPDF. Install with: `pip install PyMuPDF`")

        with col2:
            st.markdown("### File Details")

            # File metrics
            st.markdown(f"""
            <div style="background: rgba(17,24,39,0.5); border-radius: 8px; padding: 1rem;">
                <div style="margin-bottom: 1rem;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Filename</div>
                    <div style="font-family: 'Rajdhani', sans-serif; color: #f1f5f9;">{uploaded_file.name}</div>
                </div>
                <div style="margin-bottom: 1rem;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Type</div>
                    <div style="font-family: 'Rajdhani', sans-serif; color: #f1f5f9;">{uploaded_file.type}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Size</div>
                    <div style="font-family: 'Rajdhani', sans-serif; color: #f1f5f9;">{uploaded_file.size / 1024:.1f} KB</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Analyze button
        if st.button("🔍 Analyze Document", type="primary", use_container_width=True):
            with st.spinner("Analyzing document with AI..."):
                result = analyzer.analyze_document(
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                    uploaded_file.name
                )
                st.session_state.analysis_result = result
                st.session_state.uploaded_filename = uploaded_file.name

            # Show success message
            tier_info = get_tier_display_info(result.tier)
            if result.confidence >= 0.5:
                st.success(f"Analysis complete! Detected: {tier_info['icon']} {tier_info['name']} ({result.confidence*100:.0f}% confidence)")
            else:
                st.warning(f"Analysis complete with low confidence. Please review results.")

            st.info("Check the **Analysis** and **Continue** tabs for detailed results.")
    else:
        # Placeholder when no file uploaded
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.5), rgba(15,23,42,0.3));
                    border: 2px dashed rgba(0,212,255,0.3); border-radius: 16px;
                    padding: 4rem 2rem; text-align: center; margin-top: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📁</div>
            <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #94a3b8;">
                Drag and drop your document here
            </div>
            <div style="font-size: 12px; color: #64748b; margin-top: 0.5rem;">
                or click Browse files above
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    section_header("Analysis Results", "AI-extracted project information")

    if "analysis_result" not in st.session_state:
        st.info("👆 Upload and analyze a document first to see results here.")
    else:
        result: AnalysisResult = st.session_state.analysis_result
        tier_info = get_tier_display_info(result.tier)

        # Classification overview
        st.markdown("### Classification")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                        border: 1px solid {tier_info['color']}40; border-radius: 12px;
                        padding: 1.5rem; text-align: center;">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{tier_info['icon']}</div>
                <div style="font-family: 'Orbitron', sans-serif; font-size: 1.2rem;
                            font-weight: 700; color: {tier_info['color']};">{tier_info['name']}</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Project Type</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            confidence_pct = result.confidence * 100
            if confidence_pct >= 70:
                conf_color = "#22C55E"
            elif confidence_pct >= 40:
                conf_color = "#F59E0B"
            else:
                conf_color = "#EF4444"

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                        border: 1px solid {conf_color}40; border-radius: 12px;
                        padding: 1.5rem; text-align: center;">
                <div style="font-family: 'Orbitron', sans-serif; font-size: 2rem;
                            font-weight: 700; color: {conf_color};">{confidence_pct:.0f}%</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 0.5rem;">Confidence</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            subtype_display = result.subtype.replace("_", " ").title() if result.subtype else "Not Detected"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                        border: 1px solid rgba(0,212,255,0.2); border-radius: 12px;
                        padding: 1.5rem; text-align: center;">
                <div style="font-family: 'Orbitron', sans-serif; font-size: 1.1rem;
                            font-weight: 700; color: #00D4FF;">{subtype_display}</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 0.5rem;">Subtype</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            area = result.extracted_data.get("total_area_m2")
            area_display = f"{area:,.0f} m²" if area else "N/A"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                        border: 1px solid rgba(0,212,255,0.2); border-radius: 12px;
                        padding: 1.5rem; text-align: center;">
                <div style="font-family: 'Orbitron', sans-serif; font-size: 1.1rem;
                            font-weight: 700; color: #00D4FF;">{area_display}</div>
                <div style="font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 0.5rem;">Total Area</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Extracted Data
        extracted = result.extracted_data

        # Project Name
        if extracted.get("project_name"):
            st.markdown(f"**Project Name:** {extracted['project_name']}")

        # Rooms/Spaces
        if "rooms" in extracted and extracted["rooms"]:
            with st.expander("🏠 Rooms/Spaces Detected", expanded=True):
                room_data = []
                for room in extracted["rooms"]:
                    room_data.append({
                        "Name": room.get("name", "Unknown"),
                        "Type": room.get("type", "Unknown"),
                        "Area (m²)": room.get("area_m2") or "N/A"
                    })
                st.dataframe(room_data, use_container_width=True, hide_index=True)

        # Electrical Details
        if "electrical_details" in extracted:
            elec = extracted["electrical_details"]
            with st.expander("⚡ Electrical Details", expanded=True):
                elec_col1, elec_col2 = st.columns(2)
                with elec_col1:
                    st.markdown(f"**Supply Type:** {elec.get('supply_type', 'Unknown')}")
                    if elec.get("estimated_load_kva"):
                        st.markdown(f"**Estimated Load:** {elec['estimated_load_kva']} kVA")
                    if elec.get("main_breaker_size"):
                        st.markdown(f"**Main Breaker:** {elec['main_breaker_size']}")
                with elec_col2:
                    if elec.get("special_requirements"):
                        st.markdown("**Special Requirements:**")
                        for req in elec["special_requirements"]:
                            st.markdown(f"- {req}")

        # AI Reasoning
        with st.expander("🤖 AI Reasoning"):
            st.markdown(result.reasoning or "No reasoning provided.")

        # Warnings
        if result.warnings:
            st.markdown("### Warnings")
            for warning in result.warnings:
                st.warning(warning)

with tab3:
    section_header("Continue to Quotation", "Review and proceed with your project")

    if "analysis_result" not in st.session_state:
        st.info("👆 Upload and analyze a document first.")
    else:
        result: AnalysisResult = st.session_state.analysis_result
        tier_info = get_tier_display_info(result.tier)

        # Show classification summary
        if result.tier == ProjectTier.UNKNOWN or result.confidence < 0.3:
            st.warning("""
            **Classification Uncertain**

            The AI couldn't confidently classify this document.
            Please select the appropriate tier manually below.
            """)

            manual_tier = st.selectbox(
                "Select Project Tier",
                options=["residential", "commercial", "industrial", "infrastructure"],
                format_func=lambda x: f"{get_tier_display_info(ProjectTier(x))['icon']} {x.title()}"
            )
            result = AnalysisResult(
                tier=ProjectTier(manual_tier),
                confidence=1.0,  # Manual selection = 100% confidence
                subtype=None,
                extracted_data=result.extracted_data,
                reasoning="Manually selected by user",
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
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Confidence</div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #f1f5f9;">
                        {result.confidence * 100:.0f}%
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Subtype</div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #f1f5f9;">
                        {(result.subtype or 'General').replace('_', ' ').title()}
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Document</div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #f1f5f9;">
                        {st.session_state.get('uploaded_filename', 'Unknown')[:20]}...
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Pre-populate options
        st.markdown("### Data Transfer Options")

        transfer_data = st.checkbox(
            "Pre-populate extracted data in quotation page",
            value=True,
            help="Transfer rooms, areas, and electrical details to the quotation page"
        )

        st.markdown("---")

        # Navigation button
        if st.button(
            f"✅ Continue to {tier_info['name']} Quotation",
            type="primary",
            use_container_width=True
        ):
            # Store data in session state for target page
            st.session_state.from_smart_upload = True
            st.session_state.detected_tier = result.tier.value
            st.session_state.detected_subtype = result.subtype

            if transfer_data:
                st.session_state.extracted_data = result.extracted_data

                # Pre-populate tier-specific data
                if result.tier == ProjectTier.RESIDENTIAL and "rooms" in result.extracted_data:
                    # Convert to residential rooms format
                    rooms = []
                    for r in result.extracted_data["rooms"]:
                        area = r.get("area_m2", 16) or 16
                        rooms.append({
                            "name": r.get("name", "Room"),
                            "type": r.get("type", "Living Room"),
                            "w": (area ** 0.5),
                            "h": (area ** 0.5)
                        })
                    if rooms:
                        st.session_state.residential_rooms = rooms

            # Navigate to appropriate page
            target_page = get_tier_page_path(result.tier)
            st.switch_page(target_page)

        # Alternative: Go back to welcome
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Analyze Another Document", use_container_width=True):
                # Clear analysis state
                for key in ["analysis_result", "uploaded_filename", "from_smart_upload"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        with col2:
            if st.button("🏠 Return to Welcome", use_container_width=True):
                st.switch_page("pages/0_Welcome.py")
