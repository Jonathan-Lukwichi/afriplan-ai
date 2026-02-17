"""
AfriPlan Electrical v4.1 — Contractor Profile Page

Contractor's saved preferences for personalized quotations.
"""

import streamlit as st
from datetime import datetime

from agent.models import ContractorProfile, LabourRates

st.set_page_config(
    page_title="Profile | AfriPlan",
    page_icon="👤",
    layout="wide",
)


def main():
    st.title("👤 Contractor Profile")
    st.markdown("Save your company details and pricing preferences for personalized quotations.")

    # Initialize session state
    if "contractor_profile" not in st.session_state:
        st.session_state.contractor_profile = ContractorProfile()

    profile = st.session_state.contractor_profile

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Company Details",
        "💰 Financial Settings",
        "👷 Labour Rates",
        "📦 Supplier Preferences"
    ])

    with tab1:
        st.subheader("Company Information")

        col1, col2 = st.columns(2)

        with col1:
            company_name = st.text_input(
                "Company Name",
                value=profile.company_name,
                placeholder="ABC Electrical Contractors"
            )
            registration_number = st.text_input(
                "Registration Number (ECSA/CIDB)",
                value=profile.registration_number,
                placeholder="EC12345"
            )
            vat_number = st.text_input(
                "VAT Number",
                value=profile.vat_number,
                placeholder="4123456789"
            )

        with col2:
            contact_name = st.text_input(
                "Contact Name",
                value=profile.contact_name,
                placeholder="John Smith"
            )
            contact_phone = st.text_input(
                "Contact Phone",
                value=profile.contact_phone,
                placeholder="011 234 5678"
            )
            contact_email = st.text_input(
                "Contact Email",
                value=profile.contact_email,
                placeholder="john@example.com"
            )

        physical_address = st.text_area(
            "Physical Address",
            value=profile.physical_address,
            placeholder="123 Main Street, Johannesburg, 2000"
        )

        base_location = st.text_input(
            "Base Location (for travel calculations)",
            value=profile.base_location,
            placeholder="Johannesburg"
        )

        max_travel_km = st.number_input(
            "Maximum Travel Distance (km)",
            value=profile.max_travel_km,
            min_value=10,
            max_value=500,
            step=10
        )

    with tab2:
        st.subheader("Financial Settings")

        col1, col2 = st.columns(2)

        with col1:
            markup_pct = st.slider(
                "Default Markup %",
                min_value=5.0,
                max_value=50.0,
                value=profile.markup_pct,
                step=1.0,
                help="Your profit margin on materials and labour"
            )

            contingency_pct = st.slider(
                "Default Contingency %",
                min_value=0.0,
                max_value=15.0,
                value=profile.contingency_pct,
                step=0.5,
                help="Buffer for unforeseen costs"
            )

        with col2:
            vat_pct = st.number_input(
                "VAT %",
                value=profile.vat_pct,
                min_value=0.0,
                max_value=20.0,
                step=0.5,
                disabled=True,
                help="VAT rate (currently 15%)"
            )

            payment_terms = st.selectbox(
                "Default Payment Terms",
                options=["40/40/20", "50/30/20", "30/30/30/10", "50/50"],
                index=["40/40/20", "50/30/20", "30/30/30/10", "50/50"].index(profile.payment_terms) if profile.payment_terms in ["40/40/20", "50/30/20", "30/30/30/10", "50/50"] else 0
            )

        st.markdown("---")

        bq_format = st.radio(
            "Preferred BQ Format",
            options=["detailed", "summary", "jbcc"],
            index=["detailed", "summary", "jbcc"].index(profile.bq_format) if profile.bq_format in ["detailed", "summary", "jbcc"] else 0,
            horizontal=True,
            help="How detailed should the BQ export be?"
        )

    with tab3:
        st.subheader("Labour Rates")
        st.markdown("Enter your actual labour rates for accurate quotations.")

        labour = profile.labour_rates

        col1, col2 = st.columns(2)

        with col1:
            electrician_daily = st.number_input(
                "Electrician Daily Rate (R)",
                value=labour.electrician_daily_zar,
                min_value=500.0,
                max_value=5000.0,
                step=100.0
            )

            assistant_daily = st.number_input(
                "Assistant Daily Rate (R)",
                value=labour.assistant_daily_zar,
                min_value=200.0,
                max_value=2000.0,
                step=50.0
            )

            foreman_daily = st.number_input(
                "Foreman Daily Rate (R)",
                value=labour.foreman_daily_zar,
                min_value=1000.0,
                max_value=6000.0,
                step=100.0
            )

        with col2:
            team_electricians = st.number_input(
                "Team Size - Electricians",
                value=labour.team_size_electricians,
                min_value=1,
                max_value=10,
                step=1
            )

            team_assistants = st.number_input(
                "Team Size - Assistants",
                value=labour.team_size_assistants,
                min_value=0,
                max_value=10,
                step=1
            )

            travel_rate = st.number_input(
                "Travel Rate (R/km)",
                value=labour.travel_rate_per_km_zar,
                min_value=2.0,
                max_value=15.0,
                step=0.50
            )

        # Calculate and display team rate
        team_daily = (electrician_daily * team_electricians +
                      assistant_daily * team_assistants)

        st.metric(
            "Team Daily Rate",
            f"R {team_daily:,.2f}",
            help="Combined daily rate for your standard team"
        )

    with tab4:
        st.subheader("Supplier Preferences")

        preferred_supplier = st.selectbox(
            "Preferred Supplier",
            options=["", "Voltex", "ARB", "Major Tech", "Eurolux", "Radiant", "Other"],
            index=0,
            help="Default supplier for pricing"
        )

        st.markdown("---")
        st.subheader("Custom Item Prices")
        st.markdown("Override default prices for specific items you regularly use.")

        # Show existing custom prices
        if profile.custom_prices:
            st.markdown("**Current Custom Prices:**")
            for item, price_val in profile.custom_prices.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(item)
                col2.write(f"R {price_val:,.2f}")
                if col3.button("Remove", key=f"remove_{item}"):
                    del profile.custom_prices[item]
                    st.rerun()

        # Add new custom price
        st.markdown("**Add Custom Price:**")
        col1, col2, col3 = st.columns([3, 1, 1])
        new_item = col1.text_input("Item Description", placeholder="600x1200 Recessed LED", key="new_item")
        new_price = col2.number_input("Price (R)", min_value=0.0, step=10.0, key="new_price")

        if col3.button("Add"):
            if new_item and new_price > 0:
                profile.custom_prices[new_item] = new_price
                st.success(f"Added: {new_item} = R {new_price:,.2f}")
                st.rerun()

    # Save button
    st.markdown("---")

    if st.button("💾 Save Profile", type="primary", use_container_width=True):
        # Update profile with form values
        profile.company_name = company_name
        profile.registration_number = registration_number
        profile.vat_number = vat_number
        profile.contact_name = contact_name
        profile.contact_phone = contact_phone
        profile.contact_email = contact_email
        profile.physical_address = physical_address
        profile.base_location = base_location
        profile.max_travel_km = max_travel_km
        profile.markup_pct = markup_pct
        profile.contingency_pct = contingency_pct
        profile.vat_pct = vat_pct
        profile.payment_terms = payment_terms
        profile.bq_format = bq_format
        profile.preferred_supplier = preferred_supplier
        profile.updated_at = datetime.now().isoformat()

        profile.labour_rates = LabourRates(
            electrician_daily_zar=electrician_daily,
            assistant_daily_zar=assistant_daily,
            foreman_daily_zar=foreman_daily,
            team_size_electricians=team_electricians,
            team_size_assistants=team_assistants,
            travel_rate_per_km_zar=travel_rate,
        )

        st.session_state.contractor_profile = profile
        st.success("Profile saved successfully!")


if __name__ == "__main__":
    main()
