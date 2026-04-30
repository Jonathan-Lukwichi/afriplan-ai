"""
Per-page-type instruction prompts.

These get injected into the user message alongside the rasterised page
image. Keep them tight — the system prompt already carries the SA-domain
context. These tell the model *which tool* to call and *what to focus on*.
"""

CLASSIFY_PROMPT = (
    "Classify this drawing page using the `classify_page` tool. "
    "Look at the dominant visual content: schedule tables → 'sld' or 'schedule'; "
    "floor plan with bulb symbols → 'lighting_layout'; floor plan with socket "
    "symbols → 'plugs_layout'; title block / sheet index → 'register'; "
    "legend or notes block → 'notes'."
)

SLD_PROMPT = (
    "This page contains one or more distribution-board schedules and/or a "
    "single-line diagram. Use the `extract_sld` tool. For each DB:\n"
    "  • record the name, location, main-breaker rating, phase config, and "
    "    whether ELCB / surge protection is present\n"
    "  • read EVERY circuit row in the schedule, including spares\n"
    "  • give every value a confidence score per the rules in the system prompt\n"
    "If you can see only part of a schedule (e.g. it continues on another page), "
    "set the row to is_spare=false and add a warning."
)

LIGHTING_PROMPT = (
    "This is a lighting layout floor plan. Use the `extract_lighting_layout` tool.\n"
    "  1. Locate the legend and capture the symbol → fixture-type map\n"
    "  2. Walk every visible room. For each room, count every fixture symbol exactly\n"
    "     once. Use the legend to decide which counter (downlights / panel_lights / …)\n"
    "     each symbol maps to.\n"
    "  3. If a room is unnamed, label it 'Room <N>' where N is left-to-right index.\n"
    "  4. Do not infer counts from area or room type. Count what you SEE."
)

PLUGS_PROMPT = (
    "This is a plugs / power layout floor plan. Use the `extract_plugs_layout` tool. "
    "Same discipline as lighting: legend first, then walk every room and count every "
    "outlet, switch, and isolator symbol you actually see."
)

SCHEDULE_PROMPT = (
    "This page is a standalone schedule table (typically a cable or circuit "
    "schedule that's not tied to a specific DB SLD). Use the `extract_schedule` tool. "
    "Capture one row per circuit. If the schedule has columns you don't recognise, "
    "ignore them — only fill the schema fields that map cleanly."
)

NOTES_PROMPT = (
    "This page is a cover sheet, legend, general notes, or specification. Use the "
    "`extract_notes` tool to capture project metadata (project name, consultant, "
    "drawing numbers, site address) and any free-text notes worth carrying forward."
)


PROMPT_BY_PAGE_TYPE = {
    "sld":              SLD_PROMPT,
    "lighting_layout":  LIGHTING_PROMPT,
    "plugs_layout":     PLUGS_PROMPT,
    "schedule":         SCHEDULE_PROMPT,
    "notes":            NOTES_PROMPT,
    "register":         NOTES_PROMPT,
}
