# Deploy AfriPlan on Render

One Docker service: FastAPI serves the API **and** the built React app on one URL.
Everything Render needs is in the repo: `Dockerfile`, `.dockerignore`, `render.yaml`.

---

## Part A — Check it on your PC first (the exact image Render will run)

Needs **Docker Desktop** running (whale icon in the taskbar says "Engine running").

1. **Build the image** (first time ~25 min — it compiles the DWG converter; later builds are quick):
   ```powershell
   cd <your clone of the repo>
   docker build -t afriplan:test .
   ```
   *This PC only:* Avast's Web Shield intercepts HTTPS, so the plain build fails with
   `CERTIFICATE_VERIFY_FAILED`. Either turn Web Shield off while building, or build with the
   Avast certificate — see "Building behind Avast" at the bottom. Render is not affected.

2. **Run it** (same as Render will):
   ```powershell
   docker run --rm -p 8080:8000 --name afriplan-test afriplan:test
   ```
   Add `-e ANTHROPIC_API_KEY=sk-ant-...` before `afriplan:test` to test the PDF engine too.

3. **Open** http://127.0.0.1:8080 → *Sign in* → **Upload → DXF / DWG** → select all the
   `.dwg` files in `data\projects\wedela\raw\Wedela Electrical` (Ctrl+A) → **Run DXF engine**.
   Expect the *Drawing set* panel with "Feeder routes measured on WD-OL-001…" and the older
   `WD-PB-01-LIGHTING 100225` marked *skipped — older revision*; then **View Bill of Quantities**.

4. **Stop it:** `Ctrl+C` in that window (or `docker stop afriplan-test`).

---

## Part B — Deploy on Render

1. **Push the code** — already on GitHub `Jonathan-Lukwichi/afriplan-ai`, branch `main`.
2. Go to **https://dashboard.render.com** and sign in (**Sign in with GitHub** is easiest).
3. Click **New +** → **Blueprint**.
4. **Connect GitHub** if asked, and allow Render to see the repo `afriplan-ai`.
5. Pick **afriplan-ai**. Render reads `render.yaml` and shows one service: **afriplan**
   (Docker, plan *Standard*, a 1 GB disk).
6. Render asks for the secret values (they are never stored in git):
   | Key | What to put |
   |---|---|
   | `ANTHROPIC_API_KEY` | your Anthropic key — enables the **PDF** engine (paid, fast) and Live-Pricing replies. |
   | `GEMINI_API_KEY` | your free Google AI Studio key — the free, slower PDF reader. |
   | `AI_PROVIDER` | optional: `claude` or `gemini` — which one is pre-selected when both keys are set. |

   Set **both** keys and the Upload page lets each user pick the PDF reader (Claude or Gemini)
   per run; set one and that one is used; set none and only DWG/DXF works.
   | `RESEND_API_KEY` | optional — only for "Email this BoQ" |
   | `NOTIFY_FROM_EMAIL` | optional — sender address for those emails |
7. Click **Apply** / **Create**. The first build takes ~20–30 min (it compiles LibreDWG);
   watch the **Logs** tab. It is live when the log shows `Application startup complete`
   and the status turns **Live**.
8. Open the URL shown at the top (like `https://afriplan-xxxx.onrender.com`) and repeat
   Part A step 3 there.

After that, **every push to `main` redeploys automatically**.

---

## What to know

- **Plan & memory.** Measured in this image (2026-09-28): idle ~110 MB; the whole Wedela
  set (17 DWGs, one project run, 70 s) peaks at **~1.1 GB**. So the blueprint uses
  **Standard (2 GB RAM, ~$25/month)**. **Starter (512 MB, ~$7/month)** runs single drawings
  but a full set would run out of memory (the service restarts mid-run). Change `plan:` in
  `render.yaml` or in the dashboard.
- **Many users at once — the run queue.** Heavy runs take turns (`api/core/run_queue.py`):
  each kind runs `slots` at a time, the others wait in line and see *"Waiting in line: N runs
  ahead of yours"*; when every slot is busy and the line is full, a new upload gets *"AfriPlan
  is busy … try again in a few minutes"* (503) instead of crashing the server. Set with env vars:

  | Variable | Default | Meaning |
  |---|---|---|
  | `AFRIPLAN_DXF_SLOTS` | 1 | CAD projects processed at once |
  | `AFRIPLAN_PDF_SLOTS` | 2 | PDF projects processed at once (they mostly wait on the AI) |
  | `AFRIPLAN_QUEUE_MAX` | 20 | runs allowed to wait in each line |

  Load test (2026-10-06, `scripts/load_test.py`, 10 users each uploading the full 18-DWG set at
  the same moment, local PC): **10 / 10 passed, none lost.** One slot: peak **1.2 GB**, last user
  done after **14 min** (one project ≈ 85 s). Two slots: peak **2.0 GB**, last user **8.7 min** —
  too close to Standard's 2 GB, so keep `AFRIPLAN_DXF_SLOTS=1` on Standard; with **4 GB** set it
  to 2. Not load-tested: the PDF engine (paid per page) — the free AI model's daily quota is
  shared by every user, and the paid model is limited per minute by the provider account.
- **Disk.** Runs and the contractor profile are stored in SQLite on a 1 GB disk mounted at
  `/app/data` (~$0.25/month), so they survive restarts and deploys.
- **Who can use it.** The login is a demo login — **anyone with the URL can use the app**,
  and with `ANTHROPIC_API_KEY` set, every PDF run costs you ~R 2.50 per page. Share the URL
  only with people you trust until real accounts exist.
- **Not online:** client drawings, the Wedela bill and the fitted ratio model stay on your PC
  (the repo is public). So online, *Complete with derived items* is hidden, and you upload
  your own drawings.
- **Logs / restart / rollback:** service page → **Logs**, **Manual Deploy**, **Events**
  (roll back to any previous deploy).

## Building behind Avast (this PC only)
Export the Avast root certificate and pass it in as a build context — the repo's Dockerfile
is not changed. The steps and the generated `Dockerfile.local` are kept outside the repo;
ask Claude to re-create them, or turn Avast **Web Shield** off for the few minutes of the build.
