"""
run_benchmark.py - Run extraction benchmark on test documents

Usage:
    python -m evaluation.run_benchmark

This script:
1. Finds all test documents with ground truth files
2. Runs the AI extraction on each document
3. Scores the extraction against ground truth
4. Generates a summary report
"""

import sys
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.scorer import score_document, load_ground_truth, DocumentScore
from evaluation.report import print_document_report, print_summary_report, save_report_json, save_report_markdown


def find_test_documents(test_folder: str) -> List[Path]:
    """Find all test document folders that have ground truth files"""

    test_path = Path(test_folder)
    documents = []

    if not test_path.exists():
        print(f"Test folder not found: {test_folder}")
        return []

    for doc_folder in test_path.iterdir():
        if not doc_folder.is_dir():
            continue

        gt_file = doc_folder / "ground_truth.json"
        pdf_file = doc_folder / "original.pdf"

        if gt_file.exists():
            documents.append(doc_folder)
            print(f"  Found: {doc_folder.name}")
        else:
            print(f"  Skip (no ground truth): {doc_folder.name}")

    return documents


def run_benchmark(
    test_folder: str = "evaluation/test_documents",
    extraction_function: Optional[Callable] = None,
    save_results: bool = True
) -> List[DocumentScore]:
    """
    Run extraction benchmark on all test documents.

    Args:
        test_folder: Path to test documents folder
        extraction_function: Function that takes (pdf_bytes, filename) and returns extraction dict
                           If None, uses mock extraction for testing the scoring system
        save_results: Whether to save results to files

    Returns:
        List of DocumentScore objects
    """

    print("\n" + "=" * 60)
    print("  STARTING BENCHMARK")
    print("=" * 60)
    print(f"\n  Test folder: {test_folder}\n")

    # Find test documents
    print("  Scanning for test documents...")
    doc_folders = find_test_documents(test_folder)

    if not doc_folders:
        print("\n  No test documents found with ground truth files.")
        print("  Create ground_truth.json in each test document folder.")
        return []

    print(f"\n  Found {len(doc_folders)} documents to test\n")

    all_scores = []

    for doc_folder in doc_folders:
        doc_id = doc_folder.name
        gt_path = doc_folder / "ground_truth.json"
        pdf_path = doc_folder / "original.pdf"

        print(f"\n  Testing: {doc_id}")
        print("  " + "-" * 40)

        # Load ground truth
        try:
            ground_truth = load_ground_truth(str(gt_path))
        except Exception as e:
            print(f"  Error loading ground truth: {e}")
            continue

        # Run extraction (or use mock)
        if extraction_function is not None and pdf_path.exists():
            print("  Running AI extraction...")
            try:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                ai_result = extraction_function(pdf_bytes, doc_id)
            except Exception as e:
                print(f"  Extraction error: {e}")
                ai_result = {}
        else:
            # Use mock extraction for testing the scoring system
            print("  Using mock extraction (no extraction function provided)")
            ai_result = create_mock_extraction(ground_truth)

        # Score the extraction
        doc_score = score_document(ai_result, ground_truth)
        doc_score.ground_truth_path = str(gt_path)

        all_scores.append(doc_score)

        # Print quick result
        print(f"  Overall Score: {doc_score.overall_score:.1%}")
        print(f"  Critical Score: {doc_score.critical_score:.1%}")

    # Generate reports
    print("\n" + "=" * 60)
    print_summary_report(all_scores)

    # Save results
    if save_results and all_scores:
        results_folder = Path(test_folder).parent / "results"
        results_folder.mkdir(exist_ok=True)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = results_folder / f"benchmark_{timestamp}.json"
        save_report_json(all_scores, str(json_path))

        # Save Markdown
        md_path = results_folder / f"benchmark_{timestamp}.md"
        save_report_markdown(all_scores, str(md_path))

    return all_scores


def create_mock_extraction(ground_truth: Dict) -> Dict:
    """
    Create a mock extraction result for testing the scoring system.
    Simulates ~70% accuracy by introducing some errors.
    """
    import random
    import copy

    # Start with a copy of ground truth
    mock = copy.deepcopy(ground_truth)

    # Introduce some errors to simulate real extraction

    # 1. Miss some DBs (remove 20% randomly)
    if "distribution_boards" in mock and mock["distribution_boards"]:
        dbs = mock["distribution_boards"]
        num_to_remove = max(1, len(dbs) // 5)
        for _ in range(num_to_remove):
            if len(dbs) > 1:
                dbs.pop(random.randint(0, len(dbs) - 1))

    # 2. Modify some circuit counts (add/remove circuits)
    for db in mock.get("distribution_boards", []):
        circuits = db.get("circuits", [])

        # Remove some circuits
        if circuits and random.random() < 0.3:
            circuits.pop(random.randint(0, len(circuits) - 1))

        # Modify some MCB ratings (wrong by one step)
        for circuit in circuits:
            if random.random() < 0.2:
                current = circuit.get("mcb_rating_a")
                if current:
                    # Change to adjacent size
                    mcb_sizes = [6, 10, 16, 20, 25, 32, 40, 50, 63]
                    if current in mcb_sizes:
                        idx = mcb_sizes.index(current)
                        new_idx = max(0, min(len(mcb_sizes) - 1, idx + random.choice([-1, 1])))
                        circuit["mcb_rating_a"] = mcb_sizes[new_idx]

    # 3. Adjust totals to reflect changes
    total_circuits = 0
    for db in mock.get("distribution_boards", []):
        total_circuits += len(db.get("circuits", []))

    if "totals" in mock:
        mock["totals"]["total_circuits"] = total_circuits
        mock["totals"]["total_dbs"] = len(mock.get("distribution_boards", []))

    return mock


def run_with_real_extraction():
    """
    Run benchmark with actual AI extraction pipeline.
    """
    try:
        from evaluation.pipeline_adapter import run_extraction, check_api_keys

        # Check if API keys are configured
        has_key, provider = check_api_keys()
        if not has_key:
            print("\n[!] No API key configured!")
            print("    Set one of these environment variables:")
            print("    - GROQ_API_KEY (FREE)")
            print("    - XAI_API_KEY")
            print("    - GEMINI_API_KEY")
            print("    - ANTHROPIC_API_KEY")
            print("\n    Running with mock extraction instead...")
            run_benchmark()
            return

        print(f"\n[OK] Using {provider} for extraction\n")

        # Run with real extraction
        run_benchmark(extraction_function=run_extraction, save_results=True)

    except ImportError as e:
        print(f"Could not import extraction function: {e}")
        print("Running with mock extraction...")
        run_benchmark()


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run extraction benchmark")
    parser.add_argument("--test-folder", default="evaluation/test_documents",
                       help="Path to test documents folder")
    parser.add_argument("--mock", action="store_true",
                       help="Use mock extraction (for testing scoring system)")
    parser.add_argument("--real", action="store_true",
                       help="Use REAL AI extraction pipeline")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save results to files")
    parser.add_argument("--detailed", action="store_true",
                       help="Print detailed per-document reports")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  AFRIPLAN EXTRACTION BENCHMARK")
    print("=" * 60)

    if args.real:
        # Use actual AI extraction
        run_with_real_extraction()
    else:
        # Use mock or no extraction
        scores = run_benchmark(
            test_folder=args.test_folder,
            extraction_function=None,  # Mock extraction
            save_results=not args.no_save
        )

        if args.detailed:
            for doc_score in scores:
                print_document_report(doc_score)
