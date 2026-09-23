"""ItemKey taxonomy — one identity for a BOQ item, whoever wrote the description."""

import pytest

from evaluation.taxonomy import BILL_SECTION_OF, ItemKey, classify_item, line_role

SWA95 = "95mm2 x 4C PVC SWA PVC 600-1000V Cable"


@pytest.mark.parametrize("desc,parent,unit,expected", [
    # ── reference bill (Wedela) ──
    ("Supply", SWA95, "m", ("swa_cable", "95mm2|4c")),
    ("Install", "4mm2 x 3C PVC SWA PVC 600-1000V Cable", "m", ("swa_cable", "4mm2|3c")),
    ("Supply", SWA95, "Ea", ("termination", "95mm2")),              # same parent, unit Ea
    ("Supply", "35mm2 BCEW ", "m", ("bcew", "35mm2")),
    ("Install", "35mm2 BCEW ", "Ea", ("termination", "bcew|35mm2")),
    ("Supply", "95 sq. mm 5 core ABC cable.", "m", ("abc_cable", "95mm2|5c")),
    ("Supply", "2.5mm2 x 3C Surfix Cable", "m", ("surfix", "2.5mm2|3c")),
    ("Trenching and re-instatement for 450mm x 650mm measured in linear length.", "", "m", ("trench", "")),
    ("Supply and installation of plastic Warning tape, 300 mm above cables.", "", "m", ("warning_tape", "")),
    ("110 mm diameter flexible PVC cable sleeves.", "", "m", ("sleeve", "110mm")),
    ("75 mm diameter flexible PVC cable sleeves.( Future fibre)", "", "m", ("sleeve", "75mm")),
    ("Manhole complete with cover (Electrical)", "", "Ea", ("manhole", "electrical")),
    ("Main DB 1:  3 phase+N+E, 15 kA ,400 VAC ,1.6 mm thick , mild steel", "", "Sum", ("db", "")),
    ("DB CR:  3 phase+N+E, 6 kA ,400 VAC", "", "Sum", ("db", "")),
    # a DB description naming its incomer is still a DB, not a breaker
    ("DB PFA:  3 phase+N+E, 6 kA ,400 VAC , mild steel, Incomer to be MCCB 160A", "", "Sum", ("db", "")),
    ("Main DB 1:  3 phase+N+E, 15 kA, Incomer to be MCCB 150A, Type 2 Surge Arrestors", "", "Sum", ("db", "")),
    ("DB-ST:  1 phase+N+E, 6 kA ,230 VAC", "", "Sum", ("db", "")),
    # a meter installed in the kiosk is a meter, not the kiosk
    ("Energy meter installed in kiosk", "", "Ea", ("meter", "")),
    ("Mini-substation / LV kiosk supply & install", "", "Sum", ("kiosk", "")),
    ("75 mm Galvanised conduit 6 meter", "", "Ea", ("other", "")),     # 'meter' as a length unit
    # a trench that mentions the kiosk is still a trench
    ("Trenching and re-instatement for 450 mm x 600mm measured in linear length on each end "
     "of the line from pole to Mini-sub and Pole to Kiosk", "", "m", ("trench", "")),
    ("150mm medium duty cable tray ", "", "m", ("cable_tray", "150mm")),
    ("P8000 Trunking Covers", "", "m", ("trunking_cover", "p8000")),
    ("P8000 Trunking including mounting accessories (treaded rods)", "", "m", ("trunking", "p8000")),
    ("P9000 Trunking Horizontal Bend", "", "No", ("trunking_bend", "p9000")),
    ("P8000 Trunking T-Piece", "", "No", ("trunking_tee", "p8000")),
    ("PVC Round Box complete with cover and scews", "", "No", ("round_box", "")),
    ("5 Amp round plug 3 pins", "", "No", ("plug_top", "5a")),
    ("1.5mm2 GP wire Black", "", "m", ("gp_wire", "1.5mm2")),
    ("4mm2 GP wire Red Black", "", "m", ("gp_wire", "4mm2")),
    ("1.5 mm2 BCEW ", "", "m", ("bcew", "1.5mm2")),
    ("WHITE, 100X100, 16 Ampere, standard 3 pin flush mounted, double switched socket outlet", "", "No", ("socket_double", "")),
    ("WHITE, 100X50 ,30 Ampere, double pole isolator for Aircons", "", "No", ("isolator", "")),
    ("100x100 Wall box", "", "No", ("wall_box", "100x100")),
    ("100 x 50 mm Wall box", "", "No", ("wall_box", "100x50")),
    ("100x100 Extension box steel white", "", "No", ("extension_box", "")),
    ("Waterproof box", "", "No", ("waterproof_box", "")),
    ("Chasing for 4 m (height) for 20 mm conduit", "", "No", ("chasing", "4m|20mm")),
    ("Chasing 1m x1m (rate only)", "", "No", ("chasing", "1mx1m")),
    ("20mm diameter PVC conduits with accessories", "", "m", ("conduit", "20mm")),
    ("20 mm dia PVC conduit", "", "m", ("conduit", "20mm")),
    ("20mm Galvanised conduit", "", "m", ("conduit", "20mm|galv")),
    ("Draw wires ( 5kg)", "", "Ea", ("draw_wire", "")),
    ("600x1200 Recessed 3x18watt Led fluorescent light complete with Diffuser", "", "No", ("light_panel", "")),
    ("30watt led flood light", "", "No", ("light_flood", "")),
    ("2x600W LED flood light, 10m post", "", "No", ("light_highmast", "")),
    ("100W LED Solar power light post lantern", "", "No", ("light_solar_post", "")),
    ("2x24watt double vapor proof led fluorescent light", "", "No", ("light_vapour_proof", "")),
    ("24W Bulkhead Light Outdoor", "", "No", ("light_bulkhead", "")),
    ("1 Lever light switch 1 way", "", "No", ("switch", "1lever|1way")),
    ("1 Lever light switch 2 way", "", "No", ("switch", "1lever|2way")),
    ("Day Night switch", "", "No", ("day_night_switch", "")),
    ("Suply,storage, install and commission Kiosk", "", "Each", ("kiosk", "")),
    ("Supply and install conrete plinth", "", "Each", ("plinth", "")),
    ("Supply, deliver ,storage and install MCB/MCCB 250 A, 415VAC , 15kA at minisub", "", "ea", ("breaker", "250a")),
    ("Connection Fees", "", "Sum", ("connection_fee", "")),
    ("Certificate of Compliace", "", "Ea", ("coc", "")),
    # ── PDF pipeline output ──
    ("Supply 95mm² x4C SWA feeder MSB→DB1", "", "m", ("swa_cable", "95mm2|4c")),
    ("Install 16mm² BCEW earth", "", "m", ("bcew", "16mm2")),
    ("Terminate 50mm² SWA (both ends)", "", "Ea", ("termination", "50mm2")),
    ("Trench 600mm for MSB→DB1", "", "m", ("trench", "")),
    ("Warning tape 300mm above cable", "", "m", ("warning_tape", "")),
    ("16A double switched socket — Office", "", "No", ("socket_double", "")),
    ("1-lever 1-way switch", "", "No", ("switch", "1lever|1way")),
    ("600x1200 recessed 3x18W LED panel — Hall", "", "No", ("light_panel", "")),
    ("DB-CR: 3ph 150A, 12-way, wall mounted", "", "Sum", ("db", "")),
    # pipeline reticulation = the bill's GP wire (route m vs conductor m: qty will differ, visibly)
    ("1.5mm2 lighting reticulation wire — Hall", "", "m", ("gp_wire", "1.5mm2")),
    # ── DXF pipeline output ──
    ("Double Socket — wc", "", "No", ("socket_double", "")),
    ("LED Downlight", "", "No", ("light_downlight", "")),
    ("2-Lever Switch", "", "No", ("switch", "2lever|1way")),
    ("Isolator Switch", "", "No", ("isolator", "")),
    ("Fire Extinguisher", "", "No", ("fire_extinguisher", "")),
    ("Distribution Board (template-matched)", "", "No", ("db", "")),
])
def test_classify_item(desc, parent, unit, expected):
    assert classify_item(desc, parent=parent, unit=unit) == ItemKey(*expected)


def test_unknown_text_is_other():
    assert classify_item("Contractor handling fee").family == "other"


@pytest.mark.parametrize("desc,role", [
    ("Supply", "supply"), ("  Install ", "install"),
    ("Supply 95mm² x4C SWA feeder", "supply"), ("Install 16mm² BCEW earth", "install"),
    ("Supply and installation of plastic Warning tape", "combined"),
    ("Supply and install conrete plinth", "combined"),
    ("Chasing for 4 m", "combined"),
])
def test_line_role(desc, role):
    assert line_role(desc) == role


def test_every_family_has_a_bill_section():
    for fam in ["swa_cable", "db", "trunking", "gp_wire", "socket_double", "chasing",
                "conduit", "light_panel", "switch", "kiosk", "other"]:
        assert BILL_SECTION_OF[fam] in {"A", "B", "C", "D", "F", "X"}
