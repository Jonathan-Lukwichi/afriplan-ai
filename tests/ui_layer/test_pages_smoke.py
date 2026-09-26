"""Headless smoke tests: every page renders without an exception (Streamlit AppTest)."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from agent.shared import BillOfQuantities, BQLineItem, BQSection, ContractorProfile, LineKind  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _page(name: str) -> AppTest:
    return AppTest.from_file(str(ROOT / "pages" / name), default_timeout=60)


@pytest.mark.parametrize("name", ["0_Welcome.py", "1_Upload.py", "2_Extraction.py",
                                  "3_BOQ_Generation.py", "4_Live_Pricing.py", "5_Audit_BOQ.py"])
def test_page_renders_without_session(name):
    at = _page(name).run()
    assert not at.exception, [e.value for e in at.exception]


def _bill() -> BillOfQuantities:
    return BillOfQuantities(pipeline="dxf", project_name="Test Hall", run_id="abc123", line_items=[
        BQLineItem(item_no=1, section=BQSection.POWER_OUTLETS, description="Double Socket — Office",
                   unit="No", qty=6, unit_price_zar=400, total_zar=2400),
        BQLineItem(item_no=1, section=BQSection.SUBMAIN_CABLES, description="Supply 16mm² x4C SWA feeder A→B",
                   unit="m", qty=30, unit_price_zar=300, total_zar=9000, line_kind=LineKind.SUPPLY),
    ], contractor_markup_pct=0.0)


def test_boq_page_renders_with_a_bill_audit_and_completion():
    at = _page("3_BOQ_Generation.py")
    at.session_state["dxf_view"] = {"state": "passed", "boq": _bill(), "raw_run": None}
    at.session_state["contractor_profile"] = ContractorProfile()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    labels = " ".join(e.label for e in at.expander)
    assert "BOQ audit" in labels
    assert at.number_input(key="boq_markup").value == 0.0      # markup not applied twice
