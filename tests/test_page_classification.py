"""
Tests for deterministic page classification.

Tests KeywordClassifier and classify_pages functions.
"""

import pytest
from agent.parsers.keyword_classifier import KeywordClassifier, PageType, ClassificationResult


@pytest.fixture
def classifier():
    """Create a KeywordClassifier instance."""
    return KeywordClassifier()


class TestKeywordClassifier:
    """Tests for KeywordClassifier."""

    def test_sld_detection_by_drawing_number(self, classifier):
        """SLD pages should be detected from drawing number pattern."""
        result = classifier.classify("", drawing_number="WD-AB-01-SLD")
        assert result.page_type == PageType.SLD
        assert result.confidence >= 0.4

    def test_sld_detection_by_keywords(self, classifier):
        """SLD pages should be detected from schedule keywords."""
        text = """
        DB-GF CIRCUIT SCHEDULE
        CIRCUIT NO  WATTAGE  WIRE SIZE  BREAKER
        L1          198W     1.5mm²     10A
        P1          3680W    2.5mm²     20A
        """
        result = classifier.classify(text)
        assert result.page_type == PageType.SLD

    def test_sld_detection_by_db_reference(self, classifier):
        """SLD pages should be detected from DB references."""
        text = "Distribution Board DB-S1 Main Breaker 63A"
        result = classifier.classify(text)
        assert result.page_type == PageType.SLD

    def test_lighting_layout_detection(self, classifier):
        """Lighting layouts should be detected."""
        result = classifier.classify(
            "LIGHTING LAYOUT - GROUND FLOOR\ndownlight LED panel bulkhead"
        )
        assert result.page_type == PageType.LAYOUT_LIGHTING

    def test_lighting_layout_by_drawing_number(self, classifier):
        """Lighting layouts should be detected from drawing number."""
        result = classifier.classify("", drawing_number="TJM-E-01-LIGHTING")
        assert result.page_type == PageType.LAYOUT_LIGHTING
        assert result.confidence >= 0.4

    def test_plugs_layout_detection(self, classifier):
        """Power layouts should be detected."""
        result = classifier.classify(
            "PLUGS LAYOUT\ndouble socket @300mm floor box data point"
        )
        assert result.page_type == PageType.LAYOUT_PLUGS

    def test_plugs_layout_by_drawing_number(self, classifier):
        """Power layouts should be detected from drawing number."""
        result = classifier.classify("", drawing_number="WD-AB-02-PLUGS")
        assert result.page_type == PageType.LAYOUT_PLUGS

    def test_register_detection(self, classifier):
        """Drawing register should be detected."""
        result = classifier.classify(
            "DRAWING REGISTER\nPROJECT: NewMark Office Building\nCLIENT: ABC Corporation"
        )
        assert result.page_type == PageType.REGISTER

    def test_register_detection_by_table_headers(self, classifier):
        """Register should be detected from typical table headers."""
        # Need all keywords: drwg no, title, rev, date (match_type="all")
        text = "DRAWING REGISTER\nDRWG NO  TITLE  REV  DATE\n01  Cover  A  2024"
        result = classifier.classify(text)
        assert result.page_type == PageType.REGISTER

    def test_outside_lights_detection(self, classifier):
        """Outside lights pages should be detected."""
        result = classifier.classify(
            "OUTSIDE LIGHTS LAYOUT\npole light bollard boundary fence line"
        )
        assert result.page_type == PageType.OUTSIDE_LIGHTS

    def test_negative_rules_reduce_confidence(self, classifier):
        """Non-electrical pages should have reduced confidence."""
        result = classifier.classify(
            "ARCHITECTURAL FLOOR PLAN\nstructural detail plumbing layout"
        )
        # Should be low confidence or unknown
        assert result.confidence < 0.5 or result.page_type == PageType.UNKNOWN

    def test_unknown_for_generic_text(self, classifier):
        """Generic text should result in UNKNOWN or low confidence."""
        result = classifier.classify("This is some random text with no keywords.")
        assert result.confidence < 0.3 or result.page_type == PageType.UNKNOWN

    def test_drawing_number_extraction(self, classifier):
        """Drawing number should be extracted from text."""
        result = classifier.classify("DWG NO: WD-AB-01-SLD")
        assert result.drawing_number != ""

    def test_building_block_detection(self, classifier):
        """Building block should be detected from known patterns."""
        result = classifier.classify("WD-AB-01-SLD Ablution Retail Block")
        assert result.building_block != ""

    def test_matched_rules_recorded(self, classifier):
        """Matched rules should be recorded in result."""
        result = classifier.classify("LIGHTING LAYOUT downlight")
        assert len(result.matched_rules) > 0

    def test_keyword_scores_recorded(self, classifier):
        """Keyword scores should be recorded."""
        result = classifier.classify("CIRCUIT SCHEDULE breaker mcb")
        assert len(result.keyword_scores) > 0


class TestClassifyPages:
    """Tests for classify_pages module functions."""

    def test_import_classify_pages(self):
        """Should be able to import classify_pages functions."""
        from agent.stages.classify_pages import (
            classify_pages_from_list,
            classify_service_tier,
            get_classification_summary,
        )
        assert callable(classify_pages_from_list)
        assert callable(classify_service_tier)
        assert callable(get_classification_summary)

    def test_classify_service_tier_residential(self):
        """Should detect residential tier from keywords."""
        from agent.stages.classify_pages import classify_service_tier
        from agent.models import ServiceTier

        # Mock categories with residential keywords
        class MockPage:
            def __init__(self, text):
                self.text_content = text

        categories = {
            "Cover": [MockPage("RESIDENTIAL HOUSE 3 bedroom bathroom kitchen")],
            "SLD": [],
            "Lighting": [],
            "Power": [],
            "Other": [],
        }

        tier = classify_service_tier(categories)
        assert tier == ServiceTier.RESIDENTIAL

    def test_classify_service_tier_commercial(self):
        """Should detect commercial tier from keywords."""
        from agent.stages.classify_pages import classify_service_tier
        from agent.models import ServiceTier

        class MockPage:
            def __init__(self, text):
                self.text_content = text

        categories = {
            "Cover": [MockPage("OFFICE BUILDING reception boardroom suite")],
            "SLD": [],
            "Lighting": [],
            "Power": [],
            "Other": [],
        }

        tier = classify_service_tier(categories)
        assert tier == ServiceTier.COMMERCIAL

    def test_classification_summary(self):
        """Should generate correct summary statistics."""
        from agent.stages.classify_pages import get_classification_summary

        class MockPage:
            def __init__(self, page_num, conf):
                self.page_number = page_num
                self.classification_confidence = conf

        categories = {
            "Cover": [MockPage(1, 0.8)],
            "SLD": [MockPage(2, 0.9), MockPage(3, 0.85)],
            "Lighting": [MockPage(4, 0.7)],
            "Power": [MockPage(5, 0.3)],  # Low confidence
            "Other": [],
        }

        summary = get_classification_summary(categories)

        assert summary.total_pages == 5
        assert summary.cover_pages == 1
        assert summary.sld_pages == 2
        assert summary.lighting_pages == 1
        assert summary.power_pages == 1
        assert summary.other_pages == 0
        assert 5 in summary.low_confidence_pages  # Page 5 has low confidence
