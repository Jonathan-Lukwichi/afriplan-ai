"""The fixed item list: bill-style names, and older spellings still found (names saved earlier)."""

from agent.shared.symbol_catalogue import CATALOGUE, canonical_name, catalogue_item


def test_names_use_the_spelling_bills_use():
    assert "Vapour Proof Light" in CATALOGUE and "Vapour-Proof Light" not in CATALOGUE


def test_an_older_spelling_still_finds_the_item():
    assert canonical_name("Vapour-Proof Light") == "Vapour Proof Light"
    assert catalogue_item("Vapour-Proof Light") is CATALOGUE["Vapour Proof Light"]
    assert canonical_name("vapour proof light") == "Vapour Proof Light"


def test_unknown_names_stay_unknown():
    assert catalogue_item("Magic lamp") is None and canonical_name("Magic lamp") == "Magic lamp"
