"""
AfriPlan AI - Benchmark Integration
====================================
Integrates benchmark validation with the Guided Upload page.
"""

import json
import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path

# Import benchmark components
try:
    from .validator import BenchmarkValidator, BenchmarkReport
    from . import improved_prompts
except ImportError:
    from benchmark.validator import BenchmarkValidator, BenchmarkReport
    from benchmark import improved_prompts


def get_benchmark_validator() -> BenchmarkValidator:
    """Get or create cached benchmark validator."""
    if 'benchmark_validator' not in st.session_state:
        benchmark_dir = Path(__file__).parent
        ground_truth_path = benchmark_dir / "ground_truth.json"
        st.session_state.benchmark_validator = BenchmarkValidator(str(ground_truth_path))
    return st.session_state.benchmark_validator


def identify_project(project_name: str) -> Optional[str]:
    """
    Try to identify which benchmark project matches the extraction.

    Args:
        project_name: Extracted project name

    Returns:
        Project ID if matched, None otherwise
    """
    validator = get_benchmark_validator()
    name_lower = project_name.lower()

    # Try to match known projects
    if "wedela" in name_lower or "recreational" in name_lower:
        return "WEDELA_001"
    elif "eurobath" in name_lower or "yapa" in name_lower or "470" in name_lower:
        return "EUROBATH_001"
    elif "newmark" in name_lower or "offices" in name_lower or "erf1/1" in name_lower:
        return "NEWMARK_001"

    return None


def validate_extraction_against_benchmark(
    extracted_data: Dict[str, Any],
    project_id: Optional[str] = None
) -> Optional[BenchmarkReport]:
    """
    Validate extracted data against benchmark ground truth.

    Args:
        extracted_data: Data from AI extraction pipeline
        project_id: Optional specific project to validate against

    Returns:
        BenchmarkReport if validation possible, None otherwise
    """
    validator = get_benchmark_validator()

    # Try to auto-identify project
    if project_id is None:
        project_name = extracted_data.get('project_name', '')
        if not project_name:
            # Try to get from metadata
            metadata = extracted_data.get('metadata', {})
            project_name = metadata.get('project_name', '')

        project_id = identify_project(project_name)

    if project_id is None:
        return None

    try:
        return validator.validate_extraction(project_id, extracted_data)
    except Exception as e:
        st.warning(f"Benchmark validation failed: {e}")
        return None


def render_benchmark_results(report: BenchmarkReport):
    """Render benchmark validation results in Streamlit."""

    st.subheader("Benchmark Validation Results")

    # Overall accuracy with color coding
    accuracy = report.overall_accuracy
    if accuracy >= 80:
        color = "green"
        status = "Excellent"
    elif accuracy >= 60:
        color = "orange"
        status = "Good"
    else:
        color = "red"
        status = "Needs Improvement"

    st.markdown(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: {color}; margin: 0; font-size: 3rem;">{accuracy}%</h1>
        <p style="color: #94a3b8; margin: 5px 0;">{status} - Overall Accuracy</p>
        <p style="color: #64748b; margin: 0; font-size: 0.9rem;">Project: {report.project_name}</p>
    </div>
    """, unsafe_allow_html=True)

    # Category breakdown
    st.markdown("### Category Scores")

    cols = st.columns(3)
    categories = list(report.category_scores.items())

    for i, (category, score) in enumerate(categories):
        with cols[i % 3]:
            pct = score.accuracy_pct

            if pct >= 80:
                icon = ""
                bg = "#22c55e20"
            elif pct >= 60:
                icon = ""
                bg = "#f59e0b20"
            else:
                icon = ""
                bg = "#ef444420"

            st.markdown(f"""
            <div style="padding: 15px; background: {bg}; border-radius: 8px; margin-bottom: 10px; text-align: center;">
                <span style="font-size: 1.5rem;">{icon}</span>
                <h4 style="margin: 5px 0; color: #f1f5f9;">{category.replace('_', ' ').title()}</h4>
                <p style="margin: 0; font-size: 1.2rem; font-weight: bold; color: #f1f5f9;">{pct}%</p>
                <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">{score.matched_fields}/{score.total_fields} fields</p>
            </div>
            """, unsafe_allow_html=True)

    # Critical issues
    if report.critical_misses:
        st.markdown("### Critical Issues")
        for miss in report.critical_misses:
            st.error(f" {miss}")

    # Recommendations
    if report.recommendations:
        st.markdown("### Recommendations")
        for rec in report.recommendations:
            st.info(f" {rec}")

    # Detailed breakdown (expandable)
    with st.expander("View Detailed Field Results"):
        for category, score in report.category_scores.items():
            st.markdown(f"**{category.replace('_', ' ').title()}**")

            for detail in score.details:
                if detail.match:
                    st.markdown(f"- {detail.field_name}: {detail.expected} = {detail.actual}")
                else:
                    st.markdown(f"- {detail.field_name}: Expected `{detail.expected}`, Got `{detail.actual}`")

            st.markdown("---")


def convert_extraction_for_validation(
    db_data: Dict[str, Any],
    cable_routes: list,
    legend_data: Dict[str, Any],
    project_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert app session state data to format expected by validator.

    Args:
        db_data: Distribution board data from SLD extraction
        cable_routes: Cable routes list
        legend_data: Legend extraction data
        project_info: Project metadata

    Returns:
        Normalized data dict for validation
    """
    # Build distribution boards list
    distribution_boards = []

    for db_name, db_info in db_data.items():
        if isinstance(db_info, dict):
            db_entry = {
                "name": db_name,
                "is_main": db_info.get("is_main", False),
                "fed_from": db_info.get("fed_from", ""),
                "incoming_cable": db_info.get("incoming_cable", ""),
                "main_breaker_a": db_info.get("main_breaker_a", 0),
                "circuits": {
                    "lighting": db_info.get("lighting_circuits", []),
                    "power": db_info.get("power_circuits", []),
                    "isolators": db_info.get("isolators", []),
                    "dedicated": db_info.get("dedicated_circuits", []),
                }
            }
            distribution_boards.append(db_entry)

    # Build totals
    totals = {
        "distribution_boards": len(distribution_boards),
        "lighting_circuits": sum(
            len(db.get("circuits", {}).get("lighting", []))
            for db in distribution_boards
        ),
        "power_circuits": sum(
            len(db.get("circuits", {}).get("power", []))
            for db in distribution_boards
        ),
    }

    return {
        "project_name": project_info.get("project_name", ""),
        "supply_point": project_info.get("supply_point", {}),
        "distribution_boards": distribution_boards,
        "cable_routes": cable_routes,
        "legend": legend_data,
        "totals": totals,
    }


def get_improved_prompt(prompt_name: str) -> str:
    """
    Get an improved prompt from the benchmark module.

    Args:
        prompt_name: Name of the prompt (e.g., "PROMPT_DB_DETECTION")

    Returns:
        The improved prompt string
    """
    return getattr(improved_prompts, prompt_name, "")


# Export convenience functions
__all__ = [
    'get_benchmark_validator',
    'identify_project',
    'validate_extraction_against_benchmark',
    'render_benchmark_results',
    'convert_extraction_for_validation',
    'get_improved_prompt',
]
