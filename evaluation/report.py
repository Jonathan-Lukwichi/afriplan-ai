"""
report.py - Generate readable reports from scoring results

Outputs reports to console and/or files.
"""

import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from .scorer import DocumentScore
from .metrics import FieldScore


def print_document_report(doc_score: DocumentScore):
    """Print a detailed report for one document"""

    print("\n" + "=" * 70)
    print(f"  SCORING REPORT: {doc_score.document_id}")
    print("=" * 70)

    # Overall scores
    print(f"\n  Overall Score:    {doc_score.overall_score:.1%}")
    print(f"  Critical Score:   {doc_score.critical_score:.1%}")
    print(f"  Fields Checked:   {doc_score.summary.get('total_fields', 0)}")
    print(f"  Fields Correct:   {doc_score.summary.get('correct_fields', 0)}")

    # Section breakdown
    print("\n" + "-" * 40)
    print("  SCORE BY SECTION")
    print("-" * 40)

    for section, score in doc_score.section_scores.items():
        bar = create_bar(score, 20)
        emoji = get_score_emoji(score)
        print(f"  {emoji} {section:15} {bar} {score:.0%}")

    # Critical fields detail
    print("\n" + "-" * 40)
    print("  CRITICAL FIELDS")
    print("-" * 40)

    critical_fields = [f for f in doc_score.field_scores if f.priority == "critical"]
    for field in critical_fields:
        status = "PASS" if field.is_correct else "FAIL"
        emoji = "[OK]" if field.is_correct else "[X]"
        print(f"  {emoji} {field.field_name:30} {status}")
        if not field.is_correct:
            print(f"       Expected: {field.expected}")
            print(f"       Got:      {field.actual}")

    # Worst performing fields
    print("\n" + "-" * 40)
    print("  FIELDS TO IMPROVE (Lowest Scores)")
    print("-" * 40)

    worst_fields = sorted(doc_score.field_scores, key=lambda x: x.score)[:10]
    for field in worst_fields:
        if field.score < 1.0:
            print(f"  [{field.score:.0%}] {field.field_name}")
            if field.notes:
                print(f"        Note: {field.notes}")

    print("\n" + "=" * 70 + "\n")


def print_summary_report(all_scores: List[DocumentScore]):
    """Print a summary report across all documents"""

    if not all_scores:
        print("No documents scored.")
        return

    print("\n" + "=" * 70)
    print("           EXTRACTION ACCURACY BENCHMARK REPORT")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Documents Tested: {len(all_scores)}")

    # Overall averages
    avg_overall = sum(s.overall_score for s in all_scores) / len(all_scores)
    avg_critical = sum(s.critical_score for s in all_scores) / len(all_scores)

    print(f"\n  Average Overall Score:  {avg_overall:.1%}")
    print(f"  Average Critical Score: {avg_critical:.1%}")

    # Per-document scores
    print("\n" + "-" * 50)
    print("  PER-DOCUMENT SCORES")
    print("-" * 50)

    for doc_score in all_scores:
        bar = create_bar(doc_score.overall_score, 15)
        emoji = get_score_emoji(doc_score.overall_score)
        print(f"  {emoji} {doc_score.document_id:25} {bar} {doc_score.overall_score:.0%}")

    # Section averages
    print("\n" + "-" * 50)
    print("  AVERAGE SCORE BY SECTION")
    print("-" * 50)

    section_totals = {}
    section_counts = {}

    for doc_score in all_scores:
        for section, score in doc_score.section_scores.items():
            section_totals[section] = section_totals.get(section, 0) + score
            section_counts[section] = section_counts.get(section, 0) + 1

    for section in section_totals:
        avg = section_totals[section] / section_counts[section]
        bar = create_bar(avg, 20)
        emoji = get_score_emoji(avg)
        print(f"  {emoji} {section:15} {bar} {avg:.0%}")

    # Recommendations
    print("\n" + "-" * 50)
    print("  RECOMMENDATIONS")
    print("-" * 50)

    if avg_critical < 0.7:
        print("  [!] CRITICAL: Focus on improving circuit/DB extraction")
    if avg_overall < 0.5:
        print("  [!] Overall accuracy is low - review extraction prompts")

    # Find most common failures
    failure_counts = {}
    for doc_score in all_scores:
        for field in doc_score.field_scores:
            if not field.is_correct:
                # Extract field category
                parts = field.field_name.split("_")
                category = parts[0] if parts else "other"
                failure_counts[category] = failure_counts.get(category, 0) + 1

    if failure_counts:
        worst_category = max(failure_counts, key=failure_counts.get)
        print(f"  [!] Most failures in: {worst_category} ({failure_counts[worst_category]} failures)")

    print("\n" + "=" * 70 + "\n")


def create_bar(score: float, width: int = 20) -> str:
    """Create a text progress bar"""
    filled = int(score * width)
    empty = width - filled
    return "[" + "#" * filled + "-" * empty + "]"


def get_score_emoji(score: float) -> str:
    """Get status indicator based on score"""
    if score >= 0.9:
        return "[OK]"
    elif score >= 0.7:
        return "[~]"
    elif score >= 0.5:
        return "[!]"
    else:
        return "[X]"


def save_report_json(all_scores: List[DocumentScore], output_path: str):
    """Save detailed results to JSON file"""

    results = {
        "timestamp": datetime.now().isoformat(),
        "document_count": len(all_scores),
        "average_overall": sum(s.overall_score for s in all_scores) / len(all_scores) if all_scores else 0,
        "average_critical": sum(s.critical_score for s in all_scores) / len(all_scores) if all_scores else 0,
        "documents": []
    }

    for doc_score in all_scores:
        doc_result = {
            "document_id": doc_score.document_id,
            "overall_score": doc_score.overall_score,
            "critical_score": doc_score.critical_score,
            "section_scores": doc_score.section_scores,
            "summary": doc_score.summary,
            "field_details": [
                {
                    "field": f.field_name,
                    "expected": str(f.expected),
                    "actual": str(f.actual),
                    "score": f.score,
                    "priority": f.priority,
                    "correct": f.is_correct
                }
                for f in doc_score.field_scores
            ]
        }
        results["documents"].append(doc_result)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_path}")


def save_report_markdown(all_scores: List[DocumentScore], output_path: str):
    """Save summary report as Markdown file"""

    lines = []
    lines.append("# Extraction Accuracy Benchmark Report\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**Documents Tested:** {len(all_scores)}\n\n")

    if all_scores:
        avg_overall = sum(s.overall_score for s in all_scores) / len(all_scores)
        avg_critical = sum(s.critical_score for s in all_scores) / len(all_scores)

        lines.append("## Summary\n")
        lines.append(f"| Metric | Score |\n")
        lines.append(f"|--------|-------|\n")
        lines.append(f"| Average Overall | {avg_overall:.1%} |\n")
        lines.append(f"| Average Critical | {avg_critical:.1%} |\n\n")

        lines.append("## Per-Document Scores\n")
        lines.append("| Document | Overall | Critical | Status |\n")
        lines.append("|----------|---------|----------|--------|\n")

        for doc_score in all_scores:
            status = "Pass" if doc_score.overall_score >= 0.7 else "Needs Work"
            lines.append(f"| {doc_score.document_id} | {doc_score.overall_score:.1%} | {doc_score.critical_score:.1%} | {status} |\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Markdown report saved to: {output_path}")
