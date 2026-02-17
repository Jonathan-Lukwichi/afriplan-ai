"""
AfriPlan Electrical v4.1 — Review Page

THE MAIN SCREEN: Contractor reviews and corrects AI extraction.
Color-coded confidence: Green = extracted, Yellow = inferred, Red = estimated
"""

import streamlit as st
import json
from typing import Dict, Any, List

from agent.models import (
    ExtractionResult, ItemConfidence, Room, FixtureCounts,
    BuildingBlock, DistributionBoard, Circuit, SiteCableRun
)
from agent.stages.review import ReviewManager, get_items_needing_review

st.set_page_config(
    page_title="Review | AfriPlan",
    page_icon="📝",
    layout="wide",
)

# Confidence colors
CONFIDENCE_COLORS = {
    ItemConfidence.EXTRACTED: "#22C55E",   # Green
    ItemConfidence.INFERRED: "#F59E0B",    # Yellow/Amber
    ItemConfidence.ESTIMATED: "#EF4444",   # Red
    ItemConfidence.MANUAL: "#3B82F6",      # Blue
}


def get_confidence_badge(confidence: ItemConfidence) -> str:
    """Get HTML badge for confidence level."""
    color = CONFIDENCE_COLORS.get(confidence, "#64748b")
    label = confidence.value.upper()
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{label}</span>'


def main():
    st.title("📝 Review AI Extraction")
    st.markdown("Review and correct the AI-extracted quantities. Items in **red** need attention.")

    # Check for extraction data
    if "extraction" not in st.session_state or st.session_state.extraction is None:
        st.warning("No extraction data available. Please upload documents first.")
        if st.button("Go to Upload"):
            st.switch_page("pages/1_Smart_Upload.py")
        return

    extraction: ExtractionResult = st.session_state.extraction

    # Initialize review manager
    if "review_manager" not in st.session_state:
        project_name = extraction.metadata.project_name or "Project"
        st.session_state.review_manager = ReviewManager(extraction, project_name)

    review_manager: ReviewManager = st.session_state.review_manager

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Building Blocks", len(extraction.building_blocks))
    with col2:
        st.metric("Distribution Boards", extraction.total_dbs)
    with col3:
        st.metric("Rooms", len(extraction.all_rooms))
    with col4:
        items_needing_review = get_items_needing_review(extraction)
        st.metric("Items to Review", len(items_needing_review),
                  delta="Needs attention" if items_needing_review else "All good",
                  delta_color="inverse" if items_needing_review else "normal")

    st.markdown("---")

    # Legend
    with st.expander("📖 Color Legend", expanded=False):
        cols = st.columns(4)
        cols[0].markdown(f"🟢 **EXTRACTED** — Read from drawing")
        cols[1].markdown(f"🟡 **INFERRED** — Calculated")
        cols[2].markdown(f"🔴 **ESTIMATED** — Needs verification")
        cols[3].markdown(f"🔵 **MANUAL** — You edited this")

    # Tabs for different data types
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 Building Blocks",
        "⚡ Distribution Boards",
        "🚿 Rooms & Fixtures",
        "🔌 Site Cables"
    ])

    with tab1:
        _render_building_blocks(extraction, review_manager)

    with tab2:
        _render_distribution_boards(extraction, review_manager)

    with tab3:
        _render_rooms(extraction, review_manager)

    with tab4:
        _render_site_cables(extraction, review_manager)

    # Action buttons
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("↩️ Reset Changes", use_container_width=True):
            project_name = extraction.metadata.project_name or "Project"
            st.session_state.review_manager = ReviewManager(extraction, project_name)
            st.rerun()

    with col2:
        if st.button("📊 View Accuracy", use_container_width=True):
            report = review_manager.get_accuracy_report()
            st.json(report)

    with col3:
        if st.button("✅ Complete Review & Continue", type="primary", use_container_width=True):
            # Complete the review
            st.session_state.extraction = review_manager.complete_review()
            st.session_state.review_completed = True
            st.success("Review completed! Proceeding to Site Conditions...")
            st.switch_page("pages/7_Site_Conditions.py")


def _render_building_blocks(extraction: ExtractionResult, review_manager: ReviewManager):
    """Render building blocks overview."""
    st.subheader("Building Blocks")

    for i, block in enumerate(extraction.building_blocks):
        with st.expander(f"🏢 {block.name}", expanded=i == 0):
            col1, col2, col3 = st.columns(3)
            col1.metric("DBs", block.total_dbs)
            col2.metric("Rooms", len(block.rooms))
            col3.metric("Total Points", block.total_points)

            # Editable block name
            new_name = st.text_input(
                "Block Name",
                value=block.name,
                key=f"block_name_{i}"
            )
            if new_name != block.name:
                block.name = new_name

            # Description
            new_desc = st.text_area(
                "Description",
                value=block.description,
                key=f"block_desc_{i}",
                height=80
            )
            if new_desc != block.description:
                block.description = new_desc


def _render_distribution_boards(extraction: ExtractionResult, review_manager: ReviewManager):
    """Render distribution boards with circuits."""
    st.subheader("Distribution Boards")

    for block in extraction.building_blocks:
        st.markdown(f"### {block.name}")

        for db_idx, db in enumerate(block.distribution_boards):
            conf_badge = get_confidence_badge(db.confidence)
            with st.expander(f"⚡ {db.name} ({db.total_ways} ways) {conf_badge}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    main_breaker = st.number_input(
                        "Main Breaker (A)",
                        value=db.main_breaker_a,
                        min_value=20,
                        max_value=400,
                        step=20,
                        key=f"db_main_{block.name}_{db_idx}"
                    )
                    if main_breaker != db.main_breaker_a:
                        review_manager.update_circuit_value(
                            block.name, db.name, "", "main_breaker_a", main_breaker
                        )
                        db.main_breaker_a = main_breaker

                with col2:
                    st.checkbox(
                        "ELCB Present",
                        value=db.earth_leakage,
                        key=f"db_elcb_{block.name}_{db_idx}"
                    )

                with col3:
                    st.checkbox(
                        "Surge Protection",
                        value=db.surge_protection,
                        key=f"db_spd_{block.name}_{db_idx}"
                    )

                with col4:
                    spare_ways = st.number_input(
                        "Spare Ways",
                        value=db.spare_ways,
                        min_value=0,
                        max_value=20,
                        key=f"db_spare_{block.name}_{db_idx}"
                    )
                    if spare_ways != db.spare_ways:
                        db.spare_ways = spare_ways

                # Circuits table
                st.markdown("**Circuits:**")

                for ckt_idx, circuit in enumerate(db.circuits):
                    if circuit.is_spare:
                        continue

                    conf_color = CONFIDENCE_COLORS.get(circuit.confidence, "#64748b")

                    cols = st.columns([0.5, 2, 1, 1, 1, 1])

                    cols[0].markdown(
                        f"<span style='color:{conf_color};font-weight:bold;'>{circuit.id}</span>",
                        unsafe_allow_html=True
                    )
                    cols[1].text(circuit.description[:40])

                    new_breaker = cols[2].number_input(
                        "A",
                        value=circuit.breaker_a,
                        min_value=6,
                        max_value=100,
                        key=f"ckt_breaker_{block.name}_{db.name}_{ckt_idx}",
                        label_visibility="collapsed"
                    )

                    new_cable = cols[3].selectbox(
                        "Cable",
                        options=[1.5, 2.5, 4.0, 6.0, 10.0, 16.0],
                        index=[1.5, 2.5, 4.0, 6.0, 10.0, 16.0].index(circuit.cable_size_mm2) if circuit.cable_size_mm2 in [1.5, 2.5, 4.0, 6.0, 10.0, 16.0] else 1,
                        key=f"ckt_cable_{block.name}_{db.name}_{ckt_idx}",
                        label_visibility="collapsed"
                    )

                    new_points = cols[4].number_input(
                        "Pts",
                        value=circuit.num_points,
                        min_value=0,
                        max_value=20,
                        key=f"ckt_points_{block.name}_{db.name}_{ckt_idx}",
                        label_visibility="collapsed"
                    )

                    # Clamp wattage to valid range (commercial can have high values)
                    wattage_val = min(int(circuit.wattage_w), 500000)
                    new_watts = cols[5].number_input(
                        "W",
                        value=wattage_val,
                        min_value=0,
                        max_value=500000,
                        step=100,
                        key=f"ckt_watts_{block.name}_{db.name}_{ckt_idx}",
                        label_visibility="collapsed"
                    )

                    # Track changes
                    if new_breaker != circuit.breaker_a:
                        review_manager.update_circuit_value(
                            block.name, db.name, circuit.id, "breaker_a", new_breaker
                        )
                        circuit.breaker_a = new_breaker

                    if new_cable != circuit.cable_size_mm2:
                        review_manager.update_circuit_value(
                            block.name, db.name, circuit.id, "cable_size_mm2", new_cable
                        )
                        circuit.cable_size_mm2 = new_cable


def _render_rooms(extraction: ExtractionResult, review_manager: ReviewManager):
    """Render rooms with fixture counts."""
    st.subheader("Rooms & Fixtures")

    for block in extraction.building_blocks:
        st.markdown(f"### {block.name}")

        for room_idx, room in enumerate(block.rooms):
            conf_badge = get_confidence_badge(room.confidence)

            with st.expander(f"🚿 {room.name} {conf_badge}", expanded=False):
                st.markdown("**Light Fittings:**")

                light_fields = [
                    ("recessed_led_600x1200", "600×1200 Recessed LED"),
                    ("surface_mount_led_18w", "18W Surface Mount"),
                    ("downlight_led_6w", "6W Downlight"),
                    ("vapor_proof_2x24w", "2×24W Vapor Proof"),
                    ("vapor_proof_2x18w", "2×18W Vapor Proof"),
                    ("bulkhead_26w", "26W Bulkhead"),
                    ("flood_light_200w", "200W Flood Light"),
                    ("pole_light_60w", "60W Pole Light"),
                ]

                cols = st.columns(4)
                for i, (field, label) in enumerate(light_fields):
                    col = cols[i % 4]
                    current_val = getattr(room.fixtures, field, 0)
                    new_val = col.number_input(
                        label,
                        value=current_val,
                        min_value=0,
                        max_value=100,
                        key=f"room_{block.name}_{room_idx}_{field}"
                    )
                    if new_val != current_val:
                        review_manager.update_fixture_count(
                            block.name, room.name, field, new_val
                        )
                        setattr(room.fixtures, field, new_val)

                st.markdown("**Sockets & Switches:**")

                socket_fields = [
                    ("double_socket_300", "Double @300mm"),
                    ("double_socket_1100", "Double @1100mm"),
                    ("single_socket_300", "Single @300mm"),
                    ("double_socket_waterproof", "Waterproof"),
                    ("switch_1lever_1way", "1L 1W Switch"),
                    ("switch_2lever_1way", "2L 1W Switch"),
                    ("isolator_30a", "30A Isolator"),
                    ("data_points_cat6", "CAT6 Data"),
                ]

                cols = st.columns(4)
                for i, (field, label) in enumerate(socket_fields):
                    col = cols[i % 4]
                    current_val = getattr(room.fixtures, field, 0)
                    new_val = col.number_input(
                        label,
                        value=current_val,
                        min_value=0,
                        max_value=50,
                        key=f"room_sock_{block.name}_{room_idx}_{field}"
                    )
                    if new_val != current_val:
                        review_manager.update_fixture_count(
                            block.name, room.name, field, new_val
                        )
                        setattr(room.fixtures, field, new_val)

                # Room totals
                st.markdown(f"**Totals:** {room.fixtures.total_lights} lights, "
                           f"{room.fixtures.total_sockets} sockets, "
                           f"{room.fixtures.total_switches} switches")


def _render_site_cables(extraction: ExtractionResult, review_manager: ReviewManager):
    """Render site cable runs."""
    st.subheader("Site Cable Runs")

    if not extraction.site_cable_runs:
        st.info("No site cable runs detected.")
        return

    for i, run in enumerate(extraction.site_cable_runs):
        conf_badge = get_confidence_badge(run.confidence)

        with st.expander(f"🔌 {run.from_point} → {run.to_point} {conf_badge}", expanded=False):
            cols = st.columns(4)

            with cols[0]:
                st.text(f"Cable: {run.cable_spec}")

            with cols[1]:
                new_length = st.number_input(
                    "Length (m)",
                    value=run.length_m,
                    min_value=1.0,
                    max_value=1000.0,
                    step=5.0,
                    key=f"cable_length_{i}"
                )
                if new_length != run.length_m:
                    review_manager.update_cable_length(
                        run.from_point, run.to_point, new_length
                    )
                    run.length_m = new_length

            with cols[2]:
                st.checkbox("Underground", value=run.is_underground, key=f"cable_ug_{i}")

            with cols[3]:
                st.checkbox("Needs Trenching", value=run.needs_trenching, key=f"cable_trench_{i}")

            if run.notes:
                st.caption(f"Note: {run.notes}")


if __name__ == "__main__":
    main()
