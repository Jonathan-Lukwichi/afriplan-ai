"""
AfriPlan Electrical - Table Parser

Detect and parse table-like structures in PDF text.
Uses text clustering and alignment analysis.

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """A single cell in a detected table."""
    text: str = ""
    row: int = 0
    col: int = 0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0


@dataclass
class TableRegion:
    """A detected table region with cells."""
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    num_rows: int = 0
    num_cols: int = 0
    cells: List[TableCell] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class TextBlock:
    """Simple text block for table detection."""
    text: str = ""
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2


def detect_table_regions(
    text_blocks: List[Any],
    min_rows: int = 3,
    min_cols: int = 2,
    row_tolerance: float = 10.0,
    col_tolerance: float = 30.0,
) -> List[TableRegion]:
    """
    Detect table-like regions from positioned text blocks.

    Args:
        text_blocks: List of text blocks with x0, y0, x1, y1 attributes
        min_rows: Minimum rows to consider as table
        min_cols: Minimum columns to consider as table
        row_tolerance: Y-coordinate tolerance for same row
        col_tolerance: X-coordinate tolerance for same column

    Returns:
        List of detected TableRegion objects
    """
    if not text_blocks:
        return []

    tables = []

    # Convert to internal format if needed
    blocks = []
    for b in text_blocks:
        tb = TextBlock(
            text=getattr(b, 'text', str(b)),
            x0=getattr(b, 'x0', 0.0),
            y0=getattr(b, 'y0', 0.0),
            x1=getattr(b, 'x1', 0.0),
            y1=getattr(b, 'y1', 0.0),
        )
        blocks.append(tb)

    # Group blocks by approximate row (y-coordinate)
    row_groups = _group_by_y(blocks, row_tolerance)

    if len(row_groups) < min_rows:
        return []

    # Find rows with consistent column alignment
    # (table rows tend to have items at similar x-positions)

    # Get all x-positions
    all_x = []
    for row_blocks in row_groups.values():
        for b in row_blocks:
            all_x.append(b.center_x)

    # Find column positions (clustered x-coordinates)
    col_positions = _cluster_positions(all_x, col_tolerance)

    if len(col_positions) < min_cols:
        return []

    # Now identify contiguous table regions
    # A table is a group of consecutive rows with similar column structure

    sorted_rows = sorted(row_groups.keys())

    # Analyze each row's column structure
    row_columns = {}
    for y, row_blocks in row_groups.items():
        cols = _assign_to_columns(row_blocks, col_positions, col_tolerance)
        row_columns[y] = cols

    # Find contiguous table regions
    table_start = None
    table_rows = []

    for i, y in enumerate(sorted_rows):
        cols_used = len([c for c in row_columns[y] if c])
        is_table_row = cols_used >= min_cols

        if is_table_row:
            if table_start is None:
                table_start = y
            table_rows.append((y, row_groups[y], row_columns[y]))
        else:
            # End of potential table
            if len(table_rows) >= min_rows:
                table = _build_table_from_rows(table_rows, col_positions)
                if table:
                    tables.append(table)

            table_start = None
            table_rows = []

    # Don't forget last table
    if len(table_rows) >= min_rows:
        table = _build_table_from_rows(table_rows, col_positions)
        if table:
            tables.append(table)

    return tables


def _group_by_y(blocks: List[TextBlock], tolerance: float) -> Dict[float, List[TextBlock]]:
    """Group text blocks by y-coordinate (row)."""
    if not blocks:
        return {}

    # Sort by y
    sorted_blocks = sorted(blocks, key=lambda b: b.center_y)

    groups = {}
    current_y = None
    current_group = []

    for b in sorted_blocks:
        if current_y is None or abs(b.center_y - current_y) > tolerance:
            # New row
            if current_group:
                avg_y = sum(bl.center_y for bl in current_group) / len(current_group)
                groups[avg_y] = current_group
            current_y = b.center_y
            current_group = [b]
        else:
            current_group.append(b)

    # Don't forget last group
    if current_group:
        avg_y = sum(bl.center_y for bl in current_group) / len(current_group)
        groups[avg_y] = current_group

    return groups


def _cluster_positions(values: List[float], tolerance: float) -> List[float]:
    """Cluster numerical values into representative positions."""
    if not values:
        return []

    sorted_vals = sorted(values)
    clusters = []
    current_cluster = [sorted_vals[0]]

    for v in sorted_vals[1:]:
        if abs(v - current_cluster[-1]) <= tolerance:
            current_cluster.append(v)
        else:
            # End current cluster
            clusters.append(sum(current_cluster) / len(current_cluster))
            current_cluster = [v]

    # Don't forget last cluster
    if current_cluster:
        clusters.append(sum(current_cluster) / len(current_cluster))

    return clusters


def _assign_to_columns(
    blocks: List[TextBlock],
    col_positions: List[float],
    tolerance: float,
) -> List[Optional[TextBlock]]:
    """Assign blocks to column positions."""
    result = [None] * len(col_positions)

    for b in blocks:
        # Find closest column
        best_col = None
        best_dist = float('inf')

        for i, col_x in enumerate(col_positions):
            dist = abs(b.center_x - col_x)
            if dist < best_dist and dist <= tolerance:
                best_dist = dist
                best_col = i

        if best_col is not None:
            result[best_col] = b

    return result


def _build_table_from_rows(
    rows: List[Tuple],
    col_positions: List[float],
) -> Optional[TableRegion]:
    """Build a TableRegion from detected rows."""
    if not rows:
        return None

    cells = []
    min_x = float('inf')
    min_y = float('inf')
    max_x = 0.0
    max_y = 0.0

    for row_idx, (y, row_blocks, row_cols) in enumerate(rows):
        for col_idx, block in enumerate(row_cols):
            if block:
                cell = TableCell(
                    text=block.text,
                    row=row_idx,
                    col=col_idx,
                    x0=block.x0,
                    y0=block.y0,
                    x1=block.x1,
                    y1=block.y1,
                )
                cells.append(cell)

                min_x = min(min_x, block.x0)
                min_y = min(min_y, block.y0)
                max_x = max(max_x, block.x1)
                max_y = max(max_y, block.y1)

    if not cells:
        return None

    # Extract headers (first row)
    headers = []
    for col_idx in range(len(col_positions)):
        header_cells = [c for c in cells if c.row == 0 and c.col == col_idx]
        if header_cells:
            headers.append(header_cells[0].text)
        else:
            headers.append("")

    # Calculate confidence based on table completeness
    total_cells = len(rows) * len(col_positions)
    filled_cells = len(cells)
    confidence = filled_cells / total_cells if total_cells > 0 else 0.0

    return TableRegion(
        x0=min_x,
        y0=min_y,
        x1=max_x,
        y1=max_y,
        num_rows=len(rows),
        num_cols=len(col_positions),
        cells=cells,
        headers=headers,
        confidence=confidence,
    )


def parse_table_text(
    text: str,
    delimiter_pattern: str = r'\s{2,}|\t',
    min_cols: int = 2,
) -> List[List[str]]:
    """
    Parse table-like text using delimiter pattern.

    Args:
        text: Raw text that may contain a table
        delimiter_pattern: Regex pattern for column separation
        min_cols: Minimum columns to consider as table row

    Returns:
        List of rows, each row is a list of cell values
    """
    lines = text.strip().split('\n')
    table_rows = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split by delimiter
        cells = re.split(delimiter_pattern, line)
        cells = [c.strip() for c in cells if c.strip()]

        if len(cells) >= min_cols:
            table_rows.append(cells)

    return table_rows


def extract_circuit_schedule(text: str) -> List[Dict[str, str]]:
    """
    Extract circuit schedule data from SLD text.

    Looks for patterns like:
    Circuit No | Description | Wattage | Wire Size | Breaker

    Args:
        text: SLD page text

    Returns:
        List of circuit dictionaries
    """
    circuits = []

    # Pattern for circuit rows
    # L1, P1, AC1, ISO1 etc followed by description and numbers
    circuit_pattern = r'(?P<circuit_id>[LP]\d+|AC\d+|ISO\d+|PP\d+|HP\d+)\s+(?P<rest>.+)'

    lines = text.split('\n')

    for line in lines:
        match = re.search(circuit_pattern, line, re.IGNORECASE)
        if match:
            circuit = {
                'circuit_id': match.group('circuit_id').upper(),
                'raw_text': line.strip(),
            }

            rest = match.group('rest')

            # Try to extract wattage
            wattage_match = re.search(r'(\d+)\s*[wW](?:att)?', rest)
            if wattage_match:
                circuit['wattage'] = wattage_match.group(1)

            # Try to extract wire size
            wire_match = re.search(r'(\d+(?:\.\d+)?)\s*mm[²2]?', rest)
            if wire_match:
                circuit['wire_size'] = wire_match.group(1)

            # Try to extract breaker
            breaker_match = re.search(r'(\d+)\s*[aA](?:mp)?', rest)
            if breaker_match:
                circuit['breaker'] = breaker_match.group(1)

            # Try to extract point count
            points_match = re.search(r'(\d+)\s*(?:pt|point|no)', rest, re.IGNORECASE)
            if points_match:
                circuit['points'] = points_match.group(1)

            circuits.append(circuit)

    return circuits


def extract_register_rows(text: str) -> List[Dict[str, str]]:
    """
    Extract drawing register rows from text.

    Args:
        text: Register page text

    Returns:
        List of register row dictionaries
    """
    rows = []

    # Look for drawing number patterns followed by title
    # Common patterns:
    # DWG NO    TITLE    REV    DATE
    # 01    SLD - SUITE 1    A    2025-01-15

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line contains a drawing number pattern
        dwg_match = re.search(
            r'([A-Z]{2,4}[-_][A-Z]{1,4}[-_]\d{1,3}[-_][A-Z]+|'
            r'\d{1,3}[-_][A-Z]+)',
            line,
            re.IGNORECASE
        )

        if dwg_match:
            row = {
                'drawing_number': dwg_match.group(1).upper(),
                'raw_text': line,
            }

            # Try to extract other fields
            rest = line[dwg_match.end():].strip()

            # Revision (REV A, R01, etc.)
            rev_match = re.search(r'\b(REV[.\s]*[A-Z0-9]+|R\d+|[A-Z])\b', rest, re.IGNORECASE)
            if rev_match:
                row['revision'] = rev_match.group(1)

            # Date (various formats)
            date_match = re.search(
                r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{2}/\d{2}/\d{2})',
                rest
            )
            if date_match:
                row['date'] = date_match.group(1)

            # Title is typically the longest remaining text
            # Remove found patterns and use remaining as title
            title_text = rest
            if rev_match:
                title_text = title_text.replace(rev_match.group(0), '').strip()
            if date_match:
                title_text = title_text.replace(date_match.group(0), '').strip()

            row['title'] = title_text.strip(' -_')

            rows.append(row)

    return rows
