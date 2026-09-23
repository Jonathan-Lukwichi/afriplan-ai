"""
sourcing.suppliers.base — the pluggable supplier connector interface.

Every price channel (mock, web catalog, cached price list, RFQ email …) is a
`SupplierConnector`. The engine fans a list of `QuoteRequestItem`s out across
however many connectors it's given and collects their `SupplierQuote`s. New
channels drop in without touching the engine or the UI.

Two kinds of channel:
  • INSTANT connectors (mock, web catalog, price list) answer synchronously —
    implement `quote()`.
  • RFQ connectors (email/WhatsApp) are asynchronous by nature: you draft a
    request, a human replies hours later, and the reply is parsed. Those live
    in sourcing.rfq and are surfaced interactively, not through `quote()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from sourcing.models import QuoteRequestItem, SupplierInfo, SupplierQuote


class SupplierConnector(ABC):
    """An instant price source for one supplier."""

    def __init__(self, info: SupplierInfo):
        self.info = info

    @property
    def supplier_id(self) -> str:
        return self.info.supplier_id

    @abstractmethod
    def quote(self, items: List[QuoteRequestItem]) -> List[SupplierQuote]:
        """Return one SupplierQuote per item this supplier can price.

        A connector may return fewer quotes than items (it simply doesn't
        stock some), but must never raise for an item it can't price.
        """
        raise NotImplementedError
