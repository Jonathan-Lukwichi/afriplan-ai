"""
The FIXED list of items a drawing symbol can be named as (ADR-0007) — the AI must choose
from here, never invent a name — with the bill section and the catalogue price for each.
Names match the legend vocabulary (agent/shared/legend.py) so legend coverage lines up.
"""

from __future__ import annotations

import re
from typing import Dict, NamedTuple, Optional

from agent.shared.boq import BQSection

NOT_ELECTRICAL = "Not an electrical symbol"
UNSURE = "Unsure"


class CatalogueItem(NamedTuple):
    section: BQSection
    price_map: str      # core.constants map name: light | socket | switch | db
    price_key: str      # key in that map


CATALOGUE: Dict[str, CatalogueItem] = {
    # lighting
    "Vapour Proof Light": CatalogueItem(BQSection.LIGHTING, "light", "vapor_proof_2x18w"),
    "LED Downlight": CatalogueItem(BQSection.LIGHTING, "light", "downlight_led_12w"),
    "Recessed LED Panel": CatalogueItem(BQSection.LIGHTING, "light", "recessed_led_600x1200"),
    "Surface LED Light": CatalogueItem(BQSection.LIGHTING, "light", "surface_mount_led_18w"),
    "Bulkhead Light": CatalogueItem(BQSection.LIGHTING, "light", "bulkhead_24w"),
    "LED Floodlight": CatalogueItem(BQSection.LIGHTING, "light", "flood_light_50w"),
    "Pole Light": CatalogueItem(BQSection.LIGHTING, "light", "pole_light_60w"),
    "Solar Post Light": CatalogueItem(BQSection.LIGHTING, "light", "solar_post_light_100w"),
    "High-Mast Light": CatalogueItem(BQSection.LIGHTING, "light", "high_mast_2x600w_10m"),
    "Fluorescent Batten": CatalogueItem(BQSection.LIGHTING, "light", "fluorescent_50w_5ft"),
    "Prismatic Light": CatalogueItem(BQSection.LIGHTING, "light", "prismatic_2x18w"),
    "Light Fitting (generic)": CatalogueItem(BQSection.LIGHTING, "light", "surface_mount_led_18w"),
    "Emergency Light": CatalogueItem(BQSection.FIRE_SAFETY, "light", "emergency_light_led"),
    "Exit Sign": CatalogueItem(BQSection.FIRE_SAFETY, "light", "exit_sign_led"),
    # switches / control
    "1-Lever Switch": CatalogueItem(BQSection.LIGHTING, "switch", "switch_1lever_1way"),
    "2-Lever Switch": CatalogueItem(BQSection.LIGHTING, "switch", "switch_2lever_1way"),
    "3-Lever Switch": CatalogueItem(BQSection.LIGHTING, "switch", "switch_3lever_1way"),
    "Day/Night Switch": CatalogueItem(BQSection.LIGHTING, "switch", "day_night_switch"),
    "1-Lever 2-Way Switch": CatalogueItem(BQSection.LIGHTING, "switch", "switch_1lever_2way"),
    "Master Switch": CatalogueItem(BQSection.POWER_OUTLETS, "switch", "master_switch"),
    "Isolator Switch": CatalogueItem(BQSection.POWER_OUTLETS, "switch", "isolator_30a"),
    # power / data
    "16A Double Switched Socket": CatalogueItem(BQSection.POWER_OUTLETS, "socket", "double_socket_300"),
    "16A Single Switched Socket": CatalogueItem(BQSection.POWER_OUTLETS, "socket", "single_socket_300"),
    "Weatherproof Socket": CatalogueItem(BQSection.POWER_OUTLETS, "socket", "double_socket_waterproof"),
    "Floor Box Socket": CatalogueItem(BQSection.POWER_OUTLETS, "socket", "floor_box"),
    "Data Socket (CAT6)": CatalogueItem(BQSection.DATA_COMMS, "socket", "data_points_cat6"),
}

CHOICES = [*CATALOGUE, NOT_ELECTRICAL, UNSURE]


def _norm(name: str) -> str:
    return re.sub(r"[\s\-_]+", " ", name).strip().lower()


_BY_NORM = {_norm(k): k for k in CATALOGUE}


def canonical_name(name: str) -> str:
    """The catalogue's own spelling of a name; an older spelling ('Vapour-Proof Light', saved
    before the names followed bill wording) still finds its item. Unknown names unchanged."""
    return _BY_NORM.get(_norm(name), name)


def catalogue_item(name: str) -> Optional[CatalogueItem]:
    return CATALOGUE.get(canonical_name(name))
