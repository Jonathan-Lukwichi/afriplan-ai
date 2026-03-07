"""
AfriPlan Electrical v1.0 - Deterministic SLD Extraction

Extract circuit schedules from SLD pages using SLDExtractor (NO LLM).
This is the PRIMARY source of truth for circuit counts.

The "No Of Point" row in circuit schedules gives OFFICIAL fixture counts.
Layout drawings are used for verification only, not extraction.

Usage:
    from agent.stages.extract_sld import extract_sld_data, extract_all_dbs

    # Extract from all SLD pages
    sld_data = extract_all_dbs(sld_pages)
    # Returns: {"dbs": [...], "supply_point": {...}, "cable_routes": [...]}
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from agent.models import PageInfo, StageResult, PipelineStage, ItemConfidence
from agent.extractors.sld_extractor import SLDExtractor
from agent.parsers.table_parser import extract_circuit_schedule
from agent.utils import Timer


@dataclass
class CircuitData:
    """Extracted circuit data from SLD."""
    circuit_id: str
    circuit_type: str  # lighting, power, spare, dedicated
    breaker_a: int = 0
    cable_mm2: float = 0.0
    num_points: int = 0
    wattage_w: int = 0
    description: str = ""
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class DBData:
    """Extracted distribution board data."""
    name: str
    location: str = ""
    main_breaker_a: int = 0
    supply_from: str = ""
    supply_cable_mm2: float = 0.0
    circuits: List[CircuitData] = field(default_factory=list)
    total_circuits: int = 0
    spare_circuits: int = 0
    is_main: bool = False
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class SupplyPointData:
    """Main supply/incomer data."""
    name: str = "Kiosk"
    voltage: str = "400V"
    phases: int = 3
    main_breaker_a: int = 100
    cable_size_mm2: float = 35.0
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class CableRouteData:
    """Cable route between DBs."""
    from_db: str
    to_db: str
    cable_spec: str = ""
    cable_size_mm2: float = 0.0
    length_m: Optional[float] = None
    is_underground: bool = False
    confidence: ItemConfidence = ItemConfidence.EXTRACTED


@dataclass
class SLDExtractionResult:
    """Complete SLD extraction result."""
    dbs: List[DBData] = field(default_factory=list)
    supply_point: Optional[SupplyPointData] = None
    cable_routes: List[CableRouteData] = field(default_factory=list)
    total_dbs: int = 0
    total_circuits: int = 0
    warnings: List[str] = field(default_factory=list)


def extract_sld_data(page: PageInfo) -> Dict[str, Any]:
    """
    Extract SLD data from a single page using deterministic parsing.

    NO LLM CALLS - uses SLDExtractor.

    Args:
        page: PageInfo with text_content

    Returns:
        Dict with extracted SLD data
    """
    extractor = SLDExtractor()
    text = page.text_content or ""

    result = extractor.extract(
        text=text,
        page_number=page.page_number,
    )

    return {
        "db_name": result.db_name,
        "db_location": result.db_location,
        "main_breaker_a": result.main_breaker_a,
        "supply_from": result.supply_from,
        "supply_cable_mm2": result.supply_cable_mm2,
        "circuits": [
            {
                "id": c.circuit_id,
                "type": c.circuit_type,
                "breaker_a": c.breaker_a,
                "cable_mm2": c.cable_mm2,
                "num_points": c.num_points,
                "wattage_w": c.wattage_w,
            }
            for c in result.circuits
        ],
        "total_circuits": result.total_circuits,
        "spare_circuits": result.spare_circuits,
        "drawing_number": result.drawing_number,
        "db_refs": result.db_refs,
        "cable_refs": result.cable_refs,
    }


def extract_all_dbs(sld_pages: List[PageInfo]) -> SLDExtractionResult:
    """
    Extract all distribution boards from SLD pages.

    NO LLM CALLS - pure deterministic extraction.

    Args:
        sld_pages: List of SLD PageInfo objects

    Returns:
        SLDExtractionResult with all DBs, supply point, cable routes
    """
    result = SLDExtractionResult()
    extractor = SLDExtractor()
    seen_dbs = set()

    for page in sld_pages:
        text = page.text_content or ""

        # Extract SLD data
        sld_result = extractor.extract(
            text=text,
            page_number=page.page_number,
        )

        # Skip if no DB found or already seen
        if not sld_result.db_name or sld_result.db_name in seen_dbs:
            # Still check for additional DB references
            for db_ref in sld_result.db_refs:
                if db_ref not in seen_dbs:
                    # Create placeholder DB from reference
                    result.dbs.append(DBData(
                        name=db_ref,
                        confidence=ItemConfidence.INFERRED,
                    ))
                    seen_dbs.add(db_ref)
            continue

        seen_dbs.add(sld_result.db_name)

        # Build DB data
        db = DBData(
            name=sld_result.db_name,
            location=sld_result.db_location,
            main_breaker_a=sld_result.main_breaker_a,
            supply_from=sld_result.supply_from,
            supply_cable_mm2=sld_result.supply_cable_mm2,
            total_circuits=sld_result.total_circuits,
            spare_circuits=sld_result.spare_circuits,
            is_main=_is_main_db(sld_result.db_name, sld_result.supply_from),
            confidence=ItemConfidence.EXTRACTED,
        )

        # Add circuits
        for circuit in sld_result.circuits:
            db.circuits.append(CircuitData(
                circuit_id=circuit.circuit_id,
                circuit_type=circuit.circuit_type,
                breaker_a=circuit.breaker_a,
                cable_mm2=circuit.cable_mm2,
                num_points=circuit.num_points,
                wattage_w=circuit.wattage_w,
                confidence=ItemConfidence.EXTRACTED,
            ))

        result.dbs.append(db)

        # Check for cable routes
        for cable_ref in sld_result.cable_refs:
            route = _parse_cable_route(cable_ref, sld_result.db_name)
            if route:
                result.cable_routes.append(route)

    # Update totals
    result.total_dbs = len(result.dbs)
    result.total_circuits = sum(db.total_circuits for db in result.dbs)

    # Try to identify supply point from main DB
    main_dbs = [db for db in result.dbs if db.is_main]
    if main_dbs:
        main = main_dbs[0]
        result.supply_point = SupplyPointData(
            name=main.supply_from or "Kiosk",
            main_breaker_a=main.main_breaker_a,
            cable_size_mm2=main.supply_cable_mm2,
            confidence=ItemConfidence.EXTRACTED if main.supply_from else ItemConfidence.INFERRED,
        )

    return result


def extract_db_names(sld_pages: List[PageInfo]) -> List[str]:
    """
    Quick extraction of just DB names from SLD pages.

    NO LLM CALLS.

    Args:
        sld_pages: List of SLD pages

    Returns:
        List of DB names found
    """
    db_names = set()

    # DB name patterns
    patterns = [
        r'DB[-_]?([A-Z0-9]+)',  # DB-GF, DB_S1, DBS1
        r'(MSB|MAIN\s*SWITCH\s*BOARD)',
        r'(KIOSK|METERING)',
    ]

    for page in sld_pages:
        text = (page.text_content or "").upper()

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                db_name = match.group(0).strip()
                # Normalize
                db_name = re.sub(r'\s+', '-', db_name)
                db_names.add(db_name)

    return sorted(list(db_names))


def extract_circuit_counts(sld_pages: List[PageInfo]) -> Dict[str, Dict[str, int]]:
    """
    Extract circuit point counts from "No Of Point" rows.

    This is the PRIMARY source of truth for fixture counts.
    Layout drawings should reconcile against these numbers.

    NO LLM CALLS.

    Args:
        sld_pages: List of SLD pages

    Returns:
        Dict: {db_name: {circuit_id: num_points}}
    """
    result = {}
    extractor = SLDExtractor()

    for page in sld_pages:
        text = page.text_content or ""
        sld_result = extractor.extract(text, page_number=page.page_number)

        if sld_result.db_name and sld_result.circuits:
            db_counts = {}
            for circuit in sld_result.circuits:
                if circuit.num_points > 0:
                    db_counts[circuit.circuit_id] = circuit.num_points

            if db_counts:
                result[sld_result.db_name] = db_counts

    return result


def _is_main_db(db_name: str, supply_from: str) -> bool:
    """Check if DB is a main distribution board."""
    db_upper = db_name.upper()
    supply_upper = (supply_from or "").upper()

    # Main if name suggests it
    if any(x in db_upper for x in ["MSB", "MAIN", "GF", "GROUND"]):
        return True

    # Main if fed from external source
    if any(x in supply_upper for x in ["ESKOM", "KIOSK", "TRANSFORMER", "MINI SUB"]):
        return True

    return False


def _parse_cable_route(cable_ref: str, current_db: str) -> Optional[CableRouteData]:
    """Parse a cable reference into a route."""
    # Pattern: "4Cx16mm² PVC SWA" or "35mm² x 4C"
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*mm[²2]', cable_ref, re.IGNORECASE)

    if size_match:
        return CableRouteData(
            from_db="",  # Unknown without more context
            to_db=current_db,
            cable_spec=cable_ref,
            cable_size_mm2=float(size_match.group(1)),
            is_underground="SWA" in cable_ref.upper(),
            confidence=ItemConfidence.EXTRACTED,
        )

    return None


def extract_sld_with_stage_result(
    sld_pages: List[PageInfo],
) -> Tuple[SLDExtractionResult, StageResult]:
    """
    Extract SLD data with StageResult for pipeline integration.

    Args:
        sld_pages: List of SLD pages

    Returns:
        Tuple of (SLDExtractionResult, StageResult)
    """
    with Timer("extract_sld") as timer:
        result = extract_all_dbs(sld_pages)

        stage_result = StageResult(
            stage=PipelineStage.DISCOVER,
            success=result.total_dbs > 0,
            confidence=0.9 if result.total_dbs > 0 else 0.0,
            data={
                "total_dbs": result.total_dbs,
                "total_circuits": result.total_circuits,
                "db_names": [db.name for db in result.dbs],
            },
            model_used=None,  # No LLM!
            tokens_used=0,
            cost_zar=0.0,
            processing_time_ms=timer.elapsed_ms,
            errors=[],
            warnings=result.warnings,
        )

        return result, stage_result
