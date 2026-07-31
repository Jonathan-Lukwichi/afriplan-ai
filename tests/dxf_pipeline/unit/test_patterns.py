"""Unit tests for the DXF block-name pattern dictionary."""

from agent.dxf_pipeline.patterns import classify_block_name, FixtureCategory


def test_exact_match_lowercase():
    spec = classify_block_name("DL")
    assert spec is not None
    assert spec.canonical_name == "LED Downlight"
    assert spec.category == FixtureCategory.LIGHTING


def test_exact_match_with_trailing_digits():
    """DL_001 should still resolve to DL."""
    spec = classify_block_name("DL_001")
    assert spec is not None
    assert spec.canonical_name == "LED Downlight"


def test_exact_match_with_dash_and_digits():
    spec = classify_block_name("DS-12")
    assert spec is not None
    assert spec.canonical_name == "Double Socket"


def test_skip_pattern_for_walls_and_doors():
    assert classify_block_name("Wall_007") is None
    assert classify_block_name("Door_001") is None
    assert classify_block_name("Window_003") is None


def test_skip_furniture():
    assert classify_block_name("workstation_basic") is None
    assert classify_block_name("Cabinet_42") is None


def test_regex_fallback_socket_outlet_2_gang():
    spec = classify_block_name("Socket Outlet 2 Gangs 23")
    assert spec is not None
    assert spec.canonical_name == "Double Socket Outlet"


def test_regex_fallback_distribution_board():
    spec = classify_block_name("Distribution Board Main")
    assert spec is not None
    assert spec.category == FixtureCategory.DISTRIBUTION


def test_unknown_block_returns_none():
    assert classify_block_name("Some_Custom_Thing_42") is None
    assert classify_block_name("ZZZZZ") is None


def test_empty_or_whitespace_returns_none():
    assert classify_block_name("") is None
    assert classify_block_name("   ") is None


def test_all_canonical_names_have_nonzero_default_price():
    """Sanity: any spec we use for pricing should have a default price."""
    from agent.dxf_pipeline.patterns import EXACT_BLOCK_MAP, REGEX_BLOCK_PATTERNS

    for spec in EXACT_BLOCK_MAP.values():
        assert spec.default_unit_price_zar > 0, f"{spec.canonical_name} has zero price"
    for _, spec in REGEX_BLOCK_PATTERNS:
        assert spec.default_unit_price_zar > 0, f"{spec.canonical_name} has zero price"


def test_categories_are_disjoint_per_spec():
    """A canonical name should map to exactly one category in EXACT_BLOCK_MAP."""
    from agent.dxf_pipeline.patterns import EXACT_BLOCK_MAP
    by_name: dict[str, FixtureCategory] = {}
    for spec in EXACT_BLOCK_MAP.values():
        if spec.canonical_name in by_name:
            assert by_name[spec.canonical_name] == spec.category, (
                f"{spec.canonical_name} mapped to two categories"
            )
        else:
            by_name[spec.canonical_name] = spec.category
