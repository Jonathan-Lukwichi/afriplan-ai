"""
metrics.py - Basic scoring functions for comparing extracted values to ground truth

Simple functions that compare two values and return a score between 0.0 and 1.0
"""

from typing import Any, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class FieldScore:
    """Score for a single field comparison"""
    field_name: str
    expected: Any
    actual: Any
    is_correct: bool
    score: float  # 0.0 to 1.0
    priority: str  # "critical", "high", "medium", "low"
    notes: str = ""


# =============================================================================
# EXACT MATCH SCORING
# =============================================================================

def score_exact_match(field_name: str, expected: Any, actual: Any,
                      priority: str = "medium") -> FieldScore:
    """
    Score based on exact match.
    Returns 1.0 if values match exactly, 0.0 otherwise.
    """
    if expected is None and actual is None:
        return FieldScore(field_name, expected, actual, True, 1.0, priority, "Both null")

    if expected is None or actual is None:
        return FieldScore(field_name, expected, actual, False, 0.0, priority, "One value missing")

    is_correct = expected == actual
    score = 1.0 if is_correct else 0.0

    return FieldScore(field_name, expected, actual, is_correct, score, priority)


# =============================================================================
# NUMERIC SCORING (with tolerance)
# =============================================================================

def score_number(field_name: str, expected: float, actual: float,
                 tolerance: float = 0.0, priority: str = "medium") -> FieldScore:
    """
    Score a numeric value.

    Args:
        tolerance: Allowed percentage difference (0.1 = 10% tolerance)
                   Use 0.0 for exact match required

    Returns:
        FieldScore with partial credit based on how close the values are
    """
    if expected is None and actual is None:
        return FieldScore(field_name, expected, actual, True, 1.0, priority, "Both null")

    if expected is None or actual is None:
        return FieldScore(field_name, expected, actual, False, 0.0, priority, "One value missing")

    try:
        expected = float(expected)
        actual = float(actual)
    except (ValueError, TypeError):
        return FieldScore(field_name, expected, actual, False, 0.0, priority, "Invalid number")

    # Exact match
    if expected == actual:
        return FieldScore(field_name, expected, actual, True, 1.0, priority, "Exact match")

    # Calculate percentage difference
    if expected == 0:
        if actual == 0:
            return FieldScore(field_name, expected, actual, True, 1.0, priority)
        else:
            return FieldScore(field_name, expected, actual, False, 0.0, priority, "Expected 0, got non-zero")

    diff_percent = abs(expected - actual) / abs(expected)

    # Within tolerance = correct
    if diff_percent <= tolerance:
        return FieldScore(field_name, expected, actual, True, 1.0, priority,
                         f"Within {tolerance*100:.0f}% tolerance")

    # Partial credit: score decreases linearly as difference increases
    # At 2x tolerance, score = 0.5; at 4x tolerance, score = 0
    score = max(0.0, 1.0 - (diff_percent / (tolerance * 4 if tolerance > 0 else 1)))

    return FieldScore(field_name, expected, actual, False, score, priority,
                     f"Diff: {diff_percent*100:.1f}%")


def score_count(field_name: str, expected: int, actual: int,
                priority: str = "high") -> FieldScore:
    """
    Score a count value (circuits, fixtures, etc.)
    Uses 15% tolerance by default - common in electrical counting.
    """
    return score_number(field_name, expected, actual, tolerance=0.15, priority=priority)


# =============================================================================
# TEXT SCORING
# =============================================================================

def score_text(field_name: str, expected: str, actual: str,
               priority: str = "medium", case_sensitive: bool = False) -> FieldScore:
    """
    Score text comparison with partial matching.

    Returns:
        1.0 for exact match
        0.8 for match after normalization (case, whitespace)
        0.5 for partial match (one contains the other)
        0.0 for no match
    """
    if expected is None and actual is None:
        return FieldScore(field_name, expected, actual, True, 1.0, priority)

    if expected is None or actual is None:
        return FieldScore(field_name, expected, actual, False, 0.0, priority, "One value missing")

    expected_str = str(expected)
    actual_str = str(actual)

    # Exact match
    if expected_str == actual_str:
        return FieldScore(field_name, expected, actual, True, 1.0, priority, "Exact match")

    # Normalized comparison
    exp_norm = expected_str.lower().strip().replace("-", "").replace("_", "").replace(" ", "")
    act_norm = actual_str.lower().strip().replace("-", "").replace("_", "").replace(" ", "")

    if exp_norm == act_norm:
        return FieldScore(field_name, expected, actual, True, 0.9, priority, "Match after normalization")

    # Partial match
    if exp_norm in act_norm or act_norm in exp_norm:
        return FieldScore(field_name, expected, actual, False, 0.5, priority, "Partial match")

    return FieldScore(field_name, expected, actual, False, 0.0, priority, "No match")


# =============================================================================
# LIST SCORING
# =============================================================================

def score_list_count(field_name: str, expected_list: List, actual_list: List,
                     priority: str = "high") -> FieldScore:
    """
    Score based on list length (e.g., number of circuits in a DB).
    """
    expected_count = len(expected_list) if expected_list else 0
    actual_count = len(actual_list) if actual_list else 0

    return score_count(field_name, expected_count, actual_count, priority)


def score_list_items(field_name: str, expected_list: List[str], actual_list: List[str],
                     priority: str = "medium") -> FieldScore:
    """
    Score based on matching items in lists (e.g., DB names found).
    Uses Jaccard similarity: intersection / union
    """
    if not expected_list and not actual_list:
        return FieldScore(field_name, expected_list, actual_list, True, 1.0, priority)

    if not expected_list or not actual_list:
        return FieldScore(field_name, expected_list, actual_list, False, 0.0, priority,
                         "One list empty")

    # Normalize items for comparison
    exp_set = set(str(x).lower().strip() for x in expected_list)
    act_set = set(str(x).lower().strip() for x in actual_list)

    intersection = len(exp_set & act_set)
    union = len(exp_set | act_set)

    if union == 0:
        return FieldScore(field_name, expected_list, actual_list, True, 1.0, priority)

    jaccard = intersection / union
    is_correct = jaccard >= 0.8  # 80% overlap = correct

    return FieldScore(field_name, list(exp_set), list(act_set), is_correct, jaccard, priority,
                     f"Matched {intersection}/{len(exp_set)} expected")


# =============================================================================
# CIRCUIT-SPECIFIC SCORING
# =============================================================================

def score_mcb_rating(field_name: str, expected: int, actual: int) -> FieldScore:
    """
    Score MCB rating - must be exact match for safety.
    This is CRITICAL - wrong MCB rating is a safety issue.
    """
    return score_exact_match(field_name, expected, actual, priority="critical")


def score_cable_size(field_name: str, expected: float, actual: float) -> FieldScore:
    """
    Score cable size - must be exact match.
    Standard sizes: 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240
    """
    return score_exact_match(field_name, expected, actual, priority="critical")


def score_circuit_type(field_name: str, expected: str, actual: str) -> FieldScore:
    """
    Score circuit type (lighting, power, dedicated, spare, sub_feed).
    """
    return score_text(field_name, expected, actual, priority="high")


# =============================================================================
# AGGREGATE SCORING
# =============================================================================

def calculate_weighted_score(scores: List[FieldScore]) -> float:
    """
    Calculate weighted average score based on priority.

    Weights:
        critical: 1.0
        high: 0.7
        medium: 0.4
        low: 0.1
    """
    weights = {
        "critical": 1.0,
        "high": 0.7,
        "medium": 0.4,
        "low": 0.1
    }

    if not scores:
        return 0.0

    total_weighted = 0.0
    total_weight = 0.0

    for score in scores:
        weight = weights.get(score.priority, 0.4)
        total_weighted += score.score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return total_weighted / total_weight


def calculate_section_scores(scores: List[FieldScore]) -> Dict[str, float]:
    """
    Group scores by section (based on field name prefix) and calculate averages.
    """
    sections = {
        "project": [],
        "db": [],
        "circuit": [],
        "cable": [],
        "totals": [],
        "other": []
    }

    for score in scores:
        name_lower = score.field_name.lower()

        if "project" in name_lower or "client" in name_lower or "consultant" in name_lower:
            sections["project"].append(score)
        elif "db_" in name_lower or "distribution" in name_lower:
            sections["db"].append(score)
        elif "circuit" in name_lower or "mcb" in name_lower or "cable" in name_lower:
            sections["circuit"].append(score)
        elif "feed" in name_lower or "incoming" in name_lower:
            sections["cable"].append(score)
        elif "total" in name_lower or "count" in name_lower:
            sections["totals"].append(score)
        else:
            sections["other"].append(score)

    section_scores = {}
    for section_name, section_list in sections.items():
        if section_list:
            section_scores[section_name] = calculate_weighted_score(section_list)

    return section_scores
