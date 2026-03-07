"""
pipeline_adapter.py - Connects the AfriPlan extraction pipeline to the scoring system

Converts the pipeline's ExtractionResult format to the ground truth format
that our scorer expects.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("evaluation", 1)[0])


def extraction_to_scorer_format(extraction_result) -> Dict:
    """
    Convert AfriPlan ExtractionResult to the format expected by the scorer.

    Args:
        extraction_result: ExtractionResult from the pipeline

    Returns:
        Dictionary matching ground_truth.json format
    """
    result = {
        "document_id": "extraction_result",
        "document_type": "sld",
        "distribution_boards": [],
        "cables": {"main_feeds": [], "sub_feeds": []},
        "totals": {
            "total_dbs": 0,
            "total_circuits": 0,
            "total_lighting_circuits": 0,
            "total_power_circuits": 0,
            "total_dedicated_circuits": 0,
            "total_spare_circuits": 0,
        }
    }

    # Handle different extraction result structures
    dbs = []

    # Try to get DBs from extraction_result directly
    if hasattr(extraction_result, 'distribution_boards'):
        dbs = extraction_result.distribution_boards

    # Also check building_blocks
    if hasattr(extraction_result, 'building_blocks'):
        for block in extraction_result.building_blocks:
            if hasattr(block, 'distribution_boards'):
                dbs.extend(block.distribution_boards)

    # Convert each DB
    for db in dbs:
        db_dict = convert_db(db)
        result["distribution_boards"].append(db_dict)

        # Update totals
        result["totals"]["total_circuits"] += len(db_dict.get("circuits", []))

        for circuit in db_dict.get("circuits", []):
            ctype = circuit.get("type", "").lower()
            if ctype == "lighting":
                result["totals"]["total_lighting_circuits"] += 1
            elif ctype == "power":
                result["totals"]["total_power_circuits"] += 1
            elif ctype in ("dedicated", "isolator", "geyser", "aircon", "motor"):
                result["totals"]["total_dedicated_circuits"] += 1
            elif ctype == "spare" or circuit.get("is_spare"):
                result["totals"]["total_spare_circuits"] += 1

    result["totals"]["total_dbs"] = len(result["distribution_boards"])

    # Convert cable runs if available
    if hasattr(extraction_result, 'site_cable_runs'):
        for cable in extraction_result.site_cable_runs:
            cable_dict = convert_cable(cable)
            # Determine if main or sub feed based on source
            if "sub" in cable_dict.get("from", "").lower() or "mains" in cable_dict.get("from", "").lower():
                result["cables"]["main_feeds"].append(cable_dict)
            else:
                result["cables"]["sub_feeds"].append(cable_dict)

    return result


def convert_db(db) -> Dict:
    """Convert a DistributionBoard object to dictionary format."""
    db_dict = {
        "name": getattr(db, 'name', ''),
        "location": getattr(db, 'location', ''),
        "voltage": f"{getattr(db, 'voltage_v', 400)}V",
        "phase": getattr(db, 'phase', '3PH').value if hasattr(getattr(db, 'phase', ''), 'value') else str(getattr(db, 'phase', '3PH')),
        "main_breaker_a": getattr(db, 'main_breaker_a', 0),
        "total_ways": getattr(db, 'total_ways', 0) if hasattr(db, 'total_ways') else len(getattr(db, 'circuits', [])) + getattr(db, 'spare_ways', 0),
        "spare_ways": getattr(db, 'spare_ways', 0),
        "has_elcb": getattr(db, 'earth_leakage', False),
        "elcb_rating_a": getattr(db, 'earth_leakage_rating_a', 0),
        "has_surge_protection": getattr(db, 'surge_protection', False),
        "circuits": []
    }

    # Convert circuits
    for circuit in getattr(db, 'circuits', []):
        circuit_dict = convert_circuit(circuit)
        db_dict["circuits"].append(circuit_dict)

    return db_dict


def convert_circuit(circuit) -> Dict:
    """Convert a Circuit object to dictionary format."""
    # Determine circuit type
    circuit_id = getattr(circuit, 'id', '')
    circuit_type = getattr(circuit, 'type', 'power')
    is_spare = getattr(circuit, 'is_spare', False)

    # Normalize type
    if is_spare or circuit_id.upper().startswith("SPARE"):
        normalized_type = "spare"
    elif circuit_type.lower() in ("lighting", "lights"):
        normalized_type = "lighting"
    elif circuit_type.lower() in ("power", "plug", "socket", "sockets"):
        normalized_type = "power"
    elif circuit_id.upper().startswith("L") and circuit_id[1:].replace("-", "").isdigit():
        normalized_type = "lighting"
    elif circuit_id.upper().startswith("P") and circuit_id[1:].replace("-", "").isdigit():
        normalized_type = "power"
    elif circuit_type.lower() in ("dedicated", "isolator", "geyser", "aircon", "motor", "ac"):
        normalized_type = "dedicated"
    elif "DB" in circuit_id.upper() or getattr(circuit, 'feeds_board', None):
        normalized_type = "sub_feed"
    else:
        normalized_type = circuit_type.lower()

    return {
        "name": circuit_id,
        "type": normalized_type,
        "mcb_rating_a": getattr(circuit, 'breaker_a', 0),
        "cable_size_mm2": getattr(circuit, 'cable_size_mm2', 0),
        "cable_type": getattr(circuit, 'cable_type', ''),
        "num_points": getattr(circuit, 'num_points', 0),
        "wattage_w": getattr(circuit, 'wattage_w', 0),
        "description": getattr(circuit, 'description', ''),
        "phase": getattr(circuit, 'phase', ''),
        "is_spare": is_spare,
    }


def convert_cable(cable) -> Dict:
    """Convert a SiteCableRun object to dictionary format."""
    return {
        "from": getattr(cable, 'from_location', getattr(cable, 'from_db', '')),
        "to": getattr(cable, 'to_location', getattr(cable, 'to_db', '')),
        "cable_size_mm2": getattr(cable, 'cable_size_mm2', 0),
        "cable_type": getattr(cable, 'cable_type', ''),
        "length_m": getattr(cable, 'length_m', 0),
        "installation": getattr(cable, 'installation_method', ''),
    }


def run_extraction(pdf_bytes: bytes, filename: str) -> Dict:
    """
    Run the AfriPlan extraction pipeline and return results in scorer format.

    Args:
        pdf_bytes: PDF file contents
        filename: Original filename

    Returns:
        Dictionary matching ground_truth.json format
    """
    try:
        from agent.pipeline import AfriPlanPipeline

        # Create pipeline
        pipeline = AfriPlanPipeline()

        if pipeline.client is None:
            print("    [!] No API key configured. Set ANTHROPIC_API_KEY, GROQ_API_KEY, or XAI_API_KEY")
            return {}

        print(f"    Provider: {pipeline.provider}")

        # Determine mime type
        mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/png"

        # Run extraction (stages 1-3)
        extraction, confidence = pipeline.process_documents(
            files=[(pdf_bytes, filename, mime_type)]
        )

        print(f"    Confidence: {confidence:.1%}")

        # Convert to scorer format
        result = extraction_to_scorer_format(extraction)
        result["document_id"] = filename

        return result

    except ImportError as e:
        print(f"    [!] Import error: {e}")
        return {}
    except Exception as e:
        print(f"    [!] Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def check_api_keys() -> Tuple[bool, str]:
    """Check if any API key is configured."""
    providers = [
        ("GROQ_API_KEY", "Groq (FREE)"),
        ("XAI_API_KEY", "xAI Grok"),
        ("GEMINI_API_KEY", "Google Gemini"),
        ("ANTHROPIC_API_KEY", "Anthropic Claude"),
    ]

    for env_var, provider_name in providers:
        if os.environ.get(env_var):
            return True, provider_name

    return False, "None"


if __name__ == "__main__":
    # Test the adapter
    has_key, provider = check_api_keys()
    print(f"API Key configured: {has_key} ({provider})")

    if has_key:
        # Test with a sample document
        test_pdf = "evaluation/test_documents/doc_001_wedela/original.pdf"
        if os.path.exists(test_pdf):
            with open(test_pdf, "rb") as f:
                pdf_bytes = f.read()

            print(f"\nTesting extraction on: {test_pdf}")
            result = run_extraction(pdf_bytes, "doc_001_wedela")

            print(f"\nResults:")
            print(f"  DBs found: {result.get('totals', {}).get('total_dbs', 0)}")
            print(f"  Circuits found: {result.get('totals', {}).get('total_circuits', 0)}")

            for db in result.get("distribution_boards", [])[:3]:
                print(f"  - {db.get('name')}: {len(db.get('circuits', []))} circuits")
