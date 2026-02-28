"""
AfriPlan AI v5 — Core Components
=================================
Evidence-based extraction with confidence scoring and table zone detection.
"""

from .table_detector import (
    TableZone,
    detect_table_zones,
    split_multi_db_by_layout,
    HAS_OPENCV,
)
from .evidence import Evidence, Confident

__all__ = [
    "TableZone",
    "detect_table_zones",
    "split_multi_db_by_layout",
    "HAS_OPENCV",
    "Evidence",
    "Confident",
]
