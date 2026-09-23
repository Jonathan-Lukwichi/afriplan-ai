# AfriPlan Electrical — Prompt/Context/AI-Engineering Blueprint

Audited: 2026-08-29. No prior blueprint report existed at this path — this is the first pass.

Scope note: this audit read the actual code (not just README/CLAUDE.md claims) — `app.py`,
`CLAUDE.md`, `README.md`, `AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md`, `core/config.py`,
`agent/pdf_pipeline/{llm.py,pipeline.py,stages/*,passes/*,prompts/*}`,
`agent/dxf_pipeline/{pipeline.py,passes/*}`, `sourcing/engine.py`, `scoring/harness.py`,
`tests/architecture/test_independence.py`, `tests/pdf_pipeline/conftest.py`,
`.github/workflows/ci.yml`, `requirements.txt`, `scripts/score_estimator.py`, and the
`pages/2_Extraction.py` UI wiring that determines what actually runs in production.

---

## 1. Project classification

**Blend of three, with a clear dominant facet:**

1. **AI tool / product (dominant).** `app.py` → `pages/` is a shipped Streamlit product with
   real end users (SA electrical contractors) making tender decisions off the output. The BOQ
   totals and SANS-10142 compliance flags are facts stated to a paying user, not a demo.
2. **Coding assistance (dominant, equally).** This is a live Python codebase that Claude Code
   maintains day to day — CLAUDE.md, an architecture test suite, and per-pipeline READMEs exist
   specifically to govern AI-assisted edits.
3. **Research workflow (secondary, explicit).** `AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md`
   Appendix A and the README's "Research angle" section state outright that the dual-pipeline
   shape exists partly to produce a Master's thesis dataset (PDF vs DXF comparative accuracy
   study). `agent/comparison/` and `scoring/harness.py` are that instrument, not incidental.

Not a task-automation/loop project in the ongoing-operation sense today — see §7.

---

## 2. Alignment status

**Step 2 of the discovery process was genuinely done once — and done unusually well.**
`AFRIPLAN_V6_1_DUAL_PIPELINE_BLUEPRINT.md` is a strong, rare example of real upfront
discovery: stated author intent (§0 preamble — "designed to support both production use *and*
the comparative ML research"), an explicit single governing rule, acceptance criteria, and even
an "Open questions for Hervé" section (§10) that honestly flagged unresolved calls instead of
guessing them. `CLAUDE.md` is a real constitution file, not a stub. Credit where due: most
projects audited under this kit don't have this.

**But the alignment artifact has not kept pace with the code, and that is the top-priority
finding of this audit — concrete evidence below, not a vague "keep docs updated" note:**

- `CLAUDE.md`'s architecture diagram and "What's where" table describe **only** the v1 pipeline
  (`agent/pdf_pipeline/stages/{classify,extract,evaluate,generate}.py`, one page-type prompt per
  file, a `PdfEvaluation` gate with confidence/consistency/MAPE/SANS composite scoring).
- The **actual production path**, wired in `pages/2_Extraction.py`, is
  `agent/pdf_pipeline/passes/run.py::run_pdf_estimator` — a "5-pass estimator" (multi-file
  ingest, `passes/orchestrator.py`, `passes/facts.py`, `passes/assemble.py`) that CLAUDE.md
  never mentions. Same for DXF: `agent/dxf_pipeline/passes/run.py::run_dxf_estimator` is what
  the UI calls, not the pipeline described in the blueprint doc.
- Two more real subsystems exist with **zero mention** in CLAUDE.md, the README, or the
  blueprint: `sourcing/` (live supplier quote fan-out and BOQ price application) and `scoring/`
  (baseline accuracy harness). `scoring/` and `sourcing/` tests are not part of the guaranteed
  CI gate either — see §5.
- The blueprint's own §11 "Out of scope" explicitly states **"no DWG support — DXF only."**
  The shipped code has DWG support (`agent/dxf_pipeline/dwg.py`, `converted_from_dwg` surfaced
  in the UI). This is a direct, checkable contradiction between the stated constitution and the
  implementation — exactly the kind of drift a fresh Claude Code session reading only CLAUDE.md
  would not catch.
- Most consequential: v1's `PdfEvaluation`/`DxfEvaluation` composite gate (confidence threshold,
  cross-page consistency, baseline MAPE, SANS-violation blocking) has **no equivalent in the v2
  estimator path**. `EstimatorRun.success` is simply `bool(boq.line_items)` — "did we produce
  any line at all," not "should a contractor trust this total." See §3 for why this matters and
  §6/§7 for the fix.

**Recommendation (top priority, concrete):** run a second discovery pass — not from scratch,
the original blueprint's *goal* section is still valid — specifically to reconcile what v2
actually does against what v1 was specified to do, and update CLAUDE.md to describe the system
that ships. Two concrete artifacts to produce (detailed in §6):

1. Rewrite `CLAUDE.md`'s architecture section and "What's where" table to match the `passes/`
   layout, and add `sourcing/` and `scoring/` to it.
2. Create `context/decisions.md` (a durable-memory file, not prose buried in a commit message)
   recording: why v2 superseded v1, whether v1's `stages/` files are dead code to delete or kept
   deliberately, why DWG support was added despite the blueprint's stated scope, and — most
   important — whether dropping the evaluation gate in v2 was a deliberate simplification or an
   unnoticed regression. Right now nothing in the repo answers that last question, and it's the
   one with real financial/compliance consequences.

---

## 3. Foundations plan

**Role formula — already well executed, worth stating explicitly so it's protected.**
`agent/pdf_pipeline/prompts/system_prompt.py` is a textbook role formula: Core Identity ("Senior
South African Electrical Estimator") + Experience Level (reads drawings "the way a contractor
preparing a tender does") + Niche Specialization (SANS 10142-1, NRS 034, SA circuit-naming
vocabulary) + Strategic Perspective (extraction discipline, confidence banding). It is frozen
(no timestamps/per-request data) specifically to preserve prompt-cache hits at position 0 — a
detail CLAUDE.md itself calls out as a hard rule (§ "Never put dynamic data... in the PDF system
prompt"). Do not let a future edit soften this; it's both a caching decision and a Structure
discipline decision.

**What → How → Why structure — mostly present, one gap.** `pass_prompts.py`'s per-pass
instructions (`READ_PROJECT_CONTEXT_PROMPT`, `READ_POWER_SPINE_PROMPT`,
`READ_LAYOUT_TAKEOFF_PROMPT`) are numbered How-steps with the negative constraint correctly
placed **last** ("Report only what is written. Do not invent buildings or drawings." /
"Never estimate a length yourself." / "Count what you SEE. Do not infer counts from area or room
type.") — this matches the playbook's recency-effect guidance exactly, already done right.
The **Why** is present only in the module docstring ("the deterministic brain decides what to
assume"), not in the text actually sent to the model. Recommend adding one Why-clause per pass
prompt (e.g., "...because a wrong length here compounds into every downstream cable-cost line")
— cheap to add, and Why is what lets the model correctly extrapolate to a page that doesn't match
any example it saw.

**Anti-hallucination guards — this project is squarely "AI tool/product that states facts to end
users" (BOQ totals, SANS compliance flags feed real tender decisions), so per the playbook's
Step 3 router: Strict Grounding + Verbatim Traceability are MANDATORY, not optional.**

| Guard | Status in this codebase |
|---|---|
| Strict Grounding | Present and enforced structurally — extraction only ever sees the rasterised page image via `tool_use`; no external parametric-memory path exists in the extract prompts. Good. |
| Escape Hatch | Present and well-designed — "RETURN ZERO with a low confidence... do not invent counts" (v1 system prompt) and "report missing as 0/false/empty... do not guess" (v2 pass prompts) are textbook Escape Hatch phrasing. Good. |
| Verbatim Traceability | **Partial.** v1's system prompt says "Quote the drawing reference... whenever you see one." v2's pass prompts (the ones actually running in production) do not carry an equivalent instruction to cite the source drawing/page per extracted fact. Recommend adding a `source_ref` field to the pass schemas (`pass_schemas.py`) and requiring it be populated per DB/circuit/room, the same discipline `PdfExtraction.per_field_confidence` already applies to confidence. |
| Clean Slate Protocol | Not directly applicable to single-shot per-page extraction; the retry-with-validation-feedback loop in `llm.py` is the closer analog and is implemented correctly (fresh instruction appended, not silently resent). |

**The gate regression is the real finding here, not a nitpick.** v1's `PdfEvaluation` /
`DxfEvaluation` composite score (mean confidence, cross-page consistency, baseline MAPE, SANS
critical-violation blocking) *is* this project's implementation of "don't let the model ship an
answer nobody checked." v2's estimator has no equivalent — `run.success` only checks that at
least one BOQ line exists. Per the playbook, a project that states facts to end users without a
grounding/verification gate is exactly the Vacuum-Squeeze / Open-Book failure mode the toolkit
exists to prevent. **Concrete fix:** port `PdfEvaluation`'s confidence + cross-page-consistency +
SANS-violation logic (it already exists, verbatim, in `agent/pdf_pipeline/stages/evaluate.py`) into
a new `agent/pdf_pipeline/passes/evaluate.py` that runs after `build_bill()` in `passes/run.py`,
and make `EstimatorRun.success` depend on it — not just on line-item count. Do the mirror-image
fix for the DXF v2 path (`agent/dxf_pipeline/passes/run.py`) using the existing coverage-score
logic in `agent/dxf_pipeline/stages/evaluate.py`. The "Gap report" (legend-declared-but-uncounted
items) already in the UI is a good complementary signal — keep it, it's not a substitute for the
missing composite gate, it's informational.

**Coding-discipline principles (this is also a coding-assistance project):** the codebase already
follows "surgical changes only" well (the independence rule + its CI-enforced tests is exactly
this discipline made structural). The one violation worth naming: two live PDF orchestration
paths (`pipeline.py`'s `run_pdf_pipeline` and `passes/run.py`'s `run_pdf_estimator`) coexist with
no documented reason for keeping both. Per "minimum code that solves the problem," either
document why v1 must stay (e.g., it's a documented rollback path or a used-elsewhere API) in
`context/decisions.md`, or delete `stages/{extract,generate}.py`'s callers and the dead
`run_pdf_pipeline` orchestrator. Don't guess which — this is exactly the kind of question to ask
the project owner, not assume.

---

## 4. Reasoning technique map

| Task | Technique | Why it fits |
|---|---|---|
| Page classification (`classify_files`, Haiku, one of 6 fixed categories) | Plain closed-form classification, no elevated technique needed | Cheap model, single categorical output, has a human-override fallback (`manual_types`) for low confidence — Self-Consistency sampling would add cost without changing the fallback behavior already covering the failure mode. Leave as is. |
| Per-pass fact extraction (`extract_facts`, Sonnet, `tool_use`, schema-enforced) | **Algorithmic Prompting** | This is complex (SA electrical domain rules, SANS thresholds) AND error-prone (money + compliance on the line) AND runs a fixed, must-not-improvise procedure per pass ("call this tool, follow these 5 numbered steps, forced schema"). That's exactly the "both complex and error-prone" trigger condition for Algorithmic Prompting rather than a looser technique — already implemented close to this shape; the one gap is the missing per-fact source citation (§3). |
| Cross-page / cross-file fact merge (`passes/facts.py` `_merge*` functions) | Should be **ThoT-style disagreement surfacing**, currently is naive first-wins accumulation | `_merge_context`/`_first()` silently keeps whichever page's value arrived first when two pages disagree (e.g., an SLD and a DB schedule reporting different main-breaker ratings for the same board). v1's `_cross_page_consistency` in `stages/evaluate.py` explicitly modeled this as a Perception-module concern — "surface conflicting inputs explicitly rather than silently picking one" (playbook Part 3, Sentient Sensor) — and v2 dropped it. **Concrete fix:** when `_merge_spine` sees two `DistributionBoard` entries with the same name and different `main_breaker_a`, append to `facts.spine.warnings` instead of silently discarding the second value, mirroring the removed `CrossPageDisagreement` model (still defined in `agent/pdf_pipeline/models.py`, just unused by v2). |
| Baseline / MAPE scoring (`scoring/harness.py`) | Deterministic scoring, not an LLM task | Correctly kept out of the LLM entirely — this is exactly right, don't add a technique here. |
| PDF-vs-DXF cross-comparison (`agent/comparison/compare.py`) | **Second-independent-verifier pattern** (Karpathy's Verifier practice, Part 5) | Two structurally different extraction methods (stochastic vision LLM vs. deterministic CAD parse) cross-checking each other is the practical, cheap version of an independent-critic setup — already well-designed, keep it read-only exactly as the blueprint's §5.1 argues. |
| Retry-with-feedback + escalation (`PdfLLM.call_with_tool`) | **Guided re-rollout** (AgentErrorTaxonomy's Action-error fix) | Already correct: the retry appends the actual Pydantic `ValidationError` text as new context rather than blindly resending the same prompt — this is precisely "a plain retry with no new information reproduces the same failure; the diagnosis is what changes the odds" from the playbook. No change needed. |
| Supplier ranking (`sourcing/engine.py::_rank`) | Deterministic multi-criterion scoring, not an LLM task | Correct choice — no LLM needed for a normalize-and-weight ranking function. |

---

## 5. Architecture decision

**This is already a multi-module agent-shaped system, even though it isn't framed that way in
the code.** Mapping it onto the playbook's four modules makes the missing reliability layer
obvious:

- **Perception** — `ingest_files` + `classify_files`. Partially matches "Sentient Sensor": it
  does have a hypothesis-driven fallback (low-confidence classification → manual tag), which is
  good. It does **not** surface conflicting extracted values across pages (see §4) — that's the
  concrete gap.
- **Reasoning** — the three extraction passes + `build_bill`. No pre-mortem or Council-of-Experts
  debate exists or is needed here; the task is bounded extraction, not open-ended planning. Correct
  scope, no change needed.
- **Memory** — `runs/{pdf,dxf}/<run_id>.json` (episodic, one file per run) and `baselines/*.json`
  (semantic, hand-validated ground truth). This is a genuinely good implementation of the
  playbook's "durable memory belongs in a file" principle — better than most audited projects.
- **Action** — `generate_boq` / `sourcing.engine.apply_quotes`. Both correctly clone-then-mutate
  rather than mutate in place (`apply_quotes`'s `model_copy(deep=True)`), which is good defensive
  practice even though the playbook doesn't name this specifically.

**Reliability layer — this is the one genuinely missing piece, and it's not optional per the
skill's Step 5 mandate ("do not recommend shipping an agent-shaped project without this").**
Concrete, mapped to this codebase's own error taxonomy:

| AgentErrorTaxonomy category | Concrete instance here | Fix |
|---|---|---|
| Memory error | Cross-file merge silently keeps first-seen value on conflict (§4) | Reinstate disagreement surfacing in `_merge_spine`/`_merge_context` |
| Reflection error | v2 estimator has no self-critique/gate before finalizing (§3) | Port `evaluate.py` logic into `passes/evaluate.py`; gate `EstimatorRun.success` on it |
| Planning error | N/A — pipeline order is fixed, not LLM-planned | No action needed |
| Action error | Already handled correctly (retry-with-feedback + escalation) | No action needed |

**Concrete artifact recommendation — a Claude Code hook, not just a documentation update.**
CLAUDE.md's "Hard rules for AI edits" (no cross-pipeline imports, no `parse_json_safely`, no LLM
SDK in DXF) are currently enforced only by CI, *after* a PR is opened. Per Karpathy's Environment
principle in the playbook ("a written rule is only a request... critical rules need tool-level
enforcement, not just a line of text"), add a `PostToolUse` hook in `.claude/settings.json` that
runs `pytest tests/architecture/ -q` whenever an Edit/Write touches
`agent/pdf_pipeline/**` or `agent/dxf_pipeline/**`, and surfaces a failure immediately in the
session rather than at the next CI run. This is a small, high-leverage addition given the
independence rule is explicitly called "the single most important rule" in the project's own
blueprint.

---

## 6. Context engineering plan

**Retrieval strategy: Naive is correct here — don't add RAG.** Each extraction call needs exactly
one page image plus the frozen ~1500-token system prompt; there's no large static corpus to
retrieve against yet. If a future need arises to ground SANS-clause citations against actual
standard text (see the open question below), a small JIT lookup against a cited-clause reference
file would be the right upgrade — not a general RAG layer.

**Constitution file status: exists, stale — the top-priority finding from §2.** Concrete rewrite
scope for `CLAUDE.md`:
- Replace the "Architecture" ASCII diagram and "What's where" table with the actual `passes/`
  layout for both pipelines, and add `sourcing/` and `scoring/` as first-class entries.
- Add a rule stating which of `run_pdf_pipeline` (v1) vs `run_pdf_estimator` (v2) is canonical,
  and what to do with the other (§3).
- Update the "Testing" section to include `tests/sourcing_layer/` and `tests/eval/` — currently
  absent from CLAUDE.md's test list even though they exist in the repo (and, per §5 of this
  report, aren't in the guaranteed CI gate either — the `ci.yml` catch-all step for them runs
  with `continue-on-error: true`).
- Correct or update the DWG-support statement so the constitution and the blueprint's stated
  scope (§11: "no DWG support") stop contradicting the shipped code.

**Durable memory pattern: already well implemented for run history (`runs/*.json`,
`baselines/*.json`) — extend it, don't replace it.** Concrete new artifact:
`context/decisions.md` at repo root (mirroring the pattern this audit kit itself uses), to log:
why v2 superseded v1, whether DWG support and the sourcing/scoring layers are permanent scope or
experiments, and why the evaluation gate was dropped in v2 (§3) — these are exactly the
"non-obvious decisions" the playbook says belong in a durable file, not in someone's memory of a
Slack thread.

**Formatting for Claude:** current prompts are plain numbered prose, which is appropriate at
their current length (`pass_prompts.py` entries are 5–6 short numbered steps each — well under
the point where XML demarcation would add value). No change needed now; if a pass prompt grows
past roughly a screen, switch to XML section tags per the playbook's Demarcation principle rather
than letting numbered lists become the only structure.

**Triangulation Protocol — recommended for one specific open question, not the whole project.**
The comparison layer already gives this project a natural Phase-I-Divergence setup (two
independent extraction methods on the same drawing set). The genuine gap: SANS-10142 rule
citations in `core/standards.py` and `stages/evaluate.py`'s `_sans_checks` (e.g. "max 10 points
per final circuit," "30 mA ELCB," "15% spare ways") are hard-coded from the system prompt's
domain knowledge with no citation-verification step anywhere in the pipeline. **Open question,
not assumed as a fact either way:** were these thresholds verified against the actual current
SANS 10142-1:2017 text, or are they the estimator's/engineer's recalled values? Given that a
`ComplianceFlag` with a wrong rule citation is a Verbatim-Traceability failure with real
liability consequences (a contractor could rely on a false "compliant" flag), this is worth one
lateral-reading pass against the actual standard before treating `core/standards.py` as ground
truth — flagging this explicitly rather than guessing an answer.

**Concrete `.claude/` artifacts to create (this is the "operating system" scaffolding the
follow-up task will build on):**

1. `CLAUDE.md` — rewritten per above (existing file, needs the update, not a new file).
2. `context/decisions.md` — new durable-memory file, per above.
3. `.claude/settings.json` — add the architecture-test `PostToolUse` hook from §5.
4. `.claude/skills/extending-pdf-passes/SKILL.md` — an **encoded-preference** skill (per
   Anthropic's skill-authoring guidance: medium-to-low freedom, since this is the "narrow
   bridge" case — a specific sequence must be followed). Should be a checklist workflow: update
   `passes/pass_schemas.py` → `prompts/pass_prompts.py` → the matching `_merge_*` in
   `passes/facts.py` → `passes/assemble.py` → add a test under `tests/pdf_pipeline/unit/`. This
   directly encodes the "what's where" knowledge CLAUDE.md currently gets wrong for the live
   architecture.
5. `.claude/skills/adding-sans-compliance-rule/SKILL.md` — low-freedom skill requiring the human
   to paste/confirm the exact SANS clause text and number before a new `ComplianceFlag` rule is
   added to `core/standards.py` or `_sans_checks` — a tool-level guardrail against an LLM
   improvising a plausible-sounding but unverified rule code, directly addressing the open
   question above.
6. `.claude/skills/scoring-a-run/SKILL.md` — wraps `scripts/score_estimator.py` +
   `scoring/harness.py` as a documented workflow, and requires adding/updating a baseline JSON
   under `baselines/` before any accuracy-improvement claim is accepted — this is also the
   groundwork for the AutoResearch fixed-metric requirement in §7.

---

## 7. Ongoing-operation layer

**Loop Engineering — 4-question test, run explicitly, not assumed:**

| Question | Answer |
|---|---|
| Does the task repeat? | Yes — every project upload is a repeat of the same pipeline. |
| Clear definition of done? | Only partially. v1 had one (composite score ≥ threshold). v2, the live path, does not (§3). |
| Can you afford the token cost of repetition? | Yes — cost is already tracked per run (R3–R8/PDF run, R0/DXF run), well within the stated R8 ceiling. |
| Does it have everything needed to verify its own work? | **No, not currently** — this is the blocking answer. |

**Verdict: do not build an automated loop (scheduled re-runs, auto-retry-on-low-confidence,
batch regression runs) on top of the v2 estimator until §3's evaluation gate is restored.**
Building a loop on an unverified estimator would automate shipping unverified BOQs faster, which
is the opposite of the intent. Once the gate is restored, a genuinely good loop candidate exists:
a nightly/on-PR regression run of `scripts/score_estimator.py` against every file in `baselines/`,
in "loop training mode" (report only, no auto-action) for the first several runs, matching the
playbook's guidance.

**AutoResearch — checked explicitly, not forced:**
- One genuinely clear metric? MAPE vs. baseline (`scoring/harness.py`) is a real number, not a
  feeling — good candidate in principle.
- Fully automated evaluation, no human in the loop? Yes, `score_boq` is deterministic.
- Exactly one editable file? No — a prompt-tuning improvement would plausibly need to touch
  `pass_prompts.py`, `pass_schemas.py`, and `patterns.py` together, not one file.
- **Real limitation to flag:** only two full baselines exist (`wedela`, `trichard`) plus one
  `example.json`. Per the playbook's own caution — "a bad or gameable metric gets confidently
  optimized in the wrong direction" — optimizing prompts against two named projects risks
  overfitting to Wedela/Trichard's specific drawing conventions rather than improving general
  accuracy. **Recommendation: this project is not ready for AutoResearch yet.** It becomes a
  reasonable candidate once (a) the v2 evaluation gate exists again and (b) the baseline set
  grows to enough independent projects that a metric improvement is credible rather than
  overfit — no specific number is assumed here; that threshold is itself an open question for
  the project owner, not something to guess.

---

## 8. External resources consulted

Checked live, per the skill's mandatory Step 8, not relied on from memory:

- **`docs.claude.com` / `platform.claude.com` — Agent Skills best-practices guide.** Used to
  shape the concrete skill recommendations in §6: the "degrees of freedom" framework (this
  project's fragile, multi-file pass-extension work is a "narrow bridge" — low/medium freedom,
  checklist-workflow skills, not open-ended guidance), the description-field requirements, and
  the evaluation-driven-development approach (build 3 real test scenarios before writing skill
  docs). No conflict with the bundled playbook — this is complementary operational detail the
  playbook doesn't cover (it predates the current public Skills authoring guide's level of
  procedural detail).
- **`anthropic.com/engineering` — "Effective context engineering for AI agents" and "Writing
  effective tools for AI agents."** Confirmed the bundled playbook's "context is a scarce, quadratic-cost
  resource" framing is still Anthropic's current position, and reinforced evaluation-driven
  tool/skill design (observe real failures before writing docs) — applied directly to the
  skill recommendations in §6 rather than writing speculative documentation.
- **`docs.claude.com` — PDF support, Structured Outputs, and prompt-caching docs.** Worth naming
  as a genuine current-practice option, not a mandatory change: Claude now has native PDF
  ingestion and a "Structured Outputs" feature that constrains responses to a schema server-side.
  AfriPlan's current approach — manually rasterising pages with PyMuPDF and doing client-side
  Pydantic validation with a manual retry-with-feedback loop — is not wrong (page-level control
  is genuinely needed for the per-page-type routing this pipeline depends on), but Structured
  Outputs could harden/simplify the schema-validation retry path in `llm.py` if evaluated. This
  is a "worth evaluating," not a "must migrate" — no conflict with the bundled playbook, just a
  newer capability it predates.
- No direct conflict was found between current public Anthropic guidance and this kit's bundled
  `ai-engineering-playbook.md` on anything applied in this report.

---

## Summary of concrete next actions (in priority order)

1. Resolve whether the v2 estimator's missing evaluation gate is a deliberate simplification or
   an unnoticed regression — then restore an equivalent to `PdfEvaluation`/`DxfEvaluation` gating
   in `passes/run.py` for both pipelines (§3, §5).
2. Rewrite `CLAUDE.md` to describe the actual `passes/`-based architecture, `sourcing/`, and
   `scoring/` (§2, §6).
3. Create `context/decisions.md` and log the v1-vs-v2, DWG-scope, and gate-removal decisions
   (§2, §6).
4. Reinstate cross-page disagreement surfacing in `passes/facts.py`'s merge functions (§4, §5).
5. Add the architecture-test `PostToolUse` hook (§5).
6. Add the three `.claude/skills/` files scoped in §6.
7. Only after (1) is resolved: consider Loop Engineering for nightly baseline regression runs
   (§7). Do not pursue AutoResearch until the baseline set is materially larger than two projects
   (§7).
