"""
AfriPlan Electrical v4.1 — Model Tests

Tests for Pydantic models and data structures.
"""

import pytest
from datetime import datetime

from agent.models import (
    ServiceTier,
    ExtractionMode,
    ItemConfidence,
    PipelineStage,
    BQSection,
    CorrectionType,
    ValidationSeverity,
    ContractorProfile,
    LabourRates,
    SiteConditions,
    DocumentSet,
    ExtractionResult,
    ValidationResult,
    ValidationFlag,
    PricingResult,
    BQItem,
    StageResult,
    PipelineResult,
    BuildingBlock,
    Room,
    DBBoard,
    Circuit,
    Fixture,
    PlugPoint,
    SwitchPoint,
    SiteCableRun,
    CorrectionLog,
)


class TestEnums:
    """Test enum values and properties."""

    def test_service_tier_values(self):
        assert ServiceTier.RESIDENTIAL.value == "residential"
        assert ServiceTier.COMMERCIAL.value == "commercial"
        assert ServiceTier.MAINTENANCE.value == "maintenance"
        assert ServiceTier.UNKNOWN.value == "unknown"

    def test_item_confidence_values(self):
        assert ItemConfidence.EXTRACTED.value == "extracted"
        assert ItemConfidence.INFERRED.value == "inferred"
        assert ItemConfidence.ESTIMATED.value == "estimated"
        assert ItemConfidence.MANUAL.value == "manual"

    def test_pipeline_stage_values(self):
        stages = [s.value for s in PipelineStage]
        assert "ingest" in stages
        assert "classify" in stages
        assert "discover" in stages
        assert "review" in stages
        assert "validate" in stages
        assert "price" in stages
        assert "output" in stages


class TestContractorProfile:
    """Test ContractorProfile model."""

    def test_default_values(self):
        profile = ContractorProfile()
        assert profile.company_name == ""
        assert profile.markup_pct == 15.0
        assert profile.contingency_pct == 5.0
        assert profile.vat_pct == 15.0
        assert profile.payment_terms == "40/40/20"
        assert profile.bq_format == "detailed"
        assert profile.max_travel_km == 100
        assert isinstance(profile.labour_rates, LabourRates)
        assert isinstance(profile.custom_prices, dict)

    def test_labour_rates_defaults(self):
        rates = LabourRates()
        assert rates.electrician_daily_zar == 1200.0
        assert rates.assistant_daily_zar == 600.0
        assert rates.foreman_daily_zar == 1800.0
        assert rates.team_size_electricians == 2
        assert rates.team_size_assistants == 1
        assert rates.travel_rate_per_km_zar == 5.5

    def test_custom_values(self):
        profile = ContractorProfile(
            company_name="ABC Electrical",
            markup_pct=20.0,
            labour_rates=LabourRates(electrician_daily_zar=1500.0)
        )
        assert profile.company_name == "ABC Electrical"
        assert profile.markup_pct == 20.0
        assert profile.labour_rates.electrician_daily_zar == 1500.0


class TestSiteConditions:
    """Test SiteConditions model."""

    def test_default_multipliers(self):
        site = SiteConditions()
        assert site.labour_multiplier == 1.0
        assert site.trenching_multiplier == 1.0

    def test_renovation_multiplier(self):
        site = SiteConditions(is_renovation=True)
        assert site.labour_multiplier > 1.0

    def test_height_multiplier(self):
        site = SiteConditions(requires_scaffolding=True, height_m=6.0)
        assert site.labour_multiplier > 1.0

    def test_trenching_conditions(self):
        site = SiteConditions(soil_type="rock", requires_traffic_control=True)
        assert site.trenching_multiplier > 1.0


class TestExtractionModels:
    """Test extraction data models."""

    def test_room_defaults(self):
        room = Room(room_name="Bedroom 1", room_type="bedroom")
        assert room.area_m2 is None
        assert room.fixtures == []
        assert room.plugs == []
        assert room.switches == []
        assert room.confidence == ItemConfidence.ESTIMATED

    def test_building_block(self):
        block = BuildingBlock(
            block_name="House",
            block_type="residential",
            floors=1,
        )
        assert block.block_name == "House"
        assert block.db_boards == []
        assert block.rooms == []
        assert block.site_cable_runs == []

    def test_circuit(self):
        circuit = Circuit(
            circuit_number="C1",
            circuit_type="lighting",
            breaker_a=10,
        )
        assert circuit.circuit_number == "C1"
        assert circuit.cable_size_mm2 == 1.5
        assert circuit.point_count == 0
        assert circuit.confidence == ItemConfidence.ESTIMATED

    def test_fixture_with_confidence(self):
        fixture = Fixture(
            fixture_type="downlight",
            quantity=4,
            wattage_w=9,
            confidence=ItemConfidence.EXTRACTED,
        )
        assert fixture.quantity == 4
        assert fixture.confidence == ItemConfidence.EXTRACTED


class TestValidationModels:
    """Test validation models."""

    def test_validation_flag(self):
        flag = ValidationFlag(
            rule_name="ELCB Required",
            passed=False,
            severity=ValidationSeverity.CRITICAL,
            message="ELCB not found in DB",
        )
        assert not flag.passed
        assert flag.severity == ValidationSeverity.CRITICAL
        assert not flag.auto_corrected

    def test_validation_result_computed_fields(self):
        flags = [
            ValidationFlag(rule_name="R1", passed=True, severity=ValidationSeverity.INFO, message="OK"),
            ValidationFlag(rule_name="R2", passed=False, severity=ValidationSeverity.WARNING, message="Warning"),
            ValidationFlag(rule_name="R3", passed=False, severity=ValidationSeverity.CRITICAL, message="Error"),
        ]
        result = ValidationResult(flags=flags)

        # Computed fields
        assert result.passed == 1
        assert result.failed == 2
        assert result.warnings == 1
        assert result.compliance_score < 100


class TestBQModels:
    """Test BQ item models."""

    def test_bq_item_total(self):
        item = BQItem(
            section=BQSection.LIGHTING,
            description="LED Downlight 9W",
            unit="ea",
            qty=10,
            unit_price_zar=150.0,
            source=ItemConfidence.EXTRACTED,
        )
        assert item.total_zar == 1500.0

    def test_bq_item_no_price(self):
        item = BQItem(
            section=BQSection.SOCKETS,
            description="Double Socket Outlet",
            unit="ea",
            qty=8,
            source=ItemConfidence.EXTRACTED,
        )
        assert item.unit_price_zar == 0.0
        assert item.total_zar == 0.0


class TestCorrectionLog:
    """Test correction logging."""

    def test_correction_creation(self):
        log = CorrectionLog(
            field_path="rooms[0].fixtures[0].quantity",
            original_value=2,
            corrected_value=4,
            correction_type=CorrectionType.QUANTITY_CHANGE,
            confidence_before=ItemConfidence.INFERRED,
        )
        assert log.original_value == 2
        assert log.corrected_value == 4
        assert log.confidence_after == ItemConfidence.MANUAL


class TestPipelineResult:
    """Test pipeline result assembly."""

    def test_stage_result(self):
        result = StageResult(
            stage=PipelineStage.INGEST,
            success=True,
            confidence=0.95,
        )
        assert result.success
        assert result.confidence == 0.95
        assert result.tokens_used == 0
        assert result.errors == []

    def test_pipeline_result(self):
        stages = [
            StageResult(stage=PipelineStage.INGEST, success=True, confidence=1.0),
            StageResult(stage=PipelineStage.CLASSIFY, success=True, confidence=0.9),
        ]
        result = PipelineResult(
            stages=stages,
            tier=ServiceTier.RESIDENTIAL,
            extraction=ExtractionResult(),
            pricing=PricingResult(),
        )
        assert result.success
        assert len(result.stages) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
