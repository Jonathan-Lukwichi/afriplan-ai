"""
Unit tests for the deterministic (non-AI) extraction pipeline.

Tests cover:
- Parsers (keyword classifier, drawing number parser, table parser)
- Extractors (register, SLD, lighting layout, plugs layout)
- Stages (crop, merge)
- Pipeline orchestrator

Run with: pytest tests/test_deterministic_pipeline.py -v
"""

import pytest
from pathlib import Path
from typing import List

# Models
from agent.models import (
    PageType, PageClassification, PageRegions, BoundingBox,
    DocumentPage, PageExtractionResult, ProjectExtractionResult,
    RegisterExtraction, SLDExtraction, LayoutExtraction,
    ExtractionWarning, Severity, PipelineConfig, MergeStatistics,
)


# ============================================================================
# Keyword Classifier Tests
# ============================================================================

class TestKeywordClassifier:
    """Test the keyword-based page classifier."""

    def test_classifier_import(self):
        """Test that classifier can be imported."""
        from agent.parsers.keyword_classifier import KeywordClassifier
        classifier = KeywordClassifier()
        assert classifier is not None

    def test_classify_sld_page(self):
        """Test SLD page classification."""
        from agent.parsers.keyword_classifier import KeywordClassifier, PageType

        classifier = KeywordClassifier()

        sld_text = """
        SINGLE LINE DIAGRAM
        DB-GF DISTRIBUTION BOARD
        MAIN BREAKER 100A
        Circuit No | Description | Wattage | Wire Size
        L1 | Lighting Circuit 1 | 500W | 1.5mm²
        P1 | Power Circuit 1 | 2000W | 2.5mm²
        """

        result = classifier.classify(sld_text)
        assert result.page_type == PageType.SLD
        assert result.confidence >= 0.4

    def test_classify_lighting_layout(self):
        """Test lighting layout classification."""
        from agent.parsers.keyword_classifier import KeywordClassifier, PageType

        classifier = KeywordClassifier()

        lighting_text = """
        LIGHTING LAYOUT
        GROUND FLOOR
        LED Downlight 6W
        1-Lever Switch
        DB-S1 L1
        """

        result = classifier.classify(lighting_text)
        assert result.page_type == PageType.LAYOUT_LIGHTING
        assert result.confidence >= 0.3

    def test_classify_plugs_layout(self):
        """Test plugs layout classification."""
        from agent.parsers.keyword_classifier import KeywordClassifier, PageType

        classifier = KeywordClassifier()

        plugs_text = """
        PLUGS LAYOUT
        POWER OUTLET INSTALLATION
        Double Socket @300mm
        Double Socket @1100mm
        Floor Box
        CAT 6 Data Point
        """

        result = classifier.classify(plugs_text)
        assert result.page_type == PageType.LAYOUT_PLUGS
        assert result.confidence >= 0.3

    def test_classify_register(self):
        """Test drawing register classification."""
        from agent.parsers.keyword_classifier import KeywordClassifier, PageType

        classifier = KeywordClassifier()

        register_text = """
        DRAWING REGISTER
        Drwg No | Title | Rev | Date
        WD-AB-01-SLD | Single Line Diagram | A | 2025-01-15
        WD-AB-02-LIGHTING | Lighting Layout | B | 2025-01-16
        Project Name: WEDELA UPGRADE
        Client: ABC Construction
        """

        result = classifier.classify(register_text)
        assert result.page_type == PageType.REGISTER
        assert result.confidence >= 0.4


# ============================================================================
# Drawing Number Parser Tests
# ============================================================================

class TestDrawingNumberParser:
    """Test the drawing number parser."""

    def test_parser_import(self):
        """Test that parser can be imported."""
        from agent.parsers.drawing_number_parser import parse_drawing_number
        assert parse_drawing_number is not None

    def test_parse_standard_format(self):
        """Test parsing standard WD-AB-01-SLD format."""
        from agent.parsers.drawing_number_parser import parse_drawing_number

        result = parse_drawing_number("WD-AB-01-SLD")
        assert result.valid
        assert result.project_code == "WD"
        assert result.building_code == "AB"
        assert result.sequence_number == 1
        assert result.suggested_page_type == "sld"

    def test_parse_lighting_drawing(self):
        """Test parsing lighting drawing number."""
        from agent.parsers.drawing_number_parser import parse_drawing_number

        result = parse_drawing_number("WD-ECH-02-LIGHTING")
        assert result.valid
        assert result.building_code == "ECH"
        assert result.suggested_page_type == "layout_lighting"

    def test_extract_drawing_numbers(self):
        """Test extracting multiple drawing numbers from text."""
        from agent.parsers.drawing_number_parser import extract_drawing_numbers

        text = """
        Reference drawings:
        WD-AB-01-SLD for circuit schedule
        WD-AB-02-LIGHTING for lighting layout
        See also WD-AB-03-PLUGS
        """

        numbers = extract_drawing_numbers(text)
        assert len(numbers) >= 3
        assert "WD-AB-01-SLD" in numbers
        assert "WD-AB-02-LIGHTING" in numbers


# ============================================================================
# Table Parser Tests
# ============================================================================

class TestTableParser:
    """Test the table parser."""

    def test_parser_import(self):
        """Test that table parser can be imported."""
        from agent.parsers.table_parser import parse_table_text, extract_circuit_schedule
        assert parse_table_text is not None
        assert extract_circuit_schedule is not None

    def test_parse_circuit_schedule(self):
        """Test parsing circuit schedule from text."""
        from agent.parsers.table_parser import extract_circuit_schedule

        schedule_text = """
        L1 Lighting Circuit 1 500W 1.5mm² 10A
        L2 Lighting Circuit 2 400W 1.5mm² 10A
        P1 Power Circuit 1 2000W 2.5mm² 20A
        AC1 Air Con Unit 3000W 4mm² 32A
        """

        circuits = extract_circuit_schedule(schedule_text)
        assert len(circuits) >= 4

        # Check first circuit
        l1 = next((c for c in circuits if c.get('circuit_id') == 'L1'), None)
        assert l1 is not None
        assert l1.get('wattage') == '500'


# ============================================================================
# Register Extractor Tests
# ============================================================================

class TestRegisterExtractor:
    """Test the register extractor."""

    def test_extractor_import(self):
        """Test that extractor can be imported."""
        from agent.extractors.register_extractor import RegisterExtractor
        extractor = RegisterExtractor()
        assert extractor is not None

    def test_extract_project_info(self):
        """Test extracting project information."""
        from agent.extractors.register_extractor import RegisterExtractor

        extractor = RegisterExtractor()

        register_text = """
        PROJECT: THE UPGRADING OF WEDELA RETAIL CENTER
        CLIENT: ABC PROPERTY DEVELOPMENT
        CONSULTANT: CHONA MALANGA ENGINEERS

        DRAWING REGISTER
        Drwg No | Title | Rev
        WD-AB-01-SLD | Ablution Block SLD | A
        WD-AB-02-LIGHTING | Ablution Lighting | A
        """

        result = extractor.extract(register_text, page_number=1)
        assert result.project_name or len(result.rows) > 0
        # Check rows were extracted
        if result.rows:
            assert len(result.rows) >= 2


# ============================================================================
# SLD Extractor Tests
# ============================================================================

class TestSLDExtractor:
    """Test the SLD extractor."""

    def test_extractor_import(self):
        """Test that extractor can be imported."""
        from agent.extractors.sld_extractor import SLDExtractor
        extractor = SLDExtractor()
        assert extractor is not None

    def test_extract_db_info(self):
        """Test extracting distribution board info."""
        from agent.extractors.sld_extractor import SLDExtractor

        extractor = SLDExtractor()

        sld_text = """
        DISTRIBUTION BOARD: DB-GF
        MAIN BREAKER: 100A
        SUPPLY FROM: Kiosk Metering

        CIRCUIT SCHEDULE
        L1 Lighting 500W 1.5mm² 10A
        L2 Lighting 400W 1.5mm² 10A
        P1 Power 2000W 2.5mm² 20A
        """

        result = extractor.extract(sld_text, page_number=1)
        assert result.db_name or result.main_breaker_a > 0 or len(result.circuits) > 0

    def test_extract_circuits(self):
        """Test extracting circuit rows."""
        from agent.extractors.sld_extractor import SLDExtractor

        extractor = SLDExtractor()

        sld_text = """
        L1 Bedroom 1 Lights 6pts 360W 1.5mm² 10A
        L2 Kitchen Lights 4pts 240W 1.5mm² 10A
        P1 Bedroom 1 Plugs 4pts 1000W 2.5mm² 20A
        AC1 Aircon 3000W 4mm² 32A
        ISO1 Geyser 20A
        SPARE
        """

        result = extractor.extract(sld_text, page_number=1)
        assert len(result.circuits) >= 4

        # Check for different circuit types
        circuit_types = [c.circuit_type for c in result.circuits]
        assert "lighting" in circuit_types or "power" in circuit_types


# ============================================================================
# Layout Extractor Tests
# ============================================================================

class TestLayoutExtractors:
    """Test the layout extractors."""

    def test_lighting_extractor_import(self):
        """Test that lighting extractor can be imported."""
        from agent.extractors.lighting_layout_extractor import LightingLayoutExtractor
        extractor = LightingLayoutExtractor()
        assert extractor is not None

    def test_plugs_extractor_import(self):
        """Test that plugs extractor can be imported."""
        from agent.extractors.plugs_layout_extractor import PlugsLayoutExtractor
        extractor = PlugsLayoutExtractor()
        assert extractor is not None

    def test_extract_room_labels(self):
        """Test extracting room labels."""
        from agent.extractors.lighting_layout_extractor import LightingLayoutExtractor

        extractor = LightingLayoutExtractor()

        layout_text = """
        LIGHTING LAYOUT - GROUND FLOOR

        BEDROOM 1
        BEDROOM 2
        KITCHEN
        LIVING ROOM
        BATHROOM

        Legend:
        LED Downlight 6W
        1-Lever Switch
        """

        result = extractor.extract(layout_text, page_number=1)
        assert len(result.room_labels) > 0 or len(result.legend_items) > 0

    def test_extract_circuit_refs(self):
        """Test extracting circuit references."""
        from agent.extractors.lighting_layout_extractor import LightingLayoutExtractor

        extractor = LightingLayoutExtractor()

        layout_text = """
        BEDROOM 1 - DB-S1 L1
        BEDROOM 2 - DB-S1 L2
        KITCHEN - DB-S1 L3
        """

        result = extractor.extract(layout_text, page_number=1)
        # Should find circuit references
        assert len(result.circuit_refs) > 0 or len(result.room_labels) > 0


# ============================================================================
# Crop Stage Tests
# ============================================================================

class TestCropStage:
    """Test the crop/region detection stage."""

    def test_crop_import(self):
        """Test that crop module can be imported."""
        from agent.stages.crop import detect_page_regions
        assert detect_page_regions is not None

    def test_heuristic_detection(self):
        """Test heuristic region detection without text blocks."""
        from agent.stages.crop import detect_page_regions

        # Test with just page dimensions
        regions = detect_page_regions(
            page_width=800,
            page_height=600,
            text_blocks=[],
            enable_opencv=False,
            fallback_to_heuristic=True,
        )

        # Should get heuristic fallbacks
        assert regions.title_block is not None
        assert regions.legend is not None
        assert regions.schedule is not None
        assert regions.main_drawing is not None


# ============================================================================
# Merge Stage Tests
# ============================================================================

class TestMergeStage:
    """Test the merge stage."""

    def test_merge_import(self):
        """Test that merge module can be imported."""
        from agent.stages.merge import merge_page_results, validate_coverage
        assert merge_page_results is not None
        assert validate_coverage is not None

    def test_merge_empty_results(self):
        """Test merging empty page results."""
        from agent.stages.merge import merge_page_results

        result = merge_page_results([])
        assert result is not None
        assert result.pages_processed == 0

    def test_merge_mixed_pages(self):
        """Test merging mixed page types."""
        from agent.stages.merge import merge_page_results

        # Create test page results
        register_page = PageExtractionResult(
            page_id="test_page1",
            page_number=1,
            page_type=PageType.REGISTER,
            success=True,
            register_data=RegisterExtraction(
                project_name="Test Project",
                total_drawings=2,
            ),
        )

        sld_page = PageExtractionResult(
            page_id="test_page2",
            page_number=2,
            page_type=PageType.SLD,
            success=True,
            sld_data=SLDExtraction(
                db_name="DB-GF",
                main_breaker_a=100,
            ),
        )

        result = merge_page_results([register_page, sld_page])

        assert result is not None
        assert result.pages_processed == 2
        assert len(result.register_pages) == 1
        assert len(result.sld_pages) == 1
        assert result.project_name == "Test Project"


# ============================================================================
# Pipeline Orchestrator Tests
# ============================================================================

class TestDeterministicPipeline:
    """Test the deterministic pipeline orchestrator."""

    def test_pipeline_import(self):
        """Test that pipeline can be imported."""
        from agent.deterministic_pipeline import (
            DeterministicPipeline,
            DeterministicPipelineResult,
            run_deterministic_pipeline,
        )
        assert DeterministicPipeline is not None
        assert DeterministicPipelineResult is not None

    def test_pipeline_init(self):
        """Test pipeline initialization."""
        from agent.deterministic_pipeline import DeterministicPipeline

        config = PipelineConfig(
            render_dpi=150,
            debug_mode=False,
        )

        pipeline = DeterministicPipeline(config)
        assert pipeline is not None
        assert pipeline.config.render_dpi == 150

    def test_pipeline_result_structure(self):
        """Test pipeline result dataclass."""
        from agent.deterministic_pipeline import DeterministicPipelineResult

        result = DeterministicPipelineResult()
        assert result.success == True
        assert result.project_result is None
        assert result.pages == []
        assert result.total_processing_time_ms == 0


# ============================================================================
# Debug Utilities Tests
# ============================================================================

class TestDebugUtilities:
    """Test debug utilities."""

    def test_debug_import(self):
        """Test that debug modules can be imported."""
        from agent.debug import (
            DebugConfig,
            DebugArtifactSaver,
            draw_region_overlay,
            draw_classification_label,
        )
        assert DebugConfig is not None
        assert DebugArtifactSaver is not None

    def test_debug_config(self):
        """Test debug configuration."""
        from agent.debug.artifacts import DebugConfig

        config = DebugConfig(
            output_dir=Path("./test_debug"),
            enabled=True,
            save_page_images=True,
        )

        assert config.enabled == True
        assert config.save_page_images == True


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_import_chain(self):
        """Test that full import chain works."""
        from agent import (
            DeterministicPipeline,
            DeterministicPipelineResult,
            run_deterministic_pipeline,
            quick_extract,
        )

        assert DeterministicPipeline is not None

    def test_extractor_to_merge_flow(self):
        """Test data flow from extractors through merge."""
        from agent.extractors.sld_extractor import SLDExtractor
        from agent.stages.merge import merge_page_results

        # Extract from SLD
        extractor = SLDExtractor()
        sld_result = extractor.extract(
            "DB-GF L1 500W 1.5mm² 10A",
            page_number=1,
        )

        # Create page result
        page_result = PageExtractionResult(
            page_id="test",
            page_number=1,
            page_type=PageType.SLD,
            success=True,
            sld_data=sld_result,
            drawing_number="TEST-01-SLD",
        )

        # Merge
        project_result = merge_page_results([page_result])

        assert project_result.pages_processed == 1
        assert len(project_result.sld_pages) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
