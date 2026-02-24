"""
AfriPlan Electrical - Deterministic Parsers

Local-only text parsing utilities for electrical drawings.
No AI/cloud APIs used in this package.
"""

from .pdf_text import extract_text_blocks, extract_raw_text, TextBlock
from .keyword_classifier import KeywordClassifier, ClassificationRule
from .drawing_number_parser import parse_drawing_number, DrawingNumberInfo
from .table_parser import detect_table_regions, parse_table_text

__all__ = [
    "extract_text_blocks",
    "extract_raw_text",
    "TextBlock",
    "KeywordClassifier",
    "ClassificationRule",
    "parse_drawing_number",
    "DrawingNumberInfo",
    "detect_table_regions",
    "parse_table_text",
]
