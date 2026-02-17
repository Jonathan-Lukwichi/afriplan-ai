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
CONFIDENCE_THRESHOLD = 0.70  # Below this, escalate to Opus


def discover(
    doc_set: DocumentSet,
    tier: ServiceTier,
    mode: ExtractionMode,
    building_blocks: List[str],
    client: Optional[object] = None,
) -> Tuple[ExtractionResult, StageResult]:
    """
    DISCOVER stage: Extract structured data from documents.

    Args:
        doc_set: Processed documents from INGEST stage
        tier: Classification tier from CLASSIFY stage
        mode: Extraction mode (AS_BUILT, ESTIMATION, etc.)
        building_blocks: List of building block names
        client: Anthropic API client

    Returns:
        Tuple of (ExtractionResult, StageResult)
    """
    with Timer("discover") as timer:
        errors = []
        warnings = []
        total_tokens = 0
        total_cost = 0.0
        model_used = DISCOVER_MODEL

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
                sld_data, tokens, cost = _extract_sld_data(sld_pages, client)
                total_tokens += tokens
                total_cost += cost
                _merge_sld_data(extraction, sld_data)
                extraction.pages_with_data += len(sld_pages)
            except Exception as e:
                errors.append(f"SLD extraction failed: {str(e)}")

        # Extract from lighting pages
        if lighting_pages and client:
            try:
                lighting_data, tokens, cost = _extract_lighting_data(lighting_pages, client)
                total_tokens += tokens
                total_cost += cost
                _merge_lighting_data(extraction, lighting_data)
                extraction.pages_with_data += len(lighting_pages)
            except Exception as e:
                errors.append(f"Lighting extraction failed: {str(e)}")

        # Extract from plug pages
        if plug_pages and client:
            try:
                plug_data, tokens, cost = _extract_plug_data(plug_pages, client)
                total_tokens += tokens
                total_cost += cost
                _merge_plug_data(extraction, plug_data)
                extraction.pages_with_data += len(plug_pages)
            except Exception as e:
                errors.append(f"Plug extraction failed: {str(e)}")

        # Extract from outside lights pages
        if outside_pages and client:
            try:
                outside_data, tokens, cost = _extract_outside_data(outside_pages, client)
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
        model=DISCOVER_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(DISCOVER_MODEL, response.usage.input_tokens, response.usage.output_tokens)

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_lighting_data(
    pages: List,
    client: object,
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
        model=DISCOVER_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(DISCOVER_MODEL, response.usage.input_tokens, response.usage.output_tokens)

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_plug_data(
    pages: List,
    client: object,
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
        model=DISCOVER_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(DISCOVER_MODEL, response.usage.input_tokens, response.usage.output_tokens)

    parsed = parse_json_safely(response_text) or {}
    return parsed, tokens, cost


def _extract_outside_data(
    pages: List,
    client: object,
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
        model=DISCOVER_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    cost = estimate_cost_zar(DISCOVER_MODEL, response.usage.input_tokens, response.usage.output_tokens)

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
            supply_cable_size_mm2=float(db_data.get("supply_cable_size_mm2", 0)),
            supply_cable_length_m=float(db_data.get("supply_cable_length_m", 0)),
            main_breaker_a=int(db_data.get("main_breaker_a", 0)),
            earth_leakage=db_data.get("earth_leakage", False),
            earth_leakage_rating_a=int(db_data.get("earth_leakage_rating_a", 0)),
            surge_protection=db_data.get("surge_protection", False),
            spare_ways=int(db_data.get("spare_ways", 0)),
            confidence=_parse_confidence(db_data.get("confidence", "extracted")),
        )

        # Add circuits
        for ckt_data in db_data.get("circuits", []):
            circuit = Circuit(
                id=ckt_data.get("id", ""),
                type=ckt_data.get("type", "power"),
                description=ckt_data.get("description", ""),
                wattage_w=float(ckt_data.get("wattage_w", 0)),
                wattage_formula=ckt_data.get("wattage_formula", ""),
                cable_size_mm2=float(ckt_data.get("cable_size_mm2", 2.5)),
                cable_cores=int(ckt_data.get("cable_cores", 3)),
                cable_type=ckt_data.get("cable_type", "GP WIRE"),
                breaker_a=int(ckt_data.get("breaker_a", 20)),
                breaker_poles=int(ckt_data.get("breaker_poles", 1)),
                num_points=int(ckt_data.get("num_points", 0)),
                is_spare=ckt_data.get("is_spare", False),
                has_isolator=ckt_data.get("has_isolator", False),
                isolator_rating_a=int(ckt_data.get("isolator_rating_a", 0)),
                has_vsd=ckt_data.get("has_vsd", False),
                feeds_board=ckt_data.get("feeds_board"),
                confidence=_parse_confidence(ckt_data.get("confidence", "extracted")),
            )
            db.circuits.append(circuit)

        block.distribution_boards.append(db)

    # Add heavy equipment
    for eq_data in data.get("heavy_equipment", []):
        equipment = HeavyEquipment(
            name=eq_data.get("name", ""),
            type=eq_data.get("type", ""),
            rating_kw=float(eq_data.get("rating_kw", 0)),
            cable_size_mm2=float(eq_data.get("cable_size_mm2", 4)),
            cable_type=eq_data.get("cable_type", "PVC SWA PVC"),
            breaker_a=int(eq_data.get("breaker_a", 32)),
            has_vsd=eq_data.get("has_vsd", False),
            has_dol=eq_data.get("has_dol", False),
            isolator_a=int(eq_data.get("isolator_a", 0)),
            fed_from_db=eq_data.get("fed_from_db", ""),
            building_block=block.name,
            qty=int(eq_data.get("qty", 1)),
            confidence=_parse_confidence(eq_data.get("confidence", "extracted")),
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
            name=room_data.get("name", ""),
            room_number=int(room_data.get("room_number", 0)),
            type=room_data.get("type", ""),
            area_m2=float(room_data.get("area_m2", 0)),
            floor=room_data.get("floor", ""),
            building_block=block.name,
            circuit_refs=room_data.get("circuit_refs", []),
            is_wet_area=room_data.get("is_wet_area", False),
            confidence=_parse_confidence(room_data.get("confidence", "extracted")),
            notes=room_data.get("notes", []),
        )

        # Set fixture counts
        room.fixtures = FixtureCounts(
            recessed_led_600x1200=int(fixtures_data.get("recessed_led_600x1200", 0)),
            surface_mount_led_18w=int(fixtures_data.get("surface_mount_led_18w", 0)),
            flood_light_30w=int(fixtures_data.get("flood_light_30w", 0)),
            flood_light_200w=int(fixtures_data.get("flood_light_200w", 0)),
            downlight_led_6w=int(fixtures_data.get("downlight_led_6w", 0)),
            vapor_proof_2x24w=int(fixtures_data.get("vapor_proof_2x24w", 0)),
            vapor_proof_2x18w=int(fixtures_data.get("vapor_proof_2x18w", 0)),
            prismatic_2x18w=int(fixtures_data.get("prismatic_2x18w", 0)),
            bulkhead_26w=int(fixtures_data.get("bulkhead_26w", 0)),
            bulkhead_24w=int(fixtures_data.get("bulkhead_24w", 0)),
            fluorescent_50w_5ft=int(fixtures_data.get("fluorescent_50w_5ft", 0)),
            pole_light_60w=int(fixtures_data.get("pole_light_60w", 0)),
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
            existing_room.fixtures.double_socket_300 = int(fixtures_data.get("double_socket_300", 0))
            existing_room.fixtures.single_socket_300 = int(fixtures_data.get("single_socket_300", 0))
            existing_room.fixtures.double_socket_1100 = int(fixtures_data.get("double_socket_1100", 0))
            existing_room.fixtures.single_socket_1100 = int(fixtures_data.get("single_socket_1100", 0))
            existing_room.fixtures.double_socket_waterproof = int(fixtures_data.get("double_socket_waterproof", 0))
            existing_room.fixtures.double_socket_ceiling = int(fixtures_data.get("double_socket_ceiling", 0))
            existing_room.fixtures.data_points_cat6 = int(fixtures_data.get("data_points_cat6", 0))
            existing_room.fixtures.floor_box = int(fixtures_data.get("floor_box", 0))
            existing_room.fixtures.switch_1lever_1way = int(fixtures_data.get("switch_1lever_1way", 0))
            existing_room.fixtures.switch_2lever_1way = int(fixtures_data.get("switch_2lever_1way", 0))
            existing_room.fixtures.switch_1lever_2way = int(fixtures_data.get("switch_1lever_2way", 0))
            existing_room.fixtures.day_night_switch = int(fixtures_data.get("day_night_switch", 0))
            existing_room.fixtures.isolator_30a = int(fixtures_data.get("isolator_30a", 0))
            existing_room.fixtures.isolator_20a = int(fixtures_data.get("isolator_20a", 0))
            existing_room.fixtures.master_switch = int(fixtures_data.get("master_switch", 0))
            existing_room.has_ac = room_data.get("has_ac", False)
            existing_room.has_geyser = room_data.get("has_geyser", False)
        else:
            # Create new room with socket data
            room = Room(
                name=room_name,
                building_block=block.name,
                has_ac=room_data.get("has_ac", False),
                has_geyser=room_data.get("has_geyser", False),
                confidence=_parse_confidence(room_data.get("confidence", "extracted")),
            )
            room.fixtures = FixtureCounts(
                double_socket_300=int(fixtures_data.get("double_socket_300", 0)),
                single_socket_300=int(fixtures_data.get("single_socket_300", 0)),
                double_socket_1100=int(fixtures_data.get("double_socket_1100", 0)),
                single_socket_1100=int(fixtures_data.get("single_socket_1100", 0)),
                double_socket_waterproof=int(fixtures_data.get("double_socket_waterproof", 0)),
                double_socket_ceiling=int(fixtures_data.get("double_socket_ceiling", 0)),
                data_points_cat6=int(fixtures_data.get("data_points_cat6", 0)),
                floor_box=int(fixtures_data.get("floor_box", 0)),
                switch_1lever_1way=int(fixtures_data.get("switch_1lever_1way", 0)),
                switch_2lever_1way=int(fixtures_data.get("switch_2lever_1way", 0)),
                switch_1lever_2way=int(fixtures_data.get("switch_1lever_2way", 0)),
                day_night_switch=int(fixtures_data.get("day_night_switch", 0)),
                isolator_30a=int(fixtures_data.get("isolator_30a", 0)),
                isolator_20a=int(fixtures_data.get("isolator_20a", 0)),
                master_switch=int(fixtures_data.get("master_switch", 0)),
            )
            block.rooms.append(room)


def _merge_outside_data(extraction: ExtractionResult, data: Dict[str, Any]) -> None:
    """Merge outside lights and site cable data into ExtractionResult."""
    # Add site cable runs
    for run_data in data.get("site_cable_runs", []):
        run = SiteCableRun(
            from_point=run_data.get("from_point", ""),
            to_point=run_data.get("to_point", ""),
            cable_spec=run_data.get("cable_spec", ""),
            cable_size_mm2=float(run_data.get("cable_size_mm2", 0)),
            cable_cores=int(run_data.get("cable_cores", 4)),
            cable_type=run_data.get("cable_type", "PVC SWA PVC"),
            length_m=float(run_data.get("length_m", 0)),
            is_underground=run_data.get("is_underground", True),
            needs_trenching=run_data.get("needs_trenching", True),
            confidence=_parse_confidence(run_data.get("confidence", "estimated")),
            notes=run_data.get("notes", ""),
        )
        extraction.site_cable_runs.append(run)

    # Add outside lights
    outside_data = data.get("outside_lights", {})
    if outside_data:
        extraction.outside_lights = FixtureCounts(
            pole_light_60w=int(outside_data.get("pole_light_60w", 0)),
            flood_light_200w=int(outside_data.get("flood_light_200w", 0)),
            flood_light_30w=int(outside_data.get("flood_light_30w", 0)),
            bulkhead_26w=int(outside_data.get("bulkhead_26w", 0)),
            bulkhead_24w=int(outside_data.get("bulkhead_24w", 0)),
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
    """Calculate overall extraction confidence."""
    if extraction.pages_processed == 0:
        return 0.0

    # Base confidence from data completeness
    completeness = extraction.completeness

    # Adjust based on extracted vs estimated items
    total_items = 0
    extracted_items = 0

    for block in extraction.building_blocks:
        for db in block.distribution_boards:
            total_items += 1
            if db.confidence == ItemConfidence.EXTRACTED:
                extracted_items += 1
            for circuit in db.circuits:
                total_items += 1
                if circuit.confidence == ItemConfidence.EXTRACTED:
                    extracted_items += 1

        for room in block.rooms:
            total_items += 1
            if room.confidence == ItemConfidence.EXTRACTED:
                extracted_items += 1

    for run in extraction.site_cable_runs:
        total_items += 1
        if run.confidence == ItemConfidence.EXTRACTED:
            extracted_items += 1

    item_confidence = extracted_items / total_items if total_items > 0 else 0.5

    # Weighted average
    confidence = (completeness * 0.4 + item_confidence * 0.6)
    return min(1.0, max(0.0, confidence))


def _escalate_to_opus(
    doc_set: DocumentSet,
    extraction: ExtractionResult,
    client: object,
) -> Tuple[ExtractionResult, int, float]:
    """Re-extract with Opus 4.6 for low-confidence results."""
    # For now, return existing extraction
    # Full implementation would re-run extraction with Opus
    return extraction, 0, 0.0
