"""
AfriPlan AI Benchmark Module
============================
Provides ground truth data, improved prompts, and validation
for measuring and improving extraction accuracy.

Usage:
    from benchmark import BenchmarkValidator, improved_prompts

    # Validate extraction results
    validator = BenchmarkValidator()
    report = validator.validate_extraction("WEDELA_001", extracted_data)
    print(f"Accuracy: {report.overall_accuracy}%")

    # Use improved prompts
    from benchmark.improved_prompts import PROMPT_DB_DETECTION, PROMPT_SUPPLY_POINT
"""

from .validator import (
    BenchmarkValidator,
    BenchmarkReport,
    CategoryScore,
    ValidationResult,
)

from .improved_prompts import (
    PROMPT_SUPPLY_POINT,
    PROMPT_DB_DETECTION,
    PROMPT_CIRCUIT_SCHEDULE,
    PROMPT_CABLE_ROUTES,
    PROMPT_LEGEND_LIGHTING,
    PROMPT_LEGEND_POWER,
    PROMPT_CIRCUIT_CLUSTER_LIGHTING,
    PROMPT_CIRCUIT_CLUSTER_POWER,
    PROMPT_ROOM_DETECTION,
    PROMPT_PROJECT_INFO,
    get_db_schedule_prompt,
    get_room_fixtures_prompt,
)

from .integration import (
    get_benchmark_validator,
    identify_project,
    validate_extraction_against_benchmark,
    render_benchmark_results,
    convert_extraction_for_validation,
    get_improved_prompt,
)

__version__ = "1.0.0"
__all__ = [
    "BenchmarkValidator",
    "BenchmarkReport",
    "CategoryScore",
    "ValidationResult",
    "PROMPT_SUPPLY_POINT",
    "PROMPT_DB_DETECTION",
    "PROMPT_CIRCUIT_SCHEDULE",
    "PROMPT_CABLE_ROUTES",
    "PROMPT_LEGEND_LIGHTING",
    "PROMPT_LEGEND_POWER",
    "PROMPT_CIRCUIT_CLUSTER_LIGHTING",
    "PROMPT_CIRCUIT_CLUSTER_POWER",
    "PROMPT_ROOM_DETECTION",
    "PROMPT_PROJECT_INFO",
    "get_db_schedule_prompt",
    "get_room_fixtures_prompt",
]
