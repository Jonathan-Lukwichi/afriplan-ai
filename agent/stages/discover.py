"""
DISCOVER Stage: JSON extraction using Vision LLMs.

Extracts structured electrical data from drawings including:
- Distribution boards and circuits from SLDs
- Fixture counts from lighting layouts
- Socket/switch counts from plug layouts
- Site cable runs from outside lights drawings

v4.4 additions (Wedela Lighting & Plugs PDF):
- Pool lighting: pool_flood_light, pool_underwater_light
- Legend totals validation (_validate_against_legend)
- Enhanced fixture type support

v4.5 additions (Universal Electrical Project Schema):
- System parameters extraction (voltage, phases, frequency, fault levels)
- Breaker type distinction (MCB vs MCCB vs ACB)
- Phase designation for load balancing (R1/W1/B1)
- Cable material (copper vs aluminium)
- Installation method for site cables
- Overload relay detection for motor circuits
- Expanded equipment types (generator, UPS, solar, EV charger, etc.)
- Supply point with rating_kva, voltage specs

Supports multiple LLM providers:
- Groq (Llama 4 Scout/Maverick) - 100% FREE with vision!
- xAI Grok (grok-2-vision) - $25 free credits/month
- Google Gemini (gemini-2.0-flash/pro) - FREE
- Anthropic Claude (sonnet/opus) - paid
"""

import json
import base64
from typing import Tuple, Optional, List, Dict, Any

from agent.models import (
    DocumentSet, ExtractionResult, ExtractionMode, ServiceTier,
    StageResult, PipelineStage, PageType, ItemConfidence,
    BuildingBlock, DistributionBoard, Circuit, Room, FixtureCounts,
    HeavyEquipment, SiteCableRun, ProjectMetadata, SupplyPoint,
    SystemParameters  # v4.5
)
from agent.utils import parse_json_safely, Timer, estimate_cost_zar
from agent.prompts.schemas import (
    SLD_SCHEMA, LIGHTING_LAYOUT_SCHEMA, PLUGS_LAYOUT_SCHEMA,
    COMBINED_LAYOUT_SCHEMA, OUTSIDE_LIGHTS_SCHEMA, CONFIDENCE_INSTRUCTION
)
from agent.prompts.system_prompt import SYSTEM_PROMPT
from agent.prompts.sld_prompt import get_sld_extraction_prompt
from agent.prompts.lighting_layout_prompt import get_prompt as get_lighting_prompt
# v4.2 - Enhanced prompts
from agent.prompts.plugs_layout_prompt import get_plugs_layout_prompt
from agent.prompts.page_classifier_prompt import get_page_classifier_prompt
from agent.prompts.legend_prompt import get_legend_prompt

# Extraction models by provider
DISCOVER_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",  # Current recommended fast model
    "grok": "grok-2-vision-1212",  # Grok with vision support
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 Scout - 100% FREE!
}
ESCALATION_MODELS = {
    "claude": "claude-opus-4-20250514",
    "gemini": "gemini-1.5-pro-latest",  # Pro for higher accuracy
    "grok": "grok-2-vision-1212",  # Grok's best vision model
    "groq": "meta-llama/llama-4-maverick-17b-128e-instruct",  # Llama 4 Maverick - 100% FREE!
}
DISCOVER_MODEL = DISCOVER_MODELS["claude"]  # Default for backwards compatibility
ESCALATION_MODEL = ESCALATION_MODELS["claude"]
CONFIDENCE_THRESHOLD = 0.80  # Below 80%, escalate for verification

# Current provider (set by pipeline)
_current_provider = "claude"


def set_provider(provider: str):
    """Set the current LLM provider."""
    global _current_provider
    _current_provider = provider


def _call_vision_llm(
    client: object,
    pages: List,
    prompt: str,
    model: str,
    max_tokens: int = 8192,
) -> Tuple[str, int, float]:
    """
    Call the LLM with vision capabilities (works with Groq, Grok, Gemini, and Claude).

    Args:
        client: API client (Anthropic, Gemini, Grok, or Groq/OpenAI)
        pages: List of page objects with image_base64
        prompt: The prompt text
        model: Model name to use
        max_tokens: Maximum output tokens

    Returns:
        Tuple of (response_text, tokens_used, cost_zar)
    """
    global _current_provider

    if _current_provider == "groq":
        # Groq API call with vision (OpenAI-compatible with Llama Vision)
        content = [{"type": "text", "text": prompt}]

        for page in pages:
            if page.image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{page.image_base64}",
                    }
                })

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        return response_text, tokens_used, 0.0  # Groq is 100% FREE!

    elif _current_provider == "grok":
        # Grok API call with vision (OpenAI-compatible)
        content = [{"type": "text", "text": prompt}]

        for page in pages:
            if page.image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{page.image_base64}",
                    }
                })

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        return response_text, tokens_used, 0.0  # Grok has free credits!

    elif _current_provider == "gemini":
        # Gemini API call with vision
        import PIL.Image
        import io

        content_parts = [prompt]

        for page in pages:
            if page.image_base64:
                img_bytes = base64.b64decode(page.image_base64)
                img = PIL.Image.open(io.BytesIO(img_bytes))
                content_parts.append(img)

        gemini_model = client.GenerativeModel(model)
        response = gemini_model.generate_content(
            content_parts,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.1,
            }
        )

        tokens_used = 0
        if hasattr(response, 'usage_metadata'):
            tokens_used = getattr(response.usage_metadata, 'total_token_count', 0)

        return response.text, tokens_used, 0.0  # Gemini free tier!

    else:
        # Claude API call with vision (default)
        content = [{"type": "text", "text": prompt}]

        for page in pages:
            if page.image_base64:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": page.image_base64,
                    }
                })

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        cost_zar = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)

        return response_text, tokens_used, cost_zar


def discover(
    doc_set: DocumentSet,
    tier: ServiceTier,
    mode: ExtractionMode,
    building_blocks: List[str],
    client: Optional[object] = None,
    use_opus_directly: bool = False,
    provider: str = "claude",  # "claude", "gemini", "grok", or "groq"
) -> Tuple[ExtractionResult, StageResult]:
    """
    DISCOVER stage: Extract structured data from documents.

    Args:
        doc_set: Processed documents from INGEST stage
        tier: Classification tier from CLASSIFY stage
        mode: Extraction mode (AS_BUILT, ESTIMATION, etc.)
        building_blocks: List of building block names
        client: API client (Anthropic, Gemini, Grok, or Groq)
        use_opus_directly: If True, use higher-tier model for initial extraction
        provider: LLM provider ("claude", "gemini", "grok", or "groq")

    Returns:
        Tuple of (ExtractionResult, StageResult)
    """
    global _current_provider
    _current_provider = provider
    with Timer("discover") as timer:
        errors = []
        warnings = []
        total_tokens = 0
        total_cost = 0.0

        # Select model based on provider and accuracy preference
        if use_opus_directly:
            extraction_model = ESCALATION_MODELS.get(provider, ESCALATION_MODEL)
            warnings.append(f"Using {extraction_model} for maximum extraction accuracy")
        else:
            extraction_model = DISCOVER_MODELS.get(provider, DISCOVER_MODEL)
        model_used = extraction_model

        if provider == "groq":
            warnings.append("Using Groq with Llama Vision (100% FREE)")
        elif provider == "grok":
            warnings.append("Using xAI Grok ($25 free credits)")
        elif provider == "gemini":
            warnings.append("Using Google Gemini (FREE tier)")

        extraction = ExtractionResult(
            extraction_mode=mode,
            metadata=ProjectMetadata(
                building_blocks=building_blocks,
            ),
        )

        # Initialize building blocks
        for block_name in building_blocks:
            extraction.building_blocks.append(BuildingBlock(name=block_name))

        # Process pages by type
        sld_pages = doc_set.pages_by_type(PageType.SLD)
        lighting_pages = doc_set.pages_by_type(PageType.LAYOUT_LIGHTING)
        plug_pages = doc_set.pages_by_type(PageType.LAYOUT_PLUGS)
        combined_pages = doc_set.pages_by_type(PageType.LAYOUT_COMBINED)
        outside_pages = doc_set.pages_by_type(PageType.OUTSIDE_LIGHTS)

        extraction.pages_processed = len(doc_set.all_pages)

        # Extract from SLD pages
        if sld_pages and client:
            try:
                sld_data, tokens, cost = _extract_sld_data(sld_pages, client, extraction_model)
                total_tokens += tokens
                total_cost += cost
                _merge_sld_data(extraction, sld_data)
                extraction.pages_with_data += len(sld_pages)
            except Exception as e:
                errors.append(f"SLD extraction failed: {str(e)}")

        # Extract from lighting pages
        if lighting_pages and client:
            try:
                lighting_data, tokens, cost = _extract_lighting_data(lighting_pages, client, extraction_model)
                total_tokens += tokens
                total_cost += cost
                _merge_lighting_data(extraction, lighting_data)
                extraction.pages_with_data += len(lighting_pages)
            except Exception as e:
                errors.append(f"Lighting extraction failed: {str(e)}")

        # Extract from plug pages
        if plug_pages and client:
            try:
                plug_data, tokens, cost = _extract_plug_data(plug_pages, client, extraction_model)
                total_tokens += tokens
                total_cost += cost
                _merge_plug_data(extraction, plug_data)
                extraction.pages_with_data += len(plug_pages)
            except Exception as e:
                errors.append(f"Plug extraction failed: {str(e)}")

        # Extract from combined layout pages (has both lights AND sockets/switches)
        if combined_pages and client:
            try:
                combined_data, tokens, cost = _extract_combined_layout_data(
                    combined_pages, client, extraction_model
                )
                total_tokens += tokens
                total_cost += cost
                _merge_combined_data(extraction, combined_data)
                extraction.pages_with_data += len(combined_pages)
            except Exception as e:
                errors.append(f"Combined layout extraction failed: {str(e)}")

        # Extract from outside lights pages
        if outside_pages and client:
            try:
                outside_data, tokens, cost = _extract_outside_data(outside_pages, client, extraction_model)
                total_tokens += tokens
                total_cost += cost
                _merge_outside_data(extraction, outside_data)
                extraction.pages_with_data += len(outside_pages)
            except Exception as e:
                errors.append(f"Outside lights extraction failed: {str(e)}")

        # Calculate overall confidence
        confidence = _calculate_confidence(extraction)

        # Escalate to Opus if confidence is low
        if confidence < CONFIDENCE_THRESHOLD and client:
            warnings.append(f"Low confidence ({confidence:.2f}), escalating to Opus")
            try:
                extraction, escalation_tokens, escalation_cost = _escalate_to_opus(
                    doc_set, extraction, client
                )
                total_tokens += escalation_tokens
                total_cost += escalation_cost
                model_used = ESCALATION_MODEL
                confidence = _calculate_confidence(extraction)
            except Exception as e:
                errors.append(f"Opus escalation failed: {str(e)}")

        # Build stage result
        result = StageResult(
            stage=PipelineStage.DISCOVER,
            success=extraction.pages_with_data > 0,
            confidence=confidence,
            data={
                "building_blocks": len(extraction.building_blocks),
                "distribution_boards": len(extraction.all_distribution_boards),
                "rooms": len(extraction.all_rooms),
                "site_cable_runs": len(extraction.site_cable_runs),
            },
            model_used=model_used,
            tokens_used=total_tokens,
            cost_zar=total_cost,
            processing_time_ms=timer.elapsed_ms,
            errors=errors,
            warnings=warnings,
        )

        return extraction, result


def _extract_sld_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """Extract distribution board data from SLD pages."""
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

Extract distribution board and circuit data from these SLD drawings.
Return JSON matching this schema:
{SLD_SCHEMA}

{get_sld_extraction_prompt()}
"""

    response_text, tokens, cost = _call_vision_llm(
        client, pages[:5], prompt, model, max_tokens=8192
    )

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_lighting_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """Extract lighting fixture data from layout pages."""
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

Extract room and lighting fixture data from these lighting layout drawings.
Return JSON matching this schema:
{LIGHTING_LAYOUT_SCHEMA}

{get_lighting_prompt([])}
"""

    response_text, tokens, cost = _call_vision_llm(
        client, pages[:5], prompt, model, max_tokens=8192
    )

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_plug_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """Extract socket/switch data from plug layout pages using enhanced v4.2 prompt."""
    # v4.2 - Use dedicated plugs layout prompt
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

{get_plugs_layout_prompt()}

Return JSON matching this schema:
{PLUGS_LAYOUT_SCHEMA}
"""

    response_text, tokens, cost = _call_vision_llm(
        client, pages[:5], prompt, model, max_tokens=8192
    )

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_outside_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """Extract site cable runs and outside lights from external drawings."""
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

Extract site cable runs and outside lighting from these external/site drawings.
Pay special attention to cable lengths - mark as "extracted" if visible on drawing, "estimated" if not.
Return JSON matching this schema:
{OUTSIDE_LIGHTS_SCHEMA}
"""

    response_text, tokens, cost = _call_vision_llm(
        client, pages[:3], prompt, model, max_tokens=4096
    )

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_combined_layout_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """
    Extract both lighting AND socket/switch data from combined layout pages.

    Combined layout pages are common in South African electrical drawings where
    both the lighting layout and power/plug layout are shown on the same page.
    This function extracts ALL fixture types in a single pass.
    """
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

## IMPORTANT: COMBINED LAYOUT DRAWING

This drawing contains BOTH lighting fixtures AND power points (sockets/switches) on the SAME page.
You must extract ALL of the following in a single pass:

### LIGHTING FIXTURES to count:
- Recessed LED panels (600x1200, 600x600)
- Surface mount LEDs
- Downlights
- Vapor proof fittings (for wet areas)
- Bulkheads
- Flood lights

### POWER POINTS to count:
- Double sockets @300mm (floor level)
- Double sockets @1100mm (work surface level)
- Single sockets
- Waterproof sockets
- Data points (CAT6)
- Floor boxes

### SWITCHES to count:
- 1-lever 1-way switches
- 2-lever 1-way switches
- 1-lever 2-way switches
- Day/night switches
- Isolators (20A, 30A)
- Master switches

### EXTRACTION RULES:
1. Check the LEGEND carefully - it defines all symbols used on this drawing
2. Count EACH room separately - look for room names, suite numbers, or area labels
3. Match symbols to legend, then count per room
4. Mark as "extracted" if you can see and count the symbols
5. Mark as "inferred" if you calculated from other data
6. Mark as "estimated" ONLY if the area is unclear and you had to guess

Return JSON matching this schema:
{COMBINED_LAYOUT_SCHEMA}
"""

    response_text, tokens, cost = _call_vision_llm(
        client, pages[:5], prompt, model, max_tokens=8192
    )

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _merge_combined_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """
    Merge combined layout extraction data into ExtractionResult.

    This handles rooms that have BOTH lighting and socket/switch data extracted
    in a single pass from combined layout pages.
    """
    block_name = data.get("building_block", "")

    # Find building block
    block = None
    for b in extraction.building_blocks:
        if b.name.lower() == block_name.lower() or not block_name:
            block = b
            break
    if not block and extraction.building_blocks:
        block = extraction.building_blocks[0]

    if not block:
        block = BuildingBlock(name=block_name or "Main Building")
        extraction.building_blocks.append(block)

    # Process rooms with combined lighting + power data
    for room_data in data.get("rooms", []):
        room_name = room_data.get("name", "")
        fixtures_data = room_data.get("fixtures", {})

        # Check if room already exists
        existing_room = None
        for r in block.rooms:
            if r.name.lower() == room_name.lower():
                existing_room = r
                break

        if existing_room:
            # Merge ALL fixture data into existing room
            # Lighting fixtures
            if fixtures_data.get("recessed_led_600x1200"):
                existing_room.fixtures.recessed_led_600x1200 = int(fixtures_data.get("recessed_led_600x1200") or 0)
            if fixtures_data.get("surface_mount_led_18w"):
                existing_room.fixtures.surface_mount_led_18w = int(fixtures_data.get("surface_mount_led_18w") or 0)
            if fixtures_data.get("downlight_led_6w"):
                existing_room.fixtures.downlight_led_6w = int(fixtures_data.get("downlight_led_6w") or 0)
            if fixtures_data.get("vapor_proof_2x24w"):
                existing_room.fixtures.vapor_proof_2x24w = int(fixtures_data.get("vapor_proof_2x24w") or 0)
            if fixtures_data.get("vapor_proof_2x18w"):
                existing_room.fixtures.vapor_proof_2x18w = int(fixtures_data.get("vapor_proof_2x18w") or 0)
            if fixtures_data.get("bulkhead_26w"):
                existing_room.fixtures.bulkhead_26w = int(fixtures_data.get("bulkhead_26w") or 0)
            if fixtures_data.get("bulkhead_24w"):
                existing_room.fixtures.bulkhead_24w = int(fixtures_data.get("bulkhead_24w") or 0)
            if fixtures_data.get("flood_light_30w"):
                existing_room.fixtures.flood_light_30w = int(fixtures_data.get("flood_light_30w") or 0)
            if fixtures_data.get("flood_light_200w"):
                existing_room.fixtures.flood_light_200w = int(fixtures_data.get("flood_light_200w") or 0)
            # v4.4 - Pool lighting
            if fixtures_data.get("pool_flood_light"):
                existing_room.fixtures.pool_flood_light = int(fixtures_data.get("pool_flood_light") or 0)
            if fixtures_data.get("pool_underwater_light"):
                existing_room.fixtures.pool_underwater_light = int(fixtures_data.get("pool_underwater_light") or 0)

            # Sockets
            if fixtures_data.get("double_socket_300"):
                existing_room.fixtures.double_socket_300 = int(fixtures_data.get("double_socket_300") or 0)
            if fixtures_data.get("single_socket_300"):
                existing_room.fixtures.single_socket_300 = int(fixtures_data.get("single_socket_300") or 0)
            if fixtures_data.get("double_socket_1100"):
                existing_room.fixtures.double_socket_1100 = int(fixtures_data.get("double_socket_1100") or 0)
            if fixtures_data.get("single_socket_1100"):
                existing_room.fixtures.single_socket_1100 = int(fixtures_data.get("single_socket_1100") or 0)
            if fixtures_data.get("double_socket_waterproof"):
                existing_room.fixtures.double_socket_waterproof = int(fixtures_data.get("double_socket_waterproof") or 0)
            if fixtures_data.get("double_socket_ceiling"):
                existing_room.fixtures.double_socket_ceiling = int(fixtures_data.get("double_socket_ceiling") or 0)
            if fixtures_data.get("data_points_cat6"):
                existing_room.fixtures.data_points_cat6 = int(fixtures_data.get("data_points_cat6") or 0)
            if fixtures_data.get("floor_box"):
                existing_room.fixtures.floor_box = int(fixtures_data.get("floor_box") or 0)

            # Switches
            if fixtures_data.get("switch_1lever_1way"):
                existing_room.fixtures.switch_1lever_1way = int(fixtures_data.get("switch_1lever_1way") or 0)
            if fixtures_data.get("switch_2lever_1way"):
                existing_room.fixtures.switch_2lever_1way = int(fixtures_data.get("switch_2lever_1way") or 0)
            if fixtures_data.get("switch_1lever_2way"):
                existing_room.fixtures.switch_1lever_2way = int(fixtures_data.get("switch_1lever_2way") or 0)
            if fixtures_data.get("day_night_switch"):
                existing_room.fixtures.day_night_switch = int(fixtures_data.get("day_night_switch") or 0)
            if fixtures_data.get("isolator_30a"):
                existing_room.fixtures.isolator_30a = int(fixtures_data.get("isolator_30a") or 0)
            if fixtures_data.get("isolator_20a"):
                existing_room.fixtures.isolator_20a = int(fixtures_data.get("isolator_20a") or 0)
            if fixtures_data.get("master_switch"):
                existing_room.fixtures.master_switch = int(fixtures_data.get("master_switch") or 0)

            # Update room properties
            existing_room.is_wet_area = room_data.get("is_wet_area") or existing_room.is_wet_area
            existing_room.has_ac = room_data.get("has_ac") or existing_room.has_ac
            existing_room.has_geyser = room_data.get("has_geyser") or existing_room.has_geyser
            if room_data.get("circuit_refs"):
                existing_room.circuit_refs = list(set(existing_room.circuit_refs + room_data.get("circuit_refs", [])))
        else:
            # Create new room with ALL fixture data
            room = Room(
                name=room_name,
                room_number=int(room_data.get("room_number") or 0),
                type=room_data.get("type") or "",
                area_m2=float(room_data.get("area_m2") or 0),
                floor=room_data.get("floor") or "",
                building_block=block.name,
                circuit_refs=room_data.get("circuit_refs") or [],
                is_wet_area=room_data.get("is_wet_area") or False,
                has_ac=room_data.get("has_ac") or False,
                has_geyser=room_data.get("has_geyser") or False,
                confidence=_parse_confidence(room_data.get("confidence") or "extracted"),
                notes=room_data.get("notes") or [],
            )

            # Set ALL fixture counts from combined extraction (v4.4 - includes pool lighting)
            room.fixtures = FixtureCounts(
                # Lighting
                recessed_led_600x1200=int(fixtures_data.get("recessed_led_600x1200") or 0),
                surface_mount_led_18w=int(fixtures_data.get("surface_mount_led_18w") or 0),
                downlight_led_6w=int(fixtures_data.get("downlight_led_6w") or 0),
                vapor_proof_2x24w=int(fixtures_data.get("vapor_proof_2x24w") or 0),
                vapor_proof_2x18w=int(fixtures_data.get("vapor_proof_2x18w") or 0),
                bulkhead_26w=int(fixtures_data.get("bulkhead_26w") or 0),
                bulkhead_24w=int(fixtures_data.get("bulkhead_24w") or 0),
                prismatic_2x18w=int(fixtures_data.get("prismatic_2x18w") or 0),
                flood_light_30w=int(fixtures_data.get("flood_light_30w") or 0),
                flood_light_200w=int(fixtures_data.get("flood_light_200w") or 0),
                fluorescent_50w_5ft=int(fixtures_data.get("fluorescent_50w_5ft") or 0),
                pole_light_60w=int(fixtures_data.get("pole_light_60w") or 0),
                # v4.4 - Pool lighting
                pool_flood_light=int(fixtures_data.get("pool_flood_light") or 0),
                pool_underwater_light=int(fixtures_data.get("pool_underwater_light") or 0),
                # Sockets
                double_socket_300=int(fixtures_data.get("double_socket_300") or 0),
                single_socket_300=int(fixtures_data.get("single_socket_300") or 0),
                double_socket_1100=int(fixtures_data.get("double_socket_1100") or 0),
                single_socket_1100=int(fixtures_data.get("single_socket_1100") or 0),
                double_socket_waterproof=int(fixtures_data.get("double_socket_waterproof") or 0),
                double_socket_ceiling=int(fixtures_data.get("double_socket_ceiling") or 0),
                data_points_cat6=int(fixtures_data.get("data_points_cat6") or 0),
                floor_box=int(fixtures_data.get("floor_box") or 0),
                # Switches
                switch_1lever_1way=int(fixtures_data.get("switch_1lever_1way") or 0),
                switch_2lever_1way=int(fixtures_data.get("switch_2lever_1way") or 0),
                switch_1lever_2way=int(fixtures_data.get("switch_1lever_2way") or 0),
                day_night_switch=int(fixtures_data.get("day_night_switch") or 0),
                isolator_30a=int(fixtures_data.get("isolator_30a") or 0),
                isolator_20a=int(fixtures_data.get("isolator_20a") or 0),
                master_switch=int(fixtures_data.get("master_switch") or 0),
            )

            block.rooms.append(room)


def _merge_sld_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge SLD extraction data into ExtractionResult."""
    block_name = data.get("building_block", "")

    # v4.5 - Extract system parameters
    sys_params_data = data.get("system_parameters")
    if sys_params_data and extraction.metadata:
        extraction.metadata.system_parameters = SystemParameters(
            voltage_v=int(sys_params_data.get("voltage_v") or 400),
            voltage_single_phase_v=int(sys_params_data.get("voltage_single_phase_v") or 230),
            phases=sys_params_data.get("phases") or "3PH+N+E",
            num_phases=int(sys_params_data.get("num_phases") or 3),
            frequency_hz=int(sys_params_data.get("frequency_hz") or 50),
            fault_level_main_ka=float(sys_params_data.get("fault_level_main_ka") or 15.0),
            fault_level_sub_ka=float(sys_params_data.get("fault_level_sub_ka") or 6.0),
            standard=sys_params_data.get("standard") or "SANS 10142-1",
            phase_designation=sys_params_data.get("phase_designation") or "RWB",
            confidence=_parse_confidence(sys_params_data.get("confidence") or "inferred"),
        )

    # v4.5 - Extract supply point
    supply_data = data.get("supply_point")
    if supply_data:
        supply_point = SupplyPoint(
            name=supply_data.get("name") or "",
            type=supply_data.get("type") or "eskom_kiosk",
            rating_kva=float(supply_data.get("rating_kva") or 0),
            voltage_primary_v=int(supply_data.get("voltage_primary_v") or 11000),
            voltage_secondary_v=int(supply_data.get("voltage_secondary_v") or 400),
            phases=supply_data.get("phases") or "3PH+N+E",
            main_breaker_a=int(supply_data.get("main_breaker_a") or 0),
            has_meter=supply_data.get("has_meter") if supply_data.get("has_meter") is not None else True,
            meter_type=supply_data.get("meter_type") or "ct",
            feeds_db=supply_data.get("feeds_db") or "",
            cable_size_mm2=float(supply_data.get("cable_size_mm2") or 0),
            cable_cores=int(supply_data.get("cable_cores") or 4),
            cable_type=supply_data.get("cable_type") or "PVC SWA PVC",
            cable_material=supply_data.get("cable_material") or "copper",
            cable_length_m=float(supply_data.get("cable_length_m") or 0),
            fault_level_ka=float(supply_data.get("fault_level_ka") or 15.0),
            status=supply_data.get("status") or "new",
            building_block=block_name,
            confidence=_parse_confidence(supply_data.get("confidence") or "extracted"),
        )
        extraction.supply_points.append(supply_point)

    # Find or create building block
    block = None
    for b in extraction.building_blocks:
        if b.name.lower() == block_name.lower() or not block_name:
            block = b
            break
    if not block and extraction.building_blocks:
        block = extraction.building_blocks[0]
    elif not block:
        block = BuildingBlock(name=block_name or "Main Building")
        extraction.building_blocks.append(block)

    # Add distribution boards (v4.5 enhanced with breaker_type, cable_material, status)
    for db_data in data.get("distribution_boards", []):
        db = DistributionBoard(
            name=db_data.get("name", ""),
            description=db_data.get("description", ""),
            location=db_data.get("location", ""),
            building_block=block.name,
            supply_from=db_data.get("supply_from", ""),
            supply_cable=db_data.get("supply_cable", ""),
            supply_cable_size_mm2=float(db_data.get("supply_cable_size_mm2") or 0),
            supply_cable_length_m=float(db_data.get("supply_cable_length_m") or 0),
            supply_cable_material=db_data.get("supply_cable_material") or "copper",  # v4.5
            main_breaker_a=int(db_data.get("main_breaker_a") or 0),
            main_breaker_type=db_data.get("main_breaker_type") or "mccb",  # v4.5
            main_breaker_poles=int(db_data.get("main_breaker_poles") or 4),  # v4.5
            earth_leakage=db_data.get("earth_leakage") or False,
            earth_leakage_rating_a=int(db_data.get("earth_leakage_rating_a") or 0),
            earth_leakage_ma=int(db_data.get("earth_leakage_ma") or 30),  # v4.5
            earth_leakage_type=db_data.get("earth_leakage_type") or "rcd",  # v4.5
            surge_protection=db_data.get("surge_protection") or False,
            surge_type=db_data.get("surge_type") or "",  # v4.5
            spare_ways=int(db_data.get("spare_ways") or 0),
            fault_level_ka=float(db_data.get("fault_level_ka") or 15.0),  # v4.5
            status=db_data.get("status") or "new",  # v4.5
            confidence=_parse_confidence(db_data.get("confidence", "extracted")),
        )

        # Add circuits (v4.5 enhanced with breaker_type, phase, cable_material, overload_relay)
        for ckt_data in db_data.get("circuits", []):
            circuit = Circuit(
                id=ckt_data.get("id") or "",
                type=ckt_data.get("type") or "power",
                description=ckt_data.get("description") or "",
                wattage_w=float(ckt_data.get("wattage_w") or 0),
                wattage_formula=ckt_data.get("wattage_formula") or "",
                cable_size_mm2=float(ckt_data.get("cable_size_mm2") or 2.5),
                cable_cores=int(ckt_data.get("cable_cores") or 3),
                cable_type=ckt_data.get("cable_type") or "GP WIRE",
                cable_material=ckt_data.get("cable_material") or "copper",  # v4.5
                breaker_a=int(ckt_data.get("breaker_a") or 20),
                breaker_type=ckt_data.get("breaker_type") or "mcb",  # v4.5
                breaker_poles=int(ckt_data.get("breaker_poles") or 1),
                phase=ckt_data.get("phase") or "",  # v4.5
                num_points=int(ckt_data.get("num_points") or 0),
                is_spare=ckt_data.get("is_spare") or False,
                has_isolator=ckt_data.get("has_isolator") or False,
                isolator_rating_a=int(ckt_data.get("isolator_rating_a") or 0),
                has_vsd=ckt_data.get("has_vsd") or False,
                feeds_board=ckt_data.get("feeds_board"),
                confidence=_parse_confidence(ckt_data.get("confidence") or "extracted"),
                # v4.3 - VSD and starter fields
                vsd_rating_kw=float(ckt_data.get("vsd_rating_kw") or 0),
                starter_type=ckt_data.get("starter_type") or "",
                # v4.3 - Day/night switch fields
                has_day_night=ckt_data.get("has_day_night") or False,
                has_bypass=ckt_data.get("has_bypass") or False,
                controlled_circuits=ckt_data.get("controlled_circuits") or [],
                # v4.3 - ISO circuit equipment type
                equipment_type=ckt_data.get("equipment_type") or "",
                # v4.5 - Overload relay for motor circuits
                has_overload_relay=ckt_data.get("has_overload_relay") or False,
            )
            db.circuits.append(circuit)

        block.distribution_boards.append(db)

    # Add heavy equipment (v4.5 enhanced with overload_relay, breaker_type, cable_material, status)
    for eq_data in data.get("heavy_equipment", []):
        equipment = HeavyEquipment(
            name=eq_data.get("name") or "",
            type=eq_data.get("type") or "",
            rating_kw=float(eq_data.get("rating_kw") or 0),
            rating_kva=float(eq_data.get("rating_kva") or 0),  # v4.5
            cable_size_mm2=float(eq_data.get("cable_size_mm2") or 4),
            cable_type=eq_data.get("cable_type") or "PVC SWA PVC",
            cable_material=eq_data.get("cable_material") or "copper",  # v4.5
            breaker_a=int(eq_data.get("breaker_a") or 32),
            breaker_type=eq_data.get("breaker_type") or "mcb",  # v4.5
            breaker_poles=int(eq_data.get("breaker_poles") or 3),  # v4.5
            has_vsd=eq_data.get("has_vsd") or False,
            has_dol=eq_data.get("has_dol") or False,
            isolator_a=int(eq_data.get("isolator_a") or 0),
            fed_from_db=eq_data.get("fed_from_db") or "",
            building_block=block.name,
            qty=int(eq_data.get("qty") or 1),
            confidence=_parse_confidence(eq_data.get("confidence") or "extracted"),
            # v4.3 - Circuit reference and starter type
            circuit_ref=eq_data.get("circuit_ref") or "",
            starter_type=eq_data.get("starter_type") or "",
            vsd_rating_kw=float(eq_data.get("vsd_rating_kw") or 0),
            # v4.5 - Motor protection
            has_overload_relay=eq_data.get("has_overload_relay") or False,
            overload_setting_a=float(eq_data.get("overload_setting_a") or 0),
            # v4.5 - Equipment status
            status=eq_data.get("status") or "new",
            # v4.5 - Voltage (for transformers, inverters)
            voltage_primary_v=int(eq_data.get("voltage_primary_v") or 0),
            voltage_secondary_v=int(eq_data.get("voltage_secondary_v") or 0),
            # v4.5 - Backup power specific
            backup_runtime_hours=float(eq_data.get("backup_runtime_hours") or 0),
            fuel_type=eq_data.get("fuel_type") or "",
            # v4.5 - EV charger specific
            ev_charger_type=eq_data.get("ev_charger_type") or "",
            ev_charger_kw=float(eq_data.get("ev_charger_kw") or 0),
        )
        block.heavy_equipment.append(equipment)


def _merge_lighting_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge lighting extraction data into ExtractionResult."""
    block_name = data.get("building_block", "")

    # Find building block
    block = None
    for b in extraction.building_blocks:
        if b.name.lower() == block_name.lower() or not block_name:
            block = b
            break
    if not block and extraction.building_blocks:
        block = extraction.building_blocks[0]

    if not block:
        return

    # Add rooms with lighting data
    for room_data in data.get("rooms", []):
        fixtures_data = room_data.get("fixtures", {})

        room = Room(
            name=room_data.get("name") or "",
            room_number=int(room_data.get("room_number") or 0),
            type=room_data.get("type") or "",
            area_m2=float(room_data.get("area_m2") or 0),
            floor=room_data.get("floor") or "",
            building_block=block.name,
            circuit_refs=room_data.get("circuit_refs") or [],
            is_wet_area=room_data.get("is_wet_area") or False,
            confidence=_parse_confidence(room_data.get("confidence") or "extracted"),
            notes=room_data.get("notes") or [],
        )

        # Set fixture counts (v4.4 - includes pool lighting)
        room.fixtures = FixtureCounts(
            recessed_led_600x1200=int(fixtures_data.get("recessed_led_600x1200") or 0),
            surface_mount_led_18w=int(fixtures_data.get("surface_mount_led_18w") or 0),
            flood_light_30w=int(fixtures_data.get("flood_light_30w") or 0),
            flood_light_200w=int(fixtures_data.get("flood_light_200w") or 0),
            downlight_led_6w=int(fixtures_data.get("downlight_led_6w") or 0),
            vapor_proof_2x24w=int(fixtures_data.get("vapor_proof_2x24w") or 0),
            vapor_proof_2x18w=int(fixtures_data.get("vapor_proof_2x18w") or 0),
            prismatic_2x18w=int(fixtures_data.get("prismatic_2x18w") or 0),
            bulkhead_26w=int(fixtures_data.get("bulkhead_26w") or 0),
            bulkhead_24w=int(fixtures_data.get("bulkhead_24w") or 0),
            fluorescent_50w_5ft=int(fixtures_data.get("fluorescent_50w_5ft") or 0),
            pole_light_60w=int(fixtures_data.get("pole_light_60w") or 0),
            # v4.4 - Pool lighting
            pool_flood_light=int(fixtures_data.get("pool_flood_light") or 0),
            pool_underwater_light=int(fixtures_data.get("pool_underwater_light") or 0),
        )

        block.rooms.append(room)


def _merge_plug_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge plug/socket extraction data into ExtractionResult."""
    block_name = data.get("building_block", "")

    block = None
    for b in extraction.building_blocks:
        if b.name.lower() == block_name.lower() or not block_name:
            block = b
            break
    if not block and extraction.building_blocks:
        block = extraction.building_blocks[0]

    if not block:
        return

    # Merge socket/switch data into existing rooms or create new ones
    for room_data in data.get("rooms", []):
        room_name = room_data.get("name", "")
        fixtures_data = room_data.get("fixtures", {})

        # Find existing room
        existing_room = None
        for r in block.rooms:
            if r.name.lower() == room_name.lower():
                existing_room = r
                break

        if existing_room:
            # Merge socket/switch data
            existing_room.fixtures.double_socket_300 = int(fixtures_data.get("double_socket_300") or 0)
            existing_room.fixtures.single_socket_300 = int(fixtures_data.get("single_socket_300") or 0)
            existing_room.fixtures.double_socket_1100 = int(fixtures_data.get("double_socket_1100") or 0)
            existing_room.fixtures.single_socket_1100 = int(fixtures_data.get("single_socket_1100") or 0)
            existing_room.fixtures.double_socket_waterproof = int(fixtures_data.get("double_socket_waterproof") or 0)
            existing_room.fixtures.double_socket_ceiling = int(fixtures_data.get("double_socket_ceiling") or 0)
            existing_room.fixtures.data_points_cat6 = int(fixtures_data.get("data_points_cat6") or 0)
            existing_room.fixtures.floor_box = int(fixtures_data.get("floor_box") or 0)
            existing_room.fixtures.switch_1lever_1way = int(fixtures_data.get("switch_1lever_1way") or 0)
            existing_room.fixtures.switch_2lever_1way = int(fixtures_data.get("switch_2lever_1way") or 0)
            existing_room.fixtures.switch_1lever_2way = int(fixtures_data.get("switch_1lever_2way") or 0)
            existing_room.fixtures.day_night_switch = int(fixtures_data.get("day_night_switch") or 0)
            existing_room.fixtures.isolator_30a = int(fixtures_data.get("isolator_30a") or 0)
            existing_room.fixtures.isolator_20a = int(fixtures_data.get("isolator_20a") or 0)
            existing_room.fixtures.master_switch = int(fixtures_data.get("master_switch") or 0)
            existing_room.has_ac = room_data.get("has_ac") or False
            existing_room.has_geyser = room_data.get("has_geyser") or False
        else:
            # Create new room with socket data
            room = Room(
                name=room_name,
                building_block=block.name,
                has_ac=room_data.get("has_ac") or False,
                has_geyser=room_data.get("has_geyser") or False,
                confidence=_parse_confidence(room_data.get("confidence") or "extracted"),
            )
            room.fixtures = FixtureCounts(
                double_socket_300=int(fixtures_data.get("double_socket_300") or 0),
                single_socket_300=int(fixtures_data.get("single_socket_300") or 0),
                double_socket_1100=int(fixtures_data.get("double_socket_1100") or 0),
                single_socket_1100=int(fixtures_data.get("single_socket_1100") or 0),
                double_socket_waterproof=int(fixtures_data.get("double_socket_waterproof") or 0),
                double_socket_ceiling=int(fixtures_data.get("double_socket_ceiling") or 0),
                data_points_cat6=int(fixtures_data.get("data_points_cat6") or 0),
                floor_box=int(fixtures_data.get("floor_box") or 0),
                switch_1lever_1way=int(fixtures_data.get("switch_1lever_1way") or 0),
                switch_2lever_1way=int(fixtures_data.get("switch_2lever_1way") or 0),
                switch_1lever_2way=int(fixtures_data.get("switch_1lever_2way") or 0),
                day_night_switch=int(fixtures_data.get("day_night_switch") or 0),
                isolator_30a=int(fixtures_data.get("isolator_30a") or 0),
                isolator_20a=int(fixtures_data.get("isolator_20a") or 0),
                master_switch=int(fixtures_data.get("master_switch") or 0),
            )
            block.rooms.append(room)


def _merge_outside_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge outside lights and site cable data into ExtractionResult."""
    # Add site cable runs (v4.5 enhanced with material, installation_method, trench details)
    for run_data in data.get("site_cable_runs") or []:
        run = SiteCableRun(
            from_point=run_data.get("from_point") or "",
            to_point=run_data.get("to_point") or "",
            cable_spec=run_data.get("cable_spec") or "",
            cable_size_mm2=float(run_data.get("cable_size_mm2") or 0),
            cable_cores=int(run_data.get("cable_cores") or 4),
            cable_type=run_data.get("cable_type") or "PVC SWA PVC",
            length_m=float(run_data.get("length_m") or 0),
            is_underground=run_data.get("is_underground") if run_data.get("is_underground") is not None else True,
            needs_trenching=run_data.get("needs_trenching") if run_data.get("needs_trenching") is not None else True,
            confidence=_parse_confidence(run_data.get("confidence") or "estimated"),
            notes=run_data.get("notes") or "",
            # v4.5 - Enhanced cable attributes
            material=run_data.get("material") or "copper",
            is_armoured=run_data.get("is_armoured") if run_data.get("is_armoured") is not None else True,
            installation_method=run_data.get("installation_method") or "underground",
            # v4.5 - Trench details
            trench_depth_mm=int(run_data.get("trench_depth_mm") or 600),
            trench_width_mm=int(run_data.get("trench_width_mm") or 300),
            requires_warning_tape=run_data.get("requires_warning_tape") if run_data.get("requires_warning_tape") is not None else True,
            requires_sand_bedding=run_data.get("requires_sand_bedding") if run_data.get("requires_sand_bedding") is not None else True,
        )
        extraction.site_cable_runs.append(run)

    # Add outside lights (v4.4 - includes pool lighting)
    outside_data = data.get("outside_lights") or {}
    if outside_data:
        extraction.outside_lights = FixtureCounts(
            pole_light_60w=int(outside_data.get("pole_light_60w") or 0),
            flood_light_200w=int(outside_data.get("flood_light_200w") or 0),
            flood_light_30w=int(outside_data.get("flood_light_30w") or 0),
            bulkhead_26w=int(outside_data.get("bulkhead_26w") or 0),
            bulkhead_24w=int(outside_data.get("bulkhead_24w") or 0),
            # v4.4 - Pool lighting
            pool_flood_light=int(outside_data.get("pool_flood_light") or 0),
            pool_underwater_light=int(outside_data.get("pool_underwater_light") or 0),
        )


def _parse_confidence(conf_str: str) -> ItemConfidence:
    """Parse confidence string to enum."""
    mapping = {
        "extracted": ItemConfidence.EXTRACTED,
        "inferred": ItemConfidence.INFERRED,
        "estimated": ItemConfidence.ESTIMATED,
        "manual": ItemConfidence.MANUAL,
    }
    return mapping.get(conf_str.lower(), ItemConfidence.ESTIMATED)


def _validate_against_legend(extraction_data: Dict[str, Any]) -> List[str]:
    """
    v4.4 - Compare extracted room fixture totals against legend totals.

    Many SA drawings include a QTYS column in the legend showing expected totals.
    This function cross-checks extracted counts against legend_totals for validation.

    Args:
        extraction_data: Raw extraction dict containing rooms and legend_totals

    Returns:
        List of warning messages where counts don't match
    """
    warnings = []
    legend_totals = extraction_data.get("legend_totals", {})

    if not legend_totals:
        return warnings

    rooms = extraction_data.get("rooms", [])

    for fixture_type, expected in legend_totals.items():
        if expected is None or expected == 0:
            continue

        # Sum this fixture type across all rooms
        actual = 0
        for room in rooms:
            fixtures = room.get("fixtures", {})
            room_count = fixtures.get(fixture_type, 0)
            if room_count:
                actual += int(room_count)

        if actual != expected:
            diff = actual - expected
            direction = "more" if diff > 0 else "fewer"
            warnings.append(
                f"Legend mismatch: {fixture_type} - extracted {actual}, "
                f"legend shows {expected} ({abs(diff)} {direction})"
            )

    return warnings


def _calculate_confidence(extraction: ExtractionResult) -> float:
    """
    Calculate overall extraction confidence.

    Confidence scoring:
    - EXTRACTED items = 1.0 (directly read from drawing)
    - INFERRED items = 0.9 (calculated from other values - still reliable)
    - ESTIMATED items = 0.3 (guessed/assumed)
    - MANUAL items = 1.0 (user verified)
    """
    if extraction.pages_processed == 0:
        return 0.0

    # Base confidence from data completeness
    completeness = extraction.completeness

    # Score items based on confidence level
    total_items = 0
    confidence_score = 0.0

    # Define confidence weights
    conf_weights = {
        ItemConfidence.EXTRACTED: 1.0,
        ItemConfidence.INFERRED: 0.9,   # Inferred is almost as good as extracted
        ItemConfidence.ESTIMATED: 0.3,  # Estimated is a guess
        ItemConfidence.MANUAL: 1.0,     # User verified
    }

    for block in extraction.building_blocks:
        for db in block.distribution_boards:
            total_items += 1
            confidence_score += conf_weights.get(db.confidence, 0.5)

            for circuit in db.circuits:
                total_items += 1
                confidence_score += conf_weights.get(circuit.confidence, 0.5)

        for room in block.rooms:
            total_items += 1
            confidence_score += conf_weights.get(room.confidence, 0.5)

    for run in extraction.site_cable_runs:
        total_items += 1
        confidence_score += conf_weights.get(run.confidence, 0.5)

    # Calculate average item confidence
    item_confidence = confidence_score / total_items if total_items > 0 else 0.5

    # Weighted average: 30% completeness, 70% item confidence
    # This prioritizes quality of extraction over quantity
    confidence = (completeness * 0.3 + item_confidence * 0.7)
    return min(1.0, max(0.0, confidence))


def _escalate_to_opus(
    doc_set: DocumentSet,
    extraction: ExtractionResult,
    client: object,
) -> Tuple[ExtractionResult, int, float]:
    """
    Re-extract with Opus 4.6 for low-confidence results.

    Uses a verification-focused approach:
    1. Shows Opus the existing extraction
    2. Asks it to verify and correct any errors
    3. Re-extracts items marked as "estimated"
    """
    total_tokens = 0
    total_cost = 0.0

    # Build comprehensive verification prompt
    verification_prompt = f"""{SYSTEM_PROMPT}

You are performing a VERIFICATION pass on an electrical drawing extraction.
The initial extraction had LOW CONFIDENCE. Your job is to:

1. VERIFY each extracted value against what you see in the drawings
2. CORRECT any errors you find
3. RE-EXTRACT items marked as "estimated" - look more carefully
4. ADD any items that were missed in the first pass

## CURRENT EXTRACTION (to verify/correct):
```json
{json.dumps(_extraction_to_dict(extraction), indent=2)}
```

## YOUR TASK:
Review the drawings carefully and return a CORRECTED extraction.
For each item:
- If you can see it clearly in the drawing, mark confidence as "extracted"
- If you calculated it from other data, mark as "inferred"
- ONLY use "estimated" if the item is genuinely not visible and you had to guess

Be METICULOUS. Count every:
- Distribution board and its circuits
- Light fitting (by type)
- Socket outlet (by type)
- Switch (by type)
- Cable run with length

Return the complete corrected JSON matching the original schema structure.
"""

    # Gather all pages for Opus to review
    all_pages = doc_set.all_pages[:10]  # Limit to 10 pages for cost control

    content = [{"type": "text", "text": verification_prompt}]
    for page in all_pages:
        if page.image_base64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": page.image_base64,
                }
            })

    try:
        response = client.messages.create(
            model=ESCALATION_MODEL,
            max_tokens=16384,  # More tokens for comprehensive extraction
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text
        total_tokens = response.usage.input_tokens + response.usage.output_tokens
        total_cost = estimate_cost_zar(ESCALATION_MODEL, response.usage.input_tokens, response.usage.output_tokens)

        # Parse the corrected extraction
        corrected_data = parse_json_safely(response_text)

        if corrected_data:
            # Rebuild extraction from corrected data
            corrected_extraction = _rebuild_extraction_from_dict(corrected_data, extraction)
            return corrected_extraction, total_tokens, total_cost
        else:
            # JSON parse failed, return original
            return extraction, total_tokens, total_cost

    except Exception as e:
        # Log error but return original extraction
        print(f"Opus escalation failed: {e}")
        return extraction, total_tokens, total_cost


def _extraction_to_dict(extraction: ExtractionResult) -> Dict[str, Any]:
    """Convert ExtractionResult to dictionary for verification prompt."""
    result = {
        "building_blocks": [],
        "site_cable_runs": [],
        "outside_lights": {},
    }

    for block in extraction.building_blocks:
        block_data = {
            "name": block.name,
            "distribution_boards": [],
            "rooms": [],
            "heavy_equipment": [],
        }

        for db in block.distribution_boards:
            db_data = {
                "name": db.name,
                "description": db.description,
                "location": db.location,
                "supply_from": db.supply_from,
                "supply_cable": db.supply_cable,
                "supply_cable_size_mm2": db.supply_cable_size_mm2,
                "supply_cable_length_m": db.supply_cable_length_m,
                "main_breaker_a": db.main_breaker_a,
                "earth_leakage": db.earth_leakage,
                "surge_protection": db.surge_protection,
                "spare_ways": db.spare_ways,
                "confidence": db.confidence.value,
                "circuits": [],
            }

            for circuit in db.circuits:
                ckt_data = {
                    "id": circuit.id,
                    "type": circuit.type,
                    "description": circuit.description,
                    "wattage_w": circuit.wattage_w,
                    "cable_size_mm2": circuit.cable_size_mm2,
                    "cable_cores": circuit.cable_cores,
                    "breaker_a": circuit.breaker_a,
                    "breaker_poles": circuit.breaker_poles,
                    "num_points": circuit.num_points,
                    "is_spare": circuit.is_spare,
                    "has_isolator": circuit.has_isolator,
                    "confidence": circuit.confidence.value,
                }
                db_data["circuits"].append(ckt_data)

            block_data["distribution_boards"].append(db_data)

        for room in block.rooms:
            room_data = {
                "name": room.name,
                "type": room.type,
                "area_m2": room.area_m2,
                "confidence": room.confidence.value,
                "fixtures": {
                    "recessed_led_600x1200": room.fixtures.recessed_led_600x1200,
                    "surface_mount_led_18w": room.fixtures.surface_mount_led_18w,
                    "downlight_led_6w": room.fixtures.downlight_led_6w,
                    "vapor_proof_2x24w": room.fixtures.vapor_proof_2x24w,
                    "vapor_proof_2x18w": room.fixtures.vapor_proof_2x18w,
                    "bulkhead_26w": room.fixtures.bulkhead_26w,
                    "flood_light_200w": room.fixtures.flood_light_200w,
                    "pole_light_60w": room.fixtures.pole_light_60w,
                    # v4.4 - Pool lighting
                    "pool_flood_light": room.fixtures.pool_flood_light,
                    "pool_underwater_light": room.fixtures.pool_underwater_light,
                    "double_socket_300": room.fixtures.double_socket_300,
                    "double_socket_1100": room.fixtures.double_socket_1100,
                    "single_socket_300": room.fixtures.single_socket_300,
                    "double_socket_waterproof": room.fixtures.double_socket_waterproof,
                    "switch_1lever_1way": room.fixtures.switch_1lever_1way,
                    "switch_2lever_1way": room.fixtures.switch_2lever_1way,
                    "isolator_30a": room.fixtures.isolator_30a,
                    "data_points_cat6": room.fixtures.data_points_cat6,
                }
            }
            block_data["rooms"].append(room_data)

        result["building_blocks"].append(block_data)

    for run in extraction.site_cable_runs:
        result["site_cable_runs"].append({
            "from_point": run.from_point,
            "to_point": run.to_point,
            "cable_spec": run.cable_spec,
            "cable_size_mm2": run.cable_size_mm2,
            "length_m": run.length_m,
            "is_underground": run.is_underground,
            "confidence": run.confidence.value,
        })

    if extraction.outside_lights:
        result["outside_lights"] = {
            "pole_light_60w": extraction.outside_lights.pole_light_60w,
            "flood_light_200w": extraction.outside_lights.flood_light_200w,
            "bulkhead_26w": extraction.outside_lights.bulkhead_26w,
            # v4.4 - Pool lighting
            "pool_flood_light": extraction.outside_lights.pool_flood_light,
            "pool_underwater_light": extraction.outside_lights.pool_underwater_light,
        }

    return result


def _rebuild_extraction_from_dict(
    data: Dict[str, Any],
    original: ExtractionResult,
) -> ExtractionResult:
    """Rebuild ExtractionResult from corrected dictionary."""
    extraction = ExtractionResult(
        extraction_mode=original.extraction_mode,
        metadata=original.metadata,
        pages_processed=original.pages_processed,
        pages_with_data=original.pages_with_data,
    )

    # Rebuild building blocks
    for block_data in data.get("building_blocks") or []:
        block = BuildingBlock(name=block_data.get("name") or "")

        # Rebuild distribution boards
        for db_data in block_data.get("distribution_boards") or []:
            db = DistributionBoard(
                name=db_data.get("name") or "",
                description=db_data.get("description") or "",
                location=db_data.get("location") or "",
                building_block=block.name,
                supply_from=db_data.get("supply_from") or "",
                supply_cable=db_data.get("supply_cable") or "",
                supply_cable_size_mm2=float(db_data.get("supply_cable_size_mm2") or 0),
                supply_cable_length_m=float(db_data.get("supply_cable_length_m") or 0),
                main_breaker_a=int(db_data.get("main_breaker_a") or 0),
                earth_leakage=db_data.get("earth_leakage") or False,
                earth_leakage_rating_a=int(db_data.get("earth_leakage_rating_a") or 0),
                surge_protection=db_data.get("surge_protection") or False,
                spare_ways=int(db_data.get("spare_ways") or 0),
                confidence=_parse_confidence(db_data.get("confidence") or "extracted"),
            )

            # Rebuild circuits (v4.3 enhanced)
            for ckt_data in db_data.get("circuits") or []:
                circuit = Circuit(
                    id=ckt_data.get("id") or "",
                    type=ckt_data.get("type") or "power",
                    description=ckt_data.get("description") or "",
                    wattage_w=float(ckt_data.get("wattage_w") or 0),
                    wattage_formula=ckt_data.get("wattage_formula") or "",
                    cable_size_mm2=float(ckt_data.get("cable_size_mm2") or 2.5),
                    cable_cores=int(ckt_data.get("cable_cores") or 3),
                    cable_type=ckt_data.get("cable_type") or "GP WIRE",
                    breaker_a=int(ckt_data.get("breaker_a") or 20),
                    breaker_poles=int(ckt_data.get("breaker_poles") or 1),
                    num_points=int(ckt_data.get("num_points") or 0),
                    is_spare=ckt_data.get("is_spare") or False,
                    has_isolator=ckt_data.get("has_isolator") or False,
                    isolator_rating_a=int(ckt_data.get("isolator_rating_a") or 0),
                    has_vsd=ckt_data.get("has_vsd") or False,
                    feeds_board=ckt_data.get("feeds_board"),
                    confidence=_parse_confidence(ckt_data.get("confidence") or "extracted"),
                    # v4.3 fields
                    vsd_rating_kw=float(ckt_data.get("vsd_rating_kw") or 0),
                    starter_type=ckt_data.get("starter_type") or "",
                    has_day_night=ckt_data.get("has_day_night") or False,
                    has_bypass=ckt_data.get("has_bypass") or False,
                    controlled_circuits=ckt_data.get("controlled_circuits") or [],
                    equipment_type=ckt_data.get("equipment_type") or "",
                )
                db.circuits.append(circuit)

            block.distribution_boards.append(db)

        # Rebuild rooms
        for room_data in block_data.get("rooms") or []:
            fixtures_data = room_data.get("fixtures") or {}
            room = Room(
                name=room_data.get("name") or "",
                type=room_data.get("type") or "",
                area_m2=float(room_data.get("area_m2") or 0),
                building_block=block.name,
                confidence=_parse_confidence(room_data.get("confidence") or "extracted"),
            )
            room.fixtures = FixtureCounts(
                recessed_led_600x1200=int(fixtures_data.get("recessed_led_600x1200") or 0),
                surface_mount_led_18w=int(fixtures_data.get("surface_mount_led_18w") or 0),
                downlight_led_6w=int(fixtures_data.get("downlight_led_6w") or 0),
                vapor_proof_2x24w=int(fixtures_data.get("vapor_proof_2x24w") or 0),
                vapor_proof_2x18w=int(fixtures_data.get("vapor_proof_2x18w") or 0),
                bulkhead_26w=int(fixtures_data.get("bulkhead_26w") or 0),
                flood_light_200w=int(fixtures_data.get("flood_light_200w") or 0),
                pole_light_60w=int(fixtures_data.get("pole_light_60w") or 0),
                # v4.4 - Pool lighting
                pool_flood_light=int(fixtures_data.get("pool_flood_light") or 0),
                pool_underwater_light=int(fixtures_data.get("pool_underwater_light") or 0),
                double_socket_300=int(fixtures_data.get("double_socket_300") or 0),
                double_socket_1100=int(fixtures_data.get("double_socket_1100") or 0),
                single_socket_300=int(fixtures_data.get("single_socket_300") or 0),
                double_socket_waterproof=int(fixtures_data.get("double_socket_waterproof") or 0),
                switch_1lever_1way=int(fixtures_data.get("switch_1lever_1way") or 0),
                switch_2lever_1way=int(fixtures_data.get("switch_2lever_1way") or 0),
                isolator_30a=int(fixtures_data.get("isolator_30a") or 0),
                data_points_cat6=int(fixtures_data.get("data_points_cat6") or 0),
            )
            block.rooms.append(room)

        extraction.building_blocks.append(block)

    # Rebuild site cable runs
    for run_data in data.get("site_cable_runs") or []:
        run = SiteCableRun(
            from_point=run_data.get("from_point") or "",
            to_point=run_data.get("to_point") or "",
            cable_spec=run_data.get("cable_spec") or "",
            cable_size_mm2=float(run_data.get("cable_size_mm2") or 0),
            length_m=float(run_data.get("length_m") or 0),
            is_underground=run_data.get("is_underground") if run_data.get("is_underground") is not None else True,
            needs_trenching=run_data.get("needs_trenching") if run_data.get("needs_trenching") is not None else True,
            confidence=_parse_confidence(run_data.get("confidence") or "estimated"),
        )
        extraction.site_cable_runs.append(run)

    # Rebuild outside lights (v4.4 - includes pool lighting)
    outside_data = data.get("outside_lights") or {}
    if outside_data:
        extraction.outside_lights = FixtureCounts(
            pole_light_60w=int(outside_data.get("pole_light_60w") or 0),
            flood_light_200w=int(outside_data.get("flood_light_200w") or 0),
            bulkhead_26w=int(outside_data.get("bulkhead_26w") or 0),
            # v4.4 - Pool lighting
            pool_flood_light=int(outside_data.get("pool_flood_light") or 0),
            pool_underwater_light=int(outside_data.get("pool_underwater_light") or 0),
        )

    return extraction
