"""
Stage P2 — Classify.

Haiku 4.5 looks at each rasterised page and returns one PageClassification.
Tool call is forced (`tool_choice: {type: "tool", name: "classify_page"}`)
so the model can't free-form. Result + cost are aggregated into a list.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from agent.pdf_pipeline.llm import PdfLLM
from agent.pdf_pipeline.models import PageClassification, PageType, StageCost
from agent.pdf_pipeline.prompts.page_prompts import CLASSIFY_PROMPT
from agent.pdf_pipeline.prompts.tool_schemas import CLASSIFY_PAGE_TOOL
from agent.pdf_pipeline.stages.ingest import IngestedPage
from core.config import HAIKU_4_5

log = logging.getLogger(__name__)


def classify_pages(
    llm: PdfLLM,
    pages: List[IngestedPage],
) -> Tuple[List[PageClassification], List[StageCost]]:
    classifications: List[PageClassification] = []
    costs: List[StageCost] = []

    for page in pages:
        result = llm.call_with_tool(
            model=HAIKU_4_5,
            user_text=CLASSIFY_PROMPT,
            page_image_b64=page.image_b64,
            tools=[CLASSIFY_PAGE_TOOL],
            forced_tool_name="classify_page",
            stage_name=f"classify:p{page.page_index}",
            max_tokens=512,
        )
        try:
            page_type = PageType(result.tool_input.get("page_type", "unknown"))
        except ValueError:
            page_type = PageType.UNKNOWN

        classifications.append(
            PageClassification(
                page_index=page.page_index,
                page_type=page_type,
                confidence=float(result.tool_input.get("confidence", 0.0)),
                rationale=str(result.tool_input.get("rationale", "")),
            )
        )
        costs.append(result.cost)

    return classifications, costs
