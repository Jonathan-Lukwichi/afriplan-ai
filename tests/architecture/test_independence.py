"""
Architectural enforcement of the independence rule (blueprint §0).

Pipelines do not share state. Pipelines do not call each other.

These tests grep the source tree to make that mechanically true.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DXF_DIR = REPO_ROOT / "agent" / "dxf_pipeline"
PDF_DIR = REPO_ROOT / "agent" / "pdf_pipeline"


def _python_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.rglob("*.py") if "__pycache__" not in p.parts]


# Match only real import statements, not occurrences inside docstrings/comments.
# Real statements start with optional whitespace, then 'import' or 'from'.
_IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+(\S+)")


def _imports_in(path: Path) -> list[tuple[int, str, str]]:
    """Return (lineno, full_line, imported_module) for every import in the file."""
    out: list[tuple[int, str, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = _IMPORT_LINE.match(line)
        if m:
            out.append((i, line.rstrip(), m.group(1)))
    return out


def test_dxf_pipeline_does_not_import_pdf_pipeline():
    bad: list[tuple[Path, int, str]] = []
    for path in _python_files(DXF_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.pdf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "DXF pipeline imports from PDF pipeline:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_pdf_pipeline_does_not_import_dxf_pipeline():
    if not PDF_DIR.exists():
        return  # PDF pipeline not built yet
    bad: list[tuple[Path, int, str]] = []
    for path in _python_files(PDF_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.dxf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "PDF pipeline imports from DXF pipeline:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_dxf_pipeline_does_not_import_llm_sdks():
    """Per blueprint §4.4 acceptance criterion 4."""
    forbidden_prefixes = ("anthropic", "openai", "google.generativeai", "groq")
    bad: list[tuple[Path, int, str]] = []
    for path in _python_files(DXF_DIR):
        for lineno, line, mod in _imports_in(path):
            if any(mod == p or mod.startswith(p + ".") for p in forbidden_prefixes):
                bad.append((path, lineno, line))
    assert not bad, "DXF pipeline imports an LLM SDK:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_pdf_pipeline_does_not_use_parse_json_safely():
    """
    Per blueprint §3.4 acceptance criterion 4: `parse_json_safely()` must
    not exist anywhere in agent/pdf_pipeline/. The PDF pipeline uses
    tool_use with strict schemas — there is no JSON-from-text parsing.
    """
    # Match `def parse_json_safely`, `parse_json_safely(...)` calls, or
    # imports — but NOT prose mentions in docstrings/comments.
    pat = re.compile(r"(?:def\s+parse_json_safely|parse_json_safely\s*\(|import\s+parse_json_safely|from\s+\S+\s+import\s+[^#\n]*\bparse_json_safely\b)")
    bad: list[tuple[Path, int, str]] = []
    for path in _python_files(PDF_DIR):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                bad.append((path, i, line))
    assert not bad, "PDF pipeline references parse_json_safely:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_neither_pipeline_imports_comparison_layer():
    """Comparison is read-only — pipelines must not import it."""
    bad: list[tuple[Path, int, str]] = []
    for pipeline_dir in (DXF_DIR, PDF_DIR):
        if not pipeline_dir.exists():
            continue
        for path in _python_files(pipeline_dir):
            for lineno, line, mod in _imports_in(path):
                if mod.startswith("agent.comparison"):
                    bad.append((path, lineno, line))
    assert not bad, "Pipeline imports comparison layer:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_shared_does_not_import_either_pipeline():
    """agent.shared must be a leaf — it cannot depend on pipeline code."""
    shared_dir = REPO_ROOT / "agent" / "shared"
    bad: list[tuple[Path, int, str]] = []
    for path in _python_files(shared_dir):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.pdf_pipeline") or mod.startswith("agent.dxf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "agent.shared imports a pipeline:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )
