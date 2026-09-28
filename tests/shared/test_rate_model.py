"""
Tests for the deterministic rate build-up engine (core/rate_model.py).

These tests enforce the determinism contract: the same inputs must always
produce byte-identical rates, and the reconstructed rates must match the
Wedela reference bill's Installation Rate sheet exactly.
"""

from __future__ import annotations

import pytest

from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    BuiltUpRate,
    CrewRates,
    LabourTask,
    PointClass,
    RateParams,
    average_length_per_point,
    bcew_install_rate,
    build_rate,
    cable_install_rate,
    classify_point,
    fitting_install_rate,
    routed_length,
    termination_install_rate,
)


# ─── Crew hourly cost ────────────────────────────────────────────────────────

def test_crew_hourly_cost_matches_reference():
    # 95mm cable crew: 2 elec + 2 semi + 10 general = R1250/hr
    assert DEFAULT_CREW.hourly_cost(2, 2, 10) == 1250.0


def test_crew_rates_are_overridable():
    crew = CrewRates(electrician=200.0, semi_skilled=130.0, general_worker=70.0)
    assert crew.hourly_cost(1, 1, 0) == 330.0


# ─── Cable install rates reproduce the Wedela sheet exactly ──────────────────

@pytest.mark.parametrize(
    "size,expected_rate_per_m",
    [
        ("95mm2", 225.0),
        ("70mm2", 212.5),
        ("50mm2", 200.0),
        ("35mm2", 187.5),
        ("25mm2", 175.0),
        ("16mm2", 162.5),
        ("10mm2", 150.0),
        ("6mm2", 137.5),
        ("4mm2", 125.0),
        ("2.5mm2", 112.5),
        ("95mm2_abc", 262.5),
    ],
)
def test_cable_install_rate_matches_reference(size, expected_rate_per_m):
    assert cable_install_rate(size) == expected_rate_per_m


def test_cable_install_rate_unknown_size_returns_none():
    assert cable_install_rate("240mm2") is None


# ─── BCEW install rates ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "size,expected",
    [("70mm2", 85.6), ("50mm2", 74.9), ("35mm2", 64.2), ("16mm2", 42.8)],
)
def test_bcew_install_rate_matches_reference(size, expected):
    assert bcew_install_rate(size) == pytest.approx(expected)


# ─── Termination rates ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "size,expected",
    [("95mm2", 600.0), ("70mm2", 570.0), ("50mm2", 540.0), ("2.5mm2", 330.0)],
)
def test_termination_rate_matches_reference(size, expected):
    assert termination_install_rate(size) == pytest.approx(expected)


# ─── Fitting install rates ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "fitting,expected",
    [
        ("recessed_600x1200", 269.5),
        ("vapor_proof_2x24w", 245.0),
        ("bulkhead_24w", 220.5),
        ("flood_30w", 220.5),
    ],
)
def test_fitting_install_rate_matches_reference(fitting, expected):
    assert fitting_install_rate(fitting) == pytest.approx(expected)


# ─── LabourTask arithmetic ───────────────────────────────────────────────────

def test_labour_task_rate_per_unit():
    task = LabourTask("t", n_elec=2, n_semi=2, n_gen=10, hours=18.0, base_qty=100.0, unit="m")
    assert task.labour_total() == 22500.0
    assert task.rate_per_unit() == 225.0


def test_labour_task_zero_base_qty_is_safe():
    task = LabourTask("t", 1, 0, 0, 1.0, 0.0, "each")
    assert task.rate_per_unit() == 0.0


# ─── Built-up rate assembly ──────────────────────────────────────────────────

def test_build_rate_applies_markup_and_addons():
    r = build_rate(material_cost=100.0, install_labour=50.0)
    # material × 1.30 = 130; add-ons on 130: 9% + 2% + 5% = 16% → 20.8
    assert r.material_supply == 130.0
    assert r.consumables == pytest.approx(11.7)
    assert r.transport == pytest.approx(2.6)
    assert r.waste == pytest.approx(6.5)
    assert r.supply_rate == pytest.approx(150.8)
    assert r.install_rate == 50.0
    assert r.combined_rate == pytest.approx(200.8)


def test_build_rate_can_skip_addons():
    r = build_rate(material_cost=100.0, install_labour=50.0, apply_addons_to_material=False)
    assert r.consumables == 0.0
    assert r.supply_rate == 130.0


def test_custom_params_change_result():
    params = RateParams(material_markup=1.5, consumables_pct=0.0, transport_pct=0.0, waste_pct=0.0)
    r = build_rate(material_cost=100.0, install_labour=0.0, params=params)
    assert r.supply_rate == 150.0


# ─── Point-method classification ─────────────────────────────────────────────

@pytest.mark.parametrize(
    "length,expected",
    [
        (0.5, PointClass.SHORT),
        (3.0, PointClass.SHORT),
        (3.01, PointClass.MEDIUM),
        (6.0, PointClass.MEDIUM),
        (6.01, PointClass.LONG),
        (10.0, PointClass.LONG),
        (10.01, PointClass.AXIS),
        (25.0, PointClass.AXIS),
    ],
)
def test_classify_point_bands(length, expected):
    assert classify_point(length) == expected


def test_routed_length_ceiling_drop_plus_run():
    # 3m ceiling, socket @0.5m, 4m horizontal → 2.5 + 4 = 6.5m
    assert routed_length(
        ceiling_height_m=3.0, mount_height_m=0.5, horizontal_run_m=4.0
    ) == 6.5


def test_routed_length_never_negative_drop():
    # mount above ceiling (nonsensical) clamps drop to 0
    assert routed_length(
        ceiling_height_m=3.0, mount_height_m=4.0, horizontal_run_m=2.0
    ) == 2.0


def test_average_length_per_point():
    assert average_length_per_point(100.0, 10) == 10.0


def test_average_length_per_point_zero_points_is_safe():
    assert average_length_per_point(100.0, 0) == 0.0


# ─── Determinism: identical inputs → identical outputs, repeatedly ──────────

def test_rates_are_deterministic_across_calls():
    runs = [cable_install_rate("50mm2") for _ in range(50)]
    assert len(set(runs)) == 1


def test_build_rate_is_deterministic():
    a = build_rate(material_cost=938.0, install_labour=200.0)
    b = build_rate(material_cost=938.0, install_labour=200.0)
    assert a == b


# ─── DB build-up (issue 004) ─────────────────────────────────────────

def test_db_build_up_prices_the_contents_not_just_the_enclosure():
    from core.rate_model import db_build_up
    empty = db_build_up(ways=12, phases=3, main_breaker_a=0, circuits=[])
    full = db_build_up(ways=24, phases=3, main_breaker_a=250,
                       circuits=[(20, 1)] * 18 + [(32, 3)] * 2, elcb=True, surge=True)
    assert full.combined_rate > 5 * empty.combined_rate
    assert full.install_rate > empty.install_rate            # more ways → more labour


def test_db_build_up_is_monotonic_and_deterministic():
    from core.rate_model import db_build_up
    base = dict(ways=18, phases=3, main_breaker_a=100, circuits=[(20, 1)] * 12)
    a = db_build_up(**base).combined_rate
    assert db_build_up(**base, surge=True).combined_rate > a
    assert db_build_up(**base, elcb=True).combined_rate > a
    assert db_build_up(**base, floor_standing=True).combined_rate > a
    assert db_build_up(**base).combined_rate == a


def test_every_earth_size_the_rule_can_choose_has_a_price():
    """Audit finding on a real SLD: 35/70 mm² BCEW supply lines were priced at R0."""
    from core import constants
    from core.rate_model import earth_size_for
    for cable in (4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150):
        e = earth_size_for(cable)
        key = f"earth_wire_{int(e)}mm2" if float(e).is_integer() else f"earth_wire_{e}mm2"
        assert constants.CABLE_PRICES.get(key, 0) > 0, key


# ─── Board build-up: what an SLD shows on big / motor-control boards ─────────

def _db(**kw):
    from core.rate_model import db_build_up
    base = dict(ways=24, phases=3, main_breaker_a=100, circuits=[(20, 1)] * 20)
    base.update(kw)
    return db_build_up(**base).combined_rate


def test_motor_starters_isolators_and_master_switch_are_priced():
    plain = _db()
    assert _db(motor_starters=4) > plain + 4 * 4000          # a DOL starter is thousands, not a breaker
    assert _db(isolators=3) > plain
    assert _db(master_switch=True) > plain


def test_breakers_above_63a_are_priced_as_mccbs():
    small = _db(circuits=[(63, 3)])
    big = _db(circuits=[(160, 3)])
    assert big - small > 3000


def test_three_pole_ways_cost_more_than_single_pole():
    assert _db(circuits=[(32, 3)] * 10) > _db(circuits=[(32, 1)] * 10) + 2000


def test_large_boards_are_floor_standing_panels():
    wall = _db(ways=48, main_breaker_a=160)
    assert _db(ways=55, main_breaker_a=160) > wall + 8000        # more than 48 ways
    assert _db(ways=48, main_breaker_a=300) > wall + 8000        # 200 A and up


def test_trench_is_built_up_not_a_flat_guess():
    from core.rate_model import trench_build_up
    r = trench_build_up()
    assert 400 <= r.combined_rate <= 900                          # SA market band for 450 x 650 with reinstatement
    assert r.install_rate > 0 and r.supply_rate > 0               # labour (dig/backfill) and material (sand)
