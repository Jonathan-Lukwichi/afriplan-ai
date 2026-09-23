"""
Deterministic rate build-up engine — the "brain" of the estimator.

Design principle (the determinism contract):
    The LLM is only the EYES. This module is the BRAIN.
    The LLM extracts facts (counts, lengths, cable sizes). Every RATE and
    every derived quantity is computed HERE, in pure Python. Given the same
    extracted facts, this module returns the identical bill every time —
    no randomness, no network, no LLM.

The model is reconstructed from the Wedela "Installation Rate" sheet and the
three take-off / rate-build-up methodology references (see the project memory
`boq-measurement-methodology`). It reproduces those rates exactly:

    Install rate  =  (Σ crew_hourly × crew_count) × task_hours ÷ base_qty
    Built-up rate =  material × markup  +  install labour
                     +  consumables%  +  transport%  +  waste%

Worked check (95 mm² PVC SWA, from the Wedela sheet):
    crew = 2 electricians + 2 semi + 10 general
         = 180·2 + 120·2 + 65·10 = R1 250 / hour
    18 hours to install 100 m  →  1 250 × 18 ÷ 100 = R225 / m  ✓

Everything in this module is frozen data + pure functions. No I/O, no LLM,
no `datetime.now()`. It is safe to import from either pipeline or the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Mapping, Optional, Tuple


# ─── Crew hourly rates (ZAR/hour) — from the Wedela Installation Rate sheet ──

@dataclass(frozen=True)
class CrewRates:
    """Hourly labour rates per trade. Defaults match the reference bill."""

    electrician: float = 180.0
    semi_skilled: float = 120.0
    general_worker: float = 65.0

    def hourly_cost(self, n_elec: int, n_semi: int, n_gen: int) -> float:
        """Total crew cost per hour for the given team composition."""
        return (
            self.electrician * n_elec
            + self.semi_skilled * n_semi
            + self.general_worker * n_gen
        )


DEFAULT_CREW = CrewRates()


# ─── Rate build-up parameters (methodology % add-ons + markup) ───────────────

@dataclass(frozen=True)
class RateParams:
    """
    Multipliers applied on top of material + labour.

    Values are the industry conventions from the methodology references and
    the Wedela minisub build-up columns (material markup ×1.3).
    """

    material_markup: float = 1.30       # ×1.3 on supplied material
    consumables_pct: float = 0.09       # ~9% of conduit/material for bushes, couplings
    transport_pct: float = 0.02         # ~2% transport of material
    waste_pct: float = 0.05             # ~5% cable/conduit waste
    contingency_pct: float = 0.05       # 5% project contingency
    vat_pct: float = 0.15               # 15% VAT (South Africa)


DEFAULT_PARAMS = RateParams()


# ─── A single labour task (crew + duration) ──────────────────────────────────

@dataclass(frozen=True)
class LabourTask:
    """
    One installation task: a crew working for `hours` to install `base_qty`
    units of `unit`. The per-unit labour rate is fully determined by this.
    """

    key: str
    n_elec: int
    n_semi: int
    n_gen: int
    hours: float
    base_qty: float
    unit: str

    def labour_total(self, crew: CrewRates = DEFAULT_CREW) -> float:
        """Total labour cost to install `base_qty` units."""
        return crew.hourly_cost(self.n_elec, self.n_semi, self.n_gen) * self.hours

    def rate_per_unit(self, crew: CrewRates = DEFAULT_CREW) -> float:
        """Install labour cost per single unit."""
        if self.base_qty == 0:
            return 0.0
        return self.labour_total(crew) / self.base_qty


# ─── Cable install tasks — crew 2E + 2S + 10G, hours by size (per 100 m) ─────
# Reproduced verbatim from the Wedela Installation Rate sheet.

_CABLE_INSTALL_HOURS_PER_100M: Dict[str, float] = {
    "95mm2": 18.0,
    "70mm2": 17.0,
    "50mm2": 16.0,
    "35mm2": 15.0,
    "25mm2": 14.0,
    "16mm2": 13.0,
    "10mm2": 12.0,
    "6mm2": 11.0,
    "4mm2": 10.0,
    "2.5mm2": 9.0,
    "95mm2_abc": 21.0,
}

# Bare copper earth wire (BCEW) install — crew 1E + 2S + 10G, hours by size.
_BCEW_INSTALL_HOURS_PER_100M: Dict[str, float] = {
    "70mm2": 8.0,
    "50mm2": 7.0,
    "35mm2": 6.0,
    "25mm2": 5.0,
    "16mm2": 4.0,
    "10mm2": 3.0,
    "6mm2": 2.0,
    "4mm2": 1.8,
}

# Cable termination — crew 1E + 1S, hours per termination by size.
_TERMINATION_HOURS: Dict[str, float] = {
    "95mm2": 2.0,
    "70mm2": 1.9,
    "50mm2": 1.8,
    "35mm2": 1.7,
    "25mm2": 1.6,
    "16mm2": 1.5,
    "10mm2": 1.4,
    "6mm2": 1.3,
    "4mm2": 1.2,
    "2.5mm2": 1.1,
    "95mm2_abc": 2.1,
}

# Fitting install — crew 1E + 1G, hours per fitting.
_FITTING_INSTALL_HOURS: Dict[str, float] = {
    "recessed_600x1200": 1.1,
    "vapor_proof_2x24w": 1.0,
    "vapor_proof_2x18w": 0.95,
    "bulkhead_24w": 0.9,
    "flood_30w": 0.9,
    "downlight_6w": 0.5,
}


def _cable_install_task(size: str) -> Optional[LabourTask]:
    hours = _CABLE_INSTALL_HOURS_PER_100M.get(size)
    if hours is None:
        return None
    return LabourTask(f"install_cable_{size}", 2, 2, 10, hours, 100.0, "m")


def _bcew_install_task(size: str) -> Optional[LabourTask]:
    hours = _BCEW_INSTALL_HOURS_PER_100M.get(size)
    if hours is None:
        return None
    return LabourTask(f"install_bcew_{size}", 1, 2, 10, hours, 100.0, "m")


def _termination_task(size: str) -> Optional[LabourTask]:
    hours = _TERMINATION_HOURS.get(size)
    if hours is None:
        return None
    return LabourTask(f"terminate_{size}", 1, 1, 0, hours, 1.0, "each")


def _fitting_install_task(fitting: str) -> Optional[LabourTask]:
    hours = _FITTING_INSTALL_HOURS.get(fitting)
    if hours is None:
        return None
    return LabourTask(f"install_{fitting}", 1, 0, 1, hours, 1.0, "each")


# ─── Public install-rate lookups (per unit) ──────────────────────────────────

def cable_install_rate(size: str, crew: CrewRates = DEFAULT_CREW) -> Optional[float]:
    """Install labour rate per metre for a feeder/SWA cable of `size`."""
    task = _cable_install_task(size)
    return None if task is None else task.rate_per_unit(crew)


def bcew_install_rate(size: str, crew: CrewRates = DEFAULT_CREW) -> Optional[float]:
    """Install labour rate per metre for bare copper earth wire of `size`."""
    task = _bcew_install_task(size)
    return None if task is None else task.rate_per_unit(crew)


def termination_install_rate(size: str, crew: CrewRates = DEFAULT_CREW) -> Optional[float]:
    """Install labour rate per termination (one cable end) of `size`."""
    task = _termination_task(size)
    return None if task is None else task.rate_per_unit(crew)


def fitting_install_rate(fitting: str, crew: CrewRates = DEFAULT_CREW) -> Optional[float]:
    """Install labour rate per light fitting of `fitting` type."""
    task = _fitting_install_task(fitting)
    return None if task is None else task.rate_per_unit(crew)


# ─── Built-up rate (material × markup + labour + % add-ons) ──────────────────

@dataclass(frozen=True)
class BuiltUpRate:
    """A fully-derived supply/install rate pair, with its build-up exposed."""

    material_supply: float      # material cost per unit, incl. markup
    install_labour: float       # labour cost per unit
    consumables: float          # consumables add-on per unit
    transport: float            # transport add-on per unit
    waste: float                # waste add-on per unit

    @property
    def supply_rate(self) -> float:
        """SA-format 'Supply' line rate = marked-up material + its add-ons."""
        return self.material_supply + self.consumables + self.transport + self.waste

    @property
    def install_rate(self) -> float:
        """SA-format 'Install' line rate = labour only."""
        return self.install_labour

    @property
    def combined_rate(self) -> float:
        """Built-up (supply + install) single rate."""
        return self.supply_rate + self.install_rate


def build_rate(
    *,
    material_cost: float,
    install_labour: float,
    params: RateParams = DEFAULT_PARAMS,
    apply_addons_to_material: bool = True,
) -> BuiltUpRate:
    """
    Assemble a built-up rate from raw material + labour.

    material_cost   raw (un-marked-up) material cost per unit
    install_labour  labour cost per unit (from a LabourTask)
    """
    marked_up = material_cost * params.material_markup
    base = marked_up if apply_addons_to_material else 0.0
    return BuiltUpRate(
        material_supply=marked_up,
        install_labour=install_labour,
        consumables=base * params.consumables_pct,
        transport=base * params.transport_pct,
        waste=base * params.waste_pct,
    )


# ─── Point method — run-length classification (methodology references) ───────

class PointClass(str, Enum):
    """Reticulation run-length bands (DB → point routed length)."""

    SHORT = "short"     # 0–3 m      priced per point
    MEDIUM = "medium"   # 3–6 m      priced per point
    LONG = "long"       # 6–10 m     priced per point
    AXIS = "axis"       # > 10 m     priced per metre


def classify_point(routed_length_m: float) -> PointClass:
    """Classify a reticulation run by its routed (not straight-line) length."""
    if routed_length_m <= 3.0:
        return PointClass.SHORT
    if routed_length_m <= 6.0:
        return PointClass.MEDIUM
    if routed_length_m <= 10.0:
        return PointClass.LONG
    return PointClass.AXIS


def routed_length(
    *,
    ceiling_height_m: float,
    mount_height_m: float,
    horizontal_run_m: float,
    extra_drops_m: float = 0.0,
) -> float:
    """
    Routed cable length for one point: drop from ceiling to the outlet, the
    horizontal run in the ceiling void, plus any additional drops.

        length = (ceiling_height − mount_height)   # drop to this outlet
               + horizontal_run                     # across the ceiling
               + extra_drops                         # drop(s) into looped point(s)
    """
    drop = max(ceiling_height_m - mount_height_m, 0.0)
    return drop + horizontal_run_m + extra_drops_m


def average_length_per_point(total_looped_m: float, n_points: int) -> float:
    """
    Methodology fallback when runs aren't dimensioned: total measured looped
    cable ÷ number of points = average metres per point.
    """
    if n_points <= 0:
        return 0.0
    return total_looped_m / n_points
