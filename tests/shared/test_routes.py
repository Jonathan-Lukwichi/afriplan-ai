"""Route-network measurement (issue 002): pure geometry shared by both pipelines."""
import math

import pytest

from agent.shared.routes import (
    Box, Label, Seg, build_route_network, equipment_key, parse_tag,
)

H = 2.0  # tag text height (drawing units)


def _site(scale: float = 1.0, labels=()):
    """
    Two boards joined by a dashed route, plus a branch to a third board:

        DB-A box (0..4, 0..2) ── (4,1)→(50,1)→(50,40)→(100,40)→(102,40)→(102,2) ── DB-B box (100..104, 0..2)
                                          └ T at (50,20) → (80,20) ── DB-C box (80..84, 19..21)
    """
    s = scale
    segs = [
        Seg(4 * s, 1 * s, 50 * s, 1 * s),
        Seg(50 * s, 1 * s, 50 * s, 40 * s),
        Seg(50 * s, 40 * s, 102 * s, 40 * s),
        Seg(102.3 * s, 40 * s, 102 * s, 2 * s),        # 0.3 gap at the corner: snapped
        Seg(50 * s, 20 * s, 80 * s, 20 * s),            # T-junction onto the vertical run
    ]
    boxes = [Box(0, 0, 4 * s, 2 * s), Box(100 * s, 0, 104 * s, 2 * s), Box(80 * s, 19 * s, 84 * s, 21 * s)]
    tags = [
        Label("DB-A", -2 * s, 6 * s, H * s),
        Label("DB-B Fed from DB-A", 108 * s, 6 * s, H * s),
        Label("DB-C fed from DB-A", 86 * s, 24 * s, H * s),
    ]
    return segs, [*tags, *labels], boxes


def test_equipment_keys_ignore_spacing_and_hyphens():
    assert equipment_key("DB-1") == equipment_key("DB1") == equipment_key("db 1")
    assert equipment_key("Existing Mini sub") == equipment_key("MINI-SUB") == "MINISUB"
    assert equipment_key("Kiosk") == "KIOSK"


def test_parse_tag_reads_name_and_source():
    assert parse_tag("DB-AB1 Fed from DB-PFA") == ("DBAB1", "DBPFA")
    assert parse_tag("DB1-fed from DB-CR") == ("DB1", "DBCR")
    assert parse_tag("Existing Mini sub") == ("MINISUB", None)
    assert parse_tag("50m") is None
    assert parse_tag("Parking") is None


def test_route_length_follows_the_drawn_path():
    net = build_route_network(*_site(), units_per_m=1.0)
    assert net.found
    r = net.route("DB-A", "DB-B")
    # 46 + 39 + 52 + 38 (+0.3 snapped gap is not counted twice)
    assert r is not None
    assert r.length_m == pytest.approx(46 + 39 + 52.3 + 38, abs=0.5)


def test_t_junction_branch_is_routable():
    net = build_route_network(*_site(), units_per_m=1.0)
    r = net.route("DB-A", "DB-C")
    assert r is not None
    assert r.length_m == pytest.approx(46 + 19 + 30, abs=0.5)


def test_fed_from_tags_are_recorded():
    net = build_route_network(*_site(), units_per_m=1.0)
    assert net.fed_from == {"DBB": "DBA", "DBC": "DBA"}


def test_unknown_equipment_has_no_route():
    net = build_route_network(*_site(), units_per_m=1.0)
    assert net.route("DB-A", "DB-Z") is None


def test_scale_calibrated_from_length_labels_and_snapped_to_a_decade():
    # drawn in millimetres; the designer wrote metres next to the runs
    labels = [Label("46m", 27_000, 3_000, H * 1000), Label("39m", 52_000, 20_000, H * 1000),
              Label("52m", 76_000, 42_000, H * 1000)]
    net = build_route_network(*_site(scale=1000.0, labels=labels), snap_decade=True)
    assert net.units_per_m == pytest.approx(1000.0)
    assert "label" in net.scale_source
    r = net.route("DBA", "DBB")
    assert r.length_m == pytest.approx(175.3, abs=0.5)


def test_stated_length_sums_the_labels_along_the_path():
    labels = [Label("50m", 27, 3, H), Label("40m", 52, 30, H), Label("55m", 76, 42, H), Label("40m", 104, 20, H)]
    net = build_route_network(*_site(labels=labels), units_per_m=1.0)
    assert net.route("DB-A", "DB-B").stated_m == pytest.approx(185.0)
    # DB-C's branch carries no label of its own → only labels on its path count
    assert net.route("DB-A", "DB-C").stated_m == pytest.approx(50.0)


def test_a_drawing_without_fed_from_tags_is_not_a_site_route_network():
    segs, labels, boxes = _site()
    plain = [Label("DB-A", 0, 5, H), Label("DB-B", 100, 5, H)]
    net = build_route_network(segs, plain, boxes, units_per_m=1.0)
    assert not net.found


def test_a_tag_nearly_equidistant_from_two_symbols_is_flagged():
    segs, labels, boxes = _site()
    # DB-C's tag moved to sit between DB-B's and DB-C's symbols
    labels = [lb if not lb.text.startswith("DB-C") else Label(lb.text, 92, 10, H) for lb in labels]
    net = build_route_network(segs, labels, boxes, units_per_m=1.0)
    assert any("about as close" in w for w in net.warnings)
    assert not any("about as close" in w for w in build_route_network(*_site(), units_per_m=1.0).warnings)


def _dashed(points, dash=3.0, gap=2.0):
    """Plot a polyline the way a CAD plotter draws a dashed linetype: separate short strokes."""
    out, carry = [], 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        t = carry
        while t < L:
            end = min(t + dash, L)
            out.append(Seg(x1 + ux * t, y1 + uy * t, x1 + ux * end, y1 + uy * end))
            t += dash + gap
        carry = t - L
    return out


def test_dashes_plotted_as_separate_strokes_are_rebuilt_into_the_route():
    from agent.shared.routes import join_dashes
    strokes = _dashed([(0, 0), (60, 0), (60, 40)])
    joined = join_dashes(strokes, max_gap=4.0)
    total = sum(math.hypot(s.x2 - s.x1, s.y2 - s.y1) for s in joined)
    assert total == pytest.approx(100, abs=5)                    # dashes + gaps ≈ the drawn run


def test_side_by_side_hatch_strokes_are_not_a_route():
    from agent.shared.routes import join_dashes
    hatch = [Seg(0, y, 3, y) for y in range(0, 20, 2)]           # parallel strokes, 2 apart
    assert join_dashes(hatch, max_gap=4.0) == []


def test_edges_on_a_path_are_reported_for_trench_union():
    net = build_route_network(*_site(), units_per_m=1.0)
    ab = net.route("DB-A", "DB-B")
    ac = net.route("DB-A", "DB-C")
    shared = ab.edges & ac.edges
    assert shared                                     # the first run and part of the riser
    union_m = net.length_of(ab.edges | ac.edges)
    assert union_m == pytest.approx(ab.length_m + 30, abs=0.5)   # branch adds only its own 30 m
