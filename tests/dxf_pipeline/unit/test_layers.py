"""Unit tests for layer-name normalisation."""

from core.layer_aliases import is_electrical_layer, normalise_layer


def test_lighting_layer_is_electrical():
    assert is_electrical_layer("ELEC_LIGHTING")
    assert is_electrical_layer("E-Lights")
    assert is_electrical_layer("Lighting Plan")


def test_power_layer_is_electrical():
    assert is_electrical_layer("ELEC_POWER")
    assert is_electrical_layer("Power Outlets")


def test_db_layer_is_electrical():
    assert is_electrical_layer("ELEC_DB")
    assert is_electrical_layer("MSB-A")


def test_pdf_text_layer_is_recognised():
    """Layer carries circuit labels even though name doesn't say 'electrical'."""
    assert is_electrical_layer("PDF_TEXT")


def test_architectural_layer_not_electrical():
    assert not is_electrical_layer("A-WALL")
    assert not is_electrical_layer("S-COLUMNS")
    assert not is_electrical_layer("0")


def test_normalise_strips_prefixes():
    assert normalise_layer("PDF_ELEC_LIGHTING") == "ELEC LIGHTING"
    assert normalise_layer("B_ELEC_POWER")     == "ELEC POWER"
