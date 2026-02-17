"""
AfriPlan Electrical v4.1 — Site Conditions Page

Contractor fills in site-specific factors that affect pricing.
These factors are not on any drawing but significantly impact costs.
"""

import streamlit as st

from agent.models import SiteConditions

st.set_page_config(
    page_title="Site Conditions | AfriPlan",
    page_icon="🏗️",
    layout="wide",
)


def main():
    st.title("🏗️ Site Conditions")
    st.markdown("Enter site-specific factors that affect pricing. These factors aren't on the drawings.")

    # Check for extraction
    if "extraction" not in st.session_state:
        st.warning("No extraction data available. Please upload documents first.")
        return

    # Initialize site conditions
    if "site_conditions" not in st.session_state:
        st.session_state.site_conditions = SiteConditions()

    site = st.session_state.site_conditions

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Project Type",
        "🚧 Access & Height",
        "🔨 Site Works",
        "📍 Logistics"
    ])

    with tab1:
        st.subheader("Project Type")

        col1, col2, col3 = st.columns(3)

        with col1:
            is_new_build = st.checkbox(
                "New Build",
                value=site.is_new_build,
                help="New construction, not renovation"
            )

        with col2:
            is_renovation = st.checkbox(
                "Renovation",
                value=site.is_renovation,
                help="Working in existing building (+30% labour)"
            )

        with col3:
            is_occupied = st.checkbox(
                "Occupied Building",
                value=site.is_occupied,
                help="Building in use during work (+15% labour)"
            )

        st.markdown("---")

        walls_type = st.radio(
            "Wall Construction",
            options=["brick", "dry_wall", "concrete"],
            index=["brick", "dry_wall", "concrete"].index(site.walls_brick_or_dry),
            horizontal=True,
            help="Affects chasing/conduit installation time"
        )

        existing_condition = st.select_slider(
            "Existing Wiring Condition (if renovation)",
            options=["good", "fair", "poor", "unknown"],
            value=site.existing_wiring_condition,
            disabled=not is_renovation
        )

        has_asbestos = st.checkbox(
            "Asbestos Risk",
            value=site.has_asbestos_risk,
            help="Requires specialist handling"
        )

    with tab2:
        st.subheader("Access & Working Height")

        access_difficulty = st.select_slider(
            "Site Access Difficulty",
            options=["easy", "normal", "difficult", "restricted"],
            value=site.access_difficulty,
            help="Easy: Open site | Normal: Standard | Difficult: Multi-story, narrow | Restricted: Security clearance"
        )

        # Show multiplier impact
        access_mult = {"easy": 0.95, "normal": 1.0, "difficult": 1.20, "restricted": 1.35}
        mult = access_mult.get(access_difficulty, 1.0)
        if mult != 1.0:
            delta = f"{(mult - 1) * 100:+.0f}% labour"
        else:
            delta = "Standard"
        st.caption(f"Impact: {delta}")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            needs_scaffolding = st.checkbox(
                "Scaffolding Required",
                value=site.needs_scaffolding,
                help="+15% on labour if scaffolding needed"
            )

        with col2:
            max_height = st.number_input(
                "Maximum Working Height (m)",
                value=site.max_working_height_m,
                min_value=2.0,
                max_value=20.0,
                step=0.5
            )

    with tab3:
        st.subheader("Site Works & Trenching")

        soil_type = st.select_slider(
            "Soil Type (for trenching)",
            options=["soft", "normal", "hard_clay", "rock"],
            value=site.soil_type,
            help="Affects trenching costs significantly"
        )

        # Show trenching multiplier
        soil_mult = {"soft": 0.80, "normal": 1.0, "hard_clay": 1.40, "rock": 2.50}
        t_mult = soil_mult.get(soil_type, 1.0)
        if t_mult < 1.0:
            st.success(f"Trenching cost: {t_mult:.0%} of standard")
        elif t_mult > 1.0:
            st.warning(f"Trenching cost: {t_mult:.0%} of standard")
        else:
            st.info("Trenching cost: Standard")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            site_storage = st.checkbox(
                "Site Storage Available",
                value=site.site_storage_available,
                help="Can materials be stored on site?"
            )

        with col2:
            security_required = st.checkbox(
                "Security Required",
                value=site.security_required,
                help="Site guard or security measures needed"
            )

    with tab4:
        st.subheader("Logistics & Timeline")

        col1, col2 = st.columns(2)

        with col1:
            distance_base = st.number_input(
                "Distance from Base (km)",
                value=site.distance_from_base_km,
                min_value=0.0,
                max_value=500.0,
                step=5.0,
                help="Distance from your workshop/office"
            )

            distance_supplier = st.number_input(
                "Distance from Supplier (km)",
                value=site.distance_from_supplier_km,
                min_value=0.0,
                max_value=500.0,
                step=5.0,
                help="Distance from main electrical supplier"
            )

        with col2:
            working_hours = st.selectbox(
                "Working Hours",
                options=["standard", "extended", "night_work"],
                index=["standard", "extended", "night_work"].index(site.working_hours),
                help="Standard: 07-17 | Extended: 06-20 | Night: After hours"
            )

            is_rush_job = st.checkbox(
                "Rush Job",
                value=site.is_rush_job,
                help="+25% on labour for expedited timeline"
            )

        st.markdown("---")

        # Ensure duration is at least 1
        duration_val = max(1, site.estimated_duration_days or 1)
        estimated_days = st.number_input(
            "Your Estimated Duration (days)",
            value=duration_val,
            min_value=1,
            max_value=365,
            step=1,
            help="Your estimate of project duration"
        )

        notes = st.text_area(
            "Additional Notes",
            value=site.notes,
            placeholder="Any other site-specific considerations...",
            height=100
        )

    # Summary
    st.markdown("---")
    st.subheader("📊 Impact Summary")

    # Update site conditions
    site.is_new_build = is_new_build
    site.is_renovation = is_renovation
    site.is_occupied = is_occupied
    site.walls_brick_or_dry = walls_type
    site.existing_wiring_condition = existing_condition
    site.has_asbestos_risk = has_asbestos
    site.access_difficulty = access_difficulty
    site.needs_scaffolding = needs_scaffolding
    site.max_working_height_m = max_height
    site.soil_type = soil_type
    site.site_storage_available = site_storage
    site.security_required = security_required
    site.distance_from_base_km = distance_base
    site.distance_from_supplier_km = distance_supplier
    site.working_hours = working_hours
    site.is_rush_job = is_rush_job
    site.estimated_duration_days = estimated_days
    site.notes = notes

    # Display calculated multipliers
    col1, col2, col3 = st.columns(3)

    with col1:
        labour_mult = site.labour_multiplier
        if labour_mult > 1.0:
            st.metric("Labour Multiplier", f"×{labour_mult:.2f}",
                     delta=f"+{(labour_mult-1)*100:.0f}%", delta_color="inverse")
        else:
            st.metric("Labour Multiplier", f"×{labour_mult:.2f}")

    with col2:
        trench_mult = site.trenching_multiplier
        if trench_mult > 1.0:
            st.metric("Trenching Multiplier", f"×{trench_mult:.2f}",
                     delta=f"+{(trench_mult-1)*100:.0f}%", delta_color="inverse")
        elif trench_mult < 1.0:
            st.metric("Trenching Multiplier", f"×{trench_mult:.2f}",
                     delta=f"{(trench_mult-1)*100:.0f}%", delta_color="normal")
        else:
            st.metric("Trenching Multiplier", f"×{trench_mult:.2f}")

    with col3:
        transport = site.transport_cost_zar
        st.metric("Est. Transport Cost", f"R {transport:,.0f}")

    # Save and continue
    st.markdown("---")

    if st.button("✅ Save & Generate BQ", type="primary", use_container_width=True):
        st.session_state.site_conditions = site
        st.success("Site conditions saved!")
        st.switch_page("pages/8_Results.py")


if __name__ == "__main__":
    main()
