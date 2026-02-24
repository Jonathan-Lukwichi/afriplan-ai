"""
AfriPlan Electrical v4.11 - Interactive Pass Manager

Wraps multi_pass_discover functions for step-by-step interactive use.
Allows running individual passes with user validation between steps.

Target: 70%+ extraction rate through human-in-the-loop validation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from agent.models import (
    ExtractionResult, PageInfo,
    ItemConfidence,
)
from agent.stages.multi_pass_discover import (
    run_pass, ExtractionPass, MultiPassState, PassResult,
    PROMPT_PROJECT_INFO, PROMPT_DB_DETECTION, PROMPT_ROOM_DETECTION,
    PROMPT_CABLE_ROUTES, PROMPT_SUPPLY_POINT, PROMPT_LEGEND_LIGHTING,
    PROMPT_LEGEND_POWER, get_db_schedule_prompt, get_room_fixtures_prompt,
    get_room_fixtures_prompt_with_legend, build_extraction_result,
)


@dataclass
class InteractivePassResult:
    """Result from an interactive pass with UI-friendly data."""
    success: bool
    confidence: float
    raw_data: Dict[str, Any]
    display_data: Dict[str, Any]  # Formatted for UI display
    tokens_used: int = 0
    cost_zar: float = 0.0
    error: str = ""


class InteractivePipeline:
    """
    Interactive pipeline for step-by-step extraction with user validation.

    Usage:
        pipeline = InteractivePipeline(client, model, provider)

        # Step 2: Project Info
        result = pipeline.run_project_info_pass(cover_pages)
        # User validates/edits in UI
        pipeline.apply_project_info(edited_data)

        # Step 3: DB Detection
        result = pipeline.run_db_detection_pass(sld_pages)
        # User validates/edits
        pipeline.apply_detected_dbs(edited_db_list)

        # Step 4: DB Schedules (loop)
        for db_name in detected_dbs:
            result = pipeline.run_db_schedule_pass(db_name, sld_pages)
            # User validates
            pipeline.apply_db_schedule(db_name, edited_data)

        # ... continue for rooms and cable routes

        # Build final result
        extraction = pipeline.build_final_result()
    """

    def __init__(
        self,
        client: object,
        model: str,
        provider: str = "groq",
    ):
        """
        Initialize the interactive pipeline.

        Args:
            client: LLM API client (Groq, Claude, etc.)
            model: Model name to use
            provider: Provider name ("groq", "claude", "gemini", "grok")
        """
        self.client = client
        self.model = model
        self.provider = provider
        self.state = MultiPassState()
        self._categorized_pages: Dict[str, List[PageInfo]] = {}

    def set_categorized_pages(self, pages: Dict[str, List[PageInfo]]) -> None:
        """
        Set user-categorized pages for targeted extraction.

        Args:
            pages: Dict mapping category names to page lists.
                   Categories: "Cover", "SLD", "Lighting", "Power", "Legend", "Other"
        """
        self._categorized_pages = pages

    def get_pages_by_category(self, category: str) -> List[PageInfo]:
        """Get pages for a specific category."""
        return self._categorized_pages.get(category, [])

    # ==========================================
    # PASS 1: PROJECT INFO
    # ==========================================

    def run_project_info_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 1: Extract project information from cover page(s).

        Args:
            pages: Cover pages to process. If None, uses categorized "Cover" pages.

        Returns:
            InteractivePassResult with project info data
        """
        if pages is None:
            pages = self.get_pages_by_category("Cover")

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={
                    "project_name": "",
                    "client_name": "",
                    "consultant_name": "",
                    "date": "",
                    "revision": "",
                },
                error="No cover pages provided"
            )

        result = run_pass(
            ExtractionPass.PROJECT_INFO,
            PROMPT_PROJECT_INFO,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        display_data = {
            "project_name": data.get("project_name", ""),
            "client_name": data.get("client_name", ""),
            "consultant_name": data.get("consultant_name", ""),
            "date": data.get("date", ""),
            "revision": data.get("revision", ""),
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=result.success and bool(display_data.get("project_name")),
            confidence=0.85 if result.success and display_data.get("project_name") else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_project_info(self, data: Dict[str, str]) -> None:
        """
        Apply user-validated project info to state.

        Args:
            data: Dict with project_name, client_name, consultant_name, date, revision
        """
        self.state.project_name = data.get("project_name", "")
        self.state.client_name = data.get("client_name", "")
        self.state.consultant_name = data.get("consultant_name", "")
        if ExtractionPass.PROJECT_INFO not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.PROJECT_INFO)

    # ==========================================
    # PASS 2: DB DETECTION
    # ==========================================

    def run_db_detection_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 2: Detect distribution boards from SLD pages.

        Args:
            pages: SLD pages to process. If None, uses categorized "SLD" pages.

        Returns:
            InteractivePassResult with detected DB list
        """
        if pages is None:
            pages = self.get_pages_by_category("SLD")

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={"dbs": [], "count": 0},
                error="No SLD pages provided"
            )

        result = run_pass(
            ExtractionPass.DB_DETECTION,
            PROMPT_DB_DETECTION,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        dbs = data.get("distribution_boards", [])
        db_list = [
            {"name": db.get("name", ""), "location": db.get("location", "")}
            for db in dbs if db.get("name")
        ]

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=result.success and len(db_list) > 0,
            confidence=0.92 if len(db_list) > 0 else 0.3,
            raw_data=data,
            display_data={"dbs": db_list, "count": len(db_list)},
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_detected_dbs(self, db_names: List[str]) -> None:
        """
        Apply user-validated DB list to state.

        Args:
            db_names: List of DB names (e.g., ["DB-GF", "DB-S1", "DB-S2"])
        """
        self.state.db_names = db_names
        if ExtractionPass.DB_DETECTION not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.DB_DETECTION)

    # ==========================================
    # PASS 3: DB SCHEDULES (per DB)
    # ==========================================

    def run_db_schedule_pass(
        self,
        db_name: str,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 3: Extract circuit schedule for ONE specific DB.

        Args:
            db_name: Name of the DB to extract (e.g., "DB-S1")
            pages: SLD pages to process. If None, uses categorized "SLD" pages.

        Returns:
            InteractivePassResult with circuit schedule data
        """
        if pages is None:
            pages = self.get_pages_by_category("SLD")

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={
                    "db_name": db_name,
                    "schedule_found": False,
                    "circuits": [],
                },
                error="No SLD pages provided"
            )

        result = run_pass(
            ExtractionPass.DB_SCHEDULES,
            get_db_schedule_prompt(db_name),
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        schedule_found = data.get("schedule_found", False)
        circuits = data.get("circuits", [])

        display_data = {
            "db_name": db_name,
            "main_breaker_a": data.get("main_breaker_a", 0),
            "supply_from": data.get("supply_from", ""),
            "supply_cable_mm2": data.get("supply_cable_mm2", 0),
            "circuits": circuits,
            "spare_count": data.get("spare_count", 0),
            "total_ways": data.get("total_ways", len(circuits)),
            "schedule_found": schedule_found,
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=schedule_found,
            confidence=0.78 if schedule_found else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_db_schedule(self, db_name: str, schedule_data: Dict) -> None:
        """
        Apply user-validated DB schedule to state.

        Args:
            db_name: Name of the DB
            schedule_data: Dict with main_breaker_a, supply_from, circuits, etc.
        """
        self.state.db_schedules[db_name] = schedule_data

    def mark_db_schedules_complete(self) -> None:
        """Mark DB schedules pass as complete after processing all DBs."""
        if ExtractionPass.DB_SCHEDULES not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.DB_SCHEDULES)

    # ==========================================
    # PASS 4: ROOM DETECTION
    # ==========================================

    def run_room_detection_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 4: Detect rooms from layout pages.

        Args:
            pages: Layout pages to process. If None, uses Lighting + Power pages.

        Returns:
            InteractivePassResult with detected room list
        """
        if pages is None:
            lighting = self.get_pages_by_category("Lighting")
            power = self.get_pages_by_category("Power")
            pages = lighting + power

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={"rooms": [], "count": 0},
                error="No layout pages provided"
            )

        result = run_pass(
            ExtractionPass.ROOM_DETECTION,
            PROMPT_ROOM_DETECTION,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        rooms = data.get("rooms", [])
        room_list = [
            {
                "name": r.get("name", ""),
                "floor": r.get("floor", ""),
                "is_wet_area": r.get("is_wet_area", False),
                "building_block": r.get("building_block", ""),
            }
            for r in rooms if r.get("name")
        ]

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=result.success and len(room_list) > 0,
            confidence=0.88 if len(room_list) > 0 else 0.3,
            raw_data=data,
            display_data={"rooms": room_list, "count": len(room_list)},
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_detected_rooms(self, room_names: List[str]) -> None:
        """
        Apply user-validated room list to state.

        Args:
            room_names: List of room names
        """
        self.state.room_names = room_names
        if ExtractionPass.ROOM_DETECTION not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.ROOM_DETECTION)

    # ==========================================
    # PASS 5: ROOM FIXTURES (per room)
    # ==========================================

    def run_room_fixtures_pass(
        self,
        room_name: str,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 5: Extract fixtures for ONE specific room.

        Args:
            room_name: Name of the room to extract
            pages: Layout pages to process. If None, uses Lighting + Power pages.

        Returns:
            InteractivePassResult with fixture counts
        """
        if pages is None:
            lighting = self.get_pages_by_category("Lighting")
            power = self.get_pages_by_category("Power")
            pages = lighting + power

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={
                    "room_name": room_name,
                    "found_in_drawing": False,
                    "fixtures": {},
                },
                error="No layout pages provided"
            )

        result = run_pass(
            ExtractionPass.ROOM_FIXTURES,
            get_room_fixtures_prompt(room_name),
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        found = data.get("found_in_drawing", False)
        fixtures = data.get("fixtures", {})

        display_data = {
            "room_name": room_name,
            "found_in_drawing": found,
            "fixtures": fixtures,
            "circuit_refs": data.get("circuit_refs", []),
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=found,
            confidence=0.72 if found else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_room_fixtures(self, room_name: str, fixtures_data: Dict) -> None:
        """
        Apply user-validated room fixtures to state.

        Args:
            room_name: Name of the room
            fixtures_data: Dict with fixture counts
        """
        self.state.room_fixtures[room_name] = fixtures_data

    def mark_room_fixtures_complete(self) -> None:
        """Mark room fixtures pass as complete after processing all rooms."""
        if ExtractionPass.ROOM_FIXTURES not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.ROOM_FIXTURES)

    # ==========================================
    # PASS 6: CABLE ROUTES
    # ==========================================

    def run_cable_routes_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Run Pass 6: Extract cable routes from SLD pages.

        Args:
            pages: SLD pages to process. If None, uses categorized "SLD" pages.

        Returns:
            InteractivePassResult with cable route data
        """
        if pages is None:
            pages = self.get_pages_by_category("SLD")

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={"routes": [], "count": 0},
                error="No SLD pages provided"
            )

        result = run_pass(
            ExtractionPass.CABLE_ROUTES,
            PROMPT_CABLE_ROUTES,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        routes = data.get("cable_routes", [])

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=len(routes) > 0,
            confidence=0.85 if routes else 0.4,
            raw_data=data,
            display_data={"routes": routes, "count": len(routes)},
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    def apply_cable_routes(self, routes: List[Dict]) -> None:
        """
        Apply user-validated cable routes to state.

        Args:
            routes: List of cable route dicts with from, to, cable_spec, length_m
        """
        self.state.cable_routes = routes
        if ExtractionPass.CABLE_ROUTES not in self.state.passes_completed:
            self.state.passes_completed.append(ExtractionPass.CABLE_ROUTES)

    # ==========================================
    # NEW: SUPPLY POINT PASS
    # ==========================================

    def run_supply_point_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Extract main supply/metering point from SLD pages.

        Args:
            pages: SLD pages to process.

        Returns:
            InteractivePassResult with supply point data
        """
        if pages is None:
            pages = self.get_pages_by_category("SLD")

        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={
                    "supply_found": False,
                    "name": "",
                    "main_breaker_a": 0,
                },
                error="No SLD pages provided"
            )

        result = run_pass(
            ExtractionPass.DB_DETECTION,  # Reuse pass type for now
            PROMPT_SUPPLY_POINT,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        supply_found = data.get("supply_found", False)

        display_data = {
            "supply_found": supply_found,
            "name": data.get("name", ""),
            "main_breaker_a": data.get("main_breaker_a", 0),
            "meter_type": data.get("meter_type", ""),
            "feeds_to": data.get("feeds_to", ""),
            "cable_spec": data.get("cable_spec", ""),
            "cable_length_m": data.get("cable_length_m"),
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=supply_found,
            confidence=0.85 if supply_found else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    # ==========================================
    # NEW: LIGHTING LEGEND PASS
    # ==========================================

    def run_lighting_legend_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Extract lighting legend from layout pages.

        Args:
            pages: Lighting layout pages to process.

        Returns:
            InteractivePassResult with legend data
        """
        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={"has_legend": False, "light_types": [], "switch_types": []},
                error="No lighting pages provided"
            )

        result = run_pass(
            ExtractionPass.ROOM_DETECTION,  # Reuse pass type for now
            PROMPT_LEGEND_LIGHTING,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        has_legend = data.get("has_legend", False)
        light_types = data.get("light_types", [])
        switch_types = data.get("switch_types", [])

        display_data = {
            "has_legend": has_legend,
            "light_types": light_types,
            "switch_types": switch_types,
            "qtys_visible": data.get("qtys_visible", {}),
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=has_legend and len(light_types) > 0,
            confidence=0.9 if has_legend else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    # ==========================================
    # NEW: POWER LEGEND PASS
    # ==========================================

    def run_power_legend_pass(
        self,
        pages: Optional[List[PageInfo]] = None
    ) -> InteractivePassResult:
        """
        Extract power/plugs legend from layout pages.

        Args:
            pages: Power layout pages to process.

        Returns:
            InteractivePassResult with legend data
        """
        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={"has_legend": False, "socket_types": [], "isolator_types": []},
                error="No power pages provided"
            )

        result = run_pass(
            ExtractionPass.ROOM_DETECTION,  # Reuse pass type for now
            PROMPT_LEGEND_POWER,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        has_legend = data.get("has_legend", False)
        socket_types = data.get("socket_types", [])
        isolator_types = data.get("isolator_types", [])
        equipment = data.get("equipment", [])
        containment = data.get("containment", [])

        display_data = {
            "has_legend": has_legend,
            "socket_types": socket_types,
            "isolator_types": isolator_types,
            "equipment": equipment,
            "containment": containment,
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=has_legend and len(socket_types) > 0,
            confidence=0.9 if has_legend else 0.3,
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    # ==========================================
    # IMPROVED: Room fixtures with legend
    # ==========================================

    def run_room_fixtures_with_legend_pass(
        self,
        room_name: str,
        pages: Optional[List[PageInfo]] = None,
        legend_types: Optional[Dict] = None
    ) -> InteractivePassResult:
        """
        Count fixtures in ONE room using extracted legend types.

        Args:
            room_name: Name of the room to extract
            pages: Layout pages to process.
            legend_types: Dict with light_types, socket_types from legend pass

        Returns:
            InteractivePassResult with fixture counts
        """
        if not pages:
            return InteractivePassResult(
                success=False,
                confidence=0.0,
                raw_data={},
                display_data={
                    "room_name": room_name,
                    "found_in_drawing": False,
                    "fixtures": {},
                },
                error="No layout pages provided"
            )

        # Use legend-aware prompt if legend provided
        if legend_types:
            prompt = get_room_fixtures_prompt_with_legend(room_name, legend_types)
        else:
            prompt = get_room_fixtures_prompt(room_name)

        result = run_pass(
            ExtractionPass.ROOM_FIXTURES,
            prompt,
            pages,
            self.client,
            self.model,
            self.provider,
        )

        # Defensive: ensure data is always a dict
        data = result.data if result.data is not None else {}

        found = data.get("found_in_drawing", False)
        fixtures = data.get("fixtures", {})

        display_data = {
            "room_name": room_name,
            "found_in_drawing": found,
            "fixtures": fixtures,
            "circuit_refs": data.get("circuit_refs", []),
        }

        # Update running totals
        self.state.total_tokens += result.tokens_used
        self.state.total_cost += result.cost_zar

        return InteractivePassResult(
            success=found,
            confidence=0.80 if found else 0.3,  # Higher confidence with legend
            raw_data=data,
            display_data=display_data,
            tokens_used=result.tokens_used,
            cost_zar=result.cost_zar,
            error=result.error,
        )

    # ==========================================
    # RESULT BUILDING
    # ==========================================

    def build_partial_result(self) -> ExtractionResult:
        """
        Build ExtractionResult from current state.
        Can be called at any point to see current extraction progress.

        Returns:
            ExtractionResult with data extracted so far
        """
        return build_extraction_result(self.state)

    def build_final_result(self) -> ExtractionResult:
        """
        Build complete ExtractionResult after all passes.

        Returns:
            Complete ExtractionResult ready for validation and pricing
        """
        # Mark loops as complete if we have any data
        if self.state.db_schedules:
            self.mark_db_schedules_complete()

        if self.state.room_fixtures:
            self.mark_room_fixtures_complete()

        return build_extraction_result(self.state)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current extraction statistics.

        Returns:
            Dict with counts and costs
        """
        return {
            "passes_completed": len(self.state.passes_completed),
            "passes_completed_names": [p.value for p in self.state.passes_completed],
            "dbs_detected": len(self.state.db_names),
            "db_schedules_extracted": len(self.state.db_schedules),
            "rooms_detected": len(self.state.room_names),
            "room_fixtures_extracted": len(self.state.room_fixtures),
            "cable_routes": len(self.state.cable_routes),
            "total_tokens": self.state.total_tokens,
            "total_cost_zar": self.state.total_cost,
        }

    def get_state(self) -> MultiPassState:
        """Get the underlying state object."""
        return self.state
