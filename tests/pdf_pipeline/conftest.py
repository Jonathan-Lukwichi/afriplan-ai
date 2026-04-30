"""
PDF pipeline test fixtures.

Provides:
  - synthetic_pdf_bytes: a real PDF with a few text pages so PyMuPDF can
    rasterise it without us needing fixture files on disk
  - MockAnthropic: a stand-in for anthropic.Anthropic that returns
    canned tool_use responses keyed by which tool was forced

This conftest deliberately does NOT import from tests/dxf_pipeline —
the blueprint's independence rule forbids cross-pipeline test coupling.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import fitz  # PyMuPDF
import pytest

from agent.pdf_pipeline.llm import PdfLLM


# ─── Synthetic PDF builder ────────────────────────────────────────────

def _build_pdf(page_titles: List[str]) -> bytes:
    """Build a small valid PDF with one text-only page per title."""
    doc = fitz.open()
    for title in page_titles:
        page = doc.new_page(width=595, height=842)  # A4 in points
        page.insert_text((50, 100), title, fontsize=24)
        page.insert_text((50, 150), "AfriPlan synthetic test page", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def synthetic_pdf_bytes() -> bytes:
    """Tiny 3-page PDF: cover, SLD, lighting layout."""
    return _build_pdf([
        "Project Cover Sheet",
        "Distribution Board DB-MAIN — Single Line Diagram",
        "Ground Floor Lighting Layout",
    ])


@pytest.fixture
def two_page_pdf_bytes() -> bytes:
    return _build_pdf([
        "Cover",
        "Distribution Board DB-MAIN — Single Line Diagram",
    ])


# ─── MockAnthropic ────────────────────────────────────────────────────

@dataclass
class _MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _MockToolUseBlock:
    type: str
    name: str
    input: Dict[str, Any]
    id: str = "toolu_test"


@dataclass
class _MockResponse:
    content: List[Any]
    usage: _MockUsage = field(default_factory=_MockUsage)
    stop_reason: str = "tool_use"
    model: str = "claude-test"


class MockMessages:
    """Messages.create — returns canned tool_use responses."""

    def __init__(
        self,
        *,
        tool_responses: Dict[str, Any] = None,
        on_call: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self._tool_responses = tool_responses or {}
        self.calls: List[Dict[str, Any]] = []
        self._on_call = on_call

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._on_call is not None:
            self._on_call(kwargs)

        # Determine which tool was forced
        tool_choice = kwargs.get("tool_choice") or {}
        forced_name = tool_choice.get("name") if isinstance(tool_choice, dict) else None

        # Look up canned response
        resp = self._tool_responses.get(forced_name)
        if resp is None:
            # Default: empty schema-valid response per tool name
            resp = _default_tool_response(forced_name, kwargs.get("tools") or [])

        # If response is a callable, invoke with kwargs (allows simulating
        # validation failures on first call, success on retry).
        if callable(resp):
            resp = resp(kwargs, len([c for c in self.calls if c.get("tool_choice") == tool_choice]))

        block = _MockToolUseBlock(type="tool_use", name=forced_name or "unknown", input=resp)
        return _MockResponse(content=[block])


class MockAnthropic:
    """Drop-in replacement for anthropic.Anthropic in tests."""

    def __init__(self, **kwargs):
        self.messages = MockMessages(**kwargs)


def _default_tool_response(tool_name: Optional[str], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a minimal schema-valid response for the given tool."""
    if tool_name == "classify_page":
        return {"page_type": "unknown", "confidence": 0.5, "rationale": "mock"}
    if tool_name == "extract_sld":
        return {"distribution_boards": [], "extraction_warnings": []}
    if tool_name == "extract_lighting_layout":
        return {"rooms": [], "extraction_warnings": []}
    if tool_name == "extract_plugs_layout":
        return {"rooms": [], "extraction_warnings": []}
    if tool_name == "extract_schedule":
        return {"rows": [], "extraction_warnings": []}
    if tool_name == "extract_notes":
        return {"notes": []}
    return {}


# ─── Fixture: a fully primed mock LLM ─────────────────────────────────

@pytest.fixture
def mock_llm():
    """Returns a builder you can configure with per-tool responses."""
    def build(tool_responses=None, on_call=None) -> PdfLLM:
        client = MockAnthropic(tool_responses=tool_responses, on_call=on_call)
        return PdfLLM(system_prompt="TEST SYSTEM PROMPT", client=client)
    return build
