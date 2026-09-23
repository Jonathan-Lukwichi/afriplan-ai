# AfriPlan Web — AI Engineering Blueprint

Audited: `main` branch worktree, commit `eb0ee78` (the FastAPI + React rewrite).
This report **supersedes** any earlier audit run against a different local
checkout of the `legacy-streamlit` branch — that audit was against a different,
older architecture (Streamlit-only, no `api/` backend, no comparison layer, no
SQLite persistence) and its file-level findings do not carry over. Where this
report's conclusion on the anti-hallucination gate matches the stale audit's
conclusion, it is because independent re-verification against `main`'s actual
code reached the same result — not because the finding was assumed to carry
over. See "Comparison to the prior (stale) audit" at the end of this report.

No prior blueprint report existed at this path before this one.

---

## 1. Project classification

**Primary: AI tool/product** (a shipped, end-user-facing web app: React frontend
+ FastAPI backend, `src/pages/` wizard from Landing → Upload → Take-off →
Compare → BoQ → Pricing).

**Secondary: task-automation workflow** — each pipeline run (`run_pdf_estimator`,
`run_dxf_estimator`) is a bounded, repeatable, single-shot extraction job with a
clear "done" state (`EstimatorRun.success`), triggered per-upload rather than on
a schedule. It is not coding-assistance work and not a research workflow — the
"research" analog here (cross-checking a claim against reality) is the
compliance/comparison logic, which is a domain feature, not literature review.

The product's core deliverable is a **priced, tender-grade Bill of Quantities**
extracted from electrical drawings using a vision LLM (PDF pipeline) and/or
deterministic CAD parsing (DXF pipeline) — this is a high-stakes, facts-to-a-
paying-client tool, which is the lens every recommendation below is filtered
through.

---

## 2. Alignment status

**A real discovery/alignment pass clearly happened, and evidence of it is
checked into the repo** — this is well above the median for what this kit
usually finds:

- `CLAUDE.md` is a genuine constitution file, not a stub: it states "critical
  decisions carried over from the original app — do not re-litigate," names
  six explicit decisions with rationale (pipeline independence, `passes/` vs
  `stages/`, demo-only login, server-side export), and flags **one open item
  ported as a known discrepancy** (blueprint says MAPE ≤15%, code enforces
  20%) rather than silently resolving it. That is the Spec-layer behavior the
  playbook asks for (Part 5 — "surfaced to Jonathan/Hervé rather than silently
  resolved").
- `docs/HOW_AFRIPLAN_WORKS.md` is a genuine glossary/audience-aware document —
  it defines the confidence-badge taxonomy (Extracted/Inferred/Assumed/
  Provisional/Estimated/Manual) that IS this project's escape-hatch and
  grounding contract with the end user.
- The README's phase checklist (Phase 1–12) is evidence of small, checkpointed
  chunks rather than one waterfall build.

**What's missing, and is the top-priority recommendation of this whole
report:** none of this alignment material was carried into a `.claude/`
directory. There is no `.claude/skills/`, `.claude/agents/`, or `.claude/
commands/` anywhere in this worktree. `CLAUDE.md` at the repo root is read by
Claude Code automatically, but the two richest domain-knowledge documents in
the repo — the SANS 10142-1 rules baked into `system_prompt.py`, and the
plain-English mental model in `docs/HOW_AFRIPLAN_WORKS.md` — are not exposed as
reusable Skills, so every future coding session re-derives this context from
scratch rather than loading it on demand. See §5 for the concrete skill list.

---

## 3. Foundations plan

### Role formula — already partially applied, and applied well

`api/agent/pdf_pipeline/prompts/system_prompt.py`'s `SYSTEM_PROMPT` is a strong,
concrete role formula: **Core Identity** ("Senior South African Electrical
Estimator") + **Niche Specialization** (SANS 10142-1, NRS 034, SA vocabulary,
circuit-naming conventions) + **Strategic Perspective** ("the way a contractor
preparing a tender does"). This is worth preserving verbatim as the reference
example when writing any new prompt/skill for this project — don't rewrite it,
extend the pattern.

### What → How → Why structure — present but the negative fence is misplaced

The system prompt's "EXTRACTION DISCIPLINE" section states rules 1–5 as a flat
numbered list with no explicit Why for each, and negative constraints (rule 3:
"do not invent counts") are in the **middle** of the list, not at the end. Per
the playbook's recency-effect guidance, move the negative constraints ("If a
quantity is not visible... RETURN ZERO... do not invent counts," "Do not
paraphrase tool inputs") to the very end of the block, and add a one-line Why
after each rule (e.g. rule 1's "read exactly as written" should say *why*:
"so a downstream reviewer can trust the Source column without re-checking the
drawing").

### Anti-hallucination guards — MANDATORY, and partially implemented, but not
### wired into a blocking gate (see §6.2 for the full finding)

Per the playbook's AI-tool/product rule ("if it states facts to end users,
Strict Grounding + Verbatim Traceability are mandatory") — all four guards
apply here, and three of the four already exist in some form:

| Guard | Status in this codebase |
|---|---|
| Strict Grounding | Present in the system prompt ("Read every visible value EXACTLY as written") |
| Escape Hatch | Present: "If a quantity is not visible... RETURN ZERO with a low confidence — do not invent counts" is a textbook Escape Hatch instruction |
| Verbatim Traceability | Partially present: `db.source_snippet` in `orchestrator.py`'s `_check_source_alignment` requires the model to quote the exact busbar text it read a rating from, and the check fails deterministically if the reported number doesn't appear in the quote. This is Verbatim Traceability applied narrowly to one field (main breaker rating), not the whole extraction. |
| Clean Slate Protocol | Not present and not obviously needed yet — each pipeline run is stateless per-upload, so there's no long conversational context to get polluted. Note for the future: if a "re-run with corrections" feature is added, this becomes relevant. |

**The gap is not the guards themselves — it's that none of them currently
block a bad result from reaching the end user as "Passed."** See §6.2.

---

## 4. Reasoning technique map

| Task | Technique in use / recommended | Why it fits |
|---|---|---|
| Per-page vision extraction (SLD/layout pages, one page → one tool call) | Algorithmic Prompting-lite (already present: forced tool_use, explicit confidence rubric, retry-with-validation-error) | A known, deterministic-in-shape procedure (read a schedule, fill a schema) that must not silently fail — matches the playbook's criterion for Algorithmic Prompting over plain CoT |
| Power-spine (SLD) extraction specifically | **Self-Consistency**, already implemented (`_extract_power_spine_voted`, N=3, T=0.5, majority vote per field) | Exactly matches the playbook's Self-Consistency use case: closed-form fields (breaker rating, phase count), high stakes (a wrong rating changes the priced bill), and the code's own comment cites the evidence ("same SLD page read 4 times gave 4 different totals") — this is Self-Consistency correctly justified by observed failure data, not applied by default |
| Cross-page/cross-pass consistency (`_check_spine_orphans`, `_check_source_alignment`) | Deterministic post-hoc verification, not an LLM technique — correctly kept out of the LLM per the playbook's Verifier principle ("pull external signal where possible... a live system check") | Good: these are cheap, free, and catch a *specific reproduced bug* (400A vs 100A misread) rather than a generic worry |
| Page classification (Haiku pass, low stakes routing) | Single-shot, T=0, no voting | Correctly cheap — classification errors are caught downstream by `needs_manual` flag at `CLASSIFY_CONFIDENCE_FLOOR`, so paying for Self-Consistency here would be wasted spend |
| PDF vs DXF cross-pipeline comparison (`compare.py`) | Structured diff + agreement score, not an LLM call at all | This is the project's own Triangulation-Protocol analog — two independently-produced extractions compared for convergence — but it currently only *reports* the disagreement (`agreement_score`, `winner_vs_baseline`), it doesn't feed a decision. See §6.2/§7. |
| SANS 10142-1 compliance checking | Rule-based `ComplianceFlag` emission (not yet observed wired into either pipeline's EVALUATE stage — see §6.2) | Correct technique choice (a fixed rulebook is exactly what deterministic rule evaluation is for, not an LLM judgment call) — the gap is enforcement, not technique |
| Live-pricing / supplier comparison (`api/sourcing/`) | Not LLM-driven (mock supplier engine) | No reasoning-technique concern yet; flagged only because `mock.py` suggests this is not live yet — see open questions |

Nowhere in the reviewed code is plain "think step by step" used as a default —
this project already reasons technique-first rather than by habit, which is
the right instinct to keep as it grows.

---

## 5. Architecture decision

**Full four-module agent shape, already emergent in the code, not yet named as
one.** The PDF pipeline alone has:

- **Perception** — `ingest.py` + `classify_files` (page-type detection with a
  confidence floor and manual-override fallback).
- **Reasoning** — `passes/orchestrator.py`'s per-pass tool calls, the SLD
  voting logic, and the deterministic cross-checks.
- **Memory** — none currently, and this is a real gap, not a non-issue: a
  successful voting outcome, a confirmed misread pattern (the 400A/100A bug),
  or a recurring SANS violation are exactly the kind of "generalize a good run
  into a reusable rule" the playbook's Memory module describes, and right now
  every one of those lessons lives only in a code comment, not in a
  queryable, growing knowledge base the next run (or the next Claude Code
  session working on this repo) can draw on.
- **Action** — `llm.call_with_tool` with forced tool_use, retry-with-feedback,
  and Sonnet→Opus escalation — a working, auditable action loop already.

**Reliability layer:** the retry+escalate mechanism in `llm.py` is a genuine,
working instance of the self-healing loop (Worker → detect failure → guided
re-attempt with the validation error as context → escalate). What's missing
against the playbook's AgentErrorTaxonomy is the **classification** step: a
validation failure, a missing tool call, and an API error are all currently
folled into one `LLMError` with a string message, not a structured
`debug_report` categorized as Memory/Reflection/Planning/Action error. At the
current single-retry-then-escalate scale this is a minor gap; it becomes worth
fixing the moment a second failure mode needs a different fix (e.g., if
low-confidence extractions and schema-validation failures should be handled
differently, they need to be distinguishable in the log first).

**Recommendation: keep the current lightweight per-pipeline design** (don't
force a heavier "agent framework" onto this) but **name the Memory gap
explicitly as the next architectural investment**, in this concrete form:
a `runs/{pipeline}/lessons.md`-style durable file (see §6) that
`_check_source_alignment`-style deterministic catches append to when they
fire, so the third occurrence of a misread pattern updates the system prompt's
"KEY WIRING RULES" section instead of living only in a code comment forever.

---

## 6. Context engineering plan

### 6.1 Retrieval strategy

**Naive, correctly** for the PDF pipeline's per-page calls (one image, one
prompt, no corpus) — appropriate, since each page is processed independently
and there's no large static knowledge base being searched. **Hybrid** is the
right target once the Memory gap above is addressed: a stable core (SANS
10142-1 rules, already baked into the frozen system prompt and correctly
cached via `cache_control: ephemeral`) plus a growing, queryable set of
confirmed-misread patterns that should NOT go into the frozen prompt wholesale
(that would break the prompt-cache hit rate the code deliberately optimizes
for) but should be checked deterministically the way `_check_source_alignment`
already does it.

### 6.2 Constitution/glossary file status — the central finding of this audit

`CLAUDE.md` exists and is genuinely good (see §2). **The gap is not the
constitution file — it's that the thresholds the constitution's own sibling
file defines are not enforced.**

Concretely, in `api/core/config.py`, `PdfPipelineThresholds` defines:

```
min_field_confidence: float = 0.60
min_mean_confidence: float = 0.75
min_consistency_score: float = 0.80
min_overall_score: float = 0.70
max_baseline_mape: float = 0.20
max_repeat_run_deviation_pct: float = 0.05
```

A full-repo search shows **only two of these ten `PDF_THRESHOLDS` fields are
ever referenced anywhere outside `config.py` itself** — `raster_dpi` and
`max_pages`, both used in `stages/ingest.py` purely for image preprocessing,
not for gating. `min_field_confidence`, `min_mean_confidence`,
`min_consistency_score`, `min_overall_score`, `max_baseline_mape`, and
`max_repeat_run_deviation_pct` are **never read anywhere in the pipeline
code.** `DxfPipelineThresholds` (`DXF_THRESHOLDS`) is never imported outside
`config.py` at all.

The actual pass/fail gate that decides whether a run is marked `"passed"` (and
therefore becomes downloadable, priceable, emailable — `run_jobs.py`,
`routers/pricing.py`, `routers/export.py` all gate on `record.status ==
"passed"`) is, verbatim from `passes/run.py`:

```python
success=bool(boq.line_items),
error=None if boq.line_items else "No billable items extracted from the drawings",
```

That is: **"passed" currently means only "at least one line item was
produced."** It does not check field confidence, mean confidence, cross-page
consistency, baseline MAPE, or compliance-flag severity, despite all of that
data being computed and captured (`GapItem`s from the voting/orphan/alignment
checks, `ComplianceFlag.severity`, per-field `confidence`). The
`ComplianceReport` model's own `passed` property (`critical_count == 0`) is
never instantiated or checked anywhere outside `compliance.py` — no code
anywhere wraps a run's flags in a `ComplianceReport` and checks `.passed`. A
drawing set that produces one CRITICAL SANS violation and a 3-way field
disagreement on every distribution board will still be marked "Passed" and
made available to email to a client.

`compare.py`'s own docstring independently confirms half of this: the
baseline-MAPE comparison "Defaults to None, which correctly resolves to a
`no_baseline` winner" because "the v1 run objects carried a baseline-
regression result... intentionally not ported alongside 'passes/'." This is a
direct, first-party admission in the code itself that the baseline-regression
half of the old gate was deliberately left behind in the rewrite, not silently
lost.

**This is the single highest-priority recommendation of this report:** wire
`PDF_THRESHOLDS`/`DXF_THRESHOLDS` and `ComplianceReport.passed` into
`run_pdf_estimator`/`run_dxf_estimator`'s actual `success` computation, per
the Escape-Hatch/Strict-Grounding intent already written into the system
prompt and the confidence-badge UI contract already promised to the user in
`docs/HOW_AFRIPLAN_WORKS.md` §5 ("Rule of thumb: green and teal — trust it...
grey and red — don't send these to a client without checking them yourself").
Right now the badge system tells the *user* what to distrust, but the *pipeline
status* doesn't reflect that same judgment — a bill that's mostly red/grey
badges can still show "Passed" at the top of the page. Closing this gap is a
config-and-one-function-signature change, not a rearchitecture — all the raw
signal (confidence per field, GapItem severities, ComplianceFlag severities)
already exists; it's a matter of aggregating it into the `success` decision
that's currently a single `bool(boq.line_items)`.

### 6.3 Memory pattern

No `NOTES.md`-equivalent or durable per-run learning file yet. Recommend a
`runs/{pipeline}/lessons.md` (or a small SQLite table alongside the existing
`api/db/`) that accumulates confirmed misread patterns the deterministic
checks catch, so a pattern seen 3+ times becomes a candidate for promotion
into the frozen system prompt (manually reviewed before promotion — per the
playbook's "a human audits every generated example before it ships" principle
applied to prompt patches, not just few-shot examples).

### 6.4 Formatting for Claude

The system prompt already uses clear ASCII-rule demarcation between sections
(good Salience/Demarcation). `pass_prompts.py`/`pass_schemas.py` were not
fully read line-by-line in this audit pass but the tool-forcing pattern
(`forced_tool_name`, strict Pydantic validators) is itself a strong
Task-Format-Isomorphism choice — the output format (a Pydantic schema) mirrors
exactly the task's actual shape (structured facts, not prose).

### 6.5 Triangulation requirement

**Yes, partially in place, not fully leveraged.** The PDF-vs-DXF comparison
(`compare.py`) is architecturally the Triangulation Protocol's Phase I
Divergence step (two independent extraction methods, forbidden from sharing
state per the independence rule) — but there is no Phase II Convergence step:
nothing currently *acts* on `agreement_score` or `winner_vs_baseline` beyond
displaying them in `ComparisonPanel.jsx`. Per §7, recommend making a
low-`agreement_score` result surface as an explicit warning gate on the BoQ
page, not just a comparison-tab curiosity.

---

## 7. Ongoing-operation layer

**Loop Engineering check (4-question test):**
- Does the task repeat? Yes — every upload is a new run of the same pipeline.
- Clear definition of done? Currently weak — see §6.2; "done" is currently
  under-defined as "produced ≥1 line item" rather than "produced a result that
  meets the stated confidence/compliance bar."
- Can the project afford the extra token cost of automatic repetition? The
  SLD self-consistency voting already answers this — yes, selectively (3x on
  the one page type shown to need it, not everywhere).
- Does it have everything it needs to verify its own work? **Not yet** —
  this is the same gap as §6.2. The raw material for self-verification exists
  (confidence scores, GapItems, ComplianceFlags) but isn't assembled into a
  verification step the run checks itself against before declaring success.

**Recommendation:** this project is a good Loop Engineering candidate **once
§6.2 is fixed** — a single pipeline run is the natural "loop iteration," the
trigger is upload, and "battle-tested execution skill" is close to true for
the extraction passes already. Do not build a bigger automation loop (e.g.,
auto-retry-until-confidence) on top of the current success gate — that would
automate around a currently-meaningless PASS, making the problem worse, not
better. Fix the gate first.

**AutoResearch check:** does not apply. There is no single fixed metric this
project should optimize unattended yet, and the one candidate metric (baseline
MAPE) is explicitly not wired to anything live (§6.2) — bringing AutoResearch
in before the metric itself is even computed live would be optimizing against
a number that currently doesn't exist at runtime. Once `max_baseline_mape` is
wired into the gate and a `baselines/` ground-truth set exists (referenced in
config as `BASELINES_DIR` but not observed to have any actual baseline files
in this worktree), AutoResearch becomes a realistic Phase 2 project — one
editable file (the extraction prompt/schema), one untouchable file (the MAPE
scorer against `baselines/`), one metric (MAPE), matching the three-file
architecture exactly.

---

## 8. External resources consulted

Checked live for anything that supersedes this kit's bundled playbook, per the
skill's Step 8 requirement:

- **Claude Code Skills docs** (`code.claude.com/docs/en/skills`) — confirms
  the current guidance: "CLAUDE.md is always-on context. Skills are on-demand
  context. If a rule applies to nearly every task, put it in CLAUDE.md. If
  it's a specific workflow that only matters sometimes, make it a Skill." This
  directly supports §2's recommendation: the SANS-10142-1 domain rules and the
  confidence-badge contract are exactly the kind of narrower, on-demand
  knowledge that belongs in a Skill, not bloating `CLAUDE.md` further.
- **"A Mental Model for Claude Code: Skills, Subagents, and Plugins"** and
  related current commentary — reinforces "if a rule must be enforced, use
  Hooks or permissions; if it is contextual knowledge, use Skills; if it is a
  delegation boundary, use Subagents." This maps directly onto §6.2's finding:
  the confidence/MAPE/compliance thresholds are a case where a *written rule*
  (the dataclass with defaults) is not enough — the playbook's own Karpathy
  principle applies verbatim here: "a written rule is only a request; critical
  rules need tool-level enforcement." `PdfPipelineThresholds` is currently a
  request, not an enforcement.
- **Anthropic's "Effective context engineering for AI agents"** and the
  companion **"Effective harnesses for long-running agents"** post — both
  reinforce this kit's Part 4 guidance (smallest high-signal token set, not
  most comprehensive) and specifically describe multi-session incremental
  progress patterns relevant to §5's Memory-module gap (an "initializer" +
  ongoing "coding agent" pattern for context surviving across sessions) —
  directly applicable if AfriPlan's own engineering (not the product's
  pipelines, but *building* the product) moves to longer Claude Code sessions
  against this repo.
- **Anthropic's "Loop engineering: Getting started with loops"** (per the June
  2026 Claude blog) — describes four loop types (turn-based, goal-based,
  time-based, proactive) and explicit stopping conditions/token management.
  This is more granular than this kit's Part 5 Loop Engineering section but
  does not conflict with it — both agree a loop needs a clear stopping
  condition and a verification step, which is exactly the gap named in §7.

**No direct conflict found** between current public guidance and this kit's
bundled playbook. Current guidance is more specific about Skills-vs-CLAUDE.md
boundaries and loop taxonomy than the bundled playbook, but agrees on every
substantive point applied in this report.

---

## Comparison to the prior (stale) audit

The prior audit ran against a different local checkout on the
`legacy-streamlit` branch and found the anti-hallucination gate (confidence
thresholds, cross-page consistency, baseline MAPE, compliance blocking)
**missing from that branch's live pipeline.** That finding was against a
materially different, older codebase (no `api/` FastAPI backend, no
comparison layer, no SQLite persistence, no self-consistency voting) and
should not be assumed to transfer.

Independently re-verified against `main` (this audit, from scratch): **the
same conclusion holds, but the underlying picture is more nuanced and more
specific than "missing":**

- `main` has **materially more raw anti-hallucination material** than what a
  "missing gate" description implies in isolation — self-consistency voting on
  the highest-risk extraction (SLD/power-spine), two new deterministic
  cross-checks with confirmed real bugs behind them (orphan-board detection,
  source-text alignment), a documented confidence-badge UI contract, and a
  system prompt with genuine Escape-Hatch and Strict-Grounding language.
- But the **enforcement gate itself is still absent**, in the most literal
  possible sense: the ten-field `PdfPipelineThresholds`/`DxfPipelineThresholds`
  dataclasses are defined but eight of ten fields (all the confidence/
  consistency/MAPE fields) are never read anywhere in the pipeline; the
  `success` flag that actually controls whether a bill can be downloaded,
  priced, or emailed is `bool(boq.line_items)` — an even weaker condition than
  "no gate" might suggest, since it will pass on a result with zero confidence
  in every field as long as at least one line item exists.
- The comparison layer's own docstring **self-documents** that the baseline-
  MAPE portion of the old gate was a deliberate, acknowledged omission from
  the rewrite ("intentionally not ported alongside 'passes/'"), which is
  consistent with — and independently corroborates — the stale audit's
  finding on the old branch, even though the two audits examined different
  code.

So: **same top-level conclusion (gate missing), reached independently, with
more precise detail on main** — not a case where the stale audit's finding
was invalidated by the rewrite; if anything, `main`'s own code comments
confirm the gap was a known, named decision rather than an oversight, which
makes it more urgent to close explicitly (with Jonathan/Hervé sign-off per
`CLAUDE.md`'s own stated norm) rather than less.

---

## Open questions (do not guess these — flag to the project owner)

1. **Is `PDF_THRESHOLDS.max_baseline_mape = 0.20` the correct target, or is
   15% (the number in the original blueprint) still the intended target?**
   `CLAUDE.md` itself already flags this as unresolved — it is not resolved by
   this audit either; wiring the gate (§6.2) requires this be decided first.
2. **Is there an actual `baselines/` ground-truth dataset anywhere for this
   project?** `BASELINES_DIR` is referenced in config but no baseline files
   were found in this worktree during this audit — if none exist yet, the
   MAPE half of the gate cannot be wired until they're created, which is a
   prerequisite task, not a config change.
3. **Is the live-pricing supplier panel (`api/sourcing/suppliers/mock.py`)
   intended to stay mocked for the current phase, or is real supplier
   integration a near-term follow-up?** `docs/HOW_AFRIPLAN_WORKS.md` §7
   explicitly tells the end user it's simulated, so this is transparently
   communicated, not hidden — but it affects whether any AI-engineering work
   should go into that module now or later.
4. **How many real drawing sets has the SLD self-consistency voting (N=3) been
   validated against beyond the "4/4 times" and "same page read 4 times"
   evidence cited in code comments?** Those numbers read as real internal
   testing notes, not course-material fiction, but this audit did not
   independently verify them — worth confirming before treating N=3 as
   final rather than provisional.
