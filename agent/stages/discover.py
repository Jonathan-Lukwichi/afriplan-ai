"""
DISCOVER Stage: JSON extraction using Sonnet 4.5.

Extracts structured electrical data from drawings including:
- Distribution boards and circuits from SLDs
- Fixture counts from lighting layouts
- Socket/switch counts from plug layouts
- Site cable runs from outside lights drawings
"""

import json
from typing import Tuple, Optional, List, Dict, Any

from agent.models import (
    DocumentSet, ExtractionResult, ExtractionMode, ServiceTier,
    StageResult, PipelineStage, PageType, ItemConfidence,
    BuildingBlock, DistributionBoard, Circuit, Room, FixtureCounts,
    HeavyEquipment, SiteCableRun, ProjectMetadata, SupplyPoint
)
from agent.utils import parse_json_safely, Timer, estimate_cost_zar
from agent.prompts.schemas import (
    SLD_SCHEMA, LIGHTING_LAYOUT_SCHEMA, PLUGS_LAYOUT_SCHEMA,
    OUTSIDE_LIGHTS_SCHEMA, CONFIDENCE_INSTRUCTION
)
from agent.prompts.system_prompt import SYSTEM_PROMPT
from agent.prompts.sld_prompt import get_sld_extraction_prompt
from agent.prompts.lighting_layout_prompt import get_prompt as get_lighting_prompt

# Extraction model
DISCOVER_MODEL = "claude-sonnet-4-20250514"
ESCALATION_MODEL = "claude-opus-4-20250514"
CONFIDENCE_THRESHOLD = 0.80  # Below 80%, escalate to Opus for verification


def discover(
    doc_set: DocumentSet,
    tier: ServiceTier,
    mode: ExtractionMode,
    building_blocks: List[str],
    client: Optional[object] = None,
    use_opus_directly: bool = False,
) -> Tuple[ExtractionResult, StageResult]:
    """
    DISCOVER stage: Extract structured data from documents.

    Args:
        doc_set: Processed documents from INGEST stage
        tier: Classification tier from CLASSIFY stage
        mode: Extraction mode (AS_BUILT, ESTIMATION, etc.)
        building_blocks: List of building block names
        client: Anthropic API client
        use_opus_directly: If True, use Opus for initial extraction (slower but more accurate)

    Returns:
        Tuple of (ExtractionResult, StageResult)
    """
    with Timer("discover") as timer:
        errors = []
        warnings = []
        total_tokens = 0
        total_cost = 0.0

        # Select model based on accuracy preference
        extraction_model = ESCALATION_MODEL if use_opus_directly else DISCOVER_MODEL
        model_used = extraction_model

        if use_opus_directly:
            warnings.append("Using Opus for maximum extraction accuracy (slower, higher cost)")

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

    # Build content with images
    content = [{"type": "text", "text": prompt}]
    for page in pages[:5]:  # Limit to 5 pages
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
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)

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

    content = [{"type": "text", "text": prompt}]
    for page in pages[:5]:
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
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_plug_data(
    pages: List,
    client: object,
    model: str = DISCOVER_MODEL,
) -> Tuple[Dict[str, Any], int, float]:
    """Extract socket/switch data from plug layout pages."""
    prompt = f"""{SYSTEM_PROMPT}

{CONFIDENCE_INSTRUCTION}

Extract room and socket/switch data from these plug layout drawings.
Return JSON matching this schema:
{PLUGS_LAYOUT_SCHEMA}
"""

    content = [{"type": "text", "text": prompt}]
    for page in pages[:5]:
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
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)

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

    content = [{"type": "text", "text": prompt}]
    for page in pages[:3]:
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
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _merge_sld_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge SLD extraction data into ExtractionResult."""
    block_name = data.get("building_block", "")

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

    # Add distribution boards
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
            main_breaker_a=int(db_data.get("main_breaker_a") or 0),
            earth_leakage=db_data.get("earth_leakage") or False,
            earth_leakage_rating_a=int(db_data.get("earth_leakage_rating_a") or 0),
            surge_protection=db_data.get("surge_protection") or False,
            spare_ways=int(db_data.get("spare_ways") or 0),
            confidence=_parse_confidence(db_data.get("confidence", "extracted")),
        )

        # Add circuits
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
                breaker_a=int(ckt_data.get("breaker_a") or 20),
                breaker_poles=int(ckt_data.get("breaker_poles") or 1),
                num_points=int(ckt_data.get("num_points") or 0),
                is_spare=ckt_data.get("is_spare") or False,
                has_isolator=ckt_data.get("has_isolator") or False,
                isolator_rating_a=int(ckt_data.get("isolator_rating_a") or 0),
                has_vsd=ckt_data.get("has_vsd") or False,
                feeds_board=ckt_data.get("feeds_board"),
                confidence=_parse_confidence(ckt_data.get("confidence") or "extracted"),
            )
            db.circuits.append(circuit)

        block.distribution_boards.append(db)

    # Add heavy equipment
    for eq_data in data.get("heavy_equipment", []):
        equipment = HeavyEquipment(
            name=eq_data.get("name") or "",
            type=eq_data.get("type") or "",
            rating_kw=float(eq_data.get("rating_kw") or 0),
            cable_size_mm2=float(eq_data.get("cable_size_mm2") or 4),
            cable_type=eq_data.get("cable_type") or "PVC SWA PVC",
            breaker_a=int(eq_data.get("breaker_a") or 32),
            has_vsd=eq_data.get("has_vsd") or False,
            has_dol=eq_data.get("has_dol") or False,
            isolator_a=int(eq_data.get("isolator_a") or 0),
            fed_from_db=eq_data.get("fed_from_db") or "",
            building_block=block.name,
            qty=int(eq_data.get("qty") or 1),
            confidence=_parse_confidence(eq_data.get("confidence") or "extracted"),
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

        # Set fixture counts
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
    # Add site cable runs
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
        )
        extraction.site_cable_runs.append(run)

    # Add outside lights
    outside_data = data.get("outside_lights") or {}
    if outside_data:
        extraction.outside_lights = FixtureCounts(
            pole_light_60w=int(outside_data.get("pole_light_60w") or 0),
            flood_light_200w=int(outside_data.get("flood_light_200w") or 0),
            flood_light_30w=int(outside_data.get("flood_light_30w") or 0),
            bulkhead_26w=int(outside_data.get("bulkhead_26w") or 0),
            bulkhead_24w=int(outside_data.get("bulkhead_24w") or 0),
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

            # Rebuild circuits
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

    # Rebuild outside lights
    outside_data = data.get("outside_lights") or {}
    if outside_data:
        extraction.outside_lights = FixtureCounts(
            pole_light_60w=int(outside_data.get("pole_light_60w") or 0),
            flood_light_200w=int(outside_data.get("flood_light_200w") or 0),
            bulkhead_26w=int(outside_data.get("bulkhead_26w") or 0),
        )

    return extraction
