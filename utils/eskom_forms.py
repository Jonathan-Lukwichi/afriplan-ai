"""
AfriPlan Electrical - Eskom Application Forms Helper
Generate pre-populated data for Eskom supply applications
"""

from datetime import datetime


def generate_eskom_application(
    project_type: str,
    load_data: dict,
    location: dict = None,
    applicant_details: dict = None
) -> dict:
    """
    Generate pre-populated Eskom supply application data.

    Args:
        project_type: "new_connection", "upgrade", "temporary"
        load_data: Dictionary with ADMD/load calculation results
        location: Optional location details (address, province)
        applicant_details: Optional applicant info

    Returns:
        dict with form data, required documents, and cost estimate
    """
    # Base application data
    application = {
        "application_type": project_type,
        "date_generated": datetime.now().strftime('%Y-%m-%d'),
        "reference": f"ESK-{datetime.now().strftime('%Y%m%d%H%M')}",
    }

    # Load details
    admd_kva = load_data.get("total_admd_kva", load_data.get("adjusted_admd_kva", 3.5))
    supply_size = load_data.get("recommended_supply", "60A")
    supply_type = load_data.get("supply_type", "Single Phase")

    application["load_details"] = {
        "admd_kva": admd_kva,
        "supply_size": supply_size,
        "supply_type": supply_type,
        "voltage": "230V" if supply_type == "Single Phase" else "400V",
        "phases": 1 if supply_type == "Single Phase" else 3,
        "connection_type": "Overhead" if admd_kva <= 25 else "Underground",
    }

    # Location details
    if location:
        application["site_details"] = {
            "street_address": location.get("street_address", ""),
            "suburb": location.get("suburb", ""),
            "city": location.get("city", ""),
            "province": location.get("province", ""),
            "postal_code": location.get("postal_code", ""),
            "erf_number": location.get("erf_number", ""),
            "gps_coordinates": location.get("gps_coordinates", ""),
        }

    # Applicant details
    if applicant_details:
        application["applicant"] = {
            "name": applicant_details.get("name", ""),
            "id_number": applicant_details.get("id_number", ""),
            "company": applicant_details.get("company", ""),
            "contact_number": applicant_details.get("contact_number", ""),
            "email": applicant_details.get("email", ""),
        }

    # Required documents based on application type
    required_docs = [
        "Copy of ID document",
        "Proof of property ownership or written consent from owner",
        "Site plan showing proposed meter position",
        "Approved building plans (if new construction)",
    ]

    if project_type == "new_connection":
        required_docs.extend([
            "Completed NC4 application form",
            "Electrical installation certificate (COC) - to be submitted before energization",
        ])
    elif project_type == "upgrade":
        required_docs.extend([
            "Existing meter number",
            "Existing account number",
            "Motivation for upgrade",
            "Electrical installation certificate (COC)",
        ])
    elif project_type == "temporary":
        required_docs.extend([
            "Duration of temporary supply required",
            "Purpose of temporary supply",
            "Security deposit (refundable)",
        ])

    application["required_documents"] = required_docs

    # Cost estimation (approximate Eskom fees)
    costs = estimate_connection_costs(admd_kva, supply_type, project_type)
    application["estimated_costs"] = costs

    # Timeline
    application["estimated_timeline"] = {
        "application_processing": "10-14 working days",
        "quotation_validity": "60 days",
        "installation_after_payment": "30-45 working days",
        "total_estimated": "60-90 days from application",
    }

    # Eskom contact information by province
    eskom_contacts = {
        "Gauteng": {
            "region": "Gauteng Operating Unit",
            "phone": "0860 037 566",
            "email": "gauteng@eskom.co.za",
        },
        "KwaZulu-Natal": {
            "region": "KwaZulu-Natal Operating Unit",
            "phone": "0860 037 566",
            "email": "kwazulunatal@eskom.co.za",
        },
        "Western Cape": {
            "region": "Western Cape Operating Unit",
            "phone": "0860 037 566",
            "email": "westerncape@eskom.co.za",
        },
        "Eastern Cape": {
            "region": "Eastern Cape Operating Unit",
            "phone": "0860 037 566",
            "email": "easterncape@eskom.co.za",
        },
        "Mpumalanga": {
            "region": "Mpumalanga Operating Unit",
            "phone": "0860 037 566",
            "email": "mpumalanga@eskom.co.za",
        },
        "Limpopo": {
            "region": "Limpopo Operating Unit",
            "phone": "0860 037 566",
            "email": "limpopo@eskom.co.za",
        },
        "North West": {
            "region": "North West Operating Unit",
            "phone": "0860 037 566",
            "email": "northwest@eskom.co.za",
        },
        "Free State": {
            "region": "Free State Operating Unit",
            "phone": "0860 037 566",
            "email": "freestate@eskom.co.za",
        },
        "Northern Cape": {
            "region": "Northern Cape Operating Unit",
            "phone": "0860 037 566",
            "email": "northerncape@eskom.co.za",
        },
    }

    province = location.get("province", "Gauteng") if location else "Gauteng"
    application["eskom_contact"] = eskom_contacts.get(province, eskom_contacts["Gauteng"])

    return application


def estimate_connection_costs(admd_kva: float, supply_type: str, project_type: str) -> dict:
    """
    Estimate Eskom connection costs based on load and supply type.

    Note: These are approximate 2024/2025 costs and may vary by region.
    """
    costs = {
        "application_fee": 350,  # Standard application fee
        "administration_fee": 550,
    }

    # Connection fee based on supply size
    if supply_type == "Single Phase":
        if admd_kva <= 3.5:
            costs["connection_fee"] = 3500
            costs["meter_deposit"] = 500
        elif admd_kva <= 5.5:
            costs["connection_fee"] = 5500
            costs["meter_deposit"] = 750
        elif admd_kva <= 8:
            costs["connection_fee"] = 7500
            costs["meter_deposit"] = 1000
        else:
            costs["connection_fee"] = 12000
            costs["meter_deposit"] = 1500
    else:  # Three Phase
        if admd_kva <= 25:
            costs["connection_fee"] = 18000
            costs["meter_deposit"] = 2500
        elif admd_kva <= 50:
            costs["connection_fee"] = 35000
            costs["meter_deposit"] = 5000
        else:
            costs["connection_fee"] = 65000
            costs["meter_deposit"] = 10000

    # Extension costs (if supply point is more than 10m from property boundary)
    costs["extension_cost_per_meter"] = 450

    # Project type adjustments
    if project_type == "upgrade":
        costs["connection_fee"] = costs["connection_fee"] * 0.75  # Reduced for upgrades
        costs["upgrade_assessment_fee"] = 850
    elif project_type == "temporary":
        costs["temporary_installation_fee"] = 2500
        costs["security_deposit"] = costs["connection_fee"] * 1.5

    # Calculate total
    base_total = sum(v for k, v in costs.items() if isinstance(v, (int, float)) and k != "extension_cost_per_meter")
    costs["estimated_total"] = round(base_total, 2)

    # Add note about variables
    costs["notes"] = [
        "Costs are estimates and subject to Eskom quotation",
        "Extension costs apply if supply point > 10m from boundary",
        "VAT (15%) not included in above estimates",
        "Actual costs depend on site assessment",
    ]

    return costs


def generate_application_summary_text(application: dict) -> str:
    """
    Generate a text summary of the Eskom application for display/export.

    Args:
        application: Dictionary from generate_eskom_application()

    Returns:
        str: Formatted text summary
    """
    lines = []
    lines.append("=" * 60)
    lines.append("ESKOM SUPPLY APPLICATION SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Reference: {application.get('reference', 'N/A')}")
    lines.append(f"Date: {application.get('date_generated', 'N/A')}")
    lines.append(f"Application Type: {application.get('application_type', 'N/A').replace('_', ' ').title()}")
    lines.append("")

    # Load details
    if "load_details" in application:
        lines.append("-" * 40)
        lines.append("LOAD DETAILS")
        lines.append("-" * 40)
        ld = application["load_details"]
        lines.append(f"ADMD: {ld.get('admd_kva', 'N/A')} kVA")
        lines.append(f"Supply Size: {ld.get('supply_size', 'N/A')}")
        lines.append(f"Supply Type: {ld.get('supply_type', 'N/A')}")
        lines.append(f"Voltage: {ld.get('voltage', 'N/A')}")
        lines.append(f"Connection Type: {ld.get('connection_type', 'N/A')}")
        lines.append("")

    # Costs
    if "estimated_costs" in application:
        lines.append("-" * 40)
        lines.append("ESTIMATED COSTS")
        lines.append("-" * 40)
        costs = application["estimated_costs"]
        for key, value in costs.items():
            if isinstance(value, (int, float)) and key != "extension_cost_per_meter":
                lines.append(f"{key.replace('_', ' ').title()}: R {value:,.0f}")
        lines.append("")
        lines.append(f"ESTIMATED TOTAL: R {costs.get('estimated_total', 0):,.0f}")
        lines.append("(Excluding VAT and extension costs)")
        lines.append("")

    # Required documents
    if "required_documents" in application:
        lines.append("-" * 40)
        lines.append("REQUIRED DOCUMENTS")
        lines.append("-" * 40)
        for doc in application["required_documents"]:
            lines.append(f"[ ] {doc}")
        lines.append("")

    # Timeline
    if "estimated_timeline" in application:
        lines.append("-" * 40)
        lines.append("ESTIMATED TIMELINE")
        lines.append("-" * 40)
        tl = application["estimated_timeline"]
        for key, value in tl.items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
        lines.append("")

    # Contact
    if "eskom_contact" in application:
        lines.append("-" * 40)
        lines.append("ESKOM CONTACT")
        lines.append("-" * 40)
        contact = application["eskom_contact"]
        lines.append(f"Region: {contact.get('region', 'N/A')}")
        lines.append(f"Phone: {contact.get('phone', 'N/A')}")
        lines.append(f"Email: {contact.get('email', 'N/A')}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Generated by AfriPlan Electrical")
    lines.append("=" * 60)

    return "\n".join(lines)
