"""
AfriPlan Electrical - SLD (Single Line Diagram) Extractor

Extract circuit schedule information from SLD pages.
Parses:
- Distribution board info (name, main breaker, supply)
- Circuit schedule rows (circuit ID, wattage, wire size, breaker)
- Cable references
- Equipment references

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from agent.models import (
    SLDCircuitRow, SLDExtraction, ExtractionWarning, Severity
)
from agent.extractors.common import (
    normalize_text, clean_text_for_display,
    extract_db_refs, extract_cable_sizes, extract_circuit_ids,
    classify_circuit_type, parse_wattage, parse_current,
    CableSpec
)
from agent.parsers.table_parser import extract_circuit_schedule

logger = logging.getLogger(__name__)


class SLDExtractor:
    """
    Deterministic extractor for SLD pages.

    Usage:
        extractor = SLDExtractor()
        result = extractor.extract(page_text, page_number=1)
    """

    def __init__(self):
        """Initialize the SLD extractor."""
        # Circuit ID patterns with capture groups
        self.circuit_patterns = [
            (r'(L\d+)', "lighting"),
            (r'(P\d+)', "power"),
            (r'(AC\d+)', "aircon"),
            (r'(ISO\d+)', "isolator"),
            (r'(PP\d+)', "pool_pump"),
            (r'(HP\d+)', "heat_pump"),
            (r'(CP\d+)', "circulation_pump"),
            (r'(GY\d+)', "geyser"),
            (r'(ST\d+)', "stove"),
            (r'(D/?N\d*)', "day_night"),
            (r'(SP(?:ARE)?\s*\d*)', "spare"),
        ]

        # Wattage patterns
        self.wattage_patterns = [
            r'(\d+(?:\.\d+)?)\s*kW',
            r'(\d+)\s*W(?:att)?',
        ]

        # Wire size patterns
        self.wire_patterns = [
            r'(\d+(?:\.\d+)?)\s*mm[²2]',
            r'(\d+(?:\.\d+)?)\s*sq\.?\s*mm',
        ]

        # Breaker patterns
        self.breaker_patterns = [
            r'(\d+)\s*[aA](?:mp)?',
        ]

    def extract(
        self,
        text: str,
        text_blocks: Optional[List[Any]] = None,
        page_number: int = 0,
        schedule_region_text: str = "",
        title_block_text: str = "",
    ) -> SLDExtraction:
        """
        Extract SLD information from page text.

        Args:
            text: Raw page text
            text_blocks: Positioned text blocks (optional)
            page_number: Source page number
            schedule_region_text: Text from detected schedule region
            title_block_text: Text from title block region

        Returns:
            SLDExtraction with parsed data
        """
        result = SLDExtraction(source_page=page_number)

        # Extract drawing info from title block
        if title_block_text:
            result.drawing_number = self._extract_drawing_number(title_block_text)
            result.drawing_title = self._extract_drawing_title(title_block_text)

        # Fallback to main text
        if not result.drawing_number:
            result.drawing_number = self._extract_drawing_number(text)

        # Extract DB info
        db_info = self._extract_db_info(text)
        result.db_name = db_info.get("name", "")
        result.db_location = db_info.get("location", "")
        result.main_breaker_a = db_info.get("main_breaker_a", 0)
        result.supply_from = db_info.get("supply_from", "")
        result.supply_cable_mm2 = db_info.get("supply_cable_mm2", 0.0)

        # Extract circuits from schedule region if available
        schedule_text = schedule_region_text or text
        result.circuits = self._extract_circuits(schedule_text)
        result.total_circuits = len(result.circuits)
        result.spare_circuits = len([c for c in result.circuits if c.is_spare])
        result.total_wattage_w = sum(c.wattage_w for c in result.circuits)

        # Extract references
        result.db_refs = extract_db_refs(text)
        result.cable_refs = [cs.raw_text for cs in extract_cable_sizes(text)]
        result.feeder_refs = self._extract_feeder_refs(text)

        return result

    def _extract_drawing_number(self, text: str) -> str:
        """Extract drawing number from text."""
        patterns = [
            r'([A-Z]{2,4}-[A-Z]{1,4}-\d{1,3}-SLD)',
            r'([A-Z]{2,4}-\d{1,3}-SLD)',
            r'DWG\s*(?:NO)?[\s:\.]+([A-Z0-9\-]+)',
            r'DRAWING\s*(?:NO)?[\s:\.]+([A-Z0-9\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return ""

    def _extract_drawing_title(self, text: str) -> str:
        """Extract drawing title from text."""
        patterns = [
            r'TITLE[\s:]+(.+?)(?:\n|$)',
            r'(?:SINGLE\s+LINE|SCHEMATIC)\s+DIAGRAM\s+[-–]\s+(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_text_for_display(match.group(1))

        return ""

    def _extract_db_info(self, text: str) -> Dict[str, Any]:
        """Extract distribution board information."""
        info = {}

        # DB name patterns
        db_name_patterns = [
            r'(DB[-\s]?[A-Z0-9]+)',
            r'DISTRIBUTION\s+BOARD[\s:]+([A-Z0-9\-]+)',
            r'(MSB|MDB)',
        ]

        for pattern in db_name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["name"] = match.group(1).upper().replace(' ', '-')
                break

        # Main breaker
        breaker_patterns = [
            r'MAIN\s+(?:BREAKER|SWITCH)[\s:]*(\d+)\s*A',
            r'(\d+)\s*A\s+MAIN',
            r'MAIN[\s:]*(\d+)\s*A',
        ]

        for pattern in breaker_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    info["main_breaker_a"] = int(match.group(1))
                except ValueError:
                    pass
                break

        # Supply from
        supply_patterns = [
            r'(?:FED|SUPPLY)\s+FROM[\s:]+([A-Z0-9\-]+)',
            r'FROM[\s:]+([A-Z0-9\-]+)',
            r'SUPPLY[\s:]+([A-Z0-9\-]+)',
        ]

        for pattern in supply_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["supply_from"] = match.group(1).upper()
                break

        # Supply cable size
        supply_cable_patterns = [
            r'(?:SUPPLY|INCOMING|FEEDER)\s+(?:CABLE)?[\s:]*(\d+(?:\.\d+)?)\s*mm[²2]',
            r'(\d+(?:\.\d+)?)\s*mm[²2]\s+(?:SUPPLY|INCOMING|FEEDER)',
        ]

        for pattern in supply_cable_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    info["supply_cable_mm2"] = float(match.group(1))
                except ValueError:
                    pass
                break

        # Location hint from DB name
        if info.get("name"):
            info["location"] = self._guess_location(info["name"])

        return info

    def _guess_location(self, db_name: str) -> str:
        """Guess location from DB name."""
        db_upper = db_name.upper()

        location_hints = {
            "GF": "Ground Floor",
            "FF": "First Floor",
            "1F": "First Floor",
            "2F": "Second Floor",
            "CA": "Common Area",
            "S1": "Suite 1",
            "S2": "Suite 2",
            "S3": "Suite 3",
            "S4": "Suite 4",
            "PFA": "Pool Facility",
            "PPS": "Pool Pumps",
            "HPS": "Heat Pumps",
            "AB": "Ablution Block",
            "ECH": "Community Hall",
            "LGH": "Large Guard House",
            "SGH": "Small Guard House",
        }

        for code, location in location_hints.items():
            if code in db_upper:
                return location

        return ""

    def _extract_circuits(self, text: str) -> List[SLDCircuitRow]:
        """Extract circuit rows from schedule text."""
        circuits = []

        # First try structured extraction from table parser
        parsed = extract_circuit_schedule(text)

        for pc in parsed:
            circuit = SLDCircuitRow(
                circuit_id=pc.get('circuit_id', ''),
                circuit_type=classify_circuit_type(pc.get('circuit_id', '')),
                raw_text=pc.get('raw_text', ''),
                confidence=0.7,
            )

            # Parse optional fields
            if pc.get('wattage'):
                try:
                    circuit.wattage_w = float(pc['wattage'])
                except ValueError:
                    pass

            if pc.get('wire_size'):
                try:
                    circuit.wire_size_mm2 = float(pc['wire_size'])
                except ValueError:
                    pass

            if pc.get('breaker'):
                try:
                    circuit.breaker_a = int(pc['breaker'])
                except ValueError:
                    pass

            if pc.get('points'):
                try:
                    circuit.num_points = int(pc['points'])
                except ValueError:
                    pass

            circuits.append(circuit)

        # If no circuits found, try line-by-line
        if not circuits:
            circuits = self._extract_circuits_from_lines(text)

        return circuits

    def _extract_circuits_from_lines(self, text: str) -> List[SLDCircuitRow]:
        """Fallback: extract circuits line by line."""
        circuits = []
        lines = text.split('\n')

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Try each circuit pattern
            for pattern, circuit_type in self.circuit_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    circuit = SLDCircuitRow(
                        circuit_id=match.group(1).upper(),
                        circuit_type=circuit_type,
                        raw_text=line_stripped,
                        confidence=0.5,
                    )

                    # Check if spare
                    if 'SPARE' in line_stripped.upper():
                        circuit.is_spare = True
                        circuit.circuit_type = "spare"

                    # Extract wattage
                    for wp in self.wattage_patterns:
                        wm = re.search(wp, line_stripped, re.IGNORECASE)
                        if wm:
                            try:
                                val = float(wm.group(1))
                                if 'kW' in wm.group(0):
                                    val *= 1000
                                circuit.wattage_w = val
                            except ValueError:
                                pass
                            break

                    # Extract wire size
                    for wsp in self.wire_patterns:
                        wsm = re.search(wsp, line_stripped, re.IGNORECASE)
                        if wsm:
                            try:
                                circuit.wire_size_mm2 = float(wsm.group(1))
                            except ValueError:
                                pass
                            break

                    # Extract breaker
                    for bp in self.breaker_patterns:
                        bm = re.search(bp, line_stripped)
                        if bm:
                            try:
                                circuit.breaker_a = int(bm.group(1))
                            except ValueError:
                                pass
                            break

                    # Extract point count
                    points_match = re.search(r'(\d+)\s*(?:pts?|points?|no)', line_stripped, re.IGNORECASE)
                    if points_match:
                        try:
                            circuit.num_points = int(points_match.group(1))
                        except ValueError:
                            pass

                    # Check for 3-phase
                    if '3PH' in line_stripped.upper() or '3-PH' in line_stripped.upper():
                        circuit.is_3phase = True

                    circuits.append(circuit)
                    break  # One match per line

        return circuits

    def _extract_feeder_refs(self, text: str) -> List[str]:
        """Extract feeder cable references."""
        refs = []

        patterns = [
            r'FEEDER\s+(?:TO|FROM)[\s:]+([A-Z0-9\-]+)',
            r'TO\s+(DB[-\s]?[A-Z0-9]+)',
            r'FROM\s+(DB[-\s]?[A-Z0-9]+)',
            r'VIA\s+(\d+(?:\.\d+)?mm[²2]\s+\d+[cC])',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                refs.append(match.group(1).upper())

        return list(set(refs))

    def validate(self, result: SLDExtraction) -> List[ExtractionWarning]:
        """Validate extraction result and return warnings."""
        warnings = []

        if not result.db_name:
            warnings.append(ExtractionWarning(
                code="NO_DB_NAME",
                message="Distribution board name not found",
                severity=Severity.WARNING,
                source_stage="extract_sld",
            ))

        if not result.circuits:
            warnings.append(ExtractionWarning(
                code="NO_CIRCUITS",
                message="No circuits found in SLD",
                severity=Severity.WARNING,
                source_stage="extract_sld",
            ))

        # Check for circuits without wattage
        no_wattage = [c for c in result.circuits if c.wattage_w == 0 and not c.is_spare]
        if no_wattage:
            warnings.append(ExtractionWarning(
                code="CIRCUITS_NO_WATTAGE",
                message=f"{len(no_wattage)} circuits without wattage",
                severity=Severity.INFO,
                source_stage="extract_sld",
                details={"circuit_ids": [c.circuit_id for c in no_wattage]},
            ))

        return warnings

    def summarize(self, result: SLDExtraction) -> Dict[str, Any]:
        """Create a summary of the extraction."""
        return {
            "db_name": result.db_name,
            "main_breaker_a": result.main_breaker_a,
            "total_circuits": result.total_circuits,
            "spare_circuits": result.spare_circuits,
            "lighting_circuits": result.lighting_circuits,
            "power_circuits": result.power_circuits,
            "total_wattage_kw": round(result.total_wattage_w / 1000, 2),
            "db_refs_found": len(result.db_refs),
            "cable_refs_found": len(result.cable_refs),
        }
