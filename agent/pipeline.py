"""
AfriPlan Electrical v4.1 — Pipeline Orchestrator

Orchestrates the 7-stage pipeline:
INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT

Supports multiple LLM providers:
- Google Gemini (FREE tier available)
- Anthropic Claude (paid)
"""

from typing import List, Tuple, Optional, Any
import os

from agent.models import (
    PipelineResult, StageResult, PipelineStage,
    DocumentSet, ExtractionResult, ValidationResult, PricingResult,
    ServiceTier, ExtractionMode, ContractorProfile, SiteConditions
)
from agent.stages.ingest import ingest
from agent.stages.classify import classify
from agent.stages.discover import discover
from agent.stages.review import ReviewManager, create_review_stage_result
from agent.stages.validate import validate
from agent.stages.price import price
from agent.stages.output import generate_output
from agent.utils import Timer

# Provider detection
def _get_llm_provider():
    """Detect and return the appropriate LLM provider."""
    # Check for Gemini first (free!)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return "gemini", gemini_key

    # Fall back to Claude
    claude_key = os.environ.get("ANTHROPIC_API_KEY")
    if claude_key:
        return "claude", claude_key

    return None, None


class AfriPlanPipeline:
    """
    Main pipeline orchestrator for AfriPlan v4.1.

    Manages the 7-stage processing pipeline:
    1. INGEST: Convert documents to images
    2. CLASSIFY: Determine project tier
    3. DISCOVER: Extract structured data
    4. REVIEW: Contractor review/edit (interactive)
    5. VALIDATE: SANS compliance checks
    6. PRICE: Generate dual BQ
    7. OUTPUT: Assemble final result

    Supports both Google Gemini (free) and Claude (paid) as LLM providers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        contractor_profile: Optional[ContractorProfile] = None,
        provider: Optional[str] = None,  # "gemini" or "claude"
    ):
        """
        Initialize the pipeline.

        Args:
            api_key: API key. If None, uses environment variables.
            contractor_profile: Contractor's saved preferences.
            provider: LLM provider ("gemini" or "claude"). Auto-detects if None.
        """
        self.provider = provider
        self.api_key = api_key
        self.client = None

        # Auto-detect provider if not specified
        if provider is None:
            detected_provider, detected_key = _get_llm_provider()
            self.provider = detected_provider
            if api_key is None:
                self.api_key = detected_key

        # Initialize the appropriate client
        if self.provider == "gemini":
            self._init_gemini_client()
        elif self.provider == "claude":
            self._init_claude_client()
        else:
            # No provider configured - will fail when trying to use LLM
            self.client = None

        self.contractor_profile = contractor_profile
        self.stages: List[StageResult] = []

    def _init_gemini_client(self):
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            )

    def _init_claude_client(self):
        """Initialize Anthropic Claude client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic not installed. Run: pip install anthropic"
            )

    # State tracking (initialized in __init__)
    doc_set: Optional[DocumentSet] = None
    tier: ServiceTier = ServiceTier.UNKNOWN
    mode: ExtractionMode = ExtractionMode.ESTIMATION
    building_blocks: List[str] = []
    extraction: Optional[ExtractionResult] = None
    validation: Optional[ValidationResult] = None
    pricing: Optional[PricingResult] = None
    site_conditions: Optional[SiteConditions] = None

    def process_documents(
        self,
        files: List[Tuple[bytes, str, str]],  # (file_bytes, filename, mime_type)
        use_opus_directly: bool = False,
    ) -> Tuple[ExtractionResult, float]:
        """
        Run stages 1-3: INGEST → CLASSIFY → DISCOVER.

        Returns extraction result ready for contractor review.

        Args:
            files: List of (file_bytes, filename, mime_type) tuples
            use_opus_directly: If True, use Opus for extraction (slower but more accurate)

        Returns:
            Tuple of (ExtractionResult, overall_confidence)
        """
        # Stage 1: INGEST
        self.doc_set, ingest_result = ingest(files)
        self.stages.append(ingest_result)

        if not ingest_result.success:
            return ExtractionResult(), 0.0

        # Stage 2: CLASSIFY
        self.tier, self.mode, self.building_blocks, tier_conf, classify_result = classify(
            self.doc_set, self.client, provider=self.provider or "claude"
        )
        self.stages.append(classify_result)

        # Stage 3: DISCOVER (with optional higher-tier model for maximum accuracy)
        self.extraction, discover_result = discover(
            self.doc_set,
            self.tier,
            self.mode,
            self.building_blocks,
            self.client,
            use_opus_directly=use_opus_directly,
            provider=self.provider or "claude",
        )
        self.stages.append(discover_result)

        return self.extraction, discover_result.confidence

    def create_review_manager(self, project_name: str = "") -> ReviewManager:
        """
        Create a ReviewManager for contractor to edit extraction.

        Args:
            project_name: Name of the project for logging

        Returns:
            ReviewManager instance
        """
        if self.extraction is None:
            raise ValueError("No extraction to review. Run process_documents first.")

        return ReviewManager(self.extraction, project_name)

    def complete_review(
        self,
        review_manager: ReviewManager,
        processing_time_ms: int = 0,
    ) -> None:
        """
        Complete the review stage and update extraction.

        Args:
            review_manager: Completed review manager
            processing_time_ms: Time spent in review
        """
        self.extraction = review_manager.complete_review()
        review_result = create_review_stage_result(review_manager, processing_time_ms)
        self.stages.append(review_result)

    def validate_and_price(
        self,
        site_conditions: Optional[SiteConditions] = None,
    ) -> PricingResult:
        """
        Run stages 5-6: VALIDATE → PRICE.

        Args:
            site_conditions: Site-specific factors affecting pricing

        Returns:
            PricingResult with dual BQ
        """
        if self.extraction is None:
            raise ValueError("No extraction to validate. Run process_documents first.")

        self.site_conditions = site_conditions

        # Stage 5: VALIDATE
        self.validation, validate_result = validate(self.extraction)
        self.stages.append(validate_result)

        # Stage 6: PRICE
        self.pricing, price_result = price(
            self.extraction,
            self.validation,
            self.contractor_profile,
            self.site_conditions,
        )
        self.stages.append(price_result)

        return self.pricing

    def generate_final_result(self) -> PipelineResult:
        """
        Run stage 7: OUTPUT - assemble final result.

        Returns:
            Complete PipelineResult
        """
        if self.doc_set is None:
            raise ValueError("Pipeline not started. Run process_documents first.")

        return generate_output(
            stages=self.stages,
            doc_set=self.doc_set,
            tier=self.tier,
            mode=self.mode,
            extraction=self.extraction or ExtractionResult(),
            validation=self.validation,
            pricing=self.pricing,
            contractor=self.contractor_profile,
            site=self.site_conditions,
        )

    def run_full_pipeline(
        self,
        files: List[Tuple[bytes, str, str]],
        site_conditions: Optional[SiteConditions] = None,
        skip_review: bool = False,
    ) -> PipelineResult:
        """
        Run complete pipeline without interactive review.

        For automated processing or testing.

        Args:
            files: List of (file_bytes, filename, mime_type) tuples
            site_conditions: Site-specific factors
            skip_review: If True, skip the review stage

        Returns:
            Complete PipelineResult
        """
        # Stages 1-3
        extraction, confidence = self.process_documents(files)

        # Stage 4: REVIEW (auto-complete if skipping)
        if not skip_review:
            review_manager = self.create_review_manager()
            self.complete_review(review_manager, processing_time_ms=0)
        else:
            # Mark extraction as reviewed without changes
            self.extraction.review_completed = True
            skip_result = StageResult(
                stage=PipelineStage.REVIEW,
                success=True,
                confidence=confidence,
                data={"skipped": True},
            )
            self.stages.append(skip_result)

        # Stages 5-6
        self.validate_and_price(site_conditions)

        # Stage 7
        return self.generate_final_result()


def create_pipeline(
    api_key: Optional[str] = None,
    contractor_profile: Optional[ContractorProfile] = None,
    provider: Optional[str] = None,  # "gemini" or "claude"
) -> AfriPlanPipeline:
    """
    Factory function to create a pipeline instance.

    Args:
        api_key: API key (for specified provider)
        contractor_profile: Contractor preferences
        provider: LLM provider ("gemini" or "claude"). Auto-detects if None.

    Returns:
        AfriPlanPipeline instance
    """
    return AfriPlanPipeline(api_key, contractor_profile, provider)


# Convenience functions for simple use cases
def process_single_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    api_key: Optional[str] = None,
) -> PipelineResult:
    """
    Process a single document through the full pipeline.

    Convenience function for simple use cases.

    Args:
        file_bytes: Document bytes
        filename: Original filename
        mime_type: MIME type of the document
        api_key: Anthropic API key

    Returns:
        Complete PipelineResult
    """
    pipeline = create_pipeline(api_key)
    return pipeline.run_full_pipeline(
        files=[(file_bytes, filename, mime_type)],
        skip_review=True,
    )


def extract_quantities_only(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    api_key: Optional[str] = None,
) -> ExtractionResult:
    """
    Extract quantities without pricing.

    Useful for just getting the AI extraction.

    Args:
        file_bytes: Document bytes
        filename: Original filename
        mime_type: MIME type of the document
        api_key: Anthropic API key

    Returns:
        ExtractionResult
    """
    pipeline = create_pipeline(api_key)
    extraction, confidence = pipeline.process_documents(
        files=[(file_bytes, filename, mime_type)]
    )
    return extraction
