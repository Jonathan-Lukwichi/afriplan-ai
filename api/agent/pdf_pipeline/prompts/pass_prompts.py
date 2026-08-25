"""
v2 estimator — per-pass instruction prompts.

Injected into the user message alongside the page image(s). The frozen
system prompt already carries SA-domain expertise and the confidence bands;
these prompts tell the model WHICH pass tool to call and WHAT to focus on.

The recurring discipline across all passes: report what is DRAWN, not what
would be reasonable. Missing values are reported as missing (0 / false /
empty), never guessed — the deterministic brain decides what to assume.
"""

# ─── PASS 1 ──────────────────────────────────────────────────────────

READ_PROJECT_CONTEXT_PROMPT = (
    "This is an orienting sheet — a cover page, drawing register, title block, "
    "or legend. Call `read_project_context`.\n"
    "  1. Capture the project identity from the title block (project, client, "
    "consultant, contractor, site, standard, revision).\n"
    "  2. List every named building / block / part you can see — these decide "
    "whether the bill is single or per-building.\n"
    "  3. Capture the drawing index (drawing no + title + sheet type) if a "
    "register table is present.\n"
    "  4. Transcribe the legend exactly (symbol → meaning).\n"
    "  5. List any item a note marks as FREE-ISSUED / supplied by client.\n"
    "Report only what is written. Do not invent buildings or drawings."
)

# ─── PASS 2 ──────────────────────────────────────────────────────────

READ_POWER_SPINE_PROMPT = (
    "This is a single-line diagram / DB schedule. Call `read_power_spine`.\n"
    "  1. For every distribution board: name, location, main breaker, phases, "
    "voltage, kA rating, mounting, ELCB and surge presence. Quote the exact "
    "busbar header text into source_snippet, e.g. 'DB-AB1  400V, 100A, 15kA' — "
    "verbatim, not paraphrased. If a page shows more than one DB diagram, be "
    "careful not to mix up which header belongs to which board: voltage and "
    "amperage are usually printed adjacent on the same line (e.g. '400V, "
    "100A') — read the number immediately followed by 'A' as main_breaker_a, "
    "not the number followed by 'V'.\n"
    "  2. Read EVERY circuit row including spare ways; set load_type and "
    "is_spare for each.\n"
    "  3. For every FEEDER run between nodes (e.g. 'DB-CR → DB1'): record the "
    "source, destination, cable size/cores/type and the BCEW earth size if "
    "shown.\n"
    "  4. CRITICAL — feeder length: set length_annotated=TRUE and length_m to "
    "the printed value ONLY if a length (e.g. '35m') is actually drawn on that "
    "run. If no length is printed, set length_annotated=FALSE and length_m=0. "
    "Never estimate a length yourself.\n"
    "  5. Capture the incoming supply (municipal / mini-sub / kiosk / "
    "generator) and metering."
)

# ─── PASS 3 ──────────────────────────────────────────────────────────

READ_LAYOUT_TAKEOFF_PROMPT = (
    "This is a lighting / plugs floor-plan layout. Call `read_layout_takeoff`.\n"
    "  1. Find the legend first and use it as your symbol dictionary.\n"
    "  2. Walk every visible room. For each, count every light, socket, switch "
    "and isolator symbol exactly once into the matching counter.\n"
    "  3. Record the DB tag shown for the room (served_by_db) and list the "
    "circuit labels visible in it (e.g. 'L2-1', 'S4', 'ISO1').\n"
    "  4. Capture area_m2 and ceiling_height_m only if they are labelled.\n"
    "  5. If a room is unnamed, label it 'Room <N>' by left-to-right order.\n"
    "Count what you SEE. Do not infer counts from area or room type."
)


PROMPT_BY_PASS_TOOL = {
    "read_project_context": READ_PROJECT_CONTEXT_PROMPT,
    "read_power_spine":      READ_POWER_SPINE_PROMPT,
    "read_layout_takeoff":   READ_LAYOUT_TAKEOFF_PROMPT,
}
