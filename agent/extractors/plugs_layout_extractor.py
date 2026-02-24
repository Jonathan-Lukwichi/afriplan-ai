"""
AfriPlan Electrical - Plugs/Power Layout Extractor

Extract information from plugs/power layout pages.
Focuses on text-based extraction (deterministic):
- Room labels
- Circuit references
- Socket/plug types from legend
- Data points
- Isolators
- Notes and specifications

Does NOT attempt symbol counting (requires AI vision).

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any

from agent.models import LayoutExtraction, ExtractionWarning, Severity
from agent.extractors.common import (
    normalize_text, clean_text_for_display,
    extract_room_labels, extract_circuit_ids, extract_db_refs,
    extract_cable_sizes, parse_height, dedupe_strings
)

logger = logging.getLogger(__name__)


class PlugsLayoutExtractor:
    """
    Deterministic extractor for plugs/power layout pages.

    Extracts text-based information only.
    Symbol counting requires AI vision and is not implemented here.

    Usage:
        extractor = PlugsLayoutExtractor()
        result = extractor.extract(page_text, page_number=1)
    """

    def __init__(self):
        """Initialize the plugs layout extractor."""
        # Socket patterns for legend detection
        self.socket_patterns = [
            (r'DOUBLE\s*(?:SWITCHED\s*)?SOCKET\s*@?\s*300', "double_socket_300mm"),
            (r'DOUBLE\s*(?:SWITCHED\s*)?SOCKET\s*@?\s*1100', "double_socket_1100mm"),
            (r'SINGLE\s*(?:SWITCHED\s*)?SOCKET', "single_socket"),
            (r'WATERPROOF\s*(?:DOUBLE\s*)?SOCKET', "waterproof_socket"),
            (r'FLOOR\s*BOX', "floor_box"),
            (r'16\s*A\s*(?:DOUBLE|SINGLE)', "16A_socket"),
        ]

        # Data point patterns
        self.data_patterns = [
            (r'CAT\s*6\s*(?:DATA)?\s*(?:POINT|OUTLET)?', "cat6"),
            (r'CAT\s*5[eE]?\s*(?:DATA)?', "cat5e"),
            (r'DATA\s*(?:POINT|OUTLET)', "data_point"),
            (r'RJ\s*45', "rj45"),
            (r'NETWORK\s*(?:POINT|OUTLET)', "network"),
        ]

        # Isolator patterns
        self.isolator_patterns = [
            (r'(\d+)\s*A\s*ISOLATOR', "isolator"),
            (r'ISOLATOR\s*(\d+)\s*A', "isolator"),
            (r'A/?C\s*ISOLATOR', "ac_isolator"),
            (r'GEYSER\s*ISOLATOR', "geyser_isolator"),
        ]

    def extract(
        self,
        text: str,
        text_blocks: Optional[List[Any]] = None,
        page_number: int = 0,
        legend_region_text: str = "",
        title_block_text: str = "",
    ) -> LayoutExtraction:
        """
        Extract plugs layout information from page text.

        Args:
            text: Raw page text
            text_blocks: Positioned text blocks (optional)
            page_number: Source page number
            legend_region_text: Text from detected legend region
            title_block_text: Text from title block region

        Returns:
            LayoutExtraction with parsed data
        """
        result = LayoutExtraction(
            source_page=page_number,
            layout_type="plugs",
        )

        # Extract drawing info from title block
        if title_block_text:
            result.drawing_number = self._extract_drawing_number(title_block_text)
            result.drawing_title = self._extract_drawing_title(title_block_text)

        # Fallback to main text
        if not result.drawing_number:
            result.drawing_number = self._extract_drawing_number(text)

        # Extract room labels
        result.room_labels = extract_room_labels(text)

        # Extract circuit references (power circuits: P1, P2, etc.)
        all_circuit_refs = []
        db_refs = extract_db_refs(text)

        for db in db_refs:
            circuits = extract_circuit_ids(text)
            for cid in circuits:
                if cid.startswith('P') or cid.startswith('AC') or cid.startswith('ISO'):
                    all_circuit_refs.append(f"{db} {cid}")

        # Also find direct circuit references like "DB-S1 P1"
        direct_refs = re.findall(
            r'(DB[-\s]?[A-Z0-9]+\s+(?:P|AC|ISO)\d+)',
            text,
            re.IGNORECASE
        )
        for ref in direct_refs:
            all_circuit_refs.append(ref.upper())

        result.circuit_refs = dedupe_strings(all_circuit_refs)

        # Extract legend items
        legend_text = legend_region_text or text
        result.legend_items = self._extract_legend_items(legend_text)

        # Extract notes
        result.notes = self._extract_notes(text)

        # Extract mounting heights
        result.mounting_heights = self._extract_mounting_heights(text)

        # Extract cable sizes
        cable_specs = extract_cable_sizes(text)
        result.cable_sizes = [cs.raw_text for cs in cable_specs]

        # Extract equipment labels
        result.equipment_labels = self._extract_equipment_labels(text)

        # Extract containment references
        result.containment_refs = self._extract_containment(text)

        return result

    def _extract_drawing_number(self, text: str) -> str:
        """Extract drawing number from text."""
        patterns = [
            r'([A-Z]{2,4}-[A-Z]{1,4}-\d{1,3}-(?:PLUGS|PWR|POWER))',
            r'([A-Z]{2,4}-\d{1,3}-(?:PLUGS|PWR|POWER))',
            r'DWG\s*(?:NO)?[\s:\.]+([A-Z0-9\-]+)',
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
            r'(?:PLUGS?|POWER)\s+(?:LAYOUT|PLAN)\s+[-–]\s+(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_text_for_display(match.group(1))

        return ""

    def _extract_legend_items(self, text: str) -> List[str]:
        """Extract socket/plug types from legend."""
        items = []

        # Look for LEGEND section
        legend_match = re.search(
            r'LEGEND[\s:]*(.+?)(?:\n\n|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )

        search_text = legend_match.group(1) if legend_match else text

        # Find socket types
        for pattern, socket_type in self.socket_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    items.append(clean_text_for_display(match.group(0)))

        # Find data point types
        for pattern, data_type in self.data_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    items.append(clean_text_for_display(match.group(0)))

        # Find isolator types
        for pattern, iso_type in self.isolator_patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    items.append(clean_text_for_display(match.group(0)))

        return dedupe_strings(items)

    def _extract_notes(self, text: str) -> List[str]:
        """Extract notes from text."""
        notes = []

        note_patterns = [
            r'NOTE[S]?[\s:]+(.+?)(?:\n\n|\Z)',
            r'N\.B\.[\s:]+(.+?)(?:\n|$)',
            r'(?:^|\n)(\d+\.\s+.+?)(?:\n|$)',
        ]

        for pattern in note_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                note = clean_text_for_display(match.group(1))
                if len(note) > 10:
                    notes.append(note)

        return notes[:10]

    def _extract_mounting_heights(self, text: str) -> List[str]:
        """Extract mounting height specifications."""
        heights = []

        patterns = [
            r'@\s*(\d+)\s*mm',
            r'(\d+)\s*mm\s+(?:AFF|AFFL|above\s+floor)',
            r'height[\s:]+(\d+)\s*mm',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                heights.append(f"{match.group(1)}mm")

        return dedupe_strings(heights)

    def _extract_equipment_labels(self, text: str) -> List[str]:
        """Extract equipment labels from text."""
        labels = []

        patterns = [
            r'\b(A/?C\s*(?:UNIT)?)\b',
            r'\b(GEYSER\s*\d*[lL]?)\b',
            r'\b(STOVE)\b',
            r'\b(OVEN)\b',
            r'\b(HOB)\b',
            r'\b(DISHWASHER)\b',
            r'\b(WASHING\s*MACHINE)\b',
            r'\b(DRYER)\b',
            r'\b(POOL\s*PUMP)\b',
            r'\b(HEAT\s*PUMP)\b',
            r'\b(GATE\s*MOTOR)\b',
            r'\b(GARAGE\s*MOTOR)\b',
            r'\b(EV\s*CHARGER)\b',
            r'\b(UPS)\b',
            r'\b(INVERTER)\b',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                labels.append(match.group(1).upper())

        return dedupe_strings(labels)

    def _extract_containment(self, text: str) -> List[str]:
        """Extract containment references."""
        refs = []

        patterns = [
            r'(\d+mm\s*(?:PVC\s*)?CONDUIT)',
            r'(CABLE\s*TRAY\s*\d*)',
            r'(TRUNKING\s*\d*x\d*)',
            r'(SKIRTING\s*TRUNKING)',
            r'(POWER\s*SKIRTING)',
            r'(2[-\s]?COMPARTMENT\s*TRUNKING)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                refs.append(clean_text_for_display(match.group(1)))

        return dedupe_strings(refs)

    def validate(self, result: LayoutExtraction) -> List[ExtractionWarning]:
        """Validate extraction result and return warnings."""
        warnings = []

        if not result.room_labels:
            warnings.append(ExtractionWarning(
                code="NO_ROOMS",
                message="No room labels found in plugs layout",
                severity=Severity.INFO,
                source_stage="extract_plugs_layout",
            ))

        if not result.circuit_refs:
            warnings.append(ExtractionWarning(
                code="NO_CIRCUIT_REFS",
                message="No power circuit references found",
                severity=Severity.INFO,
                source_stage="extract_plugs_layout",
            ))

        if not result.legend_items:
            warnings.append(ExtractionWarning(
                code="NO_LEGEND",
                message="No legend/socket types found",
                severity=Severity.INFO,
                source_stage="extract_plugs_layout",
            ))

        return warnings
