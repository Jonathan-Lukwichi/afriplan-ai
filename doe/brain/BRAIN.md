# AfriPlan DOE — Layer 2: the Brain (Orchestration)

The brain is **Claude Code** in this repository. It reads the playbook
(`doe/playbook/PLAYBOOK.md`), runs the execution layer, reads what came back, decides what
happens next, and reports. It never computes a quantity or a price itself — every number
comes from `doe/execution/`.

## A run, step by step
1. Read `doe/playbook/PLAYBOOK.md` and `doe/playbook/LESSONS.md`.
2. Run the execution layer (7–8 minutes on Wedela):
   ```
   cd <repo>; $env:PYTHONIOENCODING="utf-8"
   api\.venv\Scripts\python.exe doe\execution\estimate.py --project wedela
   ```
   Options: `--pdf-fresh` (read the PDFs again with the AI in api/.env),
   `--ai-match` (AI pairs leftover names when combining).
3. Read `runs/doe/<stamp>/summary.json` and `evaluation.md`.
4. **Decide** (playbook §6):
   - exit code ≠ 0 → do not send the BoQ; e-mail the owner the STOP reason instead;
   - a score lower than the previous run on the same inputs → send, and say so first;
   - otherwise → send.
5. **Report** — e-mail to the owner, subject `AfriPlan BoQ — <project> — <stamp>`:
   - body: `runs/doe/<stamp>/email_body.txt`;
   - attachments: the `.xlsx` and `.pdf` in that folder.
   How it is sent, best first:
   a. `doe/execution/send_email.py` — deterministic, when `RESEND_API_KEY` or
      `SMTP_USER` + `SMTP_PASSWORD` (a Gmail app password) are set in `api/.env`;
   b. otherwise the Gmail connector of this Claude session (attachments from
      `runs/doe/<stamp>/attachments/*.b64`, base64 in 1000-character lines, joined).
6. **Learn** — if something surprised us, add it to `doe/playbook/LESSONS.md`.

## Schedule
Scheduled runs are prompts queued in this Claude Code session ("run the AfriPlan DOE brain
now"); they fire only while the session is open. The owner's address is `OWNER_EMAIL` in
`api/.env` (kept out of this public repository).

| When (local, SAST) | What |
|---|---|
| 2026-09-30 06:30 | run 1 — Wedela, DWG + saved PDF reading, combined, e-mailed |
| 2026-09-30 06:35 | run 2 — the same (repeatability check: the numbers must be identical) |

## What the brain must never do
- Change `api/`, `src/` or the scorer during a run.
- Send client figures to anyone but the owner, publish them, or commit them.
- Pay for AI without the owner's go-ahead (fresh PDF reads with Claude cost ~R 2.50/page).
