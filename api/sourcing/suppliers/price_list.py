"""
sourcing.suppliers.price_list — the price catalogue as one more supplier beside each BoQ line.

One connector per catalogue supplier (Schneider list, a contractor's own override prices…; the
AfriPlan estimates are left out — the bill already uses them). A quote is a LIST price with its
date, not an offer: availability is UNKNOWN, so the engine never recommends or auto-applies it;
a person can still pick it for a line. Matching is deliberately strict (family + every attribute
the line states); a line it cannot match exactly gets no quote rather than a wrong one.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from statistics import median_low
from typing import Dict, List, Optional, Tuple

from sourcing import catalogue as cat
from sourcing.models import Availability, QuoteRequestItem, SourcingChannel, SupplierInfo, SupplierQuote
from sourcing.suppliers.base import SupplierConnector

DEFAULT_CATALOGUE = Path(__file__).resolve().parents[3] / "data" / "catalogue" / "price_catalogue.csv"

# Protective devices only: their numbers (A, poles, kA) define the product. Sockets and switches
# are left out until product ranges are mapped — on the real list a "1-Lever Switch" matched a
# control selector head and a "Data Socket" a 16 A power socket.
_TRUSTED = {"mcb", "mccb", "earth_leakage", "surge"}
_NEEDS_AMPS_AND_POLES = {"mcb", "mccb", "earth_leakage"}
_ACCESSORY = re.compile(
    r"auxiliar|\baux\b|\bcontacts?\b|shunt|release|handle|cover|\bkit\b|accessor|terminal|lock|"
    r"plate|frame|surround|\bmech|label|bracket|adapt", re.I)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _wanted(req: QuoteRequestItem) -> Optional[Tuple[str, Dict[str, float]]]:
    family = cat.classify_family(req.description)
    if family == "other":
        family = cat.classify_family(req.description, req.section)
    if family not in _TRUSTED:
        return None
    attrs = cat.attributes(req.description)
    if family in _NEEDS_AMPS_AND_POLES and not ("amps" in attrs and "poles" in attrs):
        return None
    return family, attrs


def _fits(item: cat.CatalogueItem, family: str, attrs: Dict[str, float]) -> bool:
    if item.family != family or item.list_price_zar_excl_vat <= 0 or _ACCESSORY.search(item.description):
        return False
    if "amps" in attrs and item.amps != attrs["amps"]:
        return False
    if "poles" in attrs and item.poles != attrs["poles"]:
        return False
    if "ka" in attrs and (item.ka or 0) < attrs["ka"]:
        return False
    return True


class PriceListSupplier(SupplierConnector):
    """One catalogue supplier's list prices, offered as a dated reference quote."""

    def __init__(self, supplier: str, items: List[cat.CatalogueItem]):
        self.items = [i for i in items if i.supplier == supplier]
        date = max((i.price_date for i in self.items), default="")
        super().__init__(SupplierInfo(supplier_id=f"pricelist:{_slug(supplier)}",
                                      name=f"{supplier} list price ({date or 'undated'})",
                                      channel=SourcingChannel.PRICE_LIST))

    def quote(self, items: List[QuoteRequestItem]) -> List[SupplierQuote]:
        quotes: List[SupplierQuote] = []
        for req in items:
            wanted = _wanted(req)
            if wanted is None:
                continue
            family, attrs = wanted
            matches = sorted((i for i in self.items if _fits(i, family, attrs)),
                             key=lambda i: i.net_price_zar_excl_vat)
            if not matches:
                continue
            pick = next(i for i in matches if i.net_price_zar_excl_vat ==
                        median_low([m.net_price_zar_excl_vat for m in matches]))
            quotes.append(SupplierQuote(
                item_ref=req.item_ref, supplier_id=self.supplier_id, supplier_name=self.info.name,
                channel=SourcingChannel.PRICE_LIST, unit_price_zar=pick.net_price_zar_excl_vat,
                availability=Availability.UNKNOWN,
                notes=(f"{pick.part_no} {pick.description} — median of {len(matches)} matching list items "
                       f"(R{matches[0].net_price_zar_excl_vat:,.2f}–R{matches[-1].net_price_zar_excl_vat:,.2f}); "
                       f"list price excl. VAT dated {pick.price_date}, {pick.price_source}"
                       + (f", {pick.discount_pct:g} % discount" if pick.discount_pct else ", no trade discount set")),
                raw_source=pick.item_id,
            ))
        return quotes


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> List[cat.CatalogueItem]:
    return cat.load_catalogue(Path(path))


def default_price_list_suppliers(path: Optional[Path] = None) -> List[PriceListSupplier]:
    """A connector per catalogue supplier; none when the catalogue has not been built on this machine."""
    p = Path(path or DEFAULT_CATALOGUE)
    if not p.exists():
        return []
    items = _load(str(p), p.stat().st_mtime)
    names = sorted({i.supplier for i in items if i.supplier != cat.AFRIPLAN})
    return [PriceListSupplier(n, items) for n in names]
