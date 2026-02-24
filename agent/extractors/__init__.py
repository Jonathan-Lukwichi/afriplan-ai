"""
AfriPlan Electrical - Page-Type Specific Extractors

Deterministic extraction logic for different page types.
Each extractor handles one page type (Register, SLD, Layout, etc.)
"""

from .common import normalize_text, extract_cable_sizes, extract_db_refs, extract_circuit_ids
from .register_extractor import RegisterExtractor, RegisterRow, RegisterExtraction
from .sld_extractor import SLDExtractor, SLDCircuitRow, SLDExtraction
from .lighting_layout_extractor import LightingLayoutExtractor, LayoutExtraction
from .plugs_layout_extractor import PlugsLayoutExtractor

__all__ = [
    "normalize_text",
    "extract_cable_sizes",
    "extract_db_refs",
    "extract_circuit_ids",
    "RegisterExtractor",
    "RegisterRow",
    "RegisterExtraction",
    "SLDExtractor",
    "SLDCircuitRow",
    "SLDExtraction",
    "LightingLayoutExtractor",
    "LayoutExtraction",
    "PlugsLayoutExtractor",
]
