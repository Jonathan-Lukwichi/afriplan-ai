"""
AfriPlan Electrical v1.0 - Deterministic Page Classification

Auto-classify pages using KeywordClassifier (NO LLM).
Replaces manual page categorization in Smart Upload.

Usage:
    from agent.stages.classify_pages import classify_all_pages, classify_service_tier

    categories = classify_all_pages(doc_set)
    # Returns: {"Cover": [...], "SLD": [...], "Lighting": [...], "Power": [...], "Other": [...]}

    tier = classify_service_tier(categories)
    # Returns: ServiceTier.RESIDENTIAL or COMMERCIAL or INDUSTRIAL
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

from agent.parsers.keyword_classifier import (
    KeywordClassifier,
    PageType as ClassifierPageType,
    ClassificationResult,
)
from agent.models import (
    DocumentSet,
    PageInfo,
    PageType,
    ServiceTier,
    StageResult,
    PipelineStage,
)
from agent.utils import Timer


@dataclass
class PageClassificationSummary:
    """Summary of page classification results."""
    total_pages: int = 0
    cover_pages: int = 0
    sld_pages: int = 0
    lighting_pages: int = 0
    power_pages: int = 0
    other_pages: int = 0
    avg_confidence: float = 0.0
    low_confidence_pages: List[int] = field(default_factory=list)


def classify_all_pages(
    doc_set: DocumentSet,
    confidence_threshold: float = 0.2,
) -> Dict[str, List[PageInfo]]:
    """
    Classify all pages in document set using deterministic keyword matching.

    NO LLM CALLS - pure Python keyword matching.

    Args:
        doc_set: Document set from ingest stage
        confidence_threshold: Minimum confidence to accept classification

    Returns:
        Dict mapping category names to page lists:
        {"Cover": [...], "SLD": [...], "Lighting": [...], "Power": [...], "Other": [...]}
    """
    classifier = KeywordClassifier()

    categories: Dict[str, List[PageInfo]] = {
        "Cover": [],
        "SLD": [],
        "Lighting": [],
        "Power": [],
        "Other": [],
    }

    for doc in doc_set.documents:
        for page in doc.pages:
            # Get text content and drawing number
            text = page.text_content or ""
            drawing_number = getattr(page, 'drawing_number', "") or ""

            # Classify the page
            result = classifier.classify(text, drawing_number)

            # Update page with classification (only valid PageInfo fields)
            page.page_type = PageType(result.page_type.value)
            page.classification_confidence = result.confidence

            # Route to appropriate category
            if result.confidence < confidence_threshold:
                categories["Other"].append(page)
            elif result.page_type in (ClassifierPageType.REGISTER, ClassifierPageType.SCHEDULE):
                # Register and Legend/Schedule pages go to Cover
                categories["Cover"].append(page)
            elif result.page_type == ClassifierPageType.SLD:
                categories["SLD"].append(page)
            elif result.page_type in (ClassifierPageType.LAYOUT_LIGHTING, ClassifierPageType.OUTSIDE_LIGHTS):
                categories["Lighting"].append(page)
            elif result.page_type == ClassifierPageType.LAYOUT_PLUGS:
                categories["Power"].append(page)
            elif result.page_type == ClassifierPageType.LAYOUT_COMBINED:
                # Combined layouts go to both lighting and power
                categories["Lighting"].append(page)
                categories["Power"].append(page)
            else:
                categories["Other"].append(page)

    return categories


def classify_pages_from_list(
    pages: List[PageInfo],
    confidence_threshold: float = 0.2,
) -> Dict[str, List[PageInfo]]:
    """
    Classify a list of pages (alternative entry point).

    Args:
        pages: List of PageInfo objects
        confidence_threshold: Minimum confidence to accept classification

    Returns:
        Dict mapping category names to page lists
    """
    classifier = KeywordClassifier()

    categories: Dict[str, List[PageInfo]] = {
        "Cover": [],
        "SLD": [],
        "Lighting": [],
        "Power": [],
        "Other": [],
    }

    for page in pages:
        text = page.text_content or ""
        drawing_number = getattr(page, 'drawing_number', "") or ""

        result = classifier.classify(text, drawing_number)

        # Update page with classification (only valid PageInfo fields)
        page.page_type = PageType(result.page_type.value)
        page.classification_confidence = result.confidence

        if result.confidence < confidence_threshold:
            categories["Other"].append(page)
        elif result.page_type in (ClassifierPageType.REGISTER, ClassifierPageType.SCHEDULE):
            # Register and Legend/Schedule pages go to Cover
            categories["Cover"].append(page)
        elif result.page_type == ClassifierPageType.SLD:
            categories["SLD"].append(page)
        elif result.page_type in (ClassifierPageType.LAYOUT_LIGHTING, ClassifierPageType.OUTSIDE_LIGHTS):
            categories["Lighting"].append(page)
        elif result.page_type == ClassifierPageType.LAYOUT_PLUGS:
            categories["Power"].append(page)
        elif result.page_type == ClassifierPageType.LAYOUT_COMBINED:
            categories["Lighting"].append(page)
            categories["Power"].append(page)
        else:
            categories["Other"].append(page)

    return categories


def classify_service_tier(
    categories: Dict[str, List[PageInfo]],
) -> ServiceTier:
    """
    Determine service tier from classified pages (NO LLM).

    Logic:
    - Keywords "residential", "house", "dwelling" → RESIDENTIAL
    - Keywords "office", "commercial", "retail", "suite" → COMMERCIAL
    - Keywords "factory", "industrial", "plant" → INDUSTRIAL
    - Default: COMMERCIAL (most common for electrical drawings)

    Args:
        categories: Page categories from classify_all_pages()

    Returns:
        ServiceTier enum value
    """
    # Collect all text from all pages
    all_text = " ".join(
        (page.text_content or "")
        for pages in categories.values()
        for page in pages
    ).lower()

    # Keyword scoring
    residential_keywords = [
        "residential", "house", "dwelling", "bedroom", "bathroom",
        "kitchen", "lounge", "garage", "domestic", "home"
    ]
    commercial_keywords = [
        "office", "commercial", "retail", "suite", "reception",
        "boardroom", "server room", "ablution", "foyer", "lobby"
    ]
    industrial_keywords = [
        "factory", "industrial", "plant", "warehouse", "manufacturing",
        "workshop", "production", "machinery", "3-phase motor"
    ]

    residential_score = sum(1 for kw in residential_keywords if kw in all_text)
    commercial_score = sum(1 for kw in commercial_keywords if kw in all_text)
    industrial_score = sum(1 for kw in industrial_keywords if kw in all_text)

    scores = {
        ServiceTier.RESIDENTIAL: residential_score,
        ServiceTier.COMMERCIAL: commercial_score,
        ServiceTier.INDUSTRIAL: industrial_score,
    }

    # Return highest scoring tier, default to COMMERCIAL
    if max(scores.values()) == 0:
        return ServiceTier.COMMERCIAL

    return max(scores, key=scores.get)


def get_classification_summary(
    categories: Dict[str, List[PageInfo]],
) -> PageClassificationSummary:
    """
    Generate a summary of classification results.

    Args:
        categories: Page categories from classify_all_pages()

    Returns:
        PageClassificationSummary with counts and statistics
    """
    summary = PageClassificationSummary()

    all_pages = []
    confidences = []

    for category, pages in categories.items():
        count = len(pages)
        all_pages.extend(pages)

        if category == "Cover":
            summary.cover_pages = count
        elif category == "SLD":
            summary.sld_pages = count
        elif category == "Lighting":
            summary.lighting_pages = count
        elif category == "Power":
            summary.power_pages = count
        elif category == "Other":
            summary.other_pages = count

        for page in pages:
            conf = getattr(page, 'classification_confidence', 0.5)
            confidences.append(conf)
            if conf < 0.4:
                summary.low_confidence_pages.append(page.page_number)

    summary.total_pages = len(all_pages)
    summary.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return summary


def classify_with_stage_result(
    doc_set: DocumentSet,
) -> tuple[Dict[str, List[PageInfo]], ServiceTier, StageResult]:
    """
    Full classification with StageResult for pipeline integration.

    Args:
        doc_set: Document set from ingest stage

    Returns:
        Tuple of (categories, service_tier, stage_result)
    """
    with Timer("classify_pages") as timer:
        categories = classify_all_pages(doc_set)
        tier = classify_service_tier(categories)
        summary = get_classification_summary(categories)

        stage_result = StageResult(
            stage=PipelineStage.CLASSIFY,
            success=True,
            confidence=summary.avg_confidence,
            data={
                "tier": tier.value,
                "categories": {k: len(v) for k, v in categories.items()},
                "summary": {
                    "total_pages": summary.total_pages,
                    "sld_pages": summary.sld_pages,
                    "lighting_pages": summary.lighting_pages,
                    "power_pages": summary.power_pages,
                    "low_confidence_count": len(summary.low_confidence_pages),
                },
            },
            model_used=None,  # No LLM!
            tokens_used=0,
            cost_zar=0.0,
            processing_time_ms=timer.elapsed_ms,
            errors=[],
            warnings=summary.low_confidence_pages[:5] if summary.low_confidence_pages else [],
        )

        return categories, tier, stage_result
