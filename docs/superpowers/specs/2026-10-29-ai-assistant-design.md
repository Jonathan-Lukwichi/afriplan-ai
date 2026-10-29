# AI assistant with memory — design

- **Date:** 2026-10-29
- **Status:** waiting for the owner's approval (questions answered 2026-10-29)
- **Asked for by:** Jonathan / Hervé
- **Needs:** a new ADR (ADR-0009) before code. It adds an AI loop that can *start* work and
  a store the pipelines learn from; ADR-0002, ADR-0006 and ADR-0007 do not cover that.

## 1. Intent

A contractor looking at a bill has questions the screen cannot answer today. "Where do the
17 LED panels come from?" "Why is this cable R 38 a metre?" "How do you measure feeder
lengths?" "What is still assumed?" They also want to *do* something about the answer: re-read
the site plan, add the single-line diagram they forgot, correct a symbol.

The assistant is a chat panel in the signed-in app that answers these questions **from the
run's own record** and can **re-launch the readers** when the user confirms. The web app
becomes an agent with **memory**: it keeps each project's drawings, runs, chat and changes,
and it remembers the user's confirmed corrections from one project to the next.

The owner's words: the assistant must *explain how the tool calculates or extracts an
element*, must be able to *relaunch the tools for any missing details so the user can check
and refine the results*, and *it must have a memory*. For the demo there must be *a button to
clean the memory*.

## 2. Goals

1. **Explain a line.** For any bill line: which reader found it, on which sheet, its evidence
   (measured, counted, written, seen, assumed), the assumption and gaps behind it, and how its
   rate and amount were worked out (supply, labour hours × crew, markup).
2. **Explain the method.** Plain answers to "how do you measure / count / price X?", taken
   from fixed notes that describe what the code really does.
3. **Walk the gaps.** List what is assumed or missing, most important first, with a
   suggested fix for each.
4. **Re-run on request.** Propose a re-run (a reader, on all or some of the project's stored
   files), show the cost for a paid PDF read, run it only after the user clicks Confirm, then
   say what changed between the two bills, line by line.
5. **Change a line on request.** Propose a correction (a quantity, a rate, a closed gap). It is
   applied only on Confirm and recorded with who, when and why.
6. **Project memory.** A project keeps its drawings on disk, every run, the whole chat and
   every change. Reopen it next week and carry on.
7. **Office memory.** Corrections the user confirms are remembered and applied on later
   projects. Every line that used one says so (for example "From your fix on Clinic Block A,
   29 Oct"). The user can list, delete one, or **clear all** with one button.

## 3. Non-goals (first version)

- An "always bill this item" memory (for example draw wire). Its quantity would come from the
  completer's ratio model, which is client data and is not on the live server.
- Re-reading a single item or a single page. Re-runs are per reader, on whole files.
- Real user accounts. Login stays demo-only, with one shared profile (a settled product
  decision), so all testers share one office memory and see all projects.
- Voice, file previews inside the chat, e-mailing from the chat.
- The DOE workflow (`doe/`). This is a web-app feature only.
- Gemini as the chat model (owner's answer, §9).

## 4. Anti-goals: it has failed if any of these happen, even if it "works"

- **It invents a number.** Every quantity, length, rate or rand amount in an answer must come
  from a tool result. The model never does arithmetic (ADR-0002).
- **It changes the bill on its own.** No run, change or memory write happens without the
  user's click on Confirm.
- **A guess spreads.** Only facts a person confirmed go into office memory. AI guesses never do.
- **A hidden cost.** Every paid call shows its estimated cost before and its real cost after.
- **A silent change.** A line changed by a user or by office memory is tagged, like every
  ASSUMED line already is (hard rule 7).
- **The rules bend.** Pipelines still never import the assistant, the database or each other.

## 5. Constraints (from CLAUDE.md and the ADRs)

- **LLM = eyes, Python = brain (ADR-0002).** The model answers through tools with strict
  schemas. Python computes every figure: the rate build-up, the bill diff, the cost estimates.
- **Model IDs live only in `api/core/config.py`.** Add `ASSIST_MODEL`.
- **Read-only layers stay read-only.** Nothing under `api/agent/` imports the assistant, `db`
  or `routers`. Office memory reaches a reader the way symbol names already do: `core/run_jobs.py`
  loads it and passes it in as a parameter (see `make_shape_namer(..., remembered=load_symbol_names())`).
- **Both databases.** New tables go into `db/connection.py::_schema_statements`, so they work on
  both SQLite (Render) and Postgres.
- **Disk.** The live app on Render has a 1 GB disk at `/app/data`. Stored drawings must fit, so
  §7.4 sets a size limit and a clean-up rule.
- **Public repo (ADR-0005).** Stored drawings and chats live under `api/data/` (already
  gitignored). Tests use synthetic files only.
- **Ask first (CLAUDE.md):** paid API runs; any change to `BillOfQuantities` / `BQLineItem`; any new
  dependency. This design needs **none** of those (see §7.6 and §7.7), apart from the paid chat
  calls themselves, which the owner approved by choosing Claude (§9).

## 6. What the owner decided (2026-10-29)

- Keep each project's drawings, so the assistant can re-run without a new upload.
- The app has a memory: per project and across projects.
- Fixes confirmed on one project carry over to the next, with a visible note on every line that
  used one.
- A **Clear memory** button for demos.

## 7. Design

### 7.1 Words (add these to `context.md`)

| Term | Meaning |
|---|---|
| **Job** | One client project in the web app: its stored drawings, runs, chat and changes. The screen says *project*; the code says `job`, so it is never confused with a *reference project* (`data/projects/`). |
| **Assistant** | The chat agent. It reads the job's record through tools and proposes actions. |
| **Action** | Something the assistant proposes (a re-run, a change, a memory write) that waits for Confirm. |
| **Change** | A confirmed edit to a line of a job's bill, with who, when and why. |
| **Office memory** | Confirmed facts reused across jobs. The existing `symbol_names` table is the first kind. |

### 7.2 Where the code goes

```
api/assistant/            NEW top-level package (beside evaluation/, audit/, assist/)
  loop.py                 the tool-use conversation loop (one user turn = one loop)
  tools.py                read tools + propose tools, each a plain Python function
  explain.py              line explanation + rate build-up (uses core.rate_model, agent.shared)
  diff.py                 bill-to-bill diff for "what changed after the re-run"
  cards/*.md              fixed "how it works" notes, one per topic (§7.5)
  prompts.py              frozen system prompt (no dates, ids or names: it is the cache prefix)
api/db/jobs.py            jobs, job files, chat messages, actions, changes
api/db/office_memory.py   office memory read/write/clear
api/routers/assistant.py  HTTP: chat turn, confirm/cancel an action, memory list/delete/clear
api/routers/jobs.py       HTTP: create a job, upload files to it, list jobs, open one
src/components/assistant/ ChatPanel, ActionCard, MemoryDrawer
```

`api/assistant/` may import `core`, `db`, `agent.shared`, `audit` and `consolidate`. Nothing
under `api/agent/` may import it. Add it to the existing CI/hook import check.

### 7.3 Storage (new tables)

- `jobs(job_id, name, created_at, last_opened_at)`
- `job_files(job_id, file_id, filename, sha256, size_bytes, stored_path, created_at, evicted)`.
  The files themselves go in `api/data/jobs/<job_id>/<file_id>-<filename>`.
- `runs.job_id`: a new nullable column on the existing `runs` table (`compare` likewise). Old
  runs keep working without a job.
- `chat_messages(job_id, msg_id, role, content_json, tokens_in, tokens_out, cost_zar, created_at)`:
  the full conversation, including tool calls and results, so a turn can be replayed.
- `actions(action_id, job_id, kind, payload_json, status[proposed|confirmed|cancelled|done|failed],
  est_cost_zar, real_cost_zar, result_run_id, created_at, decided_at)`
- `changes(change_id, job_id, made_on_run_id, line_match_json, field, old_value, new_value, reason, by, status[active|orphaned], created_at)`.
  `item_no` is renumbered on every run (`agent.shared.pricing.number_lines`), so a change never
  points at an item number. `line_match_json` holds section, normalised description, building and
  unit; see §7.6 for how it is found again.
- `office_memory(fact_id, kind, key, value_json, source_job_id, source_note, created_at)`.
  Kinds for the first version (the builder's call, see §10):
  - `symbol_alias`: this CAD block name / legend code means this catalogue item (for example "P2 =
    double socket outlet"). Used by the **DXF reader only**, through the same injection as
    `symbol_names`.
  - `rate_override`: use this rate for lines matching this section + normalised description. It is
    **not** keyed by `ItemKey`: that lives in the frozen scorer (`evaluation/taxonomy.py`) and
    `agent/` may not import it.

  `symbol_names` stays as it is. The memory drawer lists it with the rest.

### 7.4 Keeping drawings, within the disk

- Upload now creates (or adds to) a job and stores the files before the run starts.
- Limit: **800 MB** of stored drawings in total, leaving room for the database. When a new
  upload would pass it, the drawings of the job opened longest ago are removed first
  (`evicted = 1`). The job, its runs, chat and changes stay. The assistant then says "the
  drawings of this job were cleared to save space; upload them again to re-run".
- The memory drawer shows the space used.

### 7.5 The assistant's tools

**Read tools.** These answer straight away and cost nothing beyond the chat call. Python
fills every figure.

| Tool | Returns |
|---|---|
| `job_overview()` | files, runs (reader, status, date, total), open gaps count |
| `find_lines(text?, section?, evidence?)` | matching lines (item no, description, qty, unit, rate, amount, evidence) |
| `explain_line(item_no)` | evidence, reader, sheet (`drawing_ref`), building, assumption, gaps, *and* the rate build-up from `core.rate_model` (supply, labour task hours, crew cost, markup), plus any change or office-memory fact applied to it |
| `list_gaps(severity?)` | gaps with assumption and suggested action |
| `compare_runs(run_a, run_b)` | Python diff: added, removed, quantity or rate changed |
| `how_it_works(topic)` | text of one card from `api/assistant/cards/`. Topics in v1: counting symbols, measuring cable and feeders on CAD, measuring on vector PDFs, reading PDF pages, combining two readers and evidence ranks, rates and markup, derived items, SANS checks, gaps |
| `list_memory()` | office memory facts and remembered symbol names |

**Propose tools.** Each creates an `actions` row with status `proposed` and returns at once.
Nothing runs until Confirm.

| Tool | What Confirm does |
|---|---|
| `propose_rerun(reader, file_ids?, ai_symbols?, provider?)` | starts a run on the stored files through the existing `launch_dxf_run` / `launch_pdf_run` (queue and slots unchanged), with office memory passed in. When done, the assistant posts the diff. Shows the estimated cost for a PDF read. |
| `propose_change(item_no, field, value, reason)` | records a `changes` row; the bill shown and exported for that job uses it |
| `propose_remember(kind, key, value, reason)` | writes an `office_memory` row |

**Which fixes become office memory.** Only symbol meanings and rates are kinds of office memory. A
quantity fix (17 panels, not 16) belongs to that job only. After the user confirms a change of a
rate, or tells the assistant what a symbol is, the assistant follows up with a second action card,
"Remember this for future projects?". The user confirms that separately. It is never automatic.

The cards are written once, by a person, from the code and `doe/knowledge/BOQ_KNOWLEDGE.md`.
When a pipeline's method changes, its card changes in the same commit.

### 7.6 How changes and memory reach the bill (no schema change)

- A **change** is an overlay, applied when a job's bill is read for display or export. This is
  the same idea as the existing `sourced_boq` override in `run_store`. The run's own result is
  never edited.
- **A change follows the job's later runs.** When a job's bill is read, each active change is
  matched to the line with the same section, normalised description, building and unit. If
  exactly one line matches, the change is applied. If none or several match, the change is marked
  `orphaned`, is not applied, and the assistant and the BoQ page list it as "a change that no
  longer fits this bill". The user can re-apply it to a chosen line or drop it.
- **When office memory takes effect.**
  - `symbol_alias` is read by `core/run_jobs.py` when a DXF run **starts** (any run: plain
    Upload or assistant re-run) and passed into the reader, like `symbol_names` today. It changes
    what is counted, so deleting it affects only later runs.
  - `rate_override` is applied as an overlay **when a bill is read**, like a change. Deleting it
    or clearing memory updates the shown bill at once.
  - Neither touches the PDF reader's prompt, so no PDF baseline moves.
- **Provenance** goes in the existing `BQLineItem.notes` (for example
  `Changed by you, 29 Oct: "count checked on site"` or `From your fix on Clinic Block A, 29 Oct`).
  `BQLineItem` gains no field. A changed quantity also emits a `GapItem` with severity `low`,
  so the change shows in the gap report (hard rule 7).

### 7.7 The loop

- The Messages API tool-use loop: system prompt (frozen) + job context + the chat so far +
  tools. Up to **8 tool calls per user turn**; then it must answer.
- **Rule in the prompt:** every figure in an answer comes from a tool result in this turn;
  if no tool gives it, say it is not known. A Python check after each answer looks for rand
  amounts and quantities that appear in no tool result this turn, and asks the model to fix
  them once if any are found.
- Same client interface as the rest of the app: Claude through the Anthropic SDK. No new
  dependency. Claude only (§9). For the record, Gemini would need work first:
  `core/gemini_client.py` converts only text and image blocks of the history, so a multi-step
  loop's `tool_use` / `tool_result` turns would be lost.
- Cost per turn is computed by `estimate_cost_zar`, stored on the message and shown in the
  panel. The job shows its running chat cost.
- Answers stream token by token if the chosen client supports it; otherwise the whole answer
  appears at once (the builder decides).

### 7.8 Screens

- **Upload** asks for a project name (or picks an existing project) and shows that the drawings
  will be kept. **Welcome** lists recent projects to reopen.
- **Chat panel:** a button in the top bar of every signed-in page opens a panel on the right.
  On phones it opens full-screen. It knows the open job and run. It shows the answers, small
  "source" chips (line numbers, sheets) and **action cards** with Confirm / Cancel, the cost
  and a one-line summary of what will happen. A finished re-run posts a card: "12 lines
  changed, 3 gaps closed. See the differences."
- **Memory drawer** (from the panel): lists office memory and remembered symbol names, each
  with where it came from and a Delete button; the disk space used; and **Clear memory**,
  which asks once ("This removes N remembered fixes and M symbol names. Projects are kept.")
  and then empties `office_memory` and `symbol_names`.
- The BoQ page shows the `notes` provenance on changed or remembered lines and a small marker.

### 7.9 Testing

- Each read tool and `diff.py`: unit tests on synthetic runs. No network.
- The loop: a fake client that scripts tool calls, to prove figures come from tools, that the
  invented-figure check catches a made-up number, that propose tools never run anything, and
  that Confirm does.
- Storage: eviction at the limit; clear memory empties both tables; an old run without a job
  still opens.
- Import rule: a test that `api/agent/` never imports `assistant` or `db`.
- e2e (Playwright, mocked API): open the panel, ask, confirm a re-run, see the diff card,
  clear memory. Must pass the existing responsive spec (320 px, 24 px hit areas).

## 8. Left to the builder

The panel's look (follow `src/styles/landing.css` tokens); whether answers stream; the exact
card texts; table indexes; how many messages of history go into each turn (keep the most
recent within a token budget, summarise older ones or drop them); the build order of the parts.

## 9. Owner's answers (2026-10-29)

- **The chat runs on Claude only** (`ASSIST_MODEL` in `core/config.py`). Gemini for the chat is out
  of scope for v1. No monthly cap was set: the panel shows the cost of every turn and the job's
  running total. A cap can be switched on later with `AFRIPLAN_ASSIST_MONTHLY_CAP_ZAR`; unset means no
  cap (the designer's call). When it is set, a turn that would pass it is refused with a plain reason.
- **Disk stays at 1 GB.** Stored drawings are capped at 800 MB, with the clean-up rule in §7.4.

## 10. Calls made by the designer (check these)

1. A confirmed change follows the job's later runs, matched by section + description + building +
   unit. A change that no longer fits is shown, not dropped silently.
2. Office memory has two kinds in v1: symbol meanings (DXF reader only) and rates (keyed by
   description, not by the frozen `ItemKey`).
3. "Always bill this item" is left out of v1.
4. Quantity fixes stay in their job. Symbol and rate fixes become office memory only through a
   second "remember this?" confirmation.
5. Symbol meanings apply when a run starts; rates apply when a bill is read, so deleting a rate
   fact shows at once.
6. Code says `job`, screen says *project*, to keep clear of *reference project*.
7. No monthly chat-spend cap by default; it can be set by an environment variable.
