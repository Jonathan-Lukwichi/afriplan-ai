"""
AfriPlan Electrical - Drawing Register Extractor

Extract drawing register information from REGISTER page type.
Parses:
- Drawing numbers
- Drawing titles
- Revision info
- Dates
- Project metadata

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from agent.models import (
    RegisterRow, RegisterExtraction, ExtractionWarning, Severity, BoundingBox
)
from agent.extractors.common import (
    normalize_text, clean_text_for_display, dedupe_strings
)
from agent.parsers.table_parser import extract_register_rows

logger = logging.getLogger(__name__)


class RegisterExtractor:
    """
    Deterministic extractor for drawing register pages.

    Usage:
        extractor = RegisterExtractor()
        result = extractor.extract(page_text, page_number=1)
    """

    def __init__(self):
        """Initialize the register extractor."""
        # Column header patterns for table detection
        self.header_patterns = [
            r'drwg\s*no',
            r'drawing\s*no',
            r'dwg\s*no',
            r'title',
            r'description',
            r'rev(?:ision)?',
            r'date',
            r'status',
        ]

        # Drawing number patterns
        self.drawing_patterns = [
            r'([A-Z]{2,4}-[A-Z]{1,4}-\d{1,3}-[A-Z]+)',  # WD-AB-01-SLD
            r'([A-Z]{2,4}-\d{1,3}-[A-Z]+)',              # TJM-01-LIGHTING
            r'(\d{1,3}[-\.][A-Z]+)',                      # 01-SLD
        ]

    def extract(
        self,
        text: str,
        text_blocks: Optional[List[Any]] = None,
        page_number: int = 0,
        title_block_text: str = "",
    ) -> RegisterExtraction:
        """
        Extract register information from page text.

        Args:
            text: Raw page text
            text_blocks: Positioned text blocks (optional, for table detection)
            page_number: Source page number
            title_block_text: Text from title block region (for project metadata)

        Returns:
            RegisterExtraction with parsed data
        """
        result = RegisterExtraction(source_page=page_number)

        # Extract project metadata from title block
        if title_block_text:
            result.project_name = self._extract_project_name(title_block_text)
            result.client_name = self._extract_client_name(title_block_text)
            result.consultant_name = self._extract_consultant_name(title_block_text)

        # Try to extract from main text as fallback
        if not result.project_name:
            result.project_name = self._extract_project_name(text)
        if not result.client_name:
            result.client_name = self._extract_client_name(text)
        if not result.consultant_name:
            result.consultant_name = self._extract_consultant_name(text)

        # Extract register rows
        rows = self._extract_register_rows(text)
        result.rows = rows
        result.total_drawings = len(rows)

        # Add warnings if extraction was partial
        if not rows:
            result.parse_warnings.append(
                "No drawing register rows found. Page may not contain a valid register table."
            )

        return result

    def _extract_project_name(self, text: str) -> str:
        """Extract project name from text."""
        patterns = [
            r'PROJECT\s*(?:NAME)?[\s:]+(.+?)(?:\n|$)',
            r'PROJECT[\s:]+(.+?)(?:\n|$)',
            r'THE\s+(?:PROPOSED\s+)?(.+?)\s+(?:FOR|AT|ON)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up common suffixes
                name = re.sub(r'\s*(?:ELECTRICAL|INSTALLATION|WORKS).*$', '', name, flags=re.IGNORECASE)
                return clean_text_for_display(name)

        return ""

    def _extract_client_name(self, text: str) -> str:
        """Extract client/owner name from text."""
        patterns = [
            r'CLIENT[\s:]+(.+?)(?:\n|$)',
            r'OWNER[\s:]+(.+?)(?:\n|$)',
            r'EMPLOYER[\s:]+(.+?)(?:\n|$)',
            r'FOR[\s:]+(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_text_for_display(match.group(1))

        return ""

    def _extract_consultant_name(self, text: str) -> str:
        """Extract consultant/engineer name from text."""
        patterns = [
            r'CONSULTANT[\s:]+(.+?)(?:\n|$)',
            r'ENGINEER[\s:]+(.+?)(?:\n|$)',
            r'ELECTRICAL\s+ENGINEER[\s:]+(.+?)(?:\n|$)',
            r'DESIGNED\s+BY[\s:]+(.+?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return clean_text_for_display(match.group(1))

        return ""

    def _extract_register_rows(self, text: str) -> List[RegisterRow]:
        """Extract drawing register rows from text."""
        rows = []

        # First try using table parser
        parsed_rows = extract_register_rows(text)

        for pr in parsed_rows:
            row = RegisterRow(
                drawing_number=pr.get('drawing_number', ''),
                drawing_title=pr.get('title', ''),
                revision=pr.get('revision', ''),
                date=pr.get('date', ''),
                raw_text=pr.get('raw_text', ''),
                confidence=0.7 if pr.get('title') else 0.5,
            )

            if row.drawing_number:  # Only add if we have a drawing number
                rows.append(row)

        # If table parser didn't find rows, try line-by-line extraction
        if not rows:
            rows = self._extract_rows_from_lines(text)

        # Deduplicate by drawing number
        seen = set()
        unique_rows = []
        for row in rows:
            key = row.drawing_number.upper()
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)

        return unique_rows

    def _extract_rows_from_lines(self, text: str) -> List[RegisterRow]:
        """
        Fallback extraction: look for drawing numbers line by line.
        """
        rows = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try each drawing number pattern
            for pattern in self.drawing_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    dwg_num = match.group(1).upper()

                    # Extract title (text after drawing number)
                    rest = line[match.end():].strip()
                    title = rest.strip(' \t-_:')

                    # Try to extract revision
                    rev = ""
                    rev_match = re.search(r'\b(REV[.\s]*[A-Z0-9]+|R\d+)\b', rest, re.IGNORECASE)
                    if rev_match:
                        rev = rev_match.group(1)
                        title = title.replace(rev_match.group(0), '').strip()

                    # Try to extract date
                    date = ""
                    date_match = re.search(
                        r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})',
                        rest
                    )
                    if date_match:
                        date = date_match.group(1)
                        title = title.replace(date_match.group(0), '').strip()

                    row = RegisterRow(
                        drawing_number=dwg_num,
                        drawing_title=clean_text_for_display(title),
                        revision=rev,
                        date=date,
                        raw_text=line,
                        confidence=0.5,  # Lower confidence for line-by-line
                    )

                    rows.append(row)
                    break  # Only match once per line

        return rows

    def validate(self, result: RegisterExtraction) -> List[ExtractionWarning]:
        """
        Validate extraction result and return warnings.
        """
        warnings = []

        # Check for empty project name
        if not result.project_name:
            warnings.append(ExtractionWarning(
                code="NO_PROJECT_NAME",
                message="Project name could not be extracted",
                severity=Severity.WARNING,
                source_stage="extract_register",
            ))

        # Check for empty rows
        if not result.rows:
            warnings.append(ExtractionWarning(
                code="NO_REGISTER_ROWS",
                message="No drawing register entries found",
                severity=Severity.WARNING,
                source_stage="extract_register",
            ))

        # Check for rows without titles
        rows_without_title = [r for r in result.rows if not r.drawing_title]
        if rows_without_title:
            warnings.append(ExtractionWarning(
                code="ROWS_WITHOUT_TITLE",
                message=f"{len(rows_without_title)} drawings without titles",
                severity=Severity.INFO,
                source_stage="extract_register",
                details={"drawing_numbers": [r.drawing_number for r in rows_without_title]},
            ))

        return warnings

    def get_drawing_numbers(self, result: RegisterExtraction) -> List[str]:
        """Get list of all drawing numbers from extraction."""
        return [r.drawing_number for r in result.rows if r.drawing_number]

    def find_drawing_by_type(
        self,
        result: RegisterExtraction,
        drawing_type: str,
    ) -> List[RegisterRow]:
        """
        Find drawings of a specific type (SLD, LIGHTING, PLUGS, etc.)
        """
        type_upper = drawing_type.upper()
        return [
            r for r in result.rows
            if type_upper in r.drawing_number.upper() or type_upper in r.drawing_title.upper()
        ]
