"""Pairing a PDF page with the CAD sheet it is a print of — by the words both show."""

from agent.shared.sheets import pair_sheets, sheet_words


def test_words_keep_names_and_joined_drawing_codes():
    w = set(sheet_words(["TUCK SHOP  WD-AB-01", "L1", "db-ab1 400V"]))
    assert {"TUCK", "SHOP", "WDAB01", "DBAB1", "400V"} <= w
    assert "L1" not in w                       # too short to tell sheets apart


def test_each_page_goes_to_the_sheet_sharing_its_rarer_words():
    legend = ["LEGEND", "DOWNLIGHT", "SOCKET", "SWITCH", "NOTES"]
    cad = {
        "AB-LIGHTING": legend + ["ABLUTION", "BLOCK", "LIGHTING", "LAYOUT", "WDAB01"],
        "AB-PLUG": legend + ["ABLUTION", "BLOCK", "PLUG", "LAYOUT", "WDAB01"],
        "HALL-LIGHTING": legend + ["COMMUNITY", "HALL", "LIGHTING", "LAYOUT", "WDECH01"],
    }
    pdf = {
        "set p0": legend + ["COMMUNITY", "HALL", "LIGHTING", "LAYOUT", "WDECH01"],
        "set p1": legend + ["ABLUTION", "BLOCK", "PLUG", "LAYOUT", "WDAB01"],
        "set p2": legend + ["ABLUTION", "BLOCK", "LIGHTING", "LAYOUT", "WDAB01"],
    }
    assert pair_sheets(cad, pdf) == {"set p0": "HALL-LIGHTING", "set p1": "AB-PLUG", "set p2": "AB-LIGHTING"}


def test_a_sheet_is_used_once_so_look_alike_pages_resolve():
    same = ["GUARD", "HOUSE", "LAYOUT", "WDLGH01"]
    cad = {"LGH-LIGHTING": same + ["LIGHTING"], "LGH-PLUG": same}
    pdf = {"p4": same + ["LIGHTING"], "p5": same}
    assert pair_sheets(cad, pdf) == {"p4": "LGH-LIGHTING", "p5": "LGH-PLUG"}


def test_a_page_with_no_text_or_no_real_match_stays_unpaired():
    cad = {"A": ["ABLUTION", "BLOCK", "WDAB01"]}
    pdf = {"scan": [], "other": ["SWIMMING", "POOL", "PUMP", "ROOM"]}
    assert pair_sheets(cad, pdf) == {}
