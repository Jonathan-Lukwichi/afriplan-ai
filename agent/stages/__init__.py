"""
AfriPlan Electrical v4.11 — Pipeline Stages Package

7-stage pipeline: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT

v4.11 additions:
- multi_pass_discover: Step-by-step extraction for better accuracy with limited models
"""

from .ingest import ingest
from .classify import classify
from .discover import discover
from .review import ReviewManager, create_review_manager, get_items_needing_review, create_review_stage_result
from .validate import validate
from .price import price
from .output import generate_output

# v4.11 - Multi-pass extraction strategy
from .multi_pass_discover import (
    multi_pass_discover,
    MultiPassState,
    ExtractionPass,
    PassResult,
)

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
    # v4.11 - Multi-pass
    "multi_pass_discover",
    "MultiPassState",
    "ExtractionPass",
    "PassResult",
]
