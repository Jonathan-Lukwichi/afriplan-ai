"""
sourcing.pricing_ref — map a BOQ line to a reference material price.

In the mock channel suppliers vary around the bill line's own unit price; the
core.constants catalogue is only a fallback for lines that carry no price.
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
    """
    The price a (simulated) supplier quotes around: the bill line's own price first.
    The catalogue lookup is by broad item type, so it cannot tell a 31-way board with its
    breakers from a bare enclosure, or 95 mm² SWA from 2.5 mm² — used alone it quoted a
    R18k board at ~R2k and heavy cable at R25/m. It is only the fallback for unpriced lines.
    """
    if anchor_price_zar > 0:
        return float(anchor_price_zar)
    item_type = guess_item_type(section, description)
    if item_type:
        price = constants.get_default_price(item_type, description)
        if price > 0:
            return float(price)
    return 0.0
