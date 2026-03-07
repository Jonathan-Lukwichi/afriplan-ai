"""
evaluation - Extraction accuracy scoring system for AfriPlan Electrical

This package provides tools to measure and track extraction accuracy
by comparing AI extraction results against manually-created ground truth.

Usage:
    # Run benchmark from command line
    python -m evaluation.run_benchmark

    # Or use programmatically
    from evaluation.scorer import score_document
    from evaluation.report import print_document_report

    score = score_document(ai_result, ground_truth)
    print_document_report(score)
"""

from .metrics import (
    FieldScore,
    score_exact_match,
    score_number,
    score_count,
    score_text,
    score_mcb_rating,
    score_cable_size,
    calculate_weighted_score,
    calculate_section_scores
)

from .scorer import (
    DocumentScore,
    score_document,
    load_ground_truth
)

from .report import (
    print_document_report,
    print_summary_report,
    save_report_json,
    save_report_markdown
)

from .run_benchmark import (
    run_benchmark,
    find_test_documents
)

__version__ = "1.0.0"
__all__ = [
    # Metrics
    "FieldScore",
    "score_exact_match",
    "score_number",
    "score_count",
    "score_text",
    "score_mcb_rating",
    "score_cable_size",
    "calculate_weighted_score",
    "calculate_section_scores",

    # Scorer
    "DocumentScore",
    "score_document",
    "load_ground_truth",

    # Report
    "print_document_report",
    "print_summary_report",
    "save_report_json",
    "save_report_markdown",

    # Benchmark
    "run_benchmark",
    "find_test_documents"
]
