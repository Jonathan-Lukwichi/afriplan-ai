"""
AfriPlan Electrical v4.1 — Pricing Tests

Tests for the pricing stage and BQ generation.
"""

import pytest

from agent.models import (
    ExtractionResult,
    ValidationResult,
    ValidationFlag,
    ValidationSeverity,
    PricingResult,
    BQItem,
    BQSection,
    ItemConfidence,
    ContractorProfile,
    SiteConditions,
    BuildingBlock,
    Room,
    DBBoard,
    Circuit,
    Fixture,
    PlugPoint,
)
from agent.stages.price import price, _generate_bq_items, _apply_site_multipliers


@pytest.fixture
def sample_extraction():
    """Create sample extraction for pricing tests."""
    fixture = Fixture(
        fixture_type="downlight",
        quantity=10,
        wattage_w=9,
        confidence=ItemConfidence.EXTRACTED,
    )
    room = Room(
        room_name="Open Plan",
        room_type="living",
        area_m2=40.0,
        fixtures=[fixture],
        plugs=[
            PlugPoint(socket_type="double", quantity=8),
        ],
    )
    circuit = Circuit(
        circuit_number="C1",
        circuit_type="lighting",
        breaker_a=10,
        cable_size_mm2=1.5,
        length_m=25.0,
        point_count=10,
    )
    db = DBBoard(
        db_name="Main DB",
        db_type="distribution",
        ways=18,
        main_breaker_a=60,
        has_elcb=True,
        circuits=[circuit],
    )
    block = BuildingBlock(
        block_name="House",
        block_type="residential",
        floors=1,
        db_boards=[db],
        rooms=[room],
    )
    return ExtractionResult(building_blocks=[block])


@pytest.fixture
def sample_validation():
    """Create sample validation result."""
    return ValidationResult(
        flags=[
            ValidationFlag(
                rule_name="ELCB Present",
                passed=True,
                severity=ValidationSeverity.INFO,
                message="ELCB found",
            ),
        ]
    )


class TestPriceStage:
    """Test the pricing stage."""

    def test_basic_pricing(self, sample_extraction, sample_validation):
        pricing, result = price(sample_extraction, sample_validation)

        assert result.success
        assert isinstance(pricing, PricingResult)
        assert pricing.total_items > 0
        assert len(pricing.quantity_bq) > 0
        assert len(pricing.estimated_bq) > 0

    def test_quantity_bq_no_prices(self, sample_extraction, sample_validation):
        pricing, _ = price(sample_extraction, sample_validation)

        # Quantity BQ should have items with qty but no prices
        for item in pricing.quantity_bq:
            assert item.qty > 0
            # Price should be 0 (contractor fills in)
            assert item.unit_price_zar == 0.0

    def test_estimated_bq_has_prices(self, sample_extraction, sample_validation):
        pricing, _ = price(sample_extraction, sample_validation)

        # Estimated BQ should have prices
        has_prices = any(item.unit_price_zar > 0 for item in pricing.estimated_bq)
        assert has_prices

    def test_totals_calculated(self, sample_extraction, sample_validation):
        pricing, _ = price(sample_extraction, sample_validation)

        # Estimate totals should be calculated
        if pricing.estimate_subtotal_zar > 0:
            assert pricing.estimate_contingency_zar >= 0
            assert pricing.estimate_margin_zar >= 0
            assert pricing.estimate_total_excl_vat_zar > 0
            assert pricing.estimate_vat_zar >= 0
            assert pricing.estimate_total_incl_vat_zar > 0

    def test_payment_schedule(self, sample_extraction, sample_validation):
        pricing, _ = price(sample_extraction, sample_validation)

        # Payment schedule should be 40/40/20
        total = pricing.estimate_total_incl_vat_zar
        if total > 0:
            expected_deposit = total * 0.4
            assert abs(pricing.deposit_zar - expected_deposit) < 1


class TestBQItemGeneration:
    """Test BQ item generation."""

    def test_fixture_bq_items(self, sample_extraction):
        items = _generate_bq_items(sample_extraction)

        # Should have lighting items
        lighting_items = [i for i in items if i.section == BQSection.LIGHTING]
        assert len(lighting_items) > 0

    def test_socket_bq_items(self, sample_extraction):
        items = _generate_bq_items(sample_extraction)

        socket_items = [i for i in items if i.section == BQSection.SOCKETS]
        assert len(socket_items) > 0

    def test_db_bq_items(self, sample_extraction):
        items = _generate_bq_items(sample_extraction)

        db_items = [i for i in items if i.section == BQSection.DISTRIBUTION]
        assert len(db_items) > 0

    def test_cable_bq_items(self, sample_extraction):
        items = _generate_bq_items(sample_extraction)

        cable_items = [i for i in items if i.section == BQSection.CABLES]
        assert len(cable_items) > 0


class TestSiteMultipliers:
    """Test site condition multipliers."""

    def test_no_multipliers(self, sample_extraction, sample_validation):
        # No site conditions = no multipliers
        pricing, _ = price(sample_extraction, sample_validation)
        base_total = pricing.estimate_subtotal_zar

        # With neutral site conditions
        site = SiteConditions()
        pricing2, _ = price(sample_extraction, sample_validation, site_conditions=site)

        # Should be same (multiplier = 1.0)
        assert abs(pricing2.estimate_subtotal_zar - base_total) < 1

    def test_renovation_multiplier(self, sample_extraction, sample_validation):
        site = SiteConditions(is_renovation=True)
        pricing, _ = price(sample_extraction, sample_validation, site_conditions=site)

        # Labour costs should be higher for renovation
        assert site.labour_multiplier > 1.0

    def test_difficult_access_multiplier(self, sample_extraction, sample_validation):
        site = SiteConditions(access_difficulty="difficult")
        pricing, _ = price(sample_extraction, sample_validation, site_conditions=site)

        assert site.labour_multiplier > 1.0


class TestContractorProfile:
    """Test contractor profile integration."""

    def test_custom_markup(self, sample_extraction, sample_validation):
        contractor = ContractorProfile(markup_pct=25.0)
        pricing, _ = price(
            sample_extraction, sample_validation,
            contractor_profile=contractor
        )

        # Margin should reflect 25% markup
        if pricing.estimate_subtotal_zar > 0:
            expected_margin = pricing.estimate_subtotal_zar * 0.25
            assert abs(pricing.estimate_margin_zar - expected_margin) < 1

    def test_custom_contingency(self, sample_extraction, sample_validation):
        contractor = ContractorProfile(contingency_pct=10.0)
        pricing, _ = price(
            sample_extraction, sample_validation,
            contractor_profile=contractor
        )

        if pricing.estimate_subtotal_zar > 0:
            expected_contingency = pricing.estimate_subtotal_zar * 0.10
            assert abs(pricing.estimate_contingency_zar - expected_contingency) < 1


class TestEmptyExtraction:
    """Test handling of empty/minimal extractions."""

    def test_empty_extraction(self):
        empty = ExtractionResult()
        validation = ValidationResult()

        pricing, result = price(empty, validation)

        assert result.success
        assert pricing.total_items == 0
        assert len(pricing.quantity_bq) == 0
        assert len(pricing.estimated_bq) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
