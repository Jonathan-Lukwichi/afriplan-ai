# AI assistant, stage 1 (Explain) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A chat panel in the signed-in app that answers questions about the open run's bill (where a line came from, how its rate was built, what is assumed, how the tool measures or counts) from the run's own record, using Claude Sonnet 5, with every figure traced to a tool result.

**Architecture:** A new top-level package `api/assistant/` runs a Claude tool-use loop over read-only Python tools that inspect a `RunRecord` (bill, findings, gaps) and fixed method cards. The pricer gains a pure `lines_for_finding` that also reports how each rate was built (`RateParts`), so a line's rate is explained by recomputing it, never by the model. Chat turns are stored per run in SQLite/Postgres; `api/routers/assistant.py` exposes them; `src/components/assistant/ChatPanel.jsx` docks into `AppShell`.

**Tech Stack:** FastAPI, pydantic, the Anthropic SDK client already used by the PDF pipeline (via `PdfLLM(..., provider="claude")._client`), SQLite/Postgres through `db.connection`, React 18 + Vite, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-29-ai-assistant-design.md` (stage 1 = §11 item 1).

## Global Constraints

- Chat model: `ASSIST_MODEL = SONNET_5` in `api/core/config.py`; no model ID anywhere else (hard rule 6).
- LLM = eyes, Python = brain (ADR-0002): every quantity, rate or rand amount in an answer must appear in a tool result of that turn; the model never does arithmetic.
- Stage 1 has **no action tools**: nothing the assistant does changes a run, a bill or memory.
- Nothing under `api/agent/` imports `assistant`, `db` or `routers` (hard rule 3); enforced by a test.
- Frozen system prompt in `api/assistant/prompts.py`: no dates, run ids or names (cache prefix, hard rule 5 by analogy).
- No change to `BillOfQuantities` or `BQLineItem`; no new dependency.
- Up to **8 tool calls per user turn**; then the model must answer.
- A user message is 1–2000 characters.
- Monthly cap: env `AFRIPLAN_ASSIST_MONTHLY_CAP_ZAR`; unset = no cap; when set, a turn is refused once this calendar month's chat cost has reached it.
- Copy: plain sentence case, no apologies, errors say what happened and what to do (frontend-design + project voice).
- Public repo: tests use synthetic findings and bills only; never a client file or figure.
- Line reference format everywhere: `"<section_number>.<item_no>"`, i.e. `BQLineItem.item_number_str` (e.g. `"4.15"`).

## Review Focus

1. **A run made before findings were stored** (`result.findings is None`): explaining a line must still return the line's own facts and say the rate build-up is not available for this run, never raise. → Task 3, `test_explain_line_without_findings`.
2. **A bill line no finding produced** (combined bills, lines added after pricing): `explain_line` returns `traced: False` with a plain reason, not a wrong match. → Task 3, `test_untraced_line_is_reported_not_guessed`.
3. **Supplier prices applied** (`record.sourced_boq` set): the explanation shows both the built-up rate and the supplier rate that the export now uses. → Task 3, `test_sourced_rate_is_shown_beside_built_up_rate`.
4. **A long conversation**: history trimmed to the budget must never split a `tool_use` from its `tool_result` (the API rejects it). → Task 7, `test_history_trim_keeps_tool_pairs_together`.
5. **The Claude API fails mid-turn** (overloaded, timeout): the endpoint answers 502 with a plain reason and stores nothing of that turn, so the history stays valid. → Task 8, `test_api_failure_saves_nothing`.

---

### Task 1: ADR-0009, words, config and the import rule

**Files:**
- Create: `docs/adr/0009-assistant-with-memory.md`
- Modify: `context.md` (add **Assistant**, **Job**, **Action**, **Change**, **Office memory** under a new `## Assistant` heading, text from spec §7.1)
- Modify: `api/core/config.py` (add `ASSIST_MODEL = SONNET_5` beside `MATCH_MODEL`, with a one-line comment)
- Modify: `tests/architecture/test_independence.py`
- Test: `tests/assistant_layer/__init__.py`, `tests/assistant_layer/test_config.py`

**Interfaces:**
- Produces: `core.config.ASSIST_MODEL: ModelSpec`

- [ ] **Step 1: Write the failing tests**

```python
# tests/architecture/test_independence.py — add
AGENT_DIR = REPO_ROOT / "api" / "agent"

def test_agent_does_not_import_assistant_db_or_routers():
    bad = []
    for path in _python_files(AGENT_DIR):
        for lineno, line, mod in _imports_in(path):
            if mod.split(".")[0] in ("assistant", "db", "routers"):
                bad.append((path, lineno, line))
    assert not bad, "agent/ imports a top-level app layer:\n" + _format(bad)

# tests/assistant_layer/test_config.py
from core.config import ASSIST_MODEL, MODEL_REGISTRY, SONNET_5

def test_the_chat_runs_on_sonnet_5():
    assert ASSIST_MODEL is SONNET_5
    assert ASSIST_MODEL.model_id in MODEL_REGISTRY
```

- [ ] **Step 2: Run** `api/.venv/Scripts/python.exe -m pytest tests/assistant_layer tests/architecture -q` — expect `ImportError: cannot import name 'ASSIST_MODEL'` (the architecture test should already pass; if it fails, stop and report the offending import).
- [ ] **Step 3: Add `ASSIST_MODEL`**, write ADR-0009 (template `docs/adr/ADR-TEMPLATE.md`; Context = spec §1; Decision = spec §7.2, §7.5–7.7 and the three stages of §11; Consequences = the anti-goals of spec §4 become tests), add the glossary entries.
- [ ] **Step 4: Run** the same command — expect PASS.
- [ ] **Step 5: Commit** `docs(adr): 0009 an assistant that explains and, on confirm, acts` (include config + tests).

---

### Task 2: The pricer explains its own rates

**Files:**
- Modify: `api/agent/shared/pricing.py` (add `RateParts`, `PricedLine`, `lines_for_finding`; `price_findings` builds its lines through it)
- Modify: `api/core/rate_model.py` (add `describe_install_task`)
- Test: `tests/shared/test_pricing_explains.py`

**Interfaces:**
- Produces:
  - `RateParts` (frozen dataclass): `method: Literal["built_up", "board_build_up", "fixed_price", "free_issue_install", "trench", "warning_tape", "tag_only_board", "plinth"]`, `components: Tuple[Tuple[str, float], ...]` (label, rand per unit; they sum to the line's unit rate within R 0.01), `markup: float` (material markup applied, e.g. 1.3; 0 when none), `labour_note: str` (crew and hours, or `""`).
  - `PricedLine = Tuple[BQLineItem, RateParts]`
  - `lines_for_finding(finding, *, crew=DEFAULT_CREW, params=DEFAULT_PARAMS, config=DEFAULT_PRICING) -> List[PricedLine]` for any `BoardFinding | FeederFinding | ItemFinding | WireFinding`, lines **not yet numbered**.
  - `core.rate_model.describe_install_task(kind: Literal["cable", "bcew", "termination"], size: str, crew=DEFAULT_CREW) -> str`, e.g. `"2 electricians, 2 semi-skilled, 10 general workers: 14 h per 100 m"`; `""` for an unknown size.

Component labels (exact copy, used by the assistant verbatim): `"Material incl. markup"`, `"Consumables"`, `"Transport"`, `"Waste"`, `"Install labour"`, `"Fixed price"`, `"Outdoor kiosk housing"`, `"Nominal install (no crew-hours entry)"`. Supply lines carry only the supply components, install lines only `"Install labour"`.

- [ ] **Step 1: Pin today's bill before touching the pricer.** Write `_FINDINGS` (synthetic: one board with `circuits=[(20,1)]*6, spares=2, elcb=True`, one main-kiosk board, one tag-only board, one 50 mm² underground feeder `length_m=120, trench_m=110`, one item with `material_zar=850, install_zar=120`, one free-issue item, one fixed-price item, one 2.5mm2 wire `metres=180`). Run the **current** `price_findings(_FINDINGS, pipeline="dxf")` once and paste the resulting `[(l.item_number_str, l.description, l.unit, l.qty, l.unit_price_zar)]` as the literal `EXPECTED` list in the test:

```python
def test_price_findings_is_unchanged():
    boq = price_findings(_FINDINGS, pipeline="dxf")
    assert [(l.item_number_str, l.description, l.unit, l.qty, l.unit_price_zar) for l in boq.line_items] == EXPECTED
```

  Run it: PASS against the current code (this is the guard for the refactor).
- [ ] **Step 2: Write the failing explanation tests**

```python
def test_every_line_rate_is_the_sum_of_its_parts():
    for f in _FINDINGS.all():
        for line, parts in lines_for_finding(f):
            assert abs(sum(v for _, v in parts.components) - line.unit_price_zar) <= 0.01, line.description

def test_feeder_supply_line_shows_markup_and_install_line_shows_crew():
    supply, install = lines_for_finding(_FINDINGS.feeders[0])[:2]
    assert supply[1].method == "built_up" and supply[1].markup == 1.3
    assert [c for c, _ in supply[1].components] == ["Material incl. markup", "Consumables", "Transport", "Waste"]
    assert [c for c, _ in install[1].components] == ["Install labour"]
    assert install[1].labour_note == "2 electricians, 2 semi-skilled, 10 general workers: 16 h per 100 m"

def test_fixed_and_free_issue_items_say_so():
    methods = {l.description: p.method for f in _FINDINGS.items for l, p in lines_for_finding(f)}
    assert set(methods.values()) == {"built_up", "free_issue_install", "fixed_price"}

def test_kiosk_board_lists_its_housing():
    line, parts = lines_for_finding(_FINDINGS.boards[1])[0]
    assert parts.method == "board_build_up" and "Outdoor kiosk housing" in [c for c, _ in parts.components]
```

- [ ] **Step 3: Run** `api/.venv/Scripts/python.exe -m pytest tests/shared/test_pricing_explains.py -q` — the four new tests FAIL with `ImportError: lines_for_finding`.
- [ ] **Step 4: Implement.** Move each `_board_lines/_feeder_lines/_item_line/_wire_line` to return `List[PricedLine]` built from the `BuiltUpRate` it already computes (components = its `material_supply`, `consumables`, `transport`, `waste`, `install_labour`; trench/tape/tag-only/plinth/kiosk/fixed price as single named components). `lines_for_finding` dispatches on type; `price_findings` = `[line for f in findings.all() for line, _ in lines_for_finding(f)]` in the **same order as today** (boards, feeders, items, wires). `describe_install_task` reads the existing private `_cable_install_task/_bcew_install_task/_termination_task`.
- [ ] **Step 5: Run** the file, then the whole suite `api/.venv/Scripts/python.exe -m pytest -q -p no:warnings` — all PASS (`test_price_findings_is_unchanged` proves the bill did not move).
- [ ] **Step 6: Commit** `feat(pricing): each line can say how its rate was built`.

---

### Task 3: Reading a run — trace, explain, find, gaps, overview

**Files:**
- Create: `api/assistant/__init__.py`, `api/assistant/explain.py`
- Test: `tests/assistant_layer/test_explain.py`, `tests/assistant_layer/conftest.py` (a `record` fixture: a `RunRecord(pipeline="dxf", status="passed")` whose `result` is a `DxfEstimatorRun` with Task 2's `_FINDINGS` (copy them into the conftest) and the bill `price_findings` makes from them)

**Interfaces:**
- Consumes: `lines_for_finding`, `RateParts` (Task 2); `core.run_store.RunRecord`
- Produces (all return JSON-safe dicts/lists; rand values rounded to 2 dp):
  - `trace_lines(result) -> Dict[str, Tuple[finding, RateParts]]` keyed by line ref `"4.15"`; a line matches a finding when section, description, unit and qty are equal to one of that finding's priced lines.
  - `run_overview(record) -> dict`: `{"run_id","pipeline","status","files":[...], "line_count", "subtotal_zar", "total_incl_vat_zar", "gap_count", "lines_by_evidence": {"measured": n, ...}, "supplier_prices_applied": bool}`
  - `find_lines(record, text: str = "", section: int | None = None, evidence: str | None = None, limit: int = 25) -> list[dict]`: each `{"ref","description","qty","unit","rate_zar","amount_zar","evidence"}`; text match is case-insensitive on description; `evidence` is `None` for untraced lines.
  - `explain_line(record, ref: str) -> dict`: `{"ref","description","section","qty","unit","rate_zar","amount_zar","amount_check": "<qty> × R <rate> = R <amount>", "traced": bool, "not_traced_reason": str, "reader","sheet","building","evidence","confidence","assumption","notes","gaps":[{description, assumption, suggested_action, severity}], "rate": {"method","components":[{"label","zar"}],"markup","labour_note"} | None, "supplier_rate_zar": float | None}`
  - `list_gaps(record, severity: str | None = None) -> list[dict]` ordered high → medium → low.
  - `ExplainError(ValueError)` for an unknown ref, with message `"No line 9.99 in this bill. Use find_lines to look one up."`

- [ ] **Step 1: Write the failing tests** — names and assertions:
  - `test_every_priced_line_traces_back_to_its_finding`: `len(trace_lines(record.result)) == len(record.result.boq.line_items)`.
  - `test_explain_feeder_line`: for the "Supply 50mm² …" line, `traced`, `evidence == "measured"` when the finding says so, `rate["components"]` labels as in Task 2, `amount_check` equals `f"{qty:g} × R {rate:,.2f} = R {amount:,.2f}"` with spaces as thousands separators (`"R 1 234.50"`).
  - `test_explain_line_without_findings`: set `record.result.findings = None`; `traced is False`, `rate is None`, `not_traced_reason == "This run was made before AfriPlan kept its findings, so the rate build-up is not available. Re-run it to see one."`, description and qty still present.
  - `test_untraced_line_is_reported_not_guessed`: append a line with a description no finding makes; `traced is False`, `not_traced_reason == "This line was added after pricing (for example by combining two readers), so no single finding explains it."`
  - `test_sourced_rate_is_shown_beside_built_up_rate`: set `record.sourced_boq` to a copy of the bill with that line's `unit_price_zar` changed; `supplier_rate_zar` is the new rate, `rate_zar` the built-up one.
  - `test_unknown_ref_raises_plain_error`: `pytest.raises(ExplainError, match="No line 9.99")`.
  - `test_find_lines_filters_by_text_section_and_evidence` and `test_gaps_come_highest_first`.
- [ ] **Step 2: Run** `api/.venv/Scripts/python.exe -m pytest tests/assistant_layer/test_explain.py -q` — FAIL (`ModuleNotFoundError: assistant`).
- [ ] **Step 3: Implement** in `api/assistant/explain.py` (imports only `agent.shared`, `core`).
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(assistant): read a run line by line, with evidence and rate build-up`.

---

### Task 4: How-it-works cards

**Files:**
- Create: `api/assistant/cards/` — one Markdown file per topic below, 120–300 words, plain language, written from the named sources; each ends with a `Source:` line naming the module(s)
- Create: `api/assistant/cards.py`
- Test: `tests/assistant_layer/test_cards.py`

| Topic id | Card says how… | Read before writing |
|---|---|---|
| `counting-symbols` | CAD blocks and repeated shapes are counted and matched to the legend | `agent/dxf_pipeline/passes/` (legend, shapes.py), `agent/shared/legend.py`, ADR-0007 |
| `measuring-cad` | wiring and feeder lengths are measured on CAD geometry and the site plan, scale, routes | `agent/shared/routes.py`, `dxf_pipeline/passes/site_routes.py` |
| `measuring-pdf` | vector site-plan PDFs are measured the same way | `pdf_pipeline/passes/site_routes.py` |
| `reading-pdf-pages` | the drawing reader reads each PDF page (AI as eyes, Python checks) | `pdf_pipeline/passes/`, ADR-0002 |
| `combining-readers` | the two readers' findings merge; evidence ranks measured > counted > written > seen > assumed | `consolidate/combine.py`, `agent/shared/findings.py`, ADR-0008 |
| `rates-and-markup` | a rate = material × 1.3 + consumables 9 % + transport 2 % + waste 5 % (of marked-up material) + labour (crew × hours ÷ quantity); contingency 5 %, VAT 15 % | `core/rate_model.py`, `agent/shared/pricing.py` |
| `sans-checks` | what SANS 10142-1:2017 checks are run | `core/standards.py` |
| `gaps` | what a gap is, severities, why nothing is silent | `agent/shared/boq.py::GapItem`, CLAUDE.md hard rule 7 |

**Interfaces:**
- Produces: `CARD_TOPICS: Tuple[str, ...]` (the eight ids, in table order); `how_it_works(topic: str) -> str`; unknown topic raises `ValueError(f"No card '{topic}'. Topics: {', '.join(CARD_TOPICS)}")`.

- [ ] **Step 1: Failing tests**: `test_every_topic_has_a_card` (file exists, 120–300 words, ends with a `Source:` line); `test_unknown_topic_lists_the_topics`; `test_rates_card_states_the_real_percentages` (the card text contains `"1.3"`, `"9 %"`, `"2 %"`, `"5 %"` **and** a test asserts those equal `DEFAULT_PARAMS.material_markup`, `consumables_pct`, `transport_pct`, `waste_pct` so the card breaks when the code changes).
- [ ] **Step 2: Run** `… pytest tests/assistant_layer/test_cards.py -q` — FAIL.
- [ ] **Step 3: Write the cards and `cards.py`.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(assistant): plain how-it-works cards, checked against the code`.

---

### Task 5: Chat storage and the monthly cap

**Files:**
- Modify: `api/db/connection.py` (`_schema_statements`: add `chat_messages`)
- Create: `api/db/assistant_chat.py`
- Test: `tests/integration/test_assistant_chat_store.py` (real dev DB, like `test_symbol_endpoints.py`; use `run_id = "test-" + uuid4().hex[:8]` and delete its rows in a fixture teardown)

Table:
```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    msg_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    role TEXT NOT NULL,              -- 'user' | 'assistant'
    content_json TEXT NOT NULL,      -- Anthropic content blocks, replayable
    display_text TEXT NOT NULL,      -- what the panel shows
    unverified_json TEXT NOT NULL DEFAULT '[]',
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_zar REAL NOT NULL DEFAULT 0,
    created_at {created_at}
)
```

**Interfaces:**
- Produces:
  - `save_turn(run_id: str, messages: list[dict]) -> None` — one transaction; each dict has the columns above except `msg_id`/`created_at` (generated; `created_at` strictly increasing within a turn so order is stable).
  - `load_messages(run_id: str) -> list[dict]` in order.
  - `delete_messages(run_id: str) -> None` (tests; later the "clear chat" in stage 3).
  - `chat_cost_zar(run_id: str) -> float`; `month_cost_zar(now: datetime) -> float` (all runs, calendar month of `now`, UTC).
  - `monthly_cap_zar() -> float | None` reading `AFRIPLAN_ASSIST_MONTHLY_CAP_ZAR` (unset/empty/invalid → `None`).

- [ ] **Step 1: Failing tests**: `test_a_turn_is_saved_and_loaded_in_order`, `test_costs_add_up_per_run_and_per_month`, `test_cap_unset_means_none` / `test_cap_reads_rand_value` (monkeypatch env).
- [ ] **Step 2: Run** `… pytest tests/integration/test_assistant_chat_store.py -q` — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS; then the full suite (schema change touches every test that opens the DB).
- [ ] **Step 5: Commit** `feat(db): store assistant chats per run, with their cost`.

---

### Task 6: The invented-figure check

**Files:**
- Create: `api/assistant/figures.py`
- Test: `tests/assistant_layer/test_figures.py`

**Interfaces:**
- Produces: `unverified_figures(answer: str, allowed_texts: Sequence[str]) -> List[str]` — the figures in `answer` (as written) that appear in none of `allowed_texts`.

Rules (each one is a test):
- A figure is a number with optional `R`, thousands separators (space, thin space U+202F, NBSP, comma) and decimals: `"R 19 550"`, `"19,550.00"`, `"186"`, `"2.5"`, `"4.15"`.
- Single-digit integers (`0`–`9`) are ignored.
- Two figures are equal if their values are equal to 2 dp, or the answer's figure equals the allowed figure rounded to 0 or 1 dp, half-up or half-even (`"R 19 550"` matches `19550.0`; `"186 m"` matches `186.0`; both `"7 812"` and `"7 813"` match `7812.5`).
- Years and standard numbers present in allowed texts (e.g. `10142-1:2017` from a card) pass like any other figure.

- [ ] **Step 1: Failing tests**: `test_tool_figures_pass_in_any_format`, `test_made_up_amount_is_caught` (answer `"about R 25 000"` with tools containing only `19550.0` → `["R 25 000"]`), `test_single_digits_are_ignored`, `test_rounded_figures_pass`, `test_line_refs_pass_when_a_tool_returned_them`.
- [ ] **Step 2: Run** — FAIL. **Step 3:** implement. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(assistant): catch figures no tool gave`.

---

### Task 7: The conversation loop

**Files:**
- Create: `api/assistant/prompts.py`, `api/assistant/tools.py`, `api/assistant/loop.py`
- Test: `tests/assistant_layer/test_loop.py` (a `FakeClient` whose `messages.create(**kw)` records `kw` and returns scripted `SimpleNamespace(content=[...], stop_reason=..., usage=SimpleNamespace(input_tokens=…, output_tokens=…))`, like `core/gemini_client.py` returns)

**Interfaces:**
- Consumes: Task 3 functions, `how_it_works`/`CARD_TOPICS` (Task 4), `unverified_figures` (Task 6), `ASSIST_MODEL`, `estimate_cost_zar`.
- Produces:
  - `tools.TOOL_SCHEMAS: list[dict]` — strict schemas for `run_overview()`, `find_lines(text?, section?, evidence? ∈ measured|counted|written|seen|assumed)`, `explain_line(ref)`, `list_gaps(severity? ∈ high|medium|low)`, `how_it_works(topic ∈ CARD_TOPICS)`.
  - `tools.call_tool(name: str, args: dict, record: RunRecord) -> tuple[str, bool]` → `(json_text, is_error)`; `ExplainError`/`ValueError` become `is_error=True` with the message, never an exception.
  - `prompts.SYSTEM_PROMPT: str` — frozen. Must say: you explain a South African electrical Bill of Quantities from this run's record; use tools for every figure and never compute one; if no tool gives a figure, say it is not known; quote line refs like 4.15; explain in plain words for a contractor; stage 1 cannot change the bill or re-run — say what the user could do instead (e.g. "re-run with the site plan included") without claiming to do it.
  - `loop.TurnResult` dataclass: `reply: str`, `new_messages: list[dict]` (Anthropic-format, starting with the user message), `unverified: list[str]`, `tokens_in: int`, `tokens_out: int`, `cost_zar: float`, `tool_calls: list[str]`.
  - `loop.run_turn(*, client, record: RunRecord, history: list[dict], user_text: str, model: ModelSpec = ASSIST_MODEL, max_tool_calls: int = 8, history_budget_chars: int = 60_000) -> TurnResult`.
  - `loop.trim_history(history: list[dict], budget_chars: int) -> list[dict]` — drops the oldest whole exchanges first; never starts on a `tool_result` turn or separates a `tool_use` from its `tool_result`.

Behaviour: the first user turn of each request is prefixed with a context block `Run <id> · <pipeline> · files: …` (outside the frozen system prompt). `system` and the last tool schema carry `cache_control: {"type": "ephemeral"}`. After `max_tool_calls`, call once more with `tool_choice={"type": "none"}`. After the final text, `unverified_figures(reply, [user_text, *every tool result text this turn])`; if any, append one user message `"These figures are in no tool result: <list>. Answer again using only figures from the tools, or say they are not known."` and loop once more (that retry may use tools, within the same cap); whatever is still unverified goes into `TurnResult.unverified`. Cost = `estimate_cost_zar(tokens_in, tokens_out, model)` summed over every call.

- [ ] **Step 1: Failing tests**: `test_answer_built_from_a_tool_call` (script: tool_use explain_line → text; the reply is returned, `tool_calls == ["explain_line"]`, the tool_result block holds Task 3's JSON); `test_tool_cap_forces_an_answer` (script 9 tool_uses; assert exactly 8 tools ran and the 9th call had `tool_choice == {"type": "none"}`); `test_made_up_figure_gets_one_retry_then_is_flagged`; `test_tool_error_goes_back_to_the_model` (`explain_line("9.99")` → tool_result `is_error: True`, loop continues); `test_history_trim_keeps_tool_pairs_together`; `test_system_prompt_is_frozen` (no digits matching a date, no `run_id`); `test_cost_sums_every_call`.
- [ ] **Step 2: Run** `… pytest tests/assistant_layer/test_loop.py -q` — FAIL. **Step 3:** implement. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(assistant): tool-use loop that answers only from the run`.

---

### Task 8: HTTP endpoints

**Files:**
- Create: `api/routers/assistant.py`
- Modify: `api/main.py` (`app.include_router(assistant.router)`)
- Test: `tests/integration/test_assistant_endpoints.py` (`TestClient(app)`; override the `get_assistant_client` dependency with Task 7's `FakeClient`; put a synthetic passed run in `run_store` with a `test-` id and remove it after)

**Interfaces:**
- Consumes: `run_turn`, `trim_history`, `save_turn`, `load_messages`, `chat_cost_zar`, `month_cost_zar`, `monthly_cap_zar`.
- Produces:
  - `get_assistant_client()` (FastAPI dependency) → `PdfLLM(system_prompt="", provider="claude")._client`; raises `HTTPException(503, "The assistant needs an Anthropic API key on the server (ANTHROPIC_API_KEY).")` when the key is missing.
  - `GET /api/assistant/{run_id}/messages` → `{"messages": [{"role","text","unverified":[...],"cost_zar","created_at"}], "total_cost_zar"}` (only messages with non-empty `display_text`; tool turns are stored but not listed).
  - `POST /api/assistant/{run_id}/messages` body `{"text": str}` → `{"reply","unverified","cost_zar","total_cost_zar","tool_calls"}`.

Errors (exact `detail` text, each a test):
| Case | Status | detail |
|---|---|---|
| run not in store | 404 | `"Run not found. Open a run from Upload or the Take-off page first."` |
| run still running | 409 | `"This run is still working. Ask again when it has finished."` |
| run has no bill | 409 | `"This run has no bill to explain (it failed: <error>)."` |
| text empty or > 2000 chars | 422 | (pydantic) |
| cap reached | 429 | `"This month's assistant budget of R <cap> is used up. It resets on the 1st."` |
| Claude API raises | 502 | `"The assistant could not reach Claude: <exception message>. Try again in a minute."` — **nothing saved** |

- [ ] **Step 1: Failing tests**: `test_ask_and_read_back`, one test per error row (`test_api_failure_saves_nothing` asserts `load_messages` is unchanged after the 502), `test_turn_cost_is_stored_and_totalled`.
- [ ] **Step 2: Run** `… pytest tests/integration/test_assistant_endpoints.py -q` — FAIL. **Step 3:** implement (the turn runs in `run_in_threadpool`; history = `trim_history([json.loads(m["content_json"]) for m in load_messages(run_id)])`). Saving: every entry of `TurnResult.new_messages` becomes one row (`content_json` = the message dict); `display_text` = the user's text for the first row and `TurnResult.reply` for the last assistant row, `""` for tool turns in between; `unverified`, tokens and `cost_zar` go on the last assistant row only. **Step 4:** PASS, then the full suite.
- [ ] **Step 5: Commit** `feat(api): ask the assistant about a run`.

---

### Task 9: The chat panel

**Files:**
- Modify: `src/api/client.js` (`api.assistant.history(runId, signal)`, `api.assistant.ask(runId, text)`)
- Create: `src/components/assistant/ChatPanel.jsx`, `src/styles/assistant.css`
- Modify: `src/components/ui/AppShell.jsx` (top-bar button "Ask AfriPlan" with a `MessageSquare` icon, `aria-expanded`; renders the panel), `src/App.jsx` (pass `runId` to `AppShell`)
- Test: `tests-e2e/assistant.spec.js`

Behaviour and exact copy:
- Panel: right-hand, 400 px wide on ≥ 900 px viewports (main content keeps its width by padding-right while open); full-screen sheet below 900 px with a close button. Closed by default; open state remembered in `localStorage` (`afriplan.assistantOpen`, wrapped in try/catch).
- Header: "Ask about this bill" + the run's file label; the running cost `"Chat so far: R 4.20"`.
- No run selected: `"Run a take-off first, then ask about its bill here."` and a button "Go to Upload".
- Empty chat: three starter buttons — "What is still assumed?", "Explain the most expensive line", "How do you measure cable lengths?".
- While waiting: input disabled, a status line `"Reading the bill…"` (`role="status"`).
- Each answer shows its cost (`"R 1.38"`) in small text. If `unverified` is non-empty, a warning under the answer: `"Check these figures yourself; they were not found in the bill: R 25 000."`
- Error: the server's `detail` text and a "Try again" button that resends the same question.
- Enter sends, Shift+Enter makes a new line; the input is a `<textarea>` labelled "Your question"; send button "Ask".
- Styles use `tokens.css` variables; answer text in `--ink`, the user's questions right-aligned on `--paper-2`; hit areas ≥ 24 px.

- [ ] **Step 1: Failing e2e test** (Playwright `page.route` mocks `/api/assistant/*` and `/api/runs/*`; auth via the same `addInitScript` as `responsive.spec.js`): `opens from the top bar and answers a starter question`, `shows the unverified-figure warning`, `shows the server reason on error and retries`, `no run → points to Upload`, `@ 390px the open panel has no overflow and no hit area under 24 px`.
- [ ] **Step 2: Run** `npm run build && npx playwright test tests-e2e/assistant.spec.js` — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the spec — PASS; then `npx playwright test tests-e2e/responsive.spec.js` (panel closed by default, so no route may regress).
- [ ] **Step 5: Commit** `feat(ui): a chat panel that explains the open bill`.

---

### Task 10: Live check and handover

**Files:**
- Modify: `CLAUDE.md` ("Current state": one bullet for the assistant stage 1, ADR-0009), `api/assistant/__init__.py` docstring (what the package is, its import rules)

- [ ] **Step 1:** Full verification: `api/.venv/Scripts/python.exe -m pytest -q -p no:warnings`, `npm run build`, `npx playwright test`. Report counts honestly.
- [ ] **Step 2: Ask the owner before the paid check** (CLAUDE.md: paid API runs). With a yes: start the app (`python scripts/dev.py start`), run a DXF take-off on a synthetic or public drawing (never client data in a screenshot that leaves the machine), ask the three starter questions and one "how is line X's rate made?" question; record cost per answer and whether any figure was flagged.
- [ ] **Step 3: Commit** `docs: assistant stage 1 in the current state` and report to the owner what stage 2 (projects and re-run) will add.
