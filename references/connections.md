# Connections

Key **names** only; values live in `api/.env` (never committed). Template: `api/.env.example`.

| Area | Tool | How | Key name(s) in `api/.env` | Where in code | Last tested |
|---|---|---|---|---|---|
| PDF reading (paid) | Claude API | Anthropic SDK | `ANTHROPIC_API_KEY`, `AI_PROVIDER` | `api/agent/pdf_pipeline/llm.py`; model IDs only in `api/core/config.py` | unsure |
| PDF reading (free) | Gemini | HTTP client | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FAST_MODEL`, `AI_PROVIDER` | `api/core/gemini_client.py` | unsure |
| Database | SQLite (local, Docker/Render) or a hosted Postgres | `sqlite3` / `psycopg` | `DATABASE_URL` (unset = SQLite) | `api/db/` | unsure |
| Report e-mail | Resend | HTTP API | `RESEND_API_KEY`, `NOTIFY_FROM_EMAIL` | `api/core/notify.py` (sending); `api/ai/boq_email.py` (AI cover note text) | unsure |
| Demo login | built-in | none | `DEMO_EMAIL`, `DEMO_PASSWORD` | `src/pages/Login.jsx` (demo-only by decision) | unsure |
| Hosting | Render (Docker) | Git deploy | set in Render, not in git | `Dockerfile`, `render.yaml` | unsure |
| CI | GitHub Actions | workflow file | none | `.github/workflows/ci.yml` (branch `ci/github-actions`) | 2026-10-26, green |
| DWG conversion | LibreDWG `dwg2dxf` | local binary | none | `api/agent/dxf_pipeline/dwg.py` | unsure |
