"""The layered BOQ network: which drawing carries the evidence for which item."""

from evaluation.network import (
    NETWORK,
    DrawingType as D,
    Method,
    missing_for,
    reproducible,
    reproducible_families,
    requirements_matrix,
)
from evaluation.taxonomy import FAMILIES


def test_every_taxonomy_family_has_a_node():
    assert set(FAMILIES) <= set(NETWORK)


def test_counted_items_need_their_layout():
    assert reproducible("socket_double", {D.PLUGS})
    assert not reproducible("socket_double", {D.LIGHTING})
    assert reproducible("light_panel", {D.LIGHTING})
    assert reproducible("db", {D.SLD}) and reproducible("db", {D.SCHEDULE})


def test_derived_items_follow_their_primary_evidence():
    assert NETWORK["wall_box"].method == Method.DERIVED
    assert reproducible("wall_box", {D.PLUGS})                 # from socket counts
    assert reproducible("termination", {D.SLD})                # 2 per feeder run
    assert not reproducible("termination", {D.LIGHTING})


def test_prelims_and_fees_are_never_drawing_derived():
    everything = set(D)
    assert not reproducible("prelims", everything)
    assert not reproducible("connection_fee", everything)
    assert NETWORK["connection_fee"].method == Method.PROVISIONAL


def test_reproducible_families_grows_with_uploads():
    few = reproducible_families({D.LIGHTING})
    more = reproducible_families({D.LIGHTING, D.PLUGS, D.SLD})
    assert few < more
    assert "light_panel" in few and "socket_double" not in few


def test_missing_for_names_the_drawing_to_request():
    need = missing_for(["socket_double", "db", "light_panel"], {D.LIGHTING})
    assert need == {D.PLUGS: ["socket_double"], D.SLD: ["db"]}


def test_requirements_matrix_is_human_readable():
    m = requirements_matrix()
    assert m["swa_cable"].startswith("length")
    assert "sld" in m["swa_cable"]
