"""
AfriPlan Electrical — SLD → BOQ Simulator

Simulates the 10-step electrical contractor process:
Upload electrical drawings (layout + SLDs) → AI extracts DB boards,
breakers, cables → Cross-references pages → Generates priced BOQ.

This page demonstrates the full pipeline from PDF to Bill of Quantities.
"""

import streamlit as st
import sys
import os
import time
import json
import io
import tempfile
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.styles import inject_custom_css
from utils.components import page_header, section_header

# Import the SLD BOQ Engine
BOQ_ENGINE_AVAILABLE = False
try:
    from agent.sld_boq_engine import (
        SLDBOQEngine,
        BOQResult,
        BOQItem,
        DBBoard,
        CableRun,
        export_boq_to_excel,
        print_boq_summary,
    )
    BOQ_ENGINE_AVAILABLE = True
except ImportError as e:
    BOQ_ENGINE_ERROR = str(e)

# ─── CSS ───
inject_custom_css()


def get_api_key() -> str:
    """Get Anthropic API key from secrets or session state."""
    if "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return st.session_state.get("api_key_input", "")


def render_pipeline_step(step_num: int, name: str, status: str = "pending",
                         detail: str = ""):
    """Render a single pipeline step indicator."""
    icons = {
        "pending": "⬜",
        "running": "🔄",
        "complete": "✅",
        "error": "❌",
    }
    icon = icons.get(status, "⬜")
    color = {
        "pending": "#666",
        "running": "#00D4FF",
        "complete": "#22C55E",
        "error": "#EF4444",
    }.get(status, "#666")

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; padding:4px 0;
                color:{color}; font-size:0.9em;">
        <span style="font-size:1.2em;">{icon}</span>
        <span style="font-weight:600;">Step {step_num}:</span>
        <span>{name}</span>
        <span style="color:#94a3b8; font-size:0.8em;">{detail}</span>
    </div>
    """, unsafe_allow_html=True)


def render_db_hierarchy(db_boards: list):
    """Render the DB board hierarchy as a visual tree."""
    if not db_boards:
        st.info("No DB boards extracted yet.")
        return

    # Build parent-child relationships
    children = {}
    roots = []
    for db in db_boards:
        parent = db.fed_from if hasattr(db, 'fed_from') else db.get("fed_from", "")
        name = db.name if hasattr(db, 'name') else db.get("name", "")
        if parent:
            children.setdefault(parent, []).append(db)
        # If parent is not another DB we know about
        known_names = [d.name if hasattr(d, 'name') else d.get("name", "") for d in db_boards]
        if not parent or parent not in known_names:
            roots.append(db)

    def render_node(db, indent=0):
        name = db.name if hasattr(db, 'name') else db.get("name", "")
        main_a = db.main_switch_a if hasattr(db, 'main_switch_a') else db.get("main_switch_a", 0)
        total = db.total_ways if hasattr(db, 'total_ways') else db.get("total_ways", 0)
        spare = db.spare_ways if hasattr(db, 'spare_ways') else db.get("spare_ways", 0)
        desc = db.description if hasattr(db, 'description') else db.get("description", "")

        prefix = "│  " * indent + ("├─ " if indent > 0 else "⚡ ")
        st.markdown(f"""
        <div style="font-family:monospace; padding:2px 0; color:#f1f5f9;">
            <span style="color:#00D4FF;">{prefix}</span>
            <span style="font-weight:bold; color:#00D4FF;">{name}</span>
            <span style="color:#94a3b8;"> ({main_a}A, {total} ways, {spare} spare)</span>
            {f'<span style="color:#666;"> — {desc}</span>' if desc else ''}
        </div>
        """, unsafe_allow_html=True)

        for child in children.get(name, []):
            render_node(child, indent + 1)

    for root in roots:
        render_node(root)


def render_boq_table(boq_items: list):
    """Render the BOQ items in a styled table grouped by section."""
    if not boq_items:
        st.info("No BOQ items generated yet.")
        return

    import pandas as pd

    # Group by section
    sections = {}
    for item in boq_items:
        sections.setdefault(item.section, []).append(item)

    for section, items in sections.items():
        section_total = sum(item.amount for item in items)

        with st.expander(f"📋 {section} — R {section_total:,.2f}", expanded=False):
            data = [{
                "Ref": item.ref,
                "Description": item.description,
                "Unit": item.unit,
                "Qty": item.quantity,
                "Rate (R)": f"{item.rate:,.2f}",
                "Amount (R)": f"{item.amount:,.2f}",
            } for item in items]

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_cable_schedule(cable_runs: list):
    """Render cable runs in a table."""
    if not cable_runs:
        st.info("No cable runs extracted.")
        return

    import pandas as pd
    data = [{
        "From": run.from_db if hasattr(run, 'from_db') else run.get("from_db", ""),
        "To": run.to_db if hasattr(run, 'to_db') else run.get("to_db", ""),
        "Cable Spec": run.spec if hasattr(run, 'spec') else run.get("spec", ""),
        "Length (m)": run.length_m if hasattr(run, 'length_m') else run.get("length_m", 0),
        "Source": run.source if hasattr(run, 'source') else run.get("source", ""),
    } for run in cable_runs]

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# MAIN PAGE
# ═══════════════════════════════════════════════════════════════

page_header("SLD → BOQ Simulator", "AI-Powered Bill of Quantities from Electrical Drawings")

if not BOQ_ENGINE_AVAILABLE:
    st.error(f"❌ BOQ Engine not available: {BOQ_ENGINE_ERROR}")
    st.stop()

# ─── SIDEBAR SETTINGS ───
with st.sidebar:
    st.markdown("### ⚙️ BOQ Simulator Settings")

    use_ai = st.toggle("Enable AI Vision", value=True,
                       help="Use Claude Vision to extract data from SLD pages. "
                            "Without AI, only text-layer data is available.")

    if use_ai:
        ai_model = st.selectbox("AI Model", [
            "claude-haiku-4-5-20241022",
            "claude-sonnet-4-5-20241022",
        ], index=0, help="Haiku is fast and cheap. Sonnet is more accurate.")

        api_key = get_api_key()
        if not api_key:
            api_key = st.text_input("Anthropic API Key", type="password",
                                    key="api_key_input",
                                    help="Required for AI Vision extraction")
    else:
        ai_model = ""
        api_key = ""

    st.divider()

    st.markdown("### 📊 Pipeline Steps")
    st.markdown("""
    1. **Page Classification** — Layout vs SLD
    2. **Layout Analysis** — Legend, DB locations, distances
    3. **SLD Extraction** — DB boards, breakers, cables
    4. **Cross-Reference** — Link SLDs to layout
    5. **Fixture Counting** — From legend
    6. **BOQ Generation** — Priced line items
    7. **Export** — Excel / PDF
    """)

    st.divider()

    st.markdown("### 💰 Cost Estimate")
    st.markdown("""
    - **Haiku**: ~R0.30/page
    - **Sonnet**: ~R2.50/page
    - **Layout + 7 SLDs**: ~R2.40 (Haiku)
    """)

# ─── FILE UPLOAD ───
st.markdown("### 📁 Upload Electrical Drawings")
st.markdown("Upload a PDF containing site layout + single-line diagrams (SLDs). "
            "The engine will extract DB boards, breakers, cables, and generate a complete BOQ.")

uploaded_file = st.file_uploader(
    "Drop your electrical drawing PDF here",
    type=["pdf"],
    key="boq_pdf_upload",
    help="Supports multi-page PDFs with layout plans and SLD diagrams"
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    file_size_kb = len(file_bytes) / 1024

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("File", uploaded_file.name)
    with col2:
        st.metric("Size", f"{file_size_kb:.0f} KB")
    with col3:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        st.metric("Pages", len(doc))
        doc.close()

    st.divider()

    # ─── PROCESS BUTTON ───
    if st.button("🚀 Generate BOQ", type="primary", use_container_width=True):

        if use_ai and not api_key:
            st.error("⚠️ Please enter your Anthropic API key in the sidebar.")
            st.stop()

        # Progress tracking
        progress_bar = st.progress(0)
        status_container = st.empty()

        pipeline_steps = {
            1: "Page Classification",
            2: "Layout Analysis",
            3: "SLD AI Extraction",
            5: "Cross-Reference",
            6: "Fixture Counting",
            8: "BOQ Generation",
            10: "Complete",
        }

        step_status = {k: "pending" for k in pipeline_steps}

        def progress_callback(stage: int, name: str, detail: str):
            # Update progress bar
            progress = min(stage / 10, 1.0)
            progress_bar.progress(progress)

            # Update status
            for s in step_status:
                if s < stage:
                    step_status[s] = "complete"
                elif s == stage:
                    step_status[s] = "running"

            status_container.markdown(f"**Step {stage}:** {name} — {detail}")

        # Run the engine
        try:
            engine = SLDBOQEngine(
                api_key=api_key,
                use_ai=use_ai,
                sld_model=ai_model if use_ai else "",
                layout_model=ai_model if use_ai else "",
            )

            boq_result = engine.process_pdf(file_bytes, progress_callback=progress_callback)

            progress_bar.progress(1.0)
            status_container.success(
                f"✅ BOQ generated: **{len(boq_result.boq_items)} items**, "
                f"**R {boq_result.total_incl_vat:,.2f}** incl. VAT "
                f"(AI cost: R{boq_result.ai_cost_zar:.2f}, "
                f"Time: {boq_result.processing_time_s}s)"
            )

            # Store in session state
            st.session_state["boq_result"] = boq_result
            st.session_state["boq_engine"] = engine

        except Exception as e:
            progress_bar.progress(0)
            st.error(f"❌ Pipeline error: {str(e)}")
            import traceback
            with st.expander("Error details"):
                st.code(traceback.format_exc())

# ─── RESULTS DISPLAY ───
if "boq_result" in st.session_state:
    boq: BOQResult = st.session_state["boq_result"]

    st.divider()
    st.markdown("## 📊 Results")

    # ─── SUMMARY METRICS ───
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("DB Boards", len(boq.db_boards))
    with m2:
        st.metric("Cable Runs", len(boq.cable_runs))
    with m3:
        st.metric("BOQ Items", len(boq.boq_items))
    with m4:
        st.metric("Total excl. VAT", f"R {boq.total_excl_vat:,.0f}")
    with m5:
        st.metric("Total incl. VAT", f"R {boq.total_incl_vat:,.0f}")

    # ─── TABS ───
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔌 DB Hierarchy",
        "🔗 Cable Schedule",
        "📋 Bill of Quantities",
        "📊 Cost Breakdown",
        "📥 Export",
    ])

    with tab1:
        st.markdown("### Distribution Board Hierarchy")
        st.markdown("*Extracted from single-line diagrams using AI Vision*")
        render_db_hierarchy(boq.db_boards)

        st.divider()
        st.markdown("### Breaker Schedule per DB")
        for db in boq.db_boards:
            with st.expander(f"⚡ {db.name} — {db.main_switch_a}A "
                           f"({db.total_ways} ways, {db.spare_ways} spare) "
                           f"— Page {db.page_num}"):
                st.markdown(f"**Rating:** {db.rating}")
                st.markdown(f"**Fed from:** {db.fed_from}")
                st.markdown(f"**Incoming cable:** {db.incoming_cable}")

                if db.breakers:
                    import pandas as pd
                    br_data = [{
                        "Ref": br.ref,
                        "Rating (A)": br.rating_a,
                        "Poles": br.poles,
                        "Type": br.type,
                        "Feeds": br.feeds,
                        "Cable": br.cable_spec,
                        "Load (W)": br.load_w if br.load_w > 0 else "",
                    } for br in db.breakers]
                    st.dataframe(pd.DataFrame(br_data), use_container_width=True,
                               hide_index=True)

    with tab2:
        st.markdown("### Cable Schedule")
        st.markdown("*SWA inter-board cables with specifications and distances*")
        render_cable_schedule(boq.cable_runs)

    with tab3:
        st.markdown("### Bill of Quantities")
        st.markdown(f"*{len(boq.boq_items)} line items across "
                   f"{len(set(i.section for i in boq.boq_items))} sections*")
        render_boq_table(boq.boq_items)

    with tab4:
        st.markdown("### Cost Breakdown by Section")

        import pandas as pd

        section_totals = {}
        for item in boq.boq_items:
            section_totals[item.section] = section_totals.get(item.section, 0) + item.amount

        chart_data = pd.DataFrame({
            "Section": list(section_totals.keys()),
            "Amount (R)": list(section_totals.values()),
        })

        st.bar_chart(chart_data.set_index("Section"), horizontal=True)

        st.divider()

        # Summary table
        summary_data = []
        for section, total in section_totals.items():
            pct = (total / boq.total_excl_vat * 100) if boq.total_excl_vat > 0 else 0
            summary_data.append({
                "Section": section,
                "Amount (R)": f"{total:,.2f}",
                "% of Total": f"{pct:.1f}%",
            })
        summary_data.append({
            "Section": "TOTAL EXCL. VAT",
            "Amount (R)": f"{boq.total_excl_vat:,.2f}",
            "% of Total": "100%",
        })
        summary_data.append({
            "Section": "VAT (15%)",
            "Amount (R)": f"{boq.vat:,.2f}",
            "% of Total": "",
        })
        summary_data.append({
            "Section": "TOTAL INCL. VAT",
            "Amount (R)": f"{boq.total_incl_vat:,.2f}",
            "% of Total": "",
        })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("### Export Options")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 📊 Excel BOQ")
            st.markdown("Professional Excel workbook with Cover, BOQ, and DB Schedule sheets.")

            if st.button("📥 Generate Excel", key="gen_excel"):
                with st.spinner("Generating Excel..."):
                    try:
                        excel_bytes = export_boq_to_excel(boq)
                        st.download_button(
                            label="⬇️ Download Excel BOQ",
                            data=excel_bytes,
                            file_name=f"AfriPlan_BOQ_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_excel",
                        )
                    except Exception as e:
                        st.error(f"Excel export failed: {e}")

        with col_b:
            st.markdown("#### 📄 JSON Data")
            st.markdown("Raw extraction data for further processing or integration.")

            json_data = {
                "project": {
                    "name": boq.project_name,
                    "description": boq.project_description,
                    "consultant": boq.consultant,
                    "standard": boq.standard,
                },
                "db_boards": [{
                    "name": db.name,
                    "rating": db.rating,
                    "main_switch_a": db.main_switch_a,
                    "fed_from": db.fed_from,
                    "incoming_cable": db.incoming_cable,
                    "total_ways": db.total_ways,
                    "spare_ways": db.spare_ways,
                    "breakers": [{
                        "ref": br.ref,
                        "rating_a": br.rating_a,
                        "poles": br.poles,
                        "type": br.type,
                        "feeds": br.feeds,
                        "cable_spec": br.cable_spec,
                        "load_w": br.load_w,
                    } for br in db.breakers]
                } for db in boq.db_boards],
                "cable_runs": [{
                    "from": run.from_db,
                    "to": run.to_db,
                    "spec": run.spec,
                    "length_m": run.length_m,
                } for run in boq.cable_runs],
                "totals": {
                    "excl_vat": boq.total_excl_vat,
                    "vat": boq.vat,
                    "incl_vat": boq.total_incl_vat,
                    "items": len(boq.boq_items),
                },
                "metadata": {
                    "extraction_method": boq.extraction_method,
                    "pages_processed": boq.pages_processed,
                    "ai_cost_zar": boq.ai_cost_zar,
                    "processing_time_s": boq.processing_time_s,
                    "generated_at": datetime.now().isoformat(),
                }
            }

            st.download_button(
                label="⬇️ Download JSON",
                data=json.dumps(json_data, indent=2),
                file_name=f"AfriPlan_BOQ_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                key="download_json",
            )

        st.divider()

        # Pipeline metadata
        st.markdown("### 🔍 Pipeline Metadata")
        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
        with meta_col1:
            st.metric("Extraction Method", boq.extraction_method)
        with meta_col2:
            st.metric("Pages Processed", boq.pages_processed)
        with meta_col3:
            st.metric("AI Cost", f"R {boq.ai_cost_zar:.2f}")
        with meta_col4:
            st.metric("Processing Time", f"{boq.processing_time_s}s")

        # Show raw AI responses if available
        engine = st.session_state.get("boq_engine")
        if engine and hasattr(engine, "stage_results"):
            with st.expander("🔧 Raw AI Extraction Data"):
                st.json(engine.stage_results.get("sld_extraction", []))

else:
    # No results yet — show instructions
    st.divider()
    st.markdown("### 🔧 How It Works")

    st.markdown("""
    This simulator replicates the **10-step process** an electrical contractor follows
    when building a Bill of Quantities from engineering drawings:

    | Step | What | How |
    |------|------|-----|
    | 1 | **Page Classification** | Identifies layout vs SLD pages |
    | 2 | **Layout Analysis** | Extracts legend, DB locations, cable distances from text layer |
    | 3 | **SLD Extraction** | AI Vision reads DB boards, breakers, cable specs from SLD images |
    | 4 | **Cable Extraction** | Captures every cable spec and rating from SLDs |
    | 5 | **Cross-Reference** | Links SLD cable specs to layout route distances |
    | 6 | **Fixture Counting** | Counts light/socket symbols from layout legend |
    | 7 | **Containment** | Derives trenching, glands, cable trays from cable data |
    | 8 | **Labour** | Calculates installation hours per item type |
    | 9 | **Pricing** | Applies SA 2025 material and labour rates |
    | 10 | **BOQ Assembly** | Structures into sections A–H with totals |
    """)

    st.info("👆 Upload a PDF above to start the BOQ generation pipeline.")
