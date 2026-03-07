"""
AfriPlan Electrical v1.0 — Pipeline Stages Package

Pipeline: INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT

v1.0 - Deterministic-first classification:
- classify_pages: Auto-classify pages using KeywordClassifier (NO LLM)
"""

from .ingest import ingest
from .classify import classify
from .discover import discover
from .review import ReviewManager, create_review_manager, get_items_needing_review, create_review_stage_result
from .validate import validate
from .price import price
from .output import generate_output

# v1.0 - Deterministic page classification (NO LLM)
from .classify_pages import (
    classify_all_pages,
    classify_pages_from_list,
    classify_service_tier,
    get_classification_summary,
    classify_with_stage_result,
    PageClassificationSummary,
)

# v1.0 - Deterministic SLD extraction (NO LLM)
from .extract_sld import (
    extract_sld_data,
    extract_all_dbs,
    extract_db_names,
    extract_circuit_counts,
    extract_sld_with_stage_result,
    SLDExtractionResult,
    DBData,
    CircuitData,
)

# v1.0 - Deterministic legend extraction (NO LLM)
from .extract_legend import (
    extract_legend,
    extract_legend_from_pages,
    extract_legend_with_stage_result,
    LegendEntry,
    LegendExtractionResult,
    build_symbol_lookup,
)

# v1.0 - Reconciliation stage (SINGLE LLM call only if needed)
from .reconcile import (
    reconcile_extraction,
    reconcile_with_stage_result,
    ReconciliationResult,
    ReconciliationIssue,
)

# Multi-pass extraction strategy
from .multi_pass_discover import (
    multi_pass_discover,
    MultiPassState,
    ExtractionPass,
    PassResult,
)

# Interactive step-by-step extraction
from .interactive_passes import (
    InteractivePipeline,
    InteractivePassResult,
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
    # v1.0 - Deterministic classification
    "classify_all_pages",
    "classify_pages_from_list",
    "classify_service_tier",
    "get_classification_summary",
    "classify_with_stage_result",
    "PageClassificationSummary",
    # v1.0 - Deterministic SLD extraction
    "extract_sld_data",
    "extract_all_dbs",
    "extract_db_names",
    "extract_circuit_counts",
    "extract_sld_with_stage_result",
    "SLDExtractionResult",
    "DBData",
    "CircuitData",
    # v1.0 - Deterministic legend extraction
    "extract_legend",
    "extract_legend_from_pages",
    "extract_legend_with_stage_result",
    "LegendEntry",
    "LegendExtractionResult",
    "build_symbol_lookup",
    # v1.0 - Reconciliation
    "reconcile_extraction",
    "reconcile_with_stage_result",
    "ReconciliationResult",
    "ReconciliationIssue",
    # Multi-pass
    "multi_pass_discover",
    "MultiPassState",
    "ExtractionPass",
    "PassResult",
    # Interactive extraction
    "InteractivePipeline",
    "InteractivePassResult",
]
