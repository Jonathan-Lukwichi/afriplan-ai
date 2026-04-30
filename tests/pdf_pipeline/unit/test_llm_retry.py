"""Tests for the LLM wrapper's retry-with-feedback and escalation logic."""

import pytest

from agent.pdf_pipeline.llm import LLMError, PdfLLM
from agent.pdf_pipeline.prompts.tool_schemas import EXTRACT_SLD_TOOL
from core.config import OPUS_4_6, SONNET_4_5


def test_first_attempt_success(mock_llm):
    """When the mock returns a valid response, no retry happens."""
    llm = mock_llm(tool_responses={
        "extract_sld": {"distribution_boards": [], "extraction_warnings": []}
    })
    result = llm.call_with_tool(
        model=SONNET_4_5,
        user_text="Extract SLD",
        page_image_b64="aGVsbG8=",
        tools=[EXTRACT_SLD_TOOL],
        forced_tool_name="extract_sld",
        stage_name="test",
    )
    assert result.tool_input["distribution_boards"] == []
    assert result.cost.retry_count == 0


def test_retry_on_validation_failure(mock_llm):
    """First call returns invalid shape; retry returns valid → success on attempt 2."""
    from typing import List
    from pydantic import BaseModel

    class StrictExtractSld(BaseModel):
        distribution_boards: List[dict]

    def planner(kwargs, call_idx):
        if call_idx == 1:
            return {"distribution_boards": "garbage"}      # not a list → fails validator
        return {"distribution_boards": []}                  # valid → passes

    llm = mock_llm(tool_responses={"extract_sld": planner})

    result = llm.call_with_tool(
        model=SONNET_4_5,
        user_text="Extract SLD",
        page_image_b64="aGVsbG8=",
        tools=[EXTRACT_SLD_TOOL],
        forced_tool_name="extract_sld",
        stage_name="test",
        validator=StrictExtractSld,
        retries=1,
    )
    assert result.cost.retry_count == 1
    assert result.tool_input["distribution_boards"] == []


def test_escalation_on_repeated_failure(mock_llm):
    """If validator keeps failing, escalation to higher model is invoked."""
    from pydantic import BaseModel

    class StrictSchema(BaseModel):
        required_field: str

    # Mock returns a tool_input that won't satisfy StrictSchema
    llm = mock_llm(tool_responses={"extract_sld": {"unrelated": True}})

    with pytest.raises(LLMError) as exc:
        llm.call_with_tool(
            model=SONNET_4_5,
            user_text="...",
            page_image_b64="aGVsbG8=",
            tools=[EXTRACT_SLD_TOOL],
            forced_tool_name="extract_sld",
            stage_name="test",
            validator=StrictSchema,
            retries=1,
            escalate_to=OPUS_4_6,
        )
    assert "failed to produce a schema-valid tool call" in str(exc.value)


def test_no_tool_call_returns_retry_message(mock_llm):
    """If the response has no tool_use block, retry is triggered with feedback."""
    from dataclasses import dataclass, field
    from typing import Any, Dict, List

    @dataclass
    class _Usage:
        input_tokens: int = 100
        output_tokens: int = 50
        cache_read_input_tokens: int = 0
        cache_creation_input_tokens: int = 0

    @dataclass
    class _Block:
        type: str
        name: str
        input: Dict[str, Any]
        id: str = "toolu_test"

    @dataclass
    class _Response:
        content: List[Any]
        usage: _Usage = field(default_factory=_Usage)
        stop_reason: str = "tool_use"

    class NoToolMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                return _Response(content=[])               # no tool_use block
            return _Response(
                content=[_Block(type="tool_use", name="extract_sld",
                                input={"distribution_boards": []})],
            )

    class NoToolClient:
        def __init__(self):
            self.messages = NoToolMessages()

    llm = PdfLLM(system_prompt="TEST", client=NoToolClient())
    result = llm.call_with_tool(
        model=SONNET_4_5,
        user_text="X",
        page_image_b64="aGVsbG8=",
        tools=[EXTRACT_SLD_TOOL],
        forced_tool_name="extract_sld",
        stage_name="test",
    )
    assert result.cost.retry_count == 1
