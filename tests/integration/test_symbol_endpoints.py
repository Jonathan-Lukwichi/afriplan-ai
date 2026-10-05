"""ADR-0007 — a person confirms or corrects a symbol name; it is remembered and wins over the AI."""
from fastapi.testclient import TestClient

from db.symbol_names import load_symbol_names, save_symbol_name
from main import app

client = TestClient(app)


def test_choices_are_the_fixed_catalogue():
    choices = client.get("/api/symbols/choices").json()["choices"]
    assert "Vapour Proof Light" in choices and "Not an electrical symbol" in choices


def test_a_person_names_a_shape_and_the_ai_cannot_overwrite_it():
    r = client.put("/api/symbols/TESTSIG-1", json={"item": "Bulkhead Light"})
    assert r.status_code == 200
    save_symbol_name("TESTSIG-1", "LED Downlight", "ai")
    assert load_symbol_names()["TESTSIG-1"] == ("Bulkhead Light", "person")


def test_an_unknown_name_is_refused():
    assert client.put("/api/symbols/TESTSIG-2", json={"item": "Magic lamp"}).status_code == 400
