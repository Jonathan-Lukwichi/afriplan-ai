"""
AfriPlan Electrical - PDF Text Extraction

Extract text content from PDF pages using PyMuPDF (fitz).
Returns both raw text and positioned text blocks.

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TextBlock(BaseModel):
    """A positioned text block from PDF."""
    text: str = ""
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    width: float = 0.0
    height: float = 0.0
    font_size: float = 0.0
    font_name: str = ""
    is_bold: bool = False
    block_number: int = 0
    line_number: int = 0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2


def extract_text_blocks(
    pdf_path: Path,
    page_number: int = 0,
    page_obj: Optional[Any] = None,
) -> List[TextBlock]:
    """
    Extract text blocks with positions from a PDF page.

    Args:
        pdf_path: Path to PDF file (ignored if page_obj provided)
        page_number: 0-based page index
        page_obj: Optional fitz.Page object (if already opened)

    Returns:
        List of TextBlock objects with positions
    """
    if not HAS_FITZ:
        logger.error("PyMuPDF (fitz) not installed")
        return []

    blocks: List[TextBlock] = []

    try:
        if page_obj is not None:
            page = page_obj
            close_doc = False
        else:
            doc = fitz.open(str(pdf_path))
            close_doc = True
            if page_number >= len(doc):
                logger.warning(f"Page {page_number} out of range for {pdf_path}")
                doc.close()
                return []
            page = doc[page_number]

        # Extract text blocks with positions
        # flags: TEXT_PRESERVE_WHITESPACE | TEXT_PRESERVE_LIGATURES
        block_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        block_num = 0
        for block in block_dict.get("blocks", []):
            # Skip image blocks
            if block.get("type") != 0:
                continue

            for line_num, line in enumerate(block.get("lines", [])):
                line_text_parts = []
                font_sizes = []
                font_names = []
                is_bold = False

                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    line_text_parts.append(span_text)
                    font_sizes.append(span.get("size", 0))
                    font_names.append(span.get("font", ""))
                    if "bold" in span.get("font", "").lower():
                        is_bold = True

                line_text = "".join(line_text_parts).strip()
                if not line_text:
                    continue

                bbox = line.get("bbox", (0, 0, 0, 0))
                avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

                tb = TextBlock(
                    text=line_text,
                    x0=bbox[0],
                    y0=bbox[1],
                    x1=bbox[2],
                    y1=bbox[3],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                    font_size=avg_font_size,
                    font_name=font_names[0] if font_names else "",
                    is_bold=is_bold,
                    block_number=block_num,
                    line_number=line_num,
                )
                blocks.append(tb)

            block_num += 1

        if close_doc:
            doc.close()

    except Exception as e:
        logger.error(f"Error extracting text blocks: {e}")

    return blocks


def extract_raw_text(
    pdf_path: Path,
    page_number: int = 0,
    page_obj: Optional[Any] = None,
) -> str:
    """
    Extract raw text from a PDF page.

    Args:
        pdf_path: Path to PDF file
        page_number: 0-based page index
        page_obj: Optional fitz.Page object

    Returns:
        Raw text content as string
    """
    if not HAS_FITZ:
        logger.error("PyMuPDF (fitz) not installed")
        return ""

    try:
        if page_obj is not None:
            page = page_obj
            close_doc = False
        else:
            doc = fitz.open(str(pdf_path))
            close_doc = True
            if page_number >= len(doc):
                doc.close()
                return ""
            page = doc[page_number]

        text = page.get_text("text")

        if close_doc:
            doc.close()

        return text

    except Exception as e:
        logger.error(f"Error extracting raw text: {e}")
        return ""


def extract_all_pages_text(pdf_path: Path) -> Dict[int, str]:
    """
    Extract raw text from all pages of a PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict mapping page number (0-based) to text content
    """
    if not HAS_FITZ:
        return {}

    result = {}

    try:
        doc = fitz.open(str(pdf_path))
        for i in range(len(doc)):
            result[i] = doc[i].get_text("text")
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting all pages text: {e}")

    return result


def find_text_in_region(
    blocks: List[TextBlock],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> List[TextBlock]:
    """
    Find text blocks within a specified region.

    Args:
        blocks: List of TextBlock objects
        x0, y0, x1, y1: Region bounds

    Returns:
        Text blocks within the region
    """
    return [
        b for b in blocks
        if b.x0 >= x0 and b.y0 >= y0 and b.x1 <= x1 and b.y1 <= y1
    ]


def find_text_near_keyword(
    blocks: List[TextBlock],
    keyword: str,
    max_distance: float = 50.0,
    direction: str = "right",  # "right", "below", "any"
) -> List[TextBlock]:
    """
    Find text blocks near a keyword.

    Args:
        blocks: List of TextBlock objects
        keyword: Keyword to search for
        max_distance: Maximum distance in pixels
        direction: Direction to search ("right", "below", "any")

    Returns:
        Text blocks near the keyword
    """
    keyword_lower = keyword.lower()

    # Find keyword block
    keyword_blocks = [b for b in blocks if keyword_lower in b.text.lower()]
    if not keyword_blocks:
        return []

    result = []
    for kb in keyword_blocks:
        for b in blocks:
            if b == kb:
                continue

            if direction == "right":
                # Block is to the right and vertically aligned
                if b.x0 > kb.x1 and abs(b.center_y - kb.center_y) < max_distance:
                    if b.x0 - kb.x1 < max_distance:
                        result.append(b)

            elif direction == "below":
                # Block is below and horizontally aligned
                if b.y0 > kb.y1 and abs(b.center_x - kb.center_x) < max_distance:
                    if b.y0 - kb.y1 < max_distance:
                        result.append(b)

            elif direction == "any":
                # Any direction within distance
                dist = ((b.center_x - kb.center_x) ** 2 +
                        (b.center_y - kb.center_y) ** 2) ** 0.5
                if dist < max_distance:
                    result.append(b)

    return result


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return " ".join(text.split())


def clean_text(text: str) -> str:
    """Clean and normalize text for comparison."""
    # Remove extra whitespace
    text = normalize_whitespace(text)
    # Convert to lowercase
    text = text.lower()
    # Remove special characters except alphanumeric and basic punctuation
    text = re.sub(r'[^\w\s\-\.\/\(\)]', '', text)
    return text.strip()
