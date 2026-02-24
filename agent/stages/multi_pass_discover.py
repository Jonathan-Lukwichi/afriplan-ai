"""
AfriPlan Electrical v4.11 - Multi-Pass Discovery

PROBLEM: Single-pass extraction overwhelms AI vision models, especially
free models like Llama 4. Complex drawings with multiple DBs and rooms
result in 20-30% extraction rates.

SOLUTION: Break extraction into focused passes:
1. PROJECT_INFO - Extract project metadata from cover page
2. DB_DETECTION - Identify all distribution boards
3. DB_SCHEDULES - Extract circuit schedule for each DB (one at a time)
4. ROOM_DETECTION - Identify all rooms/areas from layouts
5. ROOM_FIXTURES - Count fixtures per room (one at a time)
6. CABLE_ROUTES - Extract cable runs between DBs

Each pass uses a FOCUSED prompt that asks for ONE thing only.
This dramatically improves accuracy with limited vision models.
"""

import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from agent.models import (
    ExtractionResult, ExtractionMode, StageResult, PipelineStage,
    BuildingBlock, DistributionBoard, Circuit, Room, FixtureCounts,
    SiteCableRun, ProjectMetadata, ItemConfidence,
)
from agent.utils import parse_json_safely, Timer, estimate_cost_zar
from agent.prompts.system_prompt import SYSTEM_PROMPT


class ExtractionPass(Enum):
    """The six extraction passes."""
    PROJECT_INFO = "project_info"
    DB_DETECTION = "db_detection"
    DB_SCHEDULES = "db_schedules"
    ROOM_DETECTION = "room_detection"
    ROOM_FIXTURES = "room_fixtures"
    CABLE_ROUTES = "cable_routes"


@dataclass
class PassResult:
    """Result from a single extraction pass."""
    pass_type: ExtractionPass
    success: bool
    data: Dict[str, Any]
    tokens_used: int = 0
    cost_zar: float = 0.0
    error: str = ""


@dataclass
class MultiPassState:
    """State accumulated across all passes."""
    project_name: str = ""
    client_name: str = ""
    consultant_name: str = ""
    db_names: List[str] = field(default_factory=list)
    db_schedules: Dict[str, Dict] = field(default_factory=dict)  # {db_name: schedule_data}
    room_names: List[str] = field(default_factory=list)
    room_fixtures: Dict[str, Dict] = field(default_factory=dict)  # {room_name: fixture_counts}
    cable_routes: List[Dict] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    passes_completed: List[ExtractionPass] = field(default_factory=list)


# ============================================================================
# PASS 1: PROJECT INFO
# ============================================================================

PROMPT_PROJECT_INFO = """## TASK: Extract Project Information

Look at the FIRST page (cover page or title block) and extract ONLY:

1. Project Name (e.g., "Proposed New Offices on Erf 1/1, Newmark")
2. Client Name (look for "Client:", "Owner:", "Employer:")
3. Consultant Name (look for "Engineer:", "Consultant:", "Electrical Engineer:")
4. Drawing Date
5. Revision Number

Respond with ONLY this JSON (no explanation):
{
  "project_name": "...",
  "client_name": "...",
  "consultant_name": "...",
  "date": "...",
  "revision": "..."
}
"""


# ============================================================================
# PASS 2: DB DETECTION
# ============================================================================

PROMPT_DB_DETECTION = """## TASK: Find ALL Distribution Boards

Scan ALL pages and list EVERY Distribution Board (DB) you can see.

IMPORTANT: Look for ALL naming variations:

### Main/Supply Boards (usually fed from Eskom):
- MSB, Main Switch Board, Main DB
- Kiosk, Metering Box, Eskom metering
- "Fed From Eskom metering Box"

### Ground Floor / Common Area Boards:
- DB-GF, DB-G/F, DB-GND, DB-00, DB Ground, DB-GROUND
- DB-CA, DB-COMMON, DB Common Area
- Look for "Fed from..." labels to identify main boards

### Sub-Boards / Suite Boards:
- DB-S1, DB-S2, DB-S3, DB-S4 (Suites)
- DB-SUITE 1, DB-SUITE 2, DB-SUITE 3, DB-SUITE 4
- DB-1, DB-2, DB-3, DB-4 (numbered)
- DB-FF, DB-1F, DB-2F (floors)

### How to Find DBs:
1. Look for schedule TABLES with circuit columns (P1, L1, etc.)
2. Look for single-line diagram symbols (rectangles with lines)
3. Look for "Supply to DB-XX" annotations
4. Look for circuit labels like "DB-S3 P1" or "DB-GF L2"

For each DB found, note:
- The exact DB name as shown
- Its location (Suite 1, Ground Floor, Common Area, etc.)
- Whether it's a main board (fed from Eskom) or sub-board (fed from another DB)
- Which DB feeds it if visible

Respond with ONLY this JSON (no explanation):
{
  "distribution_boards": [
    {"name": "DB-GF", "location": "Ground Floor", "is_main": true, "fed_from": "Kiosk"},
    {"name": "DB-CA", "location": "Common Area", "is_main": false, "fed_from": "DB-GF"},
    {"name": "DB-S1", "location": "Suite 1", "is_main": false, "fed_from": "DB-GF"}
  ],
  "total_db_count": 3
}
"""


# ============================================================================
# PASS 3: DB SCHEDULE (per DB)
# ============================================================================

def get_db_schedule_prompt(db_name: str) -> str:
    """Generate a focused prompt for extracting ONE DB's circuit schedule."""
    return f"""## TASK: Extract Circuit Schedule for {db_name}

You are extracting the circuit schedule for ONLY this distribution board: **{db_name}**

Find the schedule table for {db_name} and read EVERY circuit column.

The schedule table typically has rows:
- CIRCUIT NO: P1, P2, L1, L2, AC1, SPARE, etc.
- WATTAGE: 3680W, 198W, 54W, etc.
- WIRE SIZE: 1.5mm², 2.5mm², 4mm², etc.
- NO OF POINT: 4, 8, 10, 1, etc.
- BREAKER: 10A, 16A, 20A, 32A, etc.

Also find:
- Main breaker rating (e.g., 63A, 100A)
- Supply source (e.g., "FROM DB-GF", "FROM MSB")
- Supply cable size (e.g., "4Cx16mm²")

Respond with ONLY this JSON (no explanation):
{{
  "db_name": "{db_name}",
  "main_breaker_a": 63,
  "supply_from": "DB-GF",
  "supply_cable_mm2": 16,
  "circuits": [
    {{"id": "P1", "type": "power", "wattage_w": 3680, "cable_mm2": 2.5, "breaker_a": 20, "num_points": 4}},
    {{"id": "L1", "type": "lighting", "wattage_w": 198, "cable_mm2": 1.5, "breaker_a": 10, "num_points": 8}},
    {{"id": "SPARE", "type": "spare", "wattage_w": 0, "cable_mm2": 0, "breaker_a": 0, "num_points": 0}}
  ],
  "spare_count": 2,
  "schedule_found": true
}}

If you CANNOT find the schedule for {db_name}, respond with:
{{
  "db_name": "{db_name}",
  "schedule_found": false,
  "reason": "Schedule table not visible on provided pages"
}}
"""


# ============================================================================
# PASS 4: ROOM DETECTION
# ============================================================================

PROMPT_ROOM_DETECTION = """## TASK: Find All Rooms and Areas

Scan the LAYOUT pages (floor plans) and list every room or area you can see.

Look for:
- Room labels: "Office", "Kitchen", "Bathroom", "Store", "Reception"
- Suite designations: "Suite 1", "Suite 2", "Suite 3", "Suite 4"
- Area labels: "Foyer", "Parking", "Carport", "Corridor"
- Numbered rooms: "Office 1", "Office 2", "WC 1", "WC 2"

For each room/area, note:
- The exact name as shown on the drawing
- The floor (Ground Floor, First Floor, etc.)
- Whether it's a wet area (bathroom, kitchen, laundry)

Respond with ONLY this JSON (no explanation):
{
  "rooms": [
    {"name": "Office 1", "floor": "Ground Floor", "is_wet_area": false},
    {"name": "Kitchen", "floor": "Ground Floor", "is_wet_area": true},
    {"name": "WC 1", "floor": "Ground Floor", "is_wet_area": true}
  ],
  "total_room_count": 3
}
"""


# ============================================================================
# PASS 5: ROOM FIXTURES (per room)
# ============================================================================

def get_room_fixtures_prompt(room_name: str) -> str:
    """Generate a focused prompt for counting fixtures in ONE room."""
    return f"""## TASK: Count Fixtures in "{room_name}"

You are counting electrical fixtures for ONLY this room: **{room_name}**

Look at the layout drawings and count EVERY fixture in {room_name}:

### LIGHTS (look for circular/rectangular symbols):
- Recessed LED panels (600x1200 or 600x600)
- Surface mount LEDs
- Downlights (small circles)
- Vapor proof fittings (wet areas)
- Bulkheads

### SOCKETS (look for square symbols):
- Double sockets @300mm (floor level)
- Double sockets @1100mm (work height)
- Single sockets
- Waterproof sockets
- Data points (CAT6)

### SWITCHES (look for small rectangles):
- 1-lever switches
- 2-lever switches
- 2-way switches
- Isolators
- Day/night switches

Respond with ONLY this JSON (no explanation):
{{
  "room_name": "{room_name}",
  "fixtures": {{
    "recessed_led_600x1200": 0,
    "surface_mount_led": 0,
    "downlight": 0,
    "vapor_proof": 0,
    "bulkhead": 0,
    "double_socket_300": 0,
    "double_socket_1100": 0,
    "single_socket": 0,
    "waterproof_socket": 0,
    "data_point_cat6": 0,
    "switch_1lever": 0,
    "switch_2lever": 0,
    "switch_2way": 0,
    "isolator": 0
  }},
  "circuit_refs": ["DB-S1 L1", "DB-S1 P1"],
  "found_in_drawing": true
}}

If you CANNOT find {room_name} clearly, respond with:
{{
  "room_name": "{room_name}",
  "found_in_drawing": false,
  "reason": "Room not clearly visible"
}}
"""


# ============================================================================
# PASS 6: CABLE ROUTES
# ============================================================================

PROMPT_CABLE_ROUTES = """## TASK: Extract Cable Routes Between Distribution Boards

Find ALL cables connecting distribution boards. This is CRITICAL for sub-main cable costing.

### WHERE TO LOOK:
1. TEXT ON cable lines: "4Cx16mm² PVC SWA", "35mm² x 4C PVC SWA PVC"
2. Cable annotation boxes near lines
3. Notes saying "Supply to XX via YYmm² cable"
4. Labels like "Cable from DB-GF to DB-S1"
5. Cable schedule tables if present

### WHAT TO EXTRACT for each cable:
- From: Source (Kiosk, MSB, DB-GF, etc.)
- To: Destination DB name
- Cable spec: Full specification including size, cores, type
  - Format: "4Cx16mm² PVC SWA PVC" or "35mm² x 4C PVC SWA PVC"
  - SWA = Steel Wire Armoured (for underground)
- Earth conductor: Look for "+ 25mm² BCEW" or "25mm² green/yellow"
- Length: If visible on drawing or in notes
- Underground: true if buried, false if surface/trunking

### ALSO LOOK FOR:
- Underground sleeves mentioned (50mm, 75mm, 110mm)
- Trench notes (e.g., "600mm deep cable trench")
- Solar cable sleeves (often 50mm)

Respond with ONLY this JSON (no explanation):
{
  "cable_routes": [
    {
      "from": "Kiosk",
      "to": "DB-GF",
      "cable_spec": "4Cx35mm² PVC SWA PVC",
      "earth_spec": "25mm² BCEW",
      "length_m": 30,
      "is_underground": true
    },
    {
      "from": "DB-GF",
      "to": "DB-S1",
      "cable_spec": "4Cx16mm² PVC SWA PVC",
      "earth_spec": null,
      "length_m": null,
      "is_underground": false
    }
  ],
  "underground_sleeves": [
    {"size_mm": 110, "qty": 2, "purpose": "Main supply cables"},
    {"size_mm": 50, "qty": 3, "purpose": "Solar cables"}
  ],
  "total_routes": 2
}
"""


# ============================================================================
# NEW PASS: SUPPLY POINT (kiosk/metering)
# ============================================================================

PROMPT_SUPPLY_POINT = """## TASK: Extract Main Supply Point / Metering

Find the incoming supply/metering point on the SLD. This is where Eskom power enters.

### LOOK FOR:
- "Kiosk", "Kiosk Metering", "Metering Box"
- "MSB", "Main Switch Board"
- "Fed from Eskom", "LV Cable from transformer"
- "Eskom metering Box"
- Main incoming cable specification

### EXTRACT:
- Name of supply point
- Main breaker/switch size (400A, 200A, 100A, etc.)
- Metering type (CT meter, prepaid, direct)
- Which DB it feeds (usually DB-GF or DB-CA)
- Cable specification to first DB
- Cable length if noted

Respond with ONLY this JSON (no explanation):
{
  "supply_found": true,
  "name": "Kiosk Metering",
  "main_breaker_a": 400,
  "meter_type": "ct",
  "feeds_to": "DB-GF",
  "cable_spec": "95mm² x 4C PVC SWA PVC",
  "cable_length_m": 30
}

If NO supply point visible:
{
  "supply_found": false,
  "reason": "No incoming supply shown on SLD"
}
"""


# ============================================================================
# NEW PASS: LIGHTING LEGEND
# ============================================================================

PROMPT_LEGEND_LIGHTING = """## TASK: Extract Lighting Legend

Find the LEGEND or KEY on the lighting layout drawing. Extract ALL lighting fixture types.

### LOOK FOR LEGEND BOX containing:
- Symbol drawings with descriptions
- "LIGHTS" or "LIGHTING" section
- Wattage specifications

### COMMON LIGHT TYPES to identify:
1. LED Panels: 600x1200 (3x18W=54W), 600x600 (40W)
2. Downlights: 6W, 9W, 12W LED (small circles)
3. Surface mount: 18W, 36W ceiling lights
4. Flood lights: 30W, 50W, 200W (outdoor)
5. Bulkheads: 24W, 26W (wall mounted)
6. Emergency lights: self-contained 3hr
7. Vapor proof: 2x18W, 2x24W (wet areas)
8. Pole lights: 60W on 2.3m poles

### ALSO EXTRACT SWITCHES:
- 1-lever, 1-way switch @ 1200mm AFFL
- 2-lever, 1-way switch @ 1200mm AFFL
- Day/Night switch (D/N) @ 2000mm AFFL
- 2-way switch

### CHECK FOR QTYS column in legend (if shown)

Respond with ONLY this JSON (no explanation):
{
  "has_legend": true,
  "light_types": [
    {"symbol": "rect_1200", "name": "600x1200 Recessed 3x18W LED", "wattage_w": 54},
    {"symbol": "circle_rays", "name": "6W LED Downlight", "wattage_w": 6},
    {"symbol": "surface", "name": "18W LED Ceiling Light", "wattage_w": 18},
    {"symbol": "flood", "name": "30W LED Flood Light", "wattage_w": 30}
  ],
  "switch_types": [
    {"symbol": "1L1W", "name": "1-lever 1-way switch", "height_mm": 1200},
    {"symbol": "2L1W", "name": "2-lever 1-way switch", "height_mm": 1200},
    {"symbol": "DN", "name": "Day/Night switch", "height_mm": 2000}
  ],
  "qtys_visible": {"downlight": 36, "panel_1200": 28}
}

If NO legend visible:
{
  "has_legend": false,
  "reason": "No legend found on page"
}
"""


# ============================================================================
# NEW PASS: POWER LEGEND
# ============================================================================

PROMPT_LEGEND_POWER = """## TASK: Extract Power/Plugs Legend

Find the LEGEND or KEY on the power/plugs layout drawing. Extract ALL socket and equipment types.

### LOOK FOR LEGEND BOX containing:
- "POWER SOCKETS" or "PLUGS" section
- Socket symbols with heights
- Equipment symbols

### COMMON SOCKET TYPES:
1. 16A Double switched socket @300mm AFFL (floor level)
2. 16A Double switched socket @1100mm AFFL (worktop)
3. 16A Single switched socket @300mm
4. Waterproof socket IP44/IP65
5. Floor box
6. Data socket CAT 6

### ISOLATORS & EQUIPMENT:
1. 20A Isolator switch @ 2000mm AFFL
2. 30A Isolator switch @ 2000mm AFFL
3. A/C - Air conditioning connection
4. Geyser connection

### CONTAINMENT (if shown):
1. 2-compartment steel grey power skirting (100x50mm)
2. 20mm PVC conduit
3. 200mm galvanized cable tray
4. 150mm wire mesh basket
5. P8000 trunking

Respond with ONLY this JSON (no explanation):
{
  "has_legend": true,
  "socket_types": [
    {"symbol": "DS300", "name": "16A Double Switched Socket", "height_mm": 300},
    {"symbol": "DS1100", "name": "16A Double Switched Socket", "height_mm": 1100},
    {"symbol": "DATA", "name": "CAT 6 Data Socket", "height_mm": 300}
  ],
  "isolator_types": [
    {"symbol": "ISO20", "name": "20A Isolator Switch", "height_mm": 2000},
    {"symbol": "ISO30", "name": "30A Isolator Switch", "height_mm": 2000}
  ],
  "equipment": [
    {"symbol": "AC", "name": "Air Conditioning Unit"},
    {"symbol": "GY", "name": "Geyser Connection"}
  ],
  "containment": [
    {"type": "skirting", "spec": "2-compartment 100x50mm"},
    {"type": "conduit", "spec": "20mm PVC"},
    {"type": "tray", "spec": "200mm galvanized cable tray"}
  ]
}

If NO legend visible:
{
  "has_legend": false,
  "reason": "No legend found on page"
}
"""


# ============================================================================
# IMPROVED: Room fixtures with legend context
# ============================================================================

def get_room_fixtures_prompt_with_legend(room_name: str, legend_types: dict) -> str:
    """Generate room-specific prompt using EXTRACTED legend types."""

    # Build fixture lists from legend
    light_list = ", ".join([lt.get("name", "") for lt in legend_types.get("light_types", [])])
    socket_list = ", ".join([st.get("name", "") for st in legend_types.get("socket_types", [])])
    switch_list = ", ".join([sw.get("name", "") for sw in legend_types.get("switch_types", [])])

    if not light_list:
        light_list = "600x1200 LED panel, 6W downlight, 18W surface mount, flood light"
    if not socket_list:
        socket_list = "double socket @300mm, double socket @1100mm, data CAT 6"
    if not switch_list:
        switch_list = "1-lever switch, 2-lever switch"

    return f"""## TASK: Count Fixtures in "{room_name}"

You are counting electrical fixtures for ONLY this room: **{room_name}**

Using the legend symbols from this drawing, count each fixture type in {room_name}.

### LIGHT TYPES to count:
{light_list}

### SOCKET TYPES to count:
{socket_list}

### SWITCH TYPES to count:
{switch_list}

For EACH type, count how many symbols appear INSIDE "{room_name}" boundary.
Also note circuit references if visible (e.g., "DB-S1 L1").

Respond with ONLY this JSON (no explanation):
{{
  "room_name": "{room_name}",
  "found_in_drawing": true,
  "fixtures": {{
    "led_panel_600x1200": 0,
    "downlight_6w": 0,
    "surface_mount_18w": 0,
    "flood_light": 0,
    "double_socket_300": 0,
    "double_socket_1100": 0,
    "single_socket": 0,
    "data_cat6": 0,
    "switch_1lever": 0,
    "switch_2lever": 0,
    "isolator_20a": 0,
    "isolator_30a": 0
  }},
  "circuit_refs": ["DB-S1 L1", "DB-S1 P1"]
}}

If {room_name} NOT clearly visible:
{{
  "room_name": "{room_name}",
  "found_in_drawing": false,
  "reason": "Room not found"
}}
"""


# ============================================================================
# MULTI-PASS ORCHESTRATOR
# ============================================================================

def call_vision_llm(
    client: object,
    pages: List,
    prompt: str,
    model: str,
    provider: str = "groq",
    max_tokens: int = 2048,
) -> Tuple[str, int, float]:
    """Call vision LLM with focused prompt."""

    if provider in ("groq", "grok"):
        # Groq and Grok both use OpenAI-compatible API
        content = [{"type": "text", "text": prompt}]
        for page in pages:
            if hasattr(page, 'image_base64') and page.image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{page.image_base64}"}
                })

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": content}]
        )

        return response.choices[0].message.content, response.usage.total_tokens if response.usage else 0, 0.0

    elif provider == "gemini":
        # Google Gemini API
        import PIL.Image
        import io
        import base64

        # Build parts for Gemini
        parts = [prompt]
        for page in pages:
            if hasattr(page, 'image_base64') and page.image_base64:
                # Convert base64 to PIL Image
                img_bytes = base64.b64decode(page.image_base64)
                img = PIL.Image.open(io.BytesIO(img_bytes))
                parts.append(img)

        model_obj = client.GenerativeModel(model)
        response = model_obj.generate_content(parts)

        # Estimate tokens (Gemini doesn't always return exact counts)
        tokens = len(prompt.split()) * 2  # Rough estimate
        return response.text, tokens, 0.0

    elif provider == "claude":
        content = [{"type": "text", "text": prompt}]
        for page in pages:
            if hasattr(page, 'image_base64') and page.image_base64:
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

        tokens = response.usage.input_tokens + response.usage.output_tokens
        cost = estimate_cost_zar(model, response.usage.input_tokens, response.usage.output_tokens)
        return response.content[0].text, tokens, cost

    else:
        raise ValueError(f"Unknown provider: {provider}")


def run_pass(
    pass_type: ExtractionPass,
    prompt: str,
    pages: List,
    client: object,
    model: str,
    provider: str,
) -> PassResult:
    """Run a single extraction pass."""
    try:
        response_text, tokens, cost = call_vision_llm(
            client, pages, prompt, model, provider, max_tokens=2048
        )

        data = parse_json_safely(response_text) or {}

        return PassResult(
            pass_type=pass_type,
            success=bool(data),
            data=data,
            tokens_used=tokens,
            cost_zar=cost,
        )
    except Exception as e:
        return PassResult(
            pass_type=pass_type,
            success=False,
            data={},
            error=str(e),
        )


def multi_pass_discover(
    pages: List,
    client: object,
    model: str,
    provider: str = "groq",
    progress_callback=None,
) -> Tuple[ExtractionResult, MultiPassState, List[str]]:
    """
    Execute multi-pass extraction strategy.

    Args:
        pages: All document pages
        client: API client
        model: Model name
        provider: "groq", "claude", etc.
        progress_callback: Optional function to call with progress updates

    Returns:
        Tuple of (ExtractionResult, MultiPassState, warnings)
    """
    state = MultiPassState()
    warnings = []

    def update_progress(message: str):
        if progress_callback:
            progress_callback(message)
        warnings.append(message)

    # Separate pages by likely type
    cover_pages = pages[:1]  # First page is usually cover
    sld_pages = pages[:4]    # SLD pages are usually in first few pages
    layout_pages = pages[1:] # Layout pages are everything after cover

    # ========================================
    # PASS 1: PROJECT INFO
    # ========================================
    update_progress("Pass 1/6: Extracting project information...")

    result1 = run_pass(
        ExtractionPass.PROJECT_INFO,
        PROMPT_PROJECT_INFO,
        cover_pages,
        client, model, provider
    )

    if result1.success:
        state.project_name = result1.data.get("project_name", "")
        state.client_name = result1.data.get("client_name", "")
        state.consultant_name = result1.data.get("consultant_name", "")
        state.passes_completed.append(ExtractionPass.PROJECT_INFO)
        state.total_tokens += result1.tokens_used
        state.total_cost += result1.cost_zar

    # ========================================
    # PASS 2: DB DETECTION
    # ========================================
    update_progress("Pass 2/6: Detecting distribution boards...")

    result2 = run_pass(
        ExtractionPass.DB_DETECTION,
        PROMPT_DB_DETECTION,
        sld_pages,
        client, model, provider
    )

    if result2.success:
        dbs = result2.data.get("distribution_boards", [])
        state.db_names = [db.get("name", "") for db in dbs if db.get("name")]
        state.passes_completed.append(ExtractionPass.DB_DETECTION)
        state.total_tokens += result2.tokens_used
        state.total_cost += result2.cost_zar
        update_progress(f"  → Found {len(state.db_names)} DBs: {', '.join(state.db_names)}")

    # ========================================
    # PASS 3: DB SCHEDULES (per DB)
    # ========================================
    update_progress("Pass 3/6: Extracting circuit schedules per DB...")

    for db_name in state.db_names:
        update_progress(f"  → Extracting schedule for {db_name}...")

        result3 = run_pass(
            ExtractionPass.DB_SCHEDULES,
            get_db_schedule_prompt(db_name),
            sld_pages,
            client, model, provider
        )

        if result3.success and result3.data.get("schedule_found", False):
            state.db_schedules[db_name] = result3.data
            circuits = result3.data.get("circuits", [])
            update_progress(f"    ✓ {db_name}: {len(circuits)} circuits")
        else:
            update_progress(f"    ✗ {db_name}: Schedule not found")

        state.total_tokens += result3.tokens_used
        state.total_cost += result3.cost_zar

    state.passes_completed.append(ExtractionPass.DB_SCHEDULES)

    # ========================================
    # PASS 4: ROOM DETECTION
    # ========================================
    update_progress("Pass 4/6: Detecting rooms and areas...")

    result4 = run_pass(
        ExtractionPass.ROOM_DETECTION,
        PROMPT_ROOM_DETECTION,
        layout_pages,
        client, model, provider
    )

    if result4.success:
        rooms = result4.data.get("rooms", [])
        state.room_names = [r.get("name", "") for r in rooms if r.get("name")]
        state.passes_completed.append(ExtractionPass.ROOM_DETECTION)
        state.total_tokens += result4.tokens_used
        state.total_cost += result4.cost_zar
        update_progress(f"  → Found {len(state.room_names)} rooms")

    # ========================================
    # PASS 5: ROOM FIXTURES (per room) - LIMITED to first 5 rooms
    # ========================================
    update_progress("Pass 5/6: Counting fixtures per room...")

    # Limit to first 5 rooms to manage API calls
    rooms_to_process = state.room_names[:5]

    for room_name in rooms_to_process:
        update_progress(f"  → Counting fixtures in {room_name}...")

        result5 = run_pass(
            ExtractionPass.ROOM_FIXTURES,
            get_room_fixtures_prompt(room_name),
            layout_pages,
            client, model, provider
        )

        if result5.success and result5.data.get("found_in_drawing", False):
            state.room_fixtures[room_name] = result5.data.get("fixtures", {})

        state.total_tokens += result5.tokens_used
        state.total_cost += result5.cost_zar

    state.passes_completed.append(ExtractionPass.ROOM_FIXTURES)

    # ========================================
    # PASS 6: CABLE ROUTES
    # ========================================
    update_progress("Pass 6/6: Extracting cable routes...")

    result6 = run_pass(
        ExtractionPass.CABLE_ROUTES,
        PROMPT_CABLE_ROUTES,
        sld_pages,
        client, model, provider
    )

    if result6.success:
        state.cable_routes = result6.data.get("cable_routes", [])
        state.passes_completed.append(ExtractionPass.CABLE_ROUTES)
        state.total_tokens += result6.tokens_used
        state.total_cost += result6.cost_zar
        update_progress(f"  → Found {len(state.cable_routes)} cable routes")

    # ========================================
    # BUILD FINAL EXTRACTION RESULT
    # ========================================
    extraction = build_extraction_result(state)

    update_progress(f"Multi-pass extraction complete: {len(state.passes_completed)}/6 passes")
    update_progress(f"Total tokens: {state.total_tokens}, Cost: R{state.total_cost:.2f}")

    return extraction, state, warnings


def build_extraction_result(state: MultiPassState) -> ExtractionResult:
    """Build ExtractionResult from accumulated state."""

    extraction = ExtractionResult(
        extraction_mode=ExtractionMode.AS_BUILT,
        metadata=ProjectMetadata(
            project_name=state.project_name,
            client_name=state.client_name,
            consultant_name=state.consultant_name,
        ),
    )

    # Create main building block
    block = BuildingBlock(name=state.project_name or "Main Building")

    # Add distribution boards
    for db_name, schedule in state.db_schedules.items():
        db = DistributionBoard(
            name=db_name,
            building_block=block.name,
            main_breaker_a=int(schedule.get("main_breaker_a") or 0),
            supply_from=schedule.get("supply_from") or "",
            supply_cable_size_mm2=float(schedule.get("supply_cable_mm2") or 0),
            spare_ways=int(schedule.get("spare_count") or 0),
            confidence=ItemConfidence.EXTRACTED,
        )

        # Add circuits
        for ckt in schedule.get("circuits", []):
            circuit = Circuit(
                id=ckt.get("id") or "",
                type=ckt.get("type") or "power",
                wattage_w=float(ckt.get("wattage_w") or 0),
                cable_size_mm2=float(ckt.get("cable_mm2") or 2.5),
                breaker_a=int(ckt.get("breaker_a") or 20),
                num_points=int(ckt.get("num_points") or 0),
                is_spare="spare" in (ckt.get("type") or "").lower(),
                confidence=ItemConfidence.EXTRACTED,
            )
            db.circuits.append(circuit)

        block.distribution_boards.append(db)

    # Add rooms with fixtures
    for room_name in state.room_names:
        fixtures_data = state.room_fixtures.get(room_name, {})

        room = Room(
            name=room_name,
            building_block=block.name,
            confidence=ItemConfidence.EXTRACTED if fixtures_data else ItemConfidence.INFERRED,
        )

        # Map fixture counts
        room.fixtures = FixtureCounts(
            recessed_led_600x1200=int(fixtures_data.get("recessed_led_600x1200") or 0),
            surface_mount_led_18w=int(fixtures_data.get("surface_mount_led") or 0),
            downlight_led_6w=int(fixtures_data.get("downlight") or 0),
            vapor_proof_2x18w=int(fixtures_data.get("vapor_proof") or 0),
            bulkhead_24w=int(fixtures_data.get("bulkhead") or 0),
            double_socket_300=int(fixtures_data.get("double_socket_300") or 0),
            double_socket_1100=int(fixtures_data.get("double_socket_1100") or 0),
            single_socket_300=int(fixtures_data.get("single_socket") or 0),
            double_socket_waterproof=int(fixtures_data.get("waterproof_socket") or 0),
            data_points_cat6=int(fixtures_data.get("data_point_cat6") or 0),
            switch_1lever_1way=int(fixtures_data.get("switch_1lever") or 0),
            switch_2lever_1way=int(fixtures_data.get("switch_2lever") or 0),
            switch_1lever_2way=int(fixtures_data.get("switch_2way") or 0),
            isolator_20a=int(fixtures_data.get("isolator") or 0),
        )

        block.rooms.append(room)

    extraction.building_blocks.append(block)

    # Add cable routes
    for route in state.cable_routes:
        cable = SiteCableRun(
            from_point=route.get("from") or "",
            to_point=route.get("to") or "",
            cable_spec=route.get("cable_spec") or "",
            length_m=float(route.get("length_m") or 0) if route.get("length_m") else 0,
            confidence=ItemConfidence.EXTRACTED,
        )
        extraction.site_cable_runs.append(cable)

    return extraction
