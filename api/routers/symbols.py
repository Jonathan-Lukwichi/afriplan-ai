"""
GET /api/symbols/choices, PUT /api/symbols/{signature} — confirm or correct what an
unnamed CAD symbol shape is (ADR-0007). A person's name is stored and always wins over
the AI's; the next run of any drawing with that shape uses it (and costs nothing).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.shared.symbol_catalogue import CHOICES
from db.symbol_names import save_symbol_name

router = APIRouter(prefix="/api/symbols", tags=["symbols"])


class SymbolName(BaseModel):
    item: str


@router.get("/choices")
def symbol_choices():
    return {"choices": CHOICES}


@router.put("/{signature}")
def name_symbol(signature: str, body: SymbolName):
    if body.item not in CHOICES:
        raise HTTPException(400, f"'{body.item}' is not one of the allowed names")
    save_symbol_name(signature, body.item, "person")
    return {"signature": signature, "item": body.item, "named_by": "person"}
