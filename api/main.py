from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# In production (Docker) the built frontend is copied to api/static and served
# by this same process — one service, same origin, no CORS. In dev the folder
# doesn't exist and Vite serves the frontend on :5173 as before.
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


from routers import compare, export, runs  # noqa: E402

app.include_router(runs.router)
app.include_router(compare.router)
app.include_router(export.router)

# Registered as each later phase lands:
# app.include_router(pricing.router)
# app.include_router(profile.router)

if _SERVE_FRONTEND:
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(_STATIC_DIR / "index.html")
