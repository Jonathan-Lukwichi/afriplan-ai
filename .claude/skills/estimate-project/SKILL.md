---
name: estimate-project
description: Turn any electrical project folder (PDF and/or DWG/DXF drawings) into a professional priced BoQ (Excel + PDF) saved in that folder, reading the PDF pages with Claude Code's own eyes (no API cost). Use when given a project folder or drawing files to estimate, when asked to run the AfriPlan DOE brain, or for a scheduled AfriPlan run.
---

# Estimate a project — the brain's procedure (DOE layer 2)

Direction: `doe/playbook/PLAYBOOK.md` (rules, scores, when to stop) and `doe/playbook/LESSONS.md`.
Execution: `doe/execution/project.py` — every number comes from it. You only READ drawings and
DECIDE; you never compute a quantity, length or price, and you never edit `api/`, `src/` or the scorer.

Run from the repo root. `$PY` = the project venv: `api\.venv\Scripts\python.exe` on Windows
(PowerShell: also set `$env:PYTHONIOENCODING="utf-8"`), `api/.venv/bin/python` on macOS/Linux.
No venv yet → run `python scripts/dev.py setup` first (macOS: `python3`).

## 1. Prepare (deterministic)
```
$PY doe/execution/project.py prepare "<project folder>"
```
It lists every PDF page as pNN with its sheet name and writes, under
`<folder>/AfriPlan_Output/work/`: `pages/pNN.png` (whole page), `pNN_q1..q4.png` (zoomed
quarters), `pNN_legend1/2.png` (the legend / quantity table at high zoom, when the page has a
text layer), `pNN.txt` (text layer), and `forms/README.md` (the exact instructions + strict
schemas). No PDFs → skip to step 3.

## 2. Read every page → one form per page (`forms/pNN.json`)
Read `forms/README.md` once. Then for each page, look at `pNN.png` first; open quarters or the
legend crops whenever text or symbols are too small. Write:
`{"page_type": ..., "tool": "read_power_spine" | "read_layout_takeoff" | "read_project_context" | "none", "input": {...}}`

**Single-line diagrams (`read_power_spine`)** — one entry per board: its name exactly as
written, main switch (the incomer breaker, not the busbar rating), kA, voltage, every outgoing
way including spares (amps, poles from the tick marks, cable size), `source_snippet` = the busbar
header verbatim. Every "FED FROM … / incoming main cable …" box is a feeder (from → to, size,
cores); `length_annotated` only if a length is printed on that run. Scanned pages are read the same way.

**Layouts (`read_layout_takeoff`)** — if the legend has a QTY/QTYS column, those printed numbers
are the designer's own count: use them for the whole sheet and set
`counts_from_legend_schedule: true` (combining then trusts a higher printed quantity over a CAD
count that missed copies). Otherwise count every symbol room by room (leave it false).
Boxes exist for battens (`fluorescent_battens`), prismatic fittings, 1-lever 2-way switches and
master switches; on SLDs, `motor_starters` (DOL boxes per board) and `master_switch`. Give a building's lighting sheet and plug sheet the
SAME `room_name` (e.g. the building's name) so the merge keeps the higher count instead of adding
them. External / site lights go in a room named "Site / external": solar post lanterns →
`solar_post_lights`, tall flood-light posts (≥ 6 m) → `high_mast_poles`.

**Never guess.** Missing → 0 / false / empty. An item the form still has no field for (e.g.
geysers, A/C units — their connection is billed via the isolator) is written in
`extraction_warnings`, not forced into a wrong field.

## 3. Finish (deterministic)
```
$PY doe/execution/project.py finish "<project folder>" [--name "<Project>"] [--reference <reference project>]
```
A missing or invalid form STOPS the run with the reason — fix the form and run finish again.
Output in `<folder>/AfriPlan_Output/`: `<Project>_BoQ_<stamp>.xlsx` + `.pdf`, `things_to_check.md`,
`summary.json` (scores when `--reference` is given).

## 4. Decide and report
- Read `summary.json` and the top of `things_to_check.md`; tell the owner the totals, the number
  of things to check, the most serious ones, and the scores if any.
- E-mail when asked: `$PY doe/execution/send_email.py "<folder>/AfriPlan_Output"` (exit 4 = no mail
  credentials → say so; never paste large attachments by hand).
- Add anything that surprised you to `doe/playbook/LESSONS.md` (general lessons, no client figures).
