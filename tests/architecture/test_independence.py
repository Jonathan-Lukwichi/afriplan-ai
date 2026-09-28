"""Architecture-enforcement tests, ported verbatim (mechanism unchanged) from
the original AfriPlan Streamlit app's tests/architecture/test_independence.py.

The one rule everything else derives from: pipelines do not share state,
pipelines do not call each other. This file grep-scans the source tree on
every run so the rule can never silently regress.
"""
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DXF_DIR = REPO_ROOT / "api" / "agent" / "dxf_pipeline"
PDF_DIR = REPO_ROOT / "api" / "agent" / "pdf_pipeline"
SHARED_DIR = REPO_ROOT / "api" / "agent" / "shared"

_IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+(\S+)")


def _python_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.rglob("*.py") if "__pycache__" not in p.parts]


def _imports_in(path: Path) -> list[tuple[int, str, str]]:
    """Return (lineno, full_line, imported_module) for every import in the file."""
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = _IMPORT_LINE.match(line)
        if m:
            out.append((i, line.rstrip(), m.group(1)))
    return out


def _format(bad: list[tuple[Path, int, str]]) -> str:
    return "\n".join(f"{p}:{n}: {line}" for p, n, line in bad)


def test_dxf_pipeline_does_not_import_pdf_pipeline():
    bad = []
    for path in _python_files(DXF_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.pdf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "DXF pipeline imports from PDF pipeline:\n" + _format(bad)


def test_pdf_pipeline_does_not_import_dxf_pipeline():
    if not PDF_DIR.exists():
        return
    bad = []
    for path in _python_files(PDF_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.dxf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "PDF pipeline imports from DXF pipeline:\n" + _format(bad)


def test_dxf_pipeline_does_not_import_llm_sdks():
    """Neither pipeline's determinism story survives an LLM import in the DXF path."""
    forbidden_prefixes = ("anthropic", "openai", "google.generativeai", "groq")
    bad = []
    for path in _python_files(DXF_DIR):
        for lineno, line, mod in _imports_in(path):
            if any(mod == p or mod.startswith(p + ".") for p in forbidden_prefixes):
                bad.append((path, lineno, line))
    assert not bad, "DXF pipeline imports an LLM SDK:\n" + _format(bad)


def test_pdf_pipeline_does_not_use_parse_json_safely():
    """
    The PDF pipeline uses tool_use with strict schemas — there is no
    JSON-from-text parsing anywhere in this package.
    """
    pat = re.compile(
        r"(?:def\s+parse_json_safely|parse_json_safely\s*\(|import\s+parse_json_safely"
        r"|from\s+\S+\s+import\s+[^#\n]*\bparse_json_safely\b)"
    )
    bad = []
    for path in _python_files(PDF_DIR):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                bad.append((path, i, line))
    assert not bad, "parse_json_safely found in pdf_pipeline:\n" + _format(bad)


def test_neither_pipeline_imports_comparison_layer():
    """Comparison is read-only — pipelines must not import it."""
    bad = []
    for pipeline_dir in (DXF_DIR, PDF_DIR):
        for path in _python_files(pipeline_dir):
            for lineno, line, mod in _imports_in(path):
                if mod.startswith("agent.comparison"):
                    bad.append((path, lineno, line))
    assert not bad, "A pipeline imports the comparison layer:\n" + _format(bad)


def test_shared_does_not_import_either_pipeline():
    """agent.shared must be a leaf — it cannot depend on pipeline code."""
    bad = []
    for path in _python_files(SHARED_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.startswith("agent.pdf_pipeline") or mod.startswith("agent.dxf_pipeline"):
                bad.append((path, lineno, line))
    assert not bad, "agent.shared imports pipeline code:\n" + _format(bad)


_READ_ONLY_LAYERS = ("evaluation", "audit", "sourcing", "ml", "routers", "db", "assist",   # assist: ADR-0007
                     "consolidate")                                                    # ADR-0008


def test_agent_package_does_not_import_read_only_layers():
    """evaluation/audit/sourcing/ml (and the web layer) read pipeline output; never the reverse."""
    bad = []
    for path in _python_files(REPO_ROOT / "api" / "agent"):
        for lineno, line, mod in _imports_in(path):
            if any(mod == p or mod.startswith(p + ".") for p in _READ_ONLY_LAYERS):
                bad.append((path, lineno, line))
    assert not bad, "api/agent imports a read-only layer:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_evaluation_and_audit_do_not_import_pipelines_or_llm_sdks():
    """The scorer must be independent of what it scores (ADR-0003/0006): no pipeline, no LLM."""
    forbidden = ("agent.pdf_pipeline", "agent.dxf_pipeline", "anthropic", "openai")
    bad = []
    for layer in ("evaluation", "audit"):
        for path in _python_files(REPO_ROOT / "api" / layer):
            for lineno, line, mod in _imports_in(path):
                if any(mod == p or mod.startswith(p + ".") for p in forbidden):
                    bad.append((path, lineno, line))
    assert not bad, "evaluation/audit import a pipeline or an LLM SDK:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )


def test_combining_calls_no_pipeline_and_no_llm_sdk():
    """ADR-0008: combining works on findings only; the AI matcher is injected from api/assist."""
    forbidden = ("agent.pdf_pipeline", "agent.dxf_pipeline", "anthropic", "openai", "assist")
    bad = []
    for path in _python_files(REPO_ROOT / "api" / "consolidate"):
        for lineno, line, mod in _imports_in(path):
            if any(mod == p or mod.startswith(p + ".") for p in forbidden):
                bad.append((path, lineno, line))
    assert not bad, "api/consolidate imports a pipeline, the assist layer or an LLM SDK:\n" + "\n".join(
        f"  {p}:{i}: {ln}" for p, i, ln in bad
    )
