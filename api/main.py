from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from db.connection import init_db  # noqa: E402

init_db()

# Off Vercel every job runs inside this one process, so a run still marked "running" at
# start-up died with the previous process (restart, crash, redeploy): say so instead of
# letting its page poll forever. On Vercel several instances share one database — skip.
import os  # noqa: E402

if not os.environ.get("VERCEL"):
    from core.compare_store import compare_store  # noqa: E402
    from core.run_store import run_store  # noqa: E402
    _RESTARTED = "The server restarted while this run was in progress - please run it again."
    run_store.fail_interrupted(_RESTARTED)
    compare_store.fail_interrupted(_RESTARTED)

# In production (Docker) the built frontend is copied to api/static and served
# by this same process — one service, same origin, no CORS. In dev the folder
# doesn't exist and Vite serves the frontend on :5180 as before.
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_SERVE_FRONTEND = _STATIC_DIR.is_dir()

app = FastAPI(
    title="AfriPlan Electrical — Web API",
    description="Dual-pipeline electrical Bill-of-Quantities extraction (PDF vision + deterministic DXF), FastAPI + React rewrite.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


from routers import audit, compare, export, pricing, runs, symbols  # noqa: E402

app.include_router(runs.router)
app.include_router(compare.router)
app.include_router(export.router)
app.include_router(pricing.router)
app.include_router(audit.router)
app.include_router(symbols.router)

# Registered as each later phase lands:
# app.include_router(profile.router)

if _SERVE_FRONTEND:
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(_STATIC_DIR / "index.html")
