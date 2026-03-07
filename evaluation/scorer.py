"""
scorer.py - Main scoring logic for comparing AI extraction to ground truth

This module takes an AI extraction result and a ground truth file,
compares them field by field, and returns a detailed score report.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .metrics import (
    FieldScore,
    score_exact_match,
    score_number,
    score_count,
    score_text,
    score_list_count,
    score_list_items,
    score_mcb_rating,
    score_cable_size,
    score_circuit_type,
    calculate_weighted_score,
    calculate_section_scores
)


@dataclass
class DocumentScore:
    """Complete score for one document"""
    document_id: str
    ground_truth_path: str
    field_scores: List[FieldScore] = field(default_factory=list)
    overall_score: float = 0.0
    section_scores: Dict[str, float] = field(default_factory=dict)
    critical_score: float = 0.0  # Score for critical fields only
    summary: Dict[str, Any] = field(default_factory=dict)


def load_ground_truth(path: str) -> Dict:
    """Load ground truth JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def score_document(ai_result: Dict, ground_truth: Dict) -> DocumentScore:
    """
    Compare AI extraction result to ground truth and return detailed scores.

    Args:
        ai_result: Dictionary from AI extraction (your pipeline output)
        ground_truth: Dictionary from ground_truth.json file

    Returns:
        DocumentScore with all field comparisons and aggregate scores
    """
    doc_id = ground_truth.get("document_id", "unknown")
    scores: List[FieldScore] = []

    # =========================================================================
    # SECTION 1: PROJECT INFO (Low priority - metadata)
    # =========================================================================
    gt_project = ground_truth.get("project_info", {})
    ai_project = ai_result.get("project_info", ai_result.get("metadata", {}))

    scores.append(score_text(
        "project_name",
        gt_project.get("project_name"),
        ai_project.get("project_name"),
        priority="low"
    ))

    scores.append(score_text(
        "consultant",
        gt_project.get("consultant"),
        ai_project.get("consultant"),
        priority="low"
    ))

    # =========================================================================
    # SECTION 2: DISTRIBUTION BOARDS (High priority)
    # =========================================================================
    gt_dbs = ground_truth.get("distribution_boards", [])
    ai_dbs = ai_result.get("distribution_boards",
                          ai_result.get("building_blocks", [{}])[0].get("distribution_boards", [])
                          if ai_result.get("building_blocks") else [])

    # DB count
    scores.append(score_count(
        "db_count",
        len(gt_dbs),
        len(ai_dbs),
        priority="critical"
    ))

    # DB names found
    gt_db_names = [db.get("name", "") for db in gt_dbs]
    ai_db_names = [db.get("name", "") for db in ai_dbs]

    scores.append(score_list_items(
        "db_names_found",
        gt_db_names,
        ai_db_names,
        priority="high"
    ))

    # Score each DB that exists in both
    for i, gt_db in enumerate(gt_dbs):
        gt_name = gt_db.get("name", f"DB_{i}")

        # Try to find matching DB in AI result
        ai_db = find_matching_db(gt_name, ai_dbs)

        if ai_db is None:
            # DB not found by AI
            scores.append(FieldScore(
                f"db_{gt_name}_found",
                gt_name, None, False, 0.0, "high",
                f"DB {gt_name} not found in extraction"
            ))
            continue

        # Score DB-level fields
        scores.extend(score_db(gt_name, gt_db, ai_db))

    # =========================================================================
    # SECTION 3: CABLES (High priority for main feeds)
    # =========================================================================
    gt_cables = ground_truth.get("cables", {})
    ai_cables = ai_result.get("cables", ai_result.get("site_cable_runs", []))

    # Main feeds
    gt_main_feeds = gt_cables.get("main_feeds", [])
    ai_main_feeds = ai_cables.get("main_feeds", []) if isinstance(ai_cables, dict) else ai_cables

    for i, gt_feed in enumerate(gt_main_feeds):
        ai_feed = ai_main_feeds[i] if i < len(ai_main_feeds) else {}

        scores.append(score_cable_size(
            f"main_feed_{i}_cable_size",
            gt_feed.get("cable_size_mm2"),
            ai_feed.get("cable_size_mm2")
        ))

    # =========================================================================
    # SECTION 4: TOTALS (Critical - these are the summary numbers)
    # =========================================================================
    gt_totals = ground_truth.get("totals", {})
    ai_totals = ai_result.get("totals", calculate_totals_from_extraction(ai_result))

    # Total DBs
    scores.append(score_count(
        "total_dbs",
        gt_totals.get("total_dbs", len(gt_dbs)),
        ai_totals.get("total_dbs", len(ai_dbs)),
        priority="critical"
    ))

    # Total circuits
    scores.append(score_count(
        "total_circuits",
        gt_totals.get("total_circuits"),
        ai_totals.get("total_circuits"),
        priority="critical"
    ))

    # Circuit breakdown
    for circuit_type in ["lighting", "power", "dedicated", "spare"]:
        gt_key = f"total_{circuit_type}_circuits"
        scores.append(score_count(
            gt_key,
            gt_totals.get(gt_key),
            ai_totals.get(gt_key),
            priority="high"
        ))

    # =========================================================================
    # CALCULATE AGGREGATE SCORES
    # =========================================================================

    # Filter out None scores
    valid_scores = [s for s in scores if s.expected is not None or s.actual is not None]

    # Overall weighted score
    overall_score = calculate_weighted_score(valid_scores)

    # Section scores
    section_scores = calculate_section_scores(valid_scores)

    # Critical fields only
    critical_scores = [s for s in valid_scores if s.priority == "critical"]
    critical_score = calculate_weighted_score(critical_scores) if critical_scores else 0.0

    # Summary stats
    correct_count = sum(1 for s in valid_scores if s.is_correct)
    summary = {
        "total_fields": len(valid_scores),
        "correct_fields": correct_count,
        "accuracy_percent": (correct_count / len(valid_scores) * 100) if valid_scores else 0,
        "critical_fields": len(critical_scores),
        "critical_correct": sum(1 for s in critical_scores if s.is_correct)
    }

    return DocumentScore(
        document_id=doc_id,
        ground_truth_path="",
        field_scores=valid_scores,
        overall_score=overall_score,
        section_scores=section_scores,
        critical_score=critical_score,
        summary=summary
    )


def score_db(db_name: str, gt_db: Dict, ai_db: Dict) -> List[FieldScore]:
    """Score all fields of a distribution board"""
    scores = []
    prefix = f"db_{db_name}"

    # Main breaker rating (CRITICAL)
    scores.append(score_mcb_rating(
        f"{prefix}_main_breaker",
        gt_db.get("main_breaker_a"),
        ai_db.get("main_breaker_a", ai_db.get("breaker_rating_a"))
    ))

    # Voltage/Phase
    scores.append(score_text(
        f"{prefix}_phase",
        gt_db.get("phase"),
        ai_db.get("phase", ai_db.get("voltage_phase")),
        priority="medium"
    ))

    # ELCB presence
    scores.append(score_exact_match(
        f"{prefix}_has_elcb",
        gt_db.get("has_elcb"),
        ai_db.get("has_elcb"),
        priority="critical"
    ))

    # Circuit count for this DB
    gt_circuits = gt_db.get("circuits", [])
    ai_circuits = ai_db.get("circuits", [])

    scores.append(score_count(
        f"{prefix}_circuit_count",
        len(gt_circuits),
        len(ai_circuits),
        priority="critical"
    ))

    # Score individual circuits
    scores.extend(score_circuits(prefix, gt_circuits, ai_circuits))

    return scores


def score_circuits(prefix: str, gt_circuits: List[Dict], ai_circuits: List[Dict]) -> List[FieldScore]:
    """Score circuit-level details"""
    scores = []

    # Count by type
    gt_types = count_circuit_types(gt_circuits)
    ai_types = count_circuit_types(ai_circuits)

    for ctype in ["lighting", "power", "dedicated", "spare"]:
        scores.append(score_count(
            f"{prefix}_{ctype}_count",
            gt_types.get(ctype, 0),
            ai_types.get(ctype, 0),
            priority="high"
        ))

    # Score individual circuit details (sample first 10 for performance)
    for i, gt_circuit in enumerate(gt_circuits[:10]):
        gt_name = gt_circuit.get("name", f"C{i}")
        ai_circuit = find_matching_circuit(gt_name, ai_circuits)

        if ai_circuit:
            # MCB rating
            scores.append(score_mcb_rating(
                f"{prefix}_cct_{gt_name}_mcb",
                gt_circuit.get("mcb_rating_a"),
                ai_circuit.get("mcb_rating_a", ai_circuit.get("mcb_a"))
            ))

            # Cable size
            scores.append(score_cable_size(
                f"{prefix}_cct_{gt_name}_cable",
                gt_circuit.get("cable_size_mm2"),
                ai_circuit.get("cable_size_mm2")
            ))

            # Circuit type
            scores.append(score_circuit_type(
                f"{prefix}_cct_{gt_name}_type",
                gt_circuit.get("type"),
                ai_circuit.get("type")
            ))

    return scores


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_matching_db(name: str, db_list: List[Dict]) -> Optional[Dict]:
    """Find a DB in the list by name (fuzzy match)"""
    name_norm = name.lower().strip().replace("-", "").replace("_", "")

    for db in db_list:
        db_name = db.get("name", "")
        db_norm = db_name.lower().strip().replace("-", "").replace("_", "")

        if name_norm == db_norm or name_norm in db_norm or db_norm in name_norm:
            return db

    return None


def find_matching_circuit(name: str, circuit_list: List[Dict]) -> Optional[Dict]:
    """Find a circuit in the list by name"""
    name_norm = name.lower().strip()

    for circuit in circuit_list:
        circuit_name = circuit.get("name", "")
        circuit_norm = circuit_name.lower().strip()

        if name_norm == circuit_norm:
            return circuit

    return None


def count_circuit_types(circuits: List[Dict]) -> Dict[str, int]:
    """Count circuits by type"""
    counts = {"lighting": 0, "power": 0, "dedicated": 0, "spare": 0, "sub_feed": 0, "other": 0}

    for circuit in circuits:
        ctype = circuit.get("type", "other").lower()
        if ctype in counts:
            counts[ctype] += 1
        else:
            counts["other"] += 1

    return counts


def calculate_totals_from_extraction(ai_result: Dict) -> Dict:
    """Calculate totals from AI extraction result (if not provided)"""
    totals = {
        "total_dbs": 0,
        "total_circuits": 0,
        "total_lighting_circuits": 0,
        "total_power_circuits": 0,
        "total_dedicated_circuits": 0,
        "total_spare_circuits": 0
    }

    # Try to find DBs in various locations
    dbs = ai_result.get("distribution_boards", [])

    if not dbs and ai_result.get("building_blocks"):
        for block in ai_result.get("building_blocks", []):
            dbs.extend(block.get("distribution_boards", []))

    totals["total_dbs"] = len(dbs)

    for db in dbs:
        circuits = db.get("circuits", [])
        totals["total_circuits"] += len(circuits)

        type_counts = count_circuit_types(circuits)
        totals["total_lighting_circuits"] += type_counts.get("lighting", 0)
        totals["total_power_circuits"] += type_counts.get("power", 0)
        totals["total_dedicated_circuits"] += type_counts.get("dedicated", 0)
        totals["total_spare_circuits"] += type_counts.get("spare", 0)

    return totals
