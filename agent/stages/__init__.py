"""
AfriPlan Electrical v4.1 — Pipeline Stages Package

7-stage pipeline: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT
"""

from .ingest import ingest
from .classify import classify
from .discover import discover
from .review import ReviewManager, create_review_manager, get_items_needing_review, create_review_stage_result
from .validate import validate
from .price import price
from .output import generate_output

__all__ = [
    "ingest",
    "classify",
    "discover",
    "ReviewManager",
    "create_review_manager",
    "get_items_needing_review",
    "create_review_stage_result",
    "validate",
    "price",
    "generate_output",
]
