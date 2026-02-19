"""
CLASSIFY Stage: Fast tier classification.

Determines the service tier (Residential/Commercial/Industrial/Maintenance/Mixed)
and identifies building blocks present in the documents.

Supports multiple LLM providers:
- xAI Grok (grok-2-vision) - $25 free credits/month
- Google Gemini (gemini-2.0-flash) - FREE
- Anthropic Claude (claude-haiku-4-5) - paid
"""

import json
from typing import Tuple, Optional, List

from agent.models import (
    DocumentSet, ServiceTier, ExtractionMode, StageResult, PipelineStage,
    PageType
)
from agent.utils import parse_json_safely, Timer, estimate_cost_zar
from agent.prompts.schemas import CLASSIFY_SCHEMA, CONFIDENCE_INSTRUCTION

# Classification models by provider
CLASSIFY_MODELS = {
    "claude": "claude-haiku-4-5-20251001",
    "gemini": "gemini-2.0-flash",  # Current recommended model
    "grok": "grok-2-vision-1212",  # Grok with vision support
}
CLASSIFY_MODEL = CLASSIFY_MODELS["claude"]  # Default for backwards compatibility


CLASSIFY_PROMPT = """You are an expert South African electrical engineer analyzing electrical drawings.

Classify this project based on the document pages provided.

Return JSON with:
- "tier": One of "RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "MAINTENANCE", "MIXED"
- "mode": One of "AS_BUILT" (has SLD drawings), "ESTIMATION" (no SLDs), "INSPECTION" (COC/maintenance)
- "building_blocks": List of distinct buildings/blocks identified
- "reasoning": Brief explanation of your classification
- "confidence": 0.0 to 1.0

Classification rules:
- RESIDENTIAL: Houses, flats, domestic installations
- COMMERCIAL: Offices, retail, hospitality, schools, healthcare, recreational clubs
- INDUSTRIAL: Factories, plants, heavy machinery, manufacturing
- MAINTENANCE: COC inspections, repairs, DB upgrades, rewiring
- MIXED: Multiple building types in one project (e.g., offices + pool + community hall)

Example response:
""" + CLASSIFY_SCHEMA


def classify(
    doc_set: DocumentSet,
    client: Optional[object] = None,  # Anthropic, Gemini, or Grok client
    provider: str = "claude",  # "claude", "gemini", or "grok"
) -> Tuple[ServiceTier, ExtractionMode, List[str], float, StageResult]:
    """
    CLASSIFY stage: Determine project tier and extraction mode.

    Args:
        doc_set: Processed documents from INGEST stage
        client: API client (Anthropic, Gemini, or Grok)
        provider: LLM provider name ("claude", "gemini", or "grok")

    Returns:
        Tuple of (tier, mode, building_blocks, confidence, StageResult)
    """
    with Timer("classify") as timer:
        errors = []
        warnings = []
        tokens_used = 0
        cost_zar = 0.0

        # Gather text content from all pages for classification
        all_text = []
        for doc in doc_set.documents:
            all_text.append(f"Document: {doc.filename}")
            for page in doc.pages:
                if page.text_content:
                    all_text.append(f"Page {page.page_number}: {page.text_content[:500]}")

        combined_text = "\n".join(all_text)[:8000]  # Limit context

        # Try API classification
        tier = ServiceTier.UNKNOWN
        mode = ExtractionMode.ESTIMATION
        building_blocks = doc_set.building_blocks_detected.copy()
        confidence = 0.5
        model_used = CLASSIFY_MODELS.get(provider, CLASSIFY_MODEL)

        if client:
            try:
                prompt_text = f"{CLASSIFY_PROMPT}\n\nDocument content:\n{combined_text}"

                if provider == "grok":
                    # Grok API call (OpenAI-compatible)
                    response = client.chat.completions.create(
                        model="grok-2-vision-1212",
                        max_tokens=1024,
                        temperature=0.1,
                        messages=[{"role": "user", "content": prompt_text}]
                    )
                    response_text = response.choices[0].message.content
                    tokens_used = response.usage.total_tokens if response.usage else 0
                    cost_zar = 0.0  # Grok has free credits!
                elif provider == "gemini":
                    # Gemini API call
                    model = client.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(
                        prompt_text,
                        generation_config={"max_output_tokens": 1024, "temperature": 0.1}
                    )
                    response_text = response.text
                    tokens_used = getattr(response.usage_metadata, 'total_token_count', 0) if hasattr(response, 'usage_metadata') else 0
                    cost_zar = 0.0  # Gemini free tier!
                else:
                    # Claude API call (default)
                    response = client.messages.create(
                        model=model_used,
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt_text}]
                    )
                    response_text = response.content[0].text
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                    cost_zar = estimate_cost_zar(model_used, response.usage.input_tokens, response.usage.output_tokens)

                # Parse response
                parsed = parse_json_safely(response_text)
                if parsed:
                    tier_str = parsed.get("tier", "UNKNOWN").upper()
                    tier = _parse_tier(tier_str)

                    mode_str = parsed.get("mode", "ESTIMATION").upper()
                    mode = _parse_mode(mode_str)

                    building_blocks = parsed.get("building_blocks", building_blocks)
                    confidence = float(parsed.get("confidence", 0.7))

            except Exception as e:
                errors.append(f"API classification failed: {str(e)}")
                warnings.append("Falling back to heuristic classification")

        # Fallback classification based on document content
        if tier == ServiceTier.UNKNOWN:
            tier, mode, confidence = _fallback_classify(doc_set, combined_text)

        # Determine extraction mode from document types
        if doc_set.num_sld_pages > 0:
            mode = ExtractionMode.AS_BUILT
        elif "coc" in combined_text.lower() or "inspection" in combined_text.lower():
            mode = ExtractionMode.INSPECTION

        # Build stage result
        result = StageResult(
            stage=PipelineStage.CLASSIFY,
            success=tier != ServiceTier.UNKNOWN,
            confidence=confidence,
            data={
                "tier": tier.value,
                "mode": mode.value,
                "building_blocks": building_blocks,
            },
            model_used=model_used if client else None,
            tokens_used=tokens_used,
            cost_zar=cost_zar,
            processing_time_ms=timer.elapsed_ms,
            errors=errors,
            warnings=warnings,
        )

        return tier, mode, building_blocks, confidence, result


def _parse_tier(tier_str: str) -> ServiceTier:
    """Parse tier string to enum."""
    mapping = {
        "RESIDENTIAL": ServiceTier.RESIDENTIAL,
        "COMMERCIAL": ServiceTier.COMMERCIAL,
        "INDUSTRIAL": ServiceTier.INDUSTRIAL,
        "MAINTENANCE": ServiceTier.MAINTENANCE,
        "MIXED": ServiceTier.MIXED,
    }
    return mapping.get(tier_str, ServiceTier.UNKNOWN)


def _parse_mode(mode_str: str) -> ExtractionMode:
    """Parse mode string to enum."""
    mapping = {
        "AS_BUILT": ExtractionMode.AS_BUILT,
        "ESTIMATION": ExtractionMode.ESTIMATION,
        "INSPECTION": ExtractionMode.INSPECTION,
        "HYBRID": ExtractionMode.HYBRID,
    }
    return mapping.get(mode_str, ExtractionMode.ESTIMATION)


def _fallback_classify(
    doc_set: DocumentSet,
    text_content: str,
) -> Tuple[ServiceTier, ExtractionMode, float]:
    """
    Fallback classification using keywords and document structure.
    Used when API is unavailable.
    """
    text_lower = text_content.lower()

    # Keyword scoring
    scores = {
        ServiceTier.RESIDENTIAL: 0,
        ServiceTier.COMMERCIAL: 0,
        ServiceTier.INDUSTRIAL: 0,
        ServiceTier.MAINTENANCE: 0,
        ServiceTier.MIXED: 0,
    }

    # Residential keywords
    residential_kw = ["house", "flat", "apartment", "domestic", "bedroom", "kitchen", "bathroom", "geyser"]
    scores[ServiceTier.RESIDENTIAL] = sum(1 for k in residential_kw if k in text_lower)

    # Commercial keywords
    commercial_kw = ["office", "retail", "shop", "restaurant", "hotel", "school", "hospital",
                     "clinic", "reception", "boardroom", "pool", "club", "recreational"]
    scores[ServiceTier.COMMERCIAL] = sum(1 for k in commercial_kw if k in text_lower)

    # Industrial keywords
    industrial_kw = ["factory", "plant", "machine", "motor", "vsd", "conveyor", "compressor",
                     "production", "warehouse", "manufacturing"]
    scores[ServiceTier.INDUSTRIAL] = sum(1 for k in industrial_kw if k in text_lower)

    # Maintenance keywords
    maintenance_kw = ["coc", "certificate", "compliance", "inspection", "defect", "repair",
                      "rewire", "upgrade", "existing", "fault"]
    scores[ServiceTier.MAINTENANCE] = sum(1 for k in maintenance_kw if k in text_lower)

    # Check for mixed use
    non_zero_scores = sum(1 for s in scores.values() if s > 2)
    if non_zero_scores >= 2:
        scores[ServiceTier.MIXED] = max(scores.values()) + 1

    # Get highest scoring tier
    best_tier = max(scores, key=scores.get)
    best_score = scores[best_tier]

    # Calculate confidence based on score distinctiveness
    total_score = sum(scores.values())
    confidence = best_score / total_score if total_score > 0 else 0.3
    confidence = min(0.8, max(0.3, confidence))  # Clamp between 0.3 and 0.8

    # Determine mode
    if doc_set.num_sld_pages > 0:
        mode = ExtractionMode.AS_BUILT
    elif best_tier == ServiceTier.MAINTENANCE:
        mode = ExtractionMode.INSPECTION
    else:
        mode = ExtractionMode.ESTIMATION

    return best_tier, mode, confidence
