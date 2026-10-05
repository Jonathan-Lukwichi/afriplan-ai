"""
GET /api/ai/providers — which AI readers the user may pick for a PDF run.

Only providers whose key the server holds are offered; `default` is what a run uses
when the user picks nothing (AI_PROVIDER, else the key that is set). Keys never leave
the server: the screen learns names only.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.config import ai_provider, ai_providers_ready

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/providers")
def list_providers():
    available = ai_providers_ready()
    return {"available": available, "default": ai_provider() if available else None}
