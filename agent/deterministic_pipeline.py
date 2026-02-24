"""
AfriPlan Electrical - Deterministic Pipeline Orchestrator

5-Stage local-only extraction pipeline for electrical drawings:
1. INGEST - Convert PDF to pages (PyMuPDF)
2. CLASSIFY - Keyword-based page classification
3. CROP - Region detection (OpenCV/heuristic)
4. EXTRACT - Page-type-specific extraction
5. MERGE - Aggregate to project level

No AI/cloud APIs used. Pure local Python processing.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple, Any, Dict
from dataclasses import dataclass, field

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from agent.models import (
    DocumentPage, PageClassification, PageRegions, PageExtractionResult,
    ProjectExtractionResult, PipelineConfig, ExtractionWarning, Severity,
    PageType, RegisterExtraction, SLDExtraction, LayoutExtraction,
    BoundingBox, TextBlock as TextBlockModel, MergeStatistics
)

from agent.parsers.pdf_text import extract_text_blocks, extract_raw_text, TextBlock
from agent.parsers.keyword_classifier import (
    KeywordClassifier, ClassificationResult, PageType as ClassifierPageType
)
from agent.parsers.drawing_number_parser import parse_drawing_number

from agent.stages.crop import detect_page_regions

from agent.extractors.register_extractor import RegisterExtractor
from agent.extractors.sld_extractor import SLDExtractor
from agent.extractors.lighting_layout_extractor import LightingLayoutExtractor
from agent.extractors.plugs_layout_extractor import PlugsLayoutExtractor

from agent.stages.merge import merge_page_results, validate_coverage

from agent.debug.artifacts import DebugArtifactSaver, DebugConfig
from agent.debug.overlays import (
    draw_region_overlay, draw_classification_label, draw_text_blocks_overlay
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    """Result from a single pipeline stage."""
    stage_name: str
    success: bool = True
    processing_time_ms: int = 0
    items_processed: int = 0
    warnings: List[ExtractionWarning] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeterministicPipelineResult:
    """Complete result from deterministic pipeline."""
    success: bool = True
    project_result: Optional[ProjectExtractionResult] = None
    pages: List[DocumentPage] = field(default_factory=list)
    page_results: List[PageExtractionResult] = field(default_factory=list)
    stage_results: List[PipelineStageResult] = field(default_factory=list)
    total_processing_time_ms: int = 0
    warnings: List[ExtractionWarning] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DeterministicPipeline:
    """
    Deterministic (non-AI) extraction pipeline for electrical drawings.

    Usage:
        pipeline = DeterministicPipeline(config)
        result = pipeline.process_pdf(Path("drawings.pdf"))
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the deterministic pipeline.

        Args:
            config: Pipeline configuration. Uses defaults if None.
        """
        self.config = config or PipelineConfig()

        # Initialize components
        self.classifier = KeywordClassifier()
        self.register_extractor = RegisterExtractor()
        self.sld_extractor = SLDExtractor()
        self.lighting_extractor = LightingLayoutExtractor()
        self.plugs_extractor = PlugsLayoutExtractor()

        # Debug artifacts
        if self.config.debug_mode:
            debug_config = DebugConfig(
                output_dir=Path(self.config.debug_output_dir),
                enabled=True,
                save_page_images=self.config.save_page_images,
                save_region_crops=self.config.save_region_crops,
                save_overlay_images=self.config.save_overlay_images,
            )
            self.debug_saver = DebugArtifactSaver(debug_config)
        else:
            self.debug_saver = None

    def process_pdf(
        self,
        pdf_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> DeterministicPipelineResult:
        """
        Process a PDF through the 5-stage pipeline.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callback(stage, progress_pct, message)

        Returns:
            DeterministicPipelineResult with all extracted data
        """
        result = DeterministicPipelineResult()
        start_time = time.time()

        if not HAS_PYMUPDF:
            result.success = False
            result.errors.append("PyMuPDF (fitz) not installed. Run: pip install PyMuPDF")
            return result

        if not pdf_path.exists():
            result.success = False
            result.errors.append(f"PDF not found: {pdf_path}")
            return result

        try:
            # Stage 1: INGEST
            if progress_callback:
                progress_callback("INGEST", 0, "Loading PDF...")

            pages, ingest_result = self._stage_ingest(pdf_path)
            result.stage_results.append(ingest_result)
            result.pages = pages

            if not ingest_result.success:
                result.success = False
                return result

            # Stage 2: CLASSIFY
            if progress_callback:
                progress_callback("CLASSIFY", 20, "Classifying pages...")

            classify_result = self._stage_classify(pages)
            result.stage_results.append(classify_result)

            # Stage 3: CROP
            if progress_callback:
                progress_callback("CROP", 40, "Detecting regions...")

            crop_result = self._stage_crop(pages)
            result.stage_results.append(crop_result)

            # Stage 4: EXTRACT
            if progress_callback:
                progress_callback("EXTRACT", 60, "Extracting data...")

            page_results, extract_result = self._stage_extract(pages)
            result.stage_results.append(extract_result)
            result.page_results = page_results

            # Stage 5: MERGE
            if progress_callback:
                progress_callback("MERGE", 80, "Merging results...")

            project_result, merge_result = self._stage_merge(page_results)
            result.stage_results.append(merge_result)
            result.project_result = project_result

            # Collect all warnings
            for stage in result.stage_results:
                result.warnings.extend(stage.warnings)

            if progress_callback:
                progress_callback("COMPLETE", 100, "Done!")

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            result.success = False
            result.errors.append(str(e))

        result.total_processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    def process_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        progress_callback: Optional[callable] = None,
    ) -> DeterministicPipelineResult:
        """
        Process PDF from bytes.

        Args:
            pdf_bytes: PDF file bytes
            filename: Original filename (for page IDs)
            progress_callback: Optional progress callback

        Returns:
            DeterministicPipelineResult
        """
        result = DeterministicPipelineResult()
        start_time = time.time()

        if not HAS_PYMUPDF:
            result.success = False
            result.errors.append("PyMuPDF (fitz) not installed")
            return result

        try:
            # Stage 1: INGEST from bytes
            if progress_callback:
                progress_callback("INGEST", 0, "Loading PDF...")

            pages, ingest_result = self._ingest_from_bytes(pdf_bytes, filename)
            result.stage_results.append(ingest_result)
            result.pages = pages

            if not ingest_result.success:
                result.success = False
                return result

            # Continue with remaining stages (same as process_pdf)
            # Stage 2: CLASSIFY
            if progress_callback:
                progress_callback("CLASSIFY", 20, "Classifying pages...")

            classify_result = self._stage_classify(pages)
            result.stage_results.append(classify_result)

            # Stage 3: CROP
            if progress_callback:
                progress_callback("CROP", 40, "Detecting regions...")

            crop_result = self._stage_crop(pages)
            result.stage_results.append(crop_result)

            # Stage 4: EXTRACT
            if progress_callback:
                progress_callback("EXTRACT", 60, "Extracting data...")

            page_results, extract_result = self._stage_extract(pages)
            result.stage_results.append(extract_result)
            result.page_results = page_results

            # Stage 5: MERGE
            if progress_callback:
                progress_callback("MERGE", 80, "Merging results...")

            project_result, merge_result = self._stage_merge(page_results)
            result.stage_results.append(merge_result)
            result.project_result = project_result

            # Collect warnings
            for stage in result.stage_results:
                result.warnings.extend(stage.warnings)

            if progress_callback:
                progress_callback("COMPLETE", 100, "Done!")

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            result.success = False
            result.errors.append(str(e))

        result.total_processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    # =========================================================================
    # Stage 1: INGEST
    # =========================================================================

    def _stage_ingest(self, pdf_path: Path) -> Tuple[List[DocumentPage], PipelineStageResult]:
        """
        Ingest PDF: Convert to pages with text and images.

        Uses PyMuPDF (fitz) for PDF processing.
        """
        stage_result = PipelineStageResult(stage_name="INGEST")
        pages: List[DocumentPage] = []
        start_time = time.time()

        try:
            doc = fitz.open(str(pdf_path))

            for page_idx in range(min(len(doc), self.config.max_pages)):
                page = doc[page_idx]

                # Create DocumentPage
                doc_page = self._process_page(
                    page,
                    page_idx,
                    pdf_path.name,
                )
                pages.append(doc_page)

            doc.close()
            stage_result.items_processed = len(pages)
            stage_result.success = True

        except Exception as e:
            logger.exception(f"Ingest error: {e}")
            stage_result.success = False
            stage_result.warnings.append(ExtractionWarning(
                code="INGEST_FAILED",
                message=str(e),
                severity=Severity.CRITICAL,
                source_stage="ingest",
            ))

        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)
        return pages, stage_result

    def _ingest_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
    ) -> Tuple[List[DocumentPage], PipelineStageResult]:
        """Ingest PDF from bytes."""
        stage_result = PipelineStageResult(stage_name="INGEST")
        pages: List[DocumentPage] = []
        start_time = time.time()

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            for page_idx in range(min(len(doc), self.config.max_pages)):
                page = doc[page_idx]

                doc_page = self._process_page(
                    page,
                    page_idx,
                    filename,
                )
                pages.append(doc_page)

            doc.close()
            stage_result.items_processed = len(pages)
            stage_result.success = True

        except Exception as e:
            logger.exception(f"Ingest error: {e}")
            stage_result.success = False
            stage_result.warnings.append(ExtractionWarning(
                code="INGEST_FAILED",
                message=str(e),
                severity=Severity.CRITICAL,
                source_stage="ingest",
            ))

        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)
        return pages, stage_result

    def _process_page(
        self,
        page: Any,  # fitz.Page
        page_idx: int,
        filename: str,
    ) -> DocumentPage:
        """Process a single PDF page."""
        doc_page = DocumentPage(
            page_id=f"{filename}_page{page_idx + 1}",
            page_index=page_idx,
            page_number=page_idx + 1,
            source_document=filename,
            width_px=int(page.rect.width),
            height_px=int(page.rect.height),
            dpi=self.config.render_dpi,
        )

        # Extract raw text
        doc_page.raw_text = page.get_text("text")

        # Extract text blocks with positions
        text_blocks = extract_text_blocks(page)
        doc_page.text_blocks = [
            TextBlockModel(
                text=tb.text,
                bbox=BoundingBox(
                    x0=tb.x0, y0=tb.y0, x1=tb.x1, y1=tb.y1,
                    page_width=int(page.rect.width),
                    page_height=int(page.rect.height),
                ),
                font_size=getattr(tb, 'font_size', 0.0),
            )
            for tb in text_blocks
        ]

        # Render page image if debug mode
        if self.config.save_page_images and self.debug_saver:
            try:
                mat = fitz.Matrix(self.config.render_dpi / 72, self.config.render_dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                import base64
                doc_page.image_base64 = base64.b64encode(img_bytes).decode()
            except Exception as e:
                logger.warning(f"Failed to render page image: {e}")

        return doc_page

    # =========================================================================
    # Stage 2: CLASSIFY
    # =========================================================================

    def _stage_classify(self, pages: List[DocumentPage]) -> PipelineStageResult:
        """
        Classify each page using keyword matching.

        Uses KeywordClassifier with weighted rules.
        """
        stage_result = PipelineStageResult(stage_name="CLASSIFY")
        start_time = time.time()

        for page in pages:
            try:
                # Get drawing number if present
                drawing_number = ""
                dwg_info = parse_drawing_number(page.raw_text[:500])
                if dwg_info.valid:
                    drawing_number = dwg_info.raw

                # Classify using keyword matcher
                class_result = self.classifier.classify(
                    page.raw_text,
                    drawing_number=drawing_number,
                )

                # Map classifier PageType to models PageType
                page_type_map = {
                    ClassifierPageType.REGISTER: PageType.REGISTER,
                    ClassifierPageType.SLD: PageType.SLD,
                    ClassifierPageType.LAYOUT_LIGHTING: PageType.LAYOUT_LIGHTING,
                    ClassifierPageType.LAYOUT_PLUGS: PageType.LAYOUT_PLUGS,
                    ClassifierPageType.LAYOUT_COMBINED: PageType.LAYOUT_COMBINED,
                    ClassifierPageType.OUTSIDE_LIGHTS: PageType.OUTSIDE_LIGHTS,
                    ClassifierPageType.SCHEDULE: PageType.SCHEDULE,
                    ClassifierPageType.DETAIL: PageType.DETAIL,
                    ClassifierPageType.SPECIFICATION: PageType.SPECIFICATION,
                    ClassifierPageType.UNKNOWN: PageType.UNKNOWN,
                }

                page.classification = PageClassification(
                    page_type=page_type_map.get(class_result.page_type, PageType.UNKNOWN),
                    confidence=class_result.confidence,
                    matched_rules=class_result.matched_rules,
                    drawing_number=class_result.drawing_number or drawing_number,
                    building_block=class_result.building_block,
                    keyword_scores=class_result.keyword_scores,
                )

                # Low confidence warning
                if class_result.confidence < self.config.classification_threshold:
                    page.warnings.append(ExtractionWarning(
                        code="LOW_CLASSIFICATION_CONFIDENCE",
                        message=f"Page {page.page_number} classified as {class_result.page_type.value} with low confidence ({class_result.confidence:.1%})",
                        severity=Severity.WARNING,
                        page_number=page.page_number,
                        source_stage="classify",
                    ))

            except Exception as e:
                logger.warning(f"Classification error on page {page.page_number}: {e}")
                page.warnings.append(ExtractionWarning(
                    code="CLASSIFY_ERROR",
                    message=str(e),
                    severity=Severity.WARNING,
                    page_number=page.page_number,
                    source_stage="classify",
                ))

        stage_result.items_processed = len(pages)
        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)

        # Count by type
        type_counts = {}
        for page in pages:
            pt = page.classification.page_type.value
            type_counts[pt] = type_counts.get(pt, 0) + 1
        stage_result.data["type_counts"] = type_counts

        return stage_result

    # =========================================================================
    # Stage 3: CROP
    # =========================================================================

    def _stage_crop(self, pages: List[DocumentPage]) -> PipelineStageResult:
        """
        Detect regions on each page (title block, legend, schedule, main drawing).

        Uses OpenCV if available, falls back to heuristics.
        """
        stage_result = PipelineStageResult(stage_name="CROP")
        start_time = time.time()

        for page in pages:
            try:
                # Convert text blocks to format expected by crop module
                text_blocks_for_crop = [
                    type('TextBlock', (), {
                        'text': tb.text,
                        'x0': tb.bbox.x0,
                        'y0': tb.bbox.y0,
                        'x1': tb.bbox.x1,
                        'y1': tb.bbox.y1,
                    })()
                    for tb in page.text_blocks
                ]

                # Detect regions
                regions = detect_page_regions(
                    page_width=page.width_px,
                    page_height=page.height_px,
                    text_blocks=text_blocks_for_crop,
                    enable_opencv=self.config.enable_opencv_region_detection,
                    fallback_to_heuristic=self.config.fallback_to_heuristic_regions,
                )

                page.regions = regions

            except Exception as e:
                logger.warning(f"Crop error on page {page.page_number}: {e}")
                page.warnings.append(ExtractionWarning(
                    code="CROP_ERROR",
                    message=str(e),
                    severity=Severity.WARNING,
                    page_number=page.page_number,
                    source_stage="crop",
                ))

        stage_result.items_processed = len(pages)
        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)
        return stage_result

    # =========================================================================
    # Stage 4: EXTRACT
    # =========================================================================

    def _stage_extract(
        self,
        pages: List[DocumentPage],
    ) -> Tuple[List[PageExtractionResult], PipelineStageResult]:
        """
        Extract data from each page using type-specific extractors.
        """
        stage_result = PipelineStageResult(stage_name="EXTRACT")
        page_results: List[PageExtractionResult] = []
        start_time = time.time()

        for page in pages:
            try:
                page_result = self._extract_page(page)
                page_results.append(page_result)
                page.extraction_complete = True

            except Exception as e:
                logger.warning(f"Extract error on page {page.page_number}: {e}")
                page.warnings.append(ExtractionWarning(
                    code="EXTRACT_ERROR",
                    message=str(e),
                    severity=Severity.WARNING,
                    page_number=page.page_number,
                    source_stage="extract",
                ))

                # Create empty result
                page_results.append(PageExtractionResult(
                    page_id=page.page_id,
                    page_number=page.page_number,
                    page_type=page.classification.page_type,
                    success=False,
                ))

        stage_result.items_processed = len(pages)
        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)

        # Count successful extractions
        successful = sum(1 for pr in page_results if pr.success)
        stage_result.data["successful_extractions"] = successful

        return page_results, stage_result

    def _extract_page(self, page: DocumentPage) -> PageExtractionResult:
        """Extract data from a single page based on its type."""
        page_type = page.classification.page_type

        result = PageExtractionResult(
            page_id=page.page_id,
            page_number=page.page_number,
            page_type=page_type,
            drawing_number=page.classification.drawing_number,
            building_block=page.classification.building_block,
        )

        # Get region-specific text
        title_block_text = self._get_region_text(page, "title_block")
        legend_text = self._get_region_text(page, "legend")
        schedule_text = self._get_region_text(page, "schedule")

        # Convert text_blocks to list format for extractors
        text_blocks = [
            type('TextBlock', (), {
                'text': tb.text,
                'x0': tb.bbox.x0,
                'y0': tb.bbox.y0,
                'x1': tb.bbox.x1,
                'y1': tb.bbox.y1,
            })()
            for tb in page.text_blocks
        ]

        try:
            if page_type == PageType.REGISTER:
                extraction = self.register_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                )
                result.register_data = extraction
                result.success = True

            elif page_type == PageType.SLD:
                extraction = self.sld_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                    schedule_region_text=schedule_text,
                    title_block_text=title_block_text,
                )
                result.sld_data = extraction
                result.success = True

            elif page_type == PageType.LAYOUT_LIGHTING:
                extraction = self.lighting_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                    legend_region_text=legend_text,
                    title_block_text=title_block_text,
                )
                result.layout_data = extraction
                result.success = True

            elif page_type == PageType.LAYOUT_PLUGS:
                extraction = self.plugs_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                    legend_region_text=legend_text,
                    title_block_text=title_block_text,
                )
                result.layout_data = extraction
                result.success = True

            elif page_type == PageType.LAYOUT_COMBINED:
                # Process as both lighting and plugs
                lighting_extraction = self.lighting_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                )
                plugs_extraction = self.plugs_extractor.extract(
                    text=page.raw_text,
                    text_blocks=text_blocks,
                    page_number=page.page_number,
                )

                # Merge into layout_data
                result.layout_data = LayoutExtraction(
                    layout_type="combined",
                    drawing_number=lighting_extraction.drawing_number or plugs_extraction.drawing_number,
                    room_labels=list(set(lighting_extraction.room_labels + plugs_extraction.room_labels)),
                    circuit_refs=list(set(lighting_extraction.circuit_refs + plugs_extraction.circuit_refs)),
                    legend_items=list(set(lighting_extraction.legend_items + plugs_extraction.legend_items)),
                    source_page=page.page_number,
                )
                result.success = True

            else:
                # Unknown or unsupported page type
                result.success = False
                result.warnings.append(ExtractionWarning(
                    code="UNSUPPORTED_PAGE_TYPE",
                    message=f"No extractor for page type: {page_type.value}",
                    severity=Severity.INFO,
                    page_number=page.page_number,
                    source_stage="extract",
                ))

        except Exception as e:
            logger.warning(f"Extraction error: {e}")
            result.success = False
            result.warnings.append(ExtractionWarning(
                code="EXTRACT_EXCEPTION",
                message=str(e),
                severity=Severity.WARNING,
                page_number=page.page_number,
                source_stage="extract",
            ))

        return result

    def _get_region_text(self, page: DocumentPage, region_name: str) -> str:
        """Get text from a specific region of the page."""
        region = getattr(page.regions, region_name, None)
        if region is None:
            return ""

        # Filter text blocks within region
        region_text = []
        for tb in page.text_blocks:
            if (tb.bbox.x0 >= region.x0 and tb.bbox.x1 <= region.x1 and
                tb.bbox.y0 >= region.y0 and tb.bbox.y1 <= region.y1):
                region_text.append(tb.text)

        return "\n".join(region_text)

    # =========================================================================
    # Stage 5: MERGE
    # =========================================================================

    def _stage_merge(
        self,
        page_results: List[PageExtractionResult],
    ) -> Tuple[ProjectExtractionResult, PipelineStageResult]:
        """
        Merge page extractions into project-level result.
        """
        stage_result = PipelineStageResult(stage_name="MERGE")
        start_time = time.time()

        try:
            project_result = merge_page_results(page_results)

            # Validate coverage and add warnings
            coverage_warnings = validate_coverage(project_result)
            project_result.all_warnings.extend(coverage_warnings)
            stage_result.warnings.extend(coverage_warnings)

            stage_result.success = True

        except Exception as e:
            logger.exception(f"Merge error: {e}")
            stage_result.success = False
            stage_result.warnings.append(ExtractionWarning(
                code="MERGE_ERROR",
                message=str(e),
                severity=Severity.WARNING,
                source_stage="merge",
            ))
            project_result = ProjectExtractionResult()

        stage_result.processing_time_ms = int((time.time() - start_time) * 1000)
        return project_result, stage_result


# ============================================================================
# Convenience Functions
# ============================================================================

def run_deterministic_pipeline(
    pdf_path: Path,
    config: Optional[PipelineConfig] = None,
    progress_callback: Optional[callable] = None,
) -> DeterministicPipelineResult:
    """
    Run the deterministic pipeline on a PDF file.

    Args:
        pdf_path: Path to PDF file
        config: Pipeline configuration (optional)
        progress_callback: Progress callback (optional)

    Returns:
        DeterministicPipelineResult
    """
    pipeline = DeterministicPipeline(config)
    return pipeline.process_pdf(pdf_path, progress_callback)


def run_deterministic_pipeline_bytes(
    pdf_bytes: bytes,
    filename: str = "document.pdf",
    config: Optional[PipelineConfig] = None,
    progress_callback: Optional[callable] = None,
) -> DeterministicPipelineResult:
    """
    Run the deterministic pipeline on PDF bytes.

    Args:
        pdf_bytes: PDF file bytes
        filename: Original filename
        config: Pipeline configuration (optional)
        progress_callback: Progress callback (optional)

    Returns:
        DeterministicPipelineResult
    """
    pipeline = DeterministicPipeline(config)
    return pipeline.process_bytes(pdf_bytes, filename, progress_callback)


def quick_extract(pdf_path: Path) -> ProjectExtractionResult:
    """
    Quick extraction with default settings.

    Args:
        pdf_path: Path to PDF file

    Returns:
        ProjectExtractionResult or empty result on failure
    """
    result = run_deterministic_pipeline(pdf_path)
    return result.project_result or ProjectExtractionResult()
