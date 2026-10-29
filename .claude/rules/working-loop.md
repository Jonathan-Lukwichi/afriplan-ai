# The working loop — step by step

Every session runs this loop. CLAUDE.md holds the short version; this file holds each step's
detail: why, which files to open, what to run, when it is done, and where to go next.
How work is split (instructions / agent / engines + check): `three-layer-approach.md`.

```
            ┌──────────────── 0. ORIENT ────────────────┐
            │  ask the mode · priorities · current state │
            └───────┬──────────────────────┬─────────────┘
       W. web app   │ A. DOE estimate      │ B. develop
                    ▼                      ▼
   A1 instructions → A2 engines      B1 pick → B2 find the layer → B3 failing test
   → A3 check → A4 learn & report    → B4 smallest change → B5 check → B6 record
                    │                      │
                    └──── back to 0 ◄──────┘   (a failed check goes to fix-and-learn,
                                                then back into the same check)
```

---

## 0. Orient (every session)
- **Ask the mode** (CLAUDE.md "Start of every session"): web app, DOE estimate, or develop.
- **Open:** `context/priorities.md` (what next) · `context/current-state.md` (scores, status) ·
  `context.md` (the words to use) · `docs/architecture.md` (the system) · `docs/adr/` (decisions
  not to re-open) · `issues/` (known defects).
- **Done when:** you can name the mode and the one task for this session.
- **Next:** W, A1 or B1.

## W. Web app (run it for the user)
- `python scripts/dev.py start` → backend :8000, frontend :5180. Confirm both answer, give the links.
- Anything that misbehaves becomes a B-loop task (B1).

---

## A. DOE estimate — produce a BoQ from a project folder

### A1. Instructions
- **Run the skill** `estimate-project` (`.claude/skills/estimate-project/SKILL.md`). It points to:
  `doe/brain/BRAIN.md` (how to read a page) · `doe/playbook/PLAYBOOK.md` (rules) ·
  `doe/playbook/LESSONS.md` (what went wrong before) · `doe/knowledge/BOQ_KNOWLEDGE.md` (how a QS
  measures; the four wiring conventions).
- **Done when:** you know the folder, the drawing types in it, and which pages you will read.

### A2. Engines (layer 3) + your reading (layer 2)
- `$PY doe/execution/project.py prepare "<folder>"` → pages and empty forms in `<folder>/AfriPlan_Output/work/`.
- Read each page and fill its form (you are the eyes; never type a total or a rate).
- `$PY doe/execution/project.py finish "<folder>" [--reference <p>]` → the priced BoQ (Excel + PDF).
- **Done when:** `finish` succeeds. A missing or invalid form stops it: fix the form, not the code.

### A3. Check
- Ask the read-only **`checker`** agent (`.claude/agents/checker.md`) to review the bill.
- With a reference project: `accuracy_report.md` from `finish --reference`, or `evaluate-boq`.
- `audit-boq` when the bill itself (human or ours) must be audited.
- **Done when:** checker verdict PASS, or every ISSUE is listed for the estimator.

### A4. Learn and report
- Report the result as **"draft for estimator review"**: total exactly as printed, the gaps, the checker verdict.
- A user correction or a wrong reading → **`fix-and-learn`**; DOE lessons → `doe/playbook/LESSONS.md`.
- **Next:** back to 0.

---

## B. Develop — change the code

### B1. Pick
- One item from `context/priorities.md` or `issues/`. Non-trivial work gets a plan in
  `docs/superpowers/plans/` first.
- **Done when:** the task has acceptance criteria (an issue's, or your plan's).

### B2. Find the layer (`three-layer-approach.md`)
- Instructions → `.claude/skills/`, `doe/brain/`, `doe/playbook/`.
- Catalogue, layers, rates → `api/agent/shared/symbol_catalogue.py`, `legend.py`,
  `api/core/layer_aliases.py`, `api/core/constants.py` (ask before changing rates).
- Engines → `api/agent/` (the two pipelines never import each other), `api/core/`, `doe/execution/`.
- UI → `src/pages/`, `src/components/ui/`, `src/api/client.js`.
- **Done when:** you can name the one file (or few) the change belongs in.

### B3. Failing test first
- Skill **`tdd`** (`.claude/skills/tdd/SKILL.md`): one behaviour, red for the right reason.
- Python → `tests/<pipeline>/unit/`, `tests/shared/`, `tests/<layer>_layer/`; UI → `tests-e2e/`;
  boundaries → `tests/architecture/`. A known defect not fixed now → a strict `xfail` naming its issue.

### B4. Smallest change at that layer
- Skill **`karpathy-coding-discipline`**. Match the surrounding code. Hard rules in CLAUDE.md apply.

### B5. Check (all that apply must pass)
| Changed | Run |
|---|---|
| any Python | `$PY -m pytest -q -p no:warnings` (the architecture hook also runs on every edit) |
| any UI | `npm run build` · `npx playwright test` · skill `dashboard-qa-gate` before shipping |
| an engine, the catalogue, layers, rates, a reading skill | **`/check-takeoff`** (`scripts/check_takeoff.py`) |
| anything that claims a better score | **`evaluate-boq`** against a dated baseline (`reports/baselines/`) |
| a milestone | `structure-review`; `prompts/review.md` for a fresh-context review |
- A failure → **`fix-and-learn`** → back into B5. Stop after 3 failed attempts and report.

### B6. Record
- `context/current-state.md` when a score or status changed · `issues/` for a defect found and not
  fixed · `docs/adr/` for a decision with lasting consequences · `context/priorities.md` if the order changed.
- Commit with a reason; grep staged files and the message for client data (hard rule 9).
- Push a branch; **CI must be green** (`.github/workflows/ci.yml`). `main` only with approval.
- **Next:** back to 0.
