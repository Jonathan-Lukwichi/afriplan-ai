"""
sourcing.pricing_ref — map a BOQ line to a reference material price.

Suppliers quote MATERIAL, not the contractor's built-up rate. So when we need
an anchor to sanity-check (or, in the mock channel, to vary around) we look up
the material price in core.constants, falling back to the line's own BOQ unit
price only if constants has nothing.
"""

from __future__ import annotations

from core import constants


def guess_item_type(section: str, description: str) -> str:
    """Best-effort map a BOQ section/description to a core.constants price map."""
    s = (section or "").lower()
    d = (description or "").lower()

    if "distribution board" in s or "incoming" in s:
        return "db"
    if "lighting" in s:
        return "light"
    if "data" in s:
        return "socket"
    if "power outlet" in s:
        if any(t in d for t in ("switch", "isolator", "dimmer", "day/night")):
            return "switch"
        return "socket"
    if "containment" in s:
        return "containment"
    if "cable" in s or "underground" in s:
        return "cable"
    # fall back to keyword sniffing on the description
    if any(t in d for t in ("downlight", "light", "flood", "bulkhead", "panel")):
        return "light"
    if any(t in d for t in ("socket", "outlet", "floor box")):
        return "socket"
    if any(t in d for t in ("switch", "isolator", "dimmer")):
        return "switch"
    if any(t in d for t in ("mcb", "breaker", "elcb", "board", "db")):
        return "db"
    if any(t in d for t in ("cable", "wire", "swa", "surfix")):
        return "cable"
    return ""


def reference_price(section: str, description: str, anchor_price_zar: float = 0.0) -> float:
    """A material reference price for the item; anchor is the last-resort fallback."""
    item_type = guess_item_type(section, description)
    if item_type:
        price = constants.get_default_price(item_type, description)
        if price > 0:
            return float(price)
    return float(anchor_price_zar) if anchor_price_zar > 0 else 0.0
