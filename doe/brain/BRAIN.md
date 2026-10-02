# AfriPlan DOE — Layer 2: the Brain (Orchestration)

The brain is **Claude Code** in this repository, running on the owner's subscription. It reads
the playbook (`doe/playbook/PLAYBOOK.md`), runs the execution layer, reads the PDF pages with
its own eyes (no API bill), decides what happens next, and reports. It never computes a
quantity or a price — every number comes from `doe/execution/`.

**Trigger:** a project folder path (or the files in it). **Output:** a professional Excel + PDF
BoQ in `<folder>\AfriPlan_Output\`. The step-by-step procedure is the skill
`.claude/skills/estimate-project/SKILL.md` (`/estimate-project <folder>`):

1. `project.py prepare <folder>` — pages, zoomed quarters, legend crops, text, form instructions.
2. Read every page → one strict form per page (the skill's reading rules).
3. `project.py finish <folder>` — checks every form (a bad one STOPS the run), reads the CAD set,
   combines, prices, writes the documents (+ scores against a reference project when asked).
4. Decide (playbook §6), report to the owner, e-mail when asked, add lessons.

## What is deterministic and what is not
- Steps 1 and 3 are deterministic: the same folder and the same forms always give the same BoQ.
- Step 2 is the only judgement step. The forms are saved, so a result can always be reproduced
  and audited; reading the same page again may differ slightly, so re-use the forms unless the
  drawings changed.

## Options
- No subscription time? `finish --pdf-reader api` reads the PDFs with the AI in `api/.env`
  (Claude, or free Gemini). `--pdf-reader none` prices the CAD drawings only.
- `--ai-match`: the AI pairs leftover equipment/fitting names when combining.

## Measured on the Wedela reference project (2026-10-02, frozen scorer)
| PDF read by | PDF alone | Combined with the DWG set |
|---|---:|---:|
| Claude API (Opus 5) | 27.1 % | 47.2 % |
| Gemini free tier | 40.2 % | — |
| **Claude Code subscription (this procedure)** | **47.5 %** | **55.8 %** |

## Schedule
Scheduled runs are prompts queued in this Claude Code session; they fire only while it is open.
The owner's address is `OWNER_EMAIL` in `api/.env` (kept out of this public repository).

## Never
- Change `api/`, `src/` or the scorer during a run.
- Send client figures to anyone but the owner, publish them, or commit them.
- Pay for AI without the owner's go-ahead.
