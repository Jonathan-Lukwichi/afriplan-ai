"""
AfriPlan AI Agent - 6-Stage Pipeline Orchestrator

Implements the core AI pipeline for document analysis and quotation generation.

Stages:
1. INGEST - Convert PDF/image to Claude-ready format
2. CLASSIFY - Fast tier routing using Haiku 4.5
3. DISCOVER - JSON extraction using Sonnet 4.5 (escalate to Opus if needed)
4. VALIDATE - SANS 10142-1 compliance checking
5. PRICE - Deterministic pricing using constants.py
6. OUTPUT - Generate BQ, PDF, Excel

Golden Rule: Claude reads & interprets, Python calculates & prices.
"""

import os
import io
import json
import time
import base64
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union

# Optional imports with graceful degradation
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class PipelineStage(Enum):
    """The 6 stages of the AfriPlan AI pipeline."""
    INGEST = "ingest"
    CLASSIFY = "classify"
    DISCOVER = "discover"
    VALIDATE = "validate"
    PRICE = "price"
    OUTPUT = "output"


class ServiceTier(Enum):
    """The 3 service tiers supported by AfriPlan v3.0."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence levels for extracted data."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class StageResult:
    """Result from a single pipeline stage."""
    stage: PipelineStage
    success: bool
    data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    processing_time_ms: float
    model_used: Optional[str] = None
    tokens_used: int = 0
    cost_zar: float = 0.0  # API cost for this stage in ZAR
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationFlag:
    """A single validation result."""
    rule_name: str
    passed: bool
    severity: str  # "critical", "major", "minor", "info"
    message: str
    auto_corrected: bool = False
    corrected_value: Any = None


@dataclass
class PipelineResult:
    """Complete result from the 6-stage pipeline."""
    success: bool
    stages: List[StageResult]
    final_tier: ServiceTier
    extracted_data: Dict[str, Any]
    validated_data: Dict[str, Any]
    bq_items: List[Dict[str, Any]]
    total_cost: float
    overall_confidence: float
    escalated_to_opus: bool = False
    validation_flags: List[ValidationFlag] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_processing_time_ms: float = 0.0
    total_tokens_used: int = 0
    total_api_cost_zar: float = 0.0


class AfriPlanAgent:
    """
    Main orchestrator for the 6-stage AI pipeline.

    Model Strategy:
    - Haiku 4.5: Classification (fast, ~R0.18 per doc)
    - Sonnet 4.5: Extraction (balanced, ~R1.50-2.25 per doc)
    - Opus 4.6: Escalation when confidence <70%

    Usage:
        agent = AfriPlanAgent(api_key="sk-ant-...")
        result = agent.process_document(file_bytes, "pdf", "floor_plan.pdf")

        if result.success:
            print(f"Tier: {result.final_tier}")
            print(f"Total: R{result.total_cost:,.2f}")
    """

    # Model identifiers
    MODEL_HAIKU = "claude-3-5-haiku-20241022"
    MODEL_SONNET = "claude-sonnet-4-20250514"
    MODEL_OPUS = "claude-opus-4-20250514"

    # Confidence threshold for escalation
    CONFIDENCE_THRESHOLD = 0.70

    # API cost estimates in ZAR (approximate)
    COST_PER_1K_INPUT = {
        "haiku": 0.015,
        "sonnet": 0.045,
        "opus": 0.225,
    }
    COST_PER_1K_OUTPUT = {
        "haiku": 0.075,
        "sonnet": 0.225,
        "opus": 1.125,
    }

    # Image processing settings
    MAX_IMAGE_SIZE = 2048  # Max dimension in pixels
    TARGET_DPI = 150  # DPI for PDF conversion
    MAX_PAGES = 5  # Max pages to process from PDF

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AfriPlan AI Agent.

        Args:
            api_key: Anthropic API key. If not provided, tries to get from:
                     1. Environment variable ANTHROPIC_API_KEY
                     2. Streamlit secrets
        """
        self.api_key = api_key or self._get_api_key()
        self.client = None
        self.available = False

        if self.api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.available = True
            except Exception as e:
                self.available = False
                print(f"Warning: Failed to initialize Anthropic client: {e}")

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or Streamlit secrets."""
        # Try environment variable first
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            return api_key

        # Try Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
                return st.secrets['ANTHROPIC_API_KEY']
        except Exception:
            pass

        return None

    def process_document(
        self,
        file_bytes: bytes,
        file_type: str,
        filename: str,
        skip_pricing: bool = False,
        custom_prompts: Optional[Dict[str, str]] = None,
    ) -> PipelineResult:
        """
        Run the full 6-stage pipeline on a document.

        Args:
            file_bytes: Raw bytes of the uploaded file
            file_type: File type ("pdf", "png", "jpg", "jpeg")
            filename: Original filename for context
            skip_pricing: If True, skip PRICE stage (useful for preview)
            custom_prompts: Optional custom prompts to override defaults

        Returns:
            PipelineResult with all stage results and final quotation
        """
        start_time = time.time()
        stages: List[StageResult] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Initialize result with defaults
        result = PipelineResult(
            success=False,
            stages=[],
            final_tier=ServiceTier.UNKNOWN,
            extracted_data={},
            validated_data={},
            bq_items=[],
            total_cost=0.0,
            overall_confidence=0.0,
        )

        try:
            # STAGE 1: INGEST
            ingest_result = self._stage_ingest(file_bytes, file_type, filename)
            stages.append(ingest_result)

            if not ingest_result.success:
                errors.extend(ingest_result.errors)
                result.stages = stages
                result.errors = errors
                return result

            images = ingest_result.data.get("images", [])
            text_content = ingest_result.data.get("text", "")

            # STAGE 2: CLASSIFY
            classify_result = self._stage_classify(images, text_content, filename)
            stages.append(classify_result)

            if not classify_result.success:
                errors.extend(classify_result.errors)
                result.stages = stages
                result.errors = errors
                return result

            tier = ServiceTier(classify_result.data.get("tier", "unknown"))
            result.final_tier = tier

            # STAGE 3: DISCOVER
            discover_result = self._stage_discover(
                images, text_content, tier, custom_prompts
            )
            stages.append(discover_result)

            if not discover_result.success:
                errors.extend(discover_result.errors)
                warnings.extend(discover_result.warnings)
                result.stages = stages
                result.errors = errors
                result.warnings = warnings
                return result

            extracted_data = discover_result.data.get("extraction", {})
            result.extracted_data = extracted_data
            result.escalated_to_opus = discover_result.data.get("escalated", False)

            # STAGE 4: VALIDATE
            validate_result = self._stage_validate(extracted_data, tier)
            stages.append(validate_result)

            validated_data = validate_result.data.get("validated_data", extracted_data)
            result.validated_data = validated_data
            result.validation_flags = [
                ValidationFlag(**f) for f in validate_result.data.get("flags", [])
            ]
            warnings.extend(validate_result.warnings)

            # STAGE 5: PRICE (unless skipped)
            if not skip_pricing:
                price_result = self._stage_price(validated_data, tier)
                stages.append(price_result)

                if price_result.success:
                    result.bq_items = price_result.data.get("bq_items", [])
                    result.total_cost = price_result.data.get("total_cost", 0.0)
                else:
                    warnings.extend(price_result.warnings)

            # STAGE 6: OUTPUT (generate summary)
            output_result = self._stage_output(
                validated_data,
                result.bq_items,
                tier,
                result.total_cost
            )
            stages.append(output_result)

            # Calculate overall metrics
            result.stages = stages
            result.overall_confidence = self._calculate_overall_confidence(stages)
            result.total_processing_time_ms = (time.time() - start_time) * 1000
            result.total_tokens_used = sum(s.tokens_used for s in stages)
            result.total_api_cost_zar = self._calculate_api_cost(stages)
            result.errors = errors
            result.warnings = warnings
            result.success = True

        except Exception as e:
            errors.append(f"Pipeline error: {str(e)}")
            result.stages = stages
            result.errors = errors
            result.total_processing_time_ms = (time.time() - start_time) * 1000

        return result

    def _stage_ingest(
        self,
        file_bytes: bytes,
        file_type: str,
        filename: str
    ) -> StageResult:
        """
        Stage 1: INGEST - Convert document to Claude-ready format.

        Processes PDF and image files into base64-encoded images and text.
        """
        start_time = time.time()
        data: Dict[str, Any] = {"images": [], "text": "", "page_count": 0}
        errors: List[str] = []

        try:
            # Handle both MIME types and file extensions
            # Strip whitespace and normalize
            file_type = file_type.lower().strip().strip('.')

            # Convert MIME types to extensions
            mime_to_ext = {
                "application/pdf": "pdf",
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/bmp": "bmp",
                "image/tiff": "tiff",
                "image/gif": "gif",
            }

            # Check exact match first
            if file_type in mime_to_ext:
                file_type = mime_to_ext[file_type]
            # Check if file_type contains a known MIME type (handle extra chars)
            elif "/" in file_type:
                for mime, ext in mime_to_ext.items():
                    if mime in file_type:
                        file_type = ext
                        break

            # Also try extracting from filename if still not recognized
            if file_type not in ("pdf", "png", "jpg", "jpeg", "bmp", "tiff", "gif"):
                ext = filename.rsplit(".", 1)[-1].lower().strip() if "." in filename else ""
                if ext in ("pdf", "png", "jpg", "jpeg", "bmp", "tiff", "gif"):
                    file_type = ext

            if file_type == "pdf":
                if not PDF_AVAILABLE:
                    errors.append("PDF processing unavailable: PyMuPDF not installed")
                    return StageResult(
                        stage=PipelineStage.INGEST,
                        success=False,
                        data=data,
                        confidence=0.0,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        errors=errors
                    )

                # Process PDF
                pdf = fitz.open(stream=file_bytes, filetype="pdf")
                page_count = min(len(pdf), self.MAX_PAGES)
                data["page_count"] = page_count

                for i in range(page_count):
                    page = pdf[i]
                    # Extract as image
                    pix = page.get_pixmap(dpi=self.TARGET_DPI)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img = self._resize_image(img)
                    data["images"].append(self._to_base64(img))

                    # Also extract text
                    text = page.get_text()
                    if text.strip():
                        data["text"] += f"\n--- Page {i+1} ---\n{text}"

                pdf.close()

            elif file_type in ("png", "jpg", "jpeg", "bmp", "tiff"):
                if not PILLOW_AVAILABLE:
                    errors.append("Image processing unavailable: Pillow not installed")
                    return StageResult(
                        stage=PipelineStage.INGEST,
                        success=False,
                        data=data,
                        confidence=0.0,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        errors=errors
                    )

                # Process image
                img = Image.open(io.BytesIO(file_bytes))
                data["page_count"] = 1

                # Enhance for better AI reading
                if img.mode != "RGB":
                    img = img.convert("RGB")
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)

                img = self._resize_image(img)
                data["images"].append(self._to_base64(img))

            else:
                errors.append(f"Unsupported file type: {file_type}")
                return StageResult(
                    stage=PipelineStage.INGEST,
                    success=False,
                    data=data,
                    confidence=0.0,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    errors=errors
                )

            # Add filename context
            data["filename"] = filename

            return StageResult(
                stage=PipelineStage.INGEST,
                success=len(data["images"]) > 0,
                data=data,
                confidence=1.0 if data["images"] else 0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            errors.append(f"Ingest error: {str(e)}")
            return StageResult(
                stage=PipelineStage.INGEST,
                success=False,
                data=data,
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                errors=errors
            )

    def _stage_classify(
        self,
        images: List[str],
        text_content: str,
        filename: str
    ) -> StageResult:
        """
        Stage 2: CLASSIFY - Fast tier routing using Haiku 4.5.

        Determines project type: residential, commercial, or maintenance.
        """
        start_time = time.time()

        if not self.available:
            # Fallback to filename-based classification
            return self._fallback_classify(filename, start_time)

        try:
            from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT
            from agent.classifier import CLASSIFICATION_PROMPT
        except ImportError:
            # Use inline prompt if imports fail
            CLASSIFICATION_PROMPT = self._get_classification_prompt()
            SA_ELECTRICAL_SYSTEM_PROMPT = ""

        try:
            # Build message content
            content = []

            # Add first image (enough for classification)
            if images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": images[0]
                    }
                })

            # Add text context
            if text_content:
                content.append({
                    "type": "text",
                    "text": f"Document text (first 2000 chars):\n{text_content[:2000]}"
                })

            content.append({
                "type": "text",
                "text": f"Filename: {filename}\n\nClassify this electrical project."
            })

            # Call Haiku for fast classification
            response = self.client.messages.create(
                model=self.MODEL_HAIKU,
                max_tokens=300,
                system=CLASSIFICATION_PROMPT,
                messages=[{"role": "user", "content": content}]
            )

            # Parse response
            response_text = response.content[0].text
            result = self._parse_json_response(response_text)

            # Extract and normalize tier
            raw_tier = result.get("tier", "unknown")
            if isinstance(raw_tier, str):
                tier = raw_tier.lower().strip()
            else:
                tier = "unknown"

            # Map variations to standard tiers
            tier_mapping = {
                "residential": "residential",
                "res": "residential",
                "house": "residential",
                "home": "residential",
                "domestic": "residential",
                "commercial": "commercial",
                "com": "commercial",
                "office": "commercial",
                "business": "commercial",
                "maintenance": "maintenance",
                "maint": "maintenance",
                "coc": "maintenance",
                "repair": "maintenance",
            }
            tier = tier_mapping.get(tier, tier)

            # If still unknown and we have images, default to residential
            if tier not in ("residential", "commercial", "maintenance"):
                tier = "residential"  # Most common case
                result["reasoning"] = (result.get("reasoning", "") +
                    " [Note: Classification uncertain, defaulted to residential]")

            confidence = self._parse_confidence(result.get("confidence", "medium"))
            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost_zar = self._calculate_stage_cost("haiku", tokens)

            return StageResult(
                stage=PipelineStage.CLASSIFY,
                success=True,
                data={
                    "tier": tier,
                    "subtype": result.get("subtype"),
                    "reasoning": result.get("reasoning", ""),
                    "raw_response": response_text,
                },
                confidence=confidence,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_used=self.MODEL_HAIKU,
                tokens_used=tokens,
                cost_zar=cost_zar,
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.CLASSIFY,
                success=False,
                data={"tier": "unknown"},
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                errors=[f"Classification error: {str(e)}"]
            )

    def _stage_discover(
        self,
        images: List[str],
        text_content: str,
        tier: ServiceTier,
        custom_prompts: Optional[Dict[str, str]] = None
    ) -> StageResult:
        """
        Stage 3: DISCOVER - JSON extraction using Sonnet 4.5.

        Extracts structured data from the document. Escalates to Opus if confidence is low.
        """
        start_time = time.time()
        escalated = False

        if not self.available:
            return self._fallback_discover(tier, start_time)

        # Get tier-specific prompt
        discovery_prompt = self._get_discovery_prompt(tier, custom_prompts)

        try:
            # Build content with all images
            content = []
            for img in images[:self.MAX_PAGES]:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img
                    }
                })

            if text_content:
                content.append({
                    "type": "text",
                    "text": f"Document text:\n{text_content[:4000]}"
                })

            content.append({
                "type": "text",
                "text": "Extract all electrical data from this document."
            })

            # First attempt with Sonnet
            response = self.client.messages.create(
                model=self.MODEL_SONNET,
                max_tokens=2000,
                system=discovery_prompt,
                messages=[{"role": "user", "content": content}]
            )

            response_text = response.content[0].text
            extraction = self._parse_json_response(response_text)
            confidence = self._evaluate_extraction_confidence(extraction)

            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            model_used = self.MODEL_SONNET

            # Check if escalation needed
            if confidence < self.CONFIDENCE_THRESHOLD:
                # Escalate to Opus
                escalated = True

                response = self.client.messages.create(
                    model=self.MODEL_OPUS,
                    max_tokens=2500,
                    system=discovery_prompt + "\n\nIMPORTANT: Previous extraction had low confidence. Be thorough and explicit about confidence levels.",
                    messages=[{"role": "user", "content": content}]
                )

                response_text = response.content[0].text
                extraction = self._parse_json_response(response_text)
                confidence = self._evaluate_extraction_confidence(extraction)
                tokens_used += response.usage.input_tokens + response.usage.output_tokens
                model_used = self.MODEL_OPUS

            warnings = []
            if confidence < 0.5:
                warnings.append("Low confidence extraction - recommend manual verification")

            # Calculate cost based on model used
            model_type = "opus" if escalated else "sonnet"
            cost_zar = self._calculate_stage_cost(model_type, tokens_used)

            return StageResult(
                stage=PipelineStage.DISCOVER,
                success=True,
                data={
                    "extraction": extraction,
                    "escalated": escalated,
                    "raw_response": response_text,
                },
                confidence=confidence,
                processing_time_ms=(time.time() - start_time) * 1000,
                model_used=model_used,
                tokens_used=tokens_used,
                cost_zar=cost_zar,
                warnings=warnings,
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.DISCOVER,
                success=False,
                data={"extraction": {}},
                confidence=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                errors=[f"Discovery error: {str(e)}"]
            )

    def _stage_validate(
        self,
        extracted_data: Dict[str, Any],
        tier: ServiceTier
    ) -> StageResult:
        """
        Stage 4: VALIDATE - SANS 10142-1 compliance checking.

        Runs Python hard rules and optionally Claude soft checks.
        """
        start_time = time.time()
        flags = []
        validated_data = extracted_data.copy()
        warnings = []

        try:
            # Import validator
            from utils.validators import SANS10142Validator
            validator = SANS10142Validator()

            if tier == ServiceTier.RESIDENTIAL:
                report = validator.validate_residential(extracted_data)
            elif tier == ServiceTier.COMMERCIAL:
                report = validator.validate_commercial(extracted_data)
            elif tier == ServiceTier.MAINTENANCE:
                report = validator.validate_maintenance(extracted_data)
            else:
                report = validator.validate_residential(extracted_data)  # Default

            flags = [
                {
                    "rule_name": r.rule_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message,
                    "auto_corrected": r.auto_corrected,
                    "corrected_value": r.corrected_value,
                }
                for r in report.results
            ]

            # Apply auto-corrections
            if report.auto_corrections_made > 0:
                validated_data = validator.apply_corrections(extracted_data, report.results)
                warnings.append(f"{report.auto_corrections_made} items auto-corrected for compliance")

            confidence = 1.0 if report.passed else 0.7

        except ImportError:
            # Validator not available, run basic checks
            flags, validated_data = self._basic_validation(extracted_data, tier)
            confidence = 0.8
            warnings.append("Full SANS 10142-1 validation unavailable")
        except Exception as e:
            flags = []
            confidence = 0.5
            warnings.append(f"Validation error: {str(e)}")

        return StageResult(
            stage=PipelineStage.VALIDATE,
            success=True,
            data={
                "validated_data": validated_data,
                "flags": flags,
            },
            confidence=confidence,
            processing_time_ms=(time.time() - start_time) * 1000,
            warnings=warnings,
        )

    def _stage_price(
        self,
        validated_data: Dict[str, Any],
        tier: ServiceTier
    ) -> StageResult:
        """
        Stage 5: PRICE - Deterministic calculation using Python only.

        No AI calls - purely algorithmic pricing from constants.py.
        """
        start_time = time.time()
        bq_items = []
        total_cost = 0.0
        warnings = []

        try:
            from utils.calculations import (
                calculate_electrical_requirements,
                calculate_load_and_circuits,
                calculate_electrical_bq,
                calculate_commercial_electrical,
            )
            from utils.constants import DEDICATED_CIRCUITS

            if tier == ServiceTier.RESIDENTIAL:
                # Convert extracted rooms to required format
                rooms = self._convert_rooms_for_calculation(validated_data)

                if rooms:
                    elec_req = calculate_electrical_requirements(rooms)
                    circuit_info = calculate_load_and_circuits(elec_req)
                    bq_items = calculate_electrical_bq(elec_req, circuit_info)

                    # Add dedicated circuits
                    dedicated = validated_data.get("dedicated_circuits", [])
                    for dc in dedicated:
                        if dc in DEDICATED_CIRCUITS:
                            item = DEDICATED_CIRCUITS[dc]
                            bq_items.append({
                                "category": "Dedicated Circuits",
                                "item": item["desc"],
                                "qty": 1,
                                "unit": "each",
                                "rate": item["total_cost"],
                                "total": item["total_cost"],
                            })

                    total_cost = sum(item.get("total", 0) for item in bq_items)
                else:
                    warnings.append("No rooms found in extraction - using defaults")

            elif tier == ServiceTier.COMMERCIAL:
                area_m2 = validated_data.get("gfa_m2", 500)
                building_type = validated_data.get("building_type", "office")
                floors = validated_data.get("floors", 1)

                result = calculate_commercial_electrical(
                    area_m2=area_m2,
                    building_type=building_type,
                    floors=floors,
                    emergency_power=validated_data.get("emergency_power", False),
                    fire_alarm=validated_data.get("fire_alarm", True),
                )

                bq_items = result.get("bq_items", [])
                total_cost = result.get("total_cost", 0)

            elif tier == ServiceTier.MAINTENANCE:
                # COC/Maintenance pricing
                bq_items, total_cost = self._calculate_maintenance_pricing(validated_data)

            else:
                warnings.append("Unknown tier - pricing skipped")

        except ImportError as e:
            warnings.append(f"Pricing module unavailable: {str(e)}")
        except Exception as e:
            warnings.append(f"Pricing error: {str(e)}")

        return StageResult(
            stage=PipelineStage.PRICE,
            success=True,
            data={
                "bq_items": bq_items,
                "total_cost": total_cost,
            },
            confidence=1.0,  # Pricing is deterministic
            processing_time_ms=(time.time() - start_time) * 1000,
            warnings=warnings,
        )

    def _stage_output(
        self,
        validated_data: Dict[str, Any],
        bq_items: List[Dict],
        tier: ServiceTier,
        total_cost: float
    ) -> StageResult:
        """
        Stage 6: OUTPUT - Generate summary and prepare for export.
        """
        start_time = time.time()

        # Generate summary
        summary = {
            "tier": tier.value,
            "item_count": len(bq_items),
            "total_cost": total_cost,
            "vat_amount": total_cost * 0.15,
            "total_incl_vat": total_cost * 1.15,
        }

        # Add tier-specific summary
        if tier == ServiceTier.RESIDENTIAL:
            summary["total_rooms"] = len(validated_data.get("rooms", []))
            summary["total_lights"] = validated_data.get("total_light_points", 0)
            summary["total_sockets"] = validated_data.get("total_socket_outlets", 0)
        elif tier == ServiceTier.COMMERCIAL:
            summary["gfa_m2"] = validated_data.get("gfa_m2", 0)
            summary["building_type"] = validated_data.get("building_type", "unknown")
        elif tier == ServiceTier.MAINTENANCE:
            summary["defect_count"] = len(validated_data.get("defects", []))
            summary["inspection_fee"] = validated_data.get("inspection_fee", 0)

        return StageResult(
            stage=PipelineStage.OUTPUT,
            success=True,
            data={
                "summary": summary,
                "ready_for_export": True,
            },
            confidence=1.0,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    # Helper methods

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize image keeping aspect ratio, max dimension MAX_IMAGE_SIZE."""
        w, h = img.size
        if max(w, h) > self.MAX_IMAGE_SIZE:
            ratio = self.MAX_IMAGE_SIZE / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        return img

    def _to_base64(self, img: Image.Image) -> str:
        """Convert PIL image to base64 string."""
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from Claude response, handling markdown code blocks."""
        text = text.strip()

        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {}

    def _parse_confidence(self, confidence_str: str) -> float:
        """Convert confidence string to float."""
        confidence_map = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.4,
        }
        return confidence_map.get(confidence_str.lower(), 0.5)

    def _evaluate_extraction_confidence(self, extraction: Dict[str, Any]) -> float:
        """Evaluate overall confidence of extraction based on completeness."""
        if not extraction:
            return 0.0

        # Count fields with values
        total_fields = 0
        filled_fields = 0
        high_confidence_fields = 0

        def count_fields(obj, path=""):
            nonlocal total_fields, filled_fields, high_confidence_fields

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.endswith("_confidence"):
                        continue
                    total_fields += 1
                    if value is not None and value != "" and value != []:
                        filled_fields += 1
                        # Check if there's a confidence field
                        conf_key = f"{key}_confidence"
                        if conf_key in obj:
                            if obj[conf_key] in ("high", "HIGH"):
                                high_confidence_fields += 1
                    if isinstance(value, (dict, list)):
                        count_fields(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    count_fields(item, f"{path}[{i}]")

        count_fields(extraction)

        if total_fields == 0:
            return 0.0

        fill_ratio = filled_fields / total_fields
        confidence_ratio = high_confidence_fields / filled_fields if filled_fields > 0 else 0

        # Weighted average
        return (fill_ratio * 0.6) + (confidence_ratio * 0.4)

    def _calculate_overall_confidence(self, stages: List[StageResult]) -> float:
        """Calculate weighted average confidence across all stages."""
        weights = {
            PipelineStage.INGEST: 0.1,
            PipelineStage.CLASSIFY: 0.15,
            PipelineStage.DISCOVER: 0.35,
            PipelineStage.VALIDATE: 0.2,
            PipelineStage.PRICE: 0.1,
            PipelineStage.OUTPUT: 0.1,
        }

        total_weight = 0
        weighted_sum = 0

        for stage in stages:
            weight = weights.get(stage.stage, 0.1)
            weighted_sum += stage.confidence * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calculate_api_cost(self, stages: List[StageResult]) -> float:
        """Calculate total API cost in ZAR."""
        total_cost = 0.0

        for stage in stages:
            if stage.model_used:
                model_type = "haiku"
                if "sonnet" in stage.model_used.lower():
                    model_type = "sonnet"
                elif "opus" in stage.model_used.lower():
                    model_type = "opus"

                # Rough estimate: assume 70% input, 30% output
                tokens = stage.tokens_used
                input_tokens = tokens * 0.7
                output_tokens = tokens * 0.3

                cost = (input_tokens / 1000) * self.COST_PER_1K_INPUT[model_type]
                cost += (output_tokens / 1000) * self.COST_PER_1K_OUTPUT[model_type]
                total_cost += cost

        return total_cost

    def _calculate_stage_cost(self, model_type: str, tokens: int) -> float:
        """Calculate API cost for a single stage in ZAR."""
        if model_type not in self.COST_PER_1K_INPUT:
            return 0.0

        # Rough estimate: assume 70% input, 30% output
        input_tokens = tokens * 0.7
        output_tokens = tokens * 0.3

        cost = (input_tokens / 1000) * self.COST_PER_1K_INPUT[model_type]
        cost += (output_tokens / 1000) * self.COST_PER_1K_OUTPUT[model_type]
        return cost

    def _convert_rooms_for_calculation(self, validated_data: Dict) -> List[Dict]:
        """Convert extracted room data to format expected by calculations.py."""
        rooms = validated_data.get("rooms", [])
        converted = []

        for room in rooms:
            area = room.get("area_m2", 16)
            side = area ** 0.5  # Assume square for width/height

            converted.append({
                "name": room.get("name", room.get("room_name", "Room")),
                "type": room.get("type", room.get("room_type", "Living Room")),
                "w": room.get("width", side),
                "h": room.get("height", side),
            })

        return converted

    def _calculate_maintenance_pricing(self, validated_data: Dict) -> Tuple[List[Dict], float]:
        """Calculate pricing for COC/maintenance work."""
        bq_items = []
        total = 0.0

        try:
            from utils.constants import COC_INSPECTION_FEES, COC_DEFECT_PRICING

            # Inspection fee
            property_type = validated_data.get("property_type", "standard")
            if property_type in COC_INSPECTION_FEES:
                fee = COC_INSPECTION_FEES[property_type]
                bq_items.append({
                    "category": "COC Inspection",
                    "item": fee["name"],
                    "qty": 1,
                    "unit": "each",
                    "rate": fee["base_fee"],
                    "total": fee["base_fee"],
                })
                total += fee["base_fee"]

                # Certificate fee
                cert_fee = fee.get("certificate_fee", 450)
                bq_items.append({
                    "category": "COC Inspection",
                    "item": "COC Certificate",
                    "qty": 1,
                    "unit": "each",
                    "rate": cert_fee,
                    "total": cert_fee,
                })
                total += cert_fee

            # Defect remedial items
            defects = validated_data.get("defects", [])
            for defect in defects:
                defect_code = defect if isinstance(defect, str) else defect.get("code", "")
                if defect_code in COC_DEFECT_PRICING:
                    item = COC_DEFECT_PRICING[defect_code]
                    qty = defect.get("qty", 1) if isinstance(defect, dict) else 1
                    bq_items.append({
                        "category": "Remedial Work",
                        "item": item["desc"],
                        "qty": qty,
                        "unit": "each",
                        "rate": item["total"],
                        "total": item["total"] * qty,
                    })
                    total += item["total"] * qty

        except ImportError:
            pass

        return bq_items, total

    def _fallback_classify(self, filename: str, start_time: float) -> StageResult:
        """Fallback classification using filename keywords."""
        filename_lower = filename.lower()

        tier = "unknown"
        confidence = 0.3
        reasoning = "Classified from filename keywords (API unavailable)"

        residential_keywords = ["house", "home", "bedroom", "residential", "dwelling"]
        commercial_keywords = ["office", "retail", "shop", "commercial", "business"]
        maintenance_keywords = ["coc", "inspection", "repair", "defect", "remedial"]

        for kw in maintenance_keywords:
            if kw in filename_lower:
                tier = "maintenance"
                confidence = 0.4
                break

        if tier == "unknown":
            for kw in commercial_keywords:
                if kw in filename_lower:
                    tier = "commercial"
                    confidence = 0.4
                    break

        if tier == "unknown":
            for kw in residential_keywords:
                if kw in filename_lower:
                    tier = "residential"
                    confidence = 0.4
                    break

        if tier == "unknown":
            tier = "residential"  # Default
            reasoning = "Defaulted to residential (no clear indicators)"

        return StageResult(
            stage=PipelineStage.CLASSIFY,
            success=True,
            data={
                "tier": tier,
                "reasoning": reasoning,
            },
            confidence=confidence,
            processing_time_ms=(time.time() - start_time) * 1000,
            warnings=["API unavailable - using fallback classification"],
        )

    def _fallback_discover(self, tier: ServiceTier, start_time: float) -> StageResult:
        """Fallback discovery with default values."""
        extraction = {}

        if tier == ServiceTier.RESIDENTIAL:
            extraction = {
                "project": {"dwelling_type": "house", "floors": 1},
                "rooms": [],
                "db_board": {"recommended_ways": 12, "elcb": True},
                "notes": ["Manual entry required - AI extraction unavailable"],
            }
        elif tier == ServiceTier.COMMERCIAL:
            extraction = {
                "project": {"building_type": "office", "floors": 1},
                "gfa_m2": 500,
                "areas": [],
                "notes": ["Manual entry required - AI extraction unavailable"],
            }
        elif tier == ServiceTier.MAINTENANCE:
            extraction = {
                "property": {"type": "house"},
                "work_type": "coc_inspection",
                "defects": [],
                "notes": ["Manual entry required - AI extraction unavailable"],
            }

        return StageResult(
            stage=PipelineStage.DISCOVER,
            success=True,
            data={
                "extraction": extraction,
                "escalated": False,
            },
            confidence=0.2,
            processing_time_ms=(time.time() - start_time) * 1000,
            warnings=["API unavailable - using default values, manual entry recommended"],
        )

    def _basic_validation(
        self,
        extracted_data: Dict,
        tier: ServiceTier
    ) -> Tuple[List[Dict], Dict]:
        """Basic validation when full validator unavailable."""
        flags = []
        validated = extracted_data.copy()

        # Basic ELCB check
        db_board = extracted_data.get("db_board", {})
        if not db_board.get("elcb"):
            flags.append({
                "rule_name": "ELCB Required",
                "passed": False,
                "severity": "critical",
                "message": "Earth leakage device (30mA) is mandatory",
                "auto_corrected": True,
                "corrected_value": True,
            })
            if "db_board" not in validated:
                validated["db_board"] = {}
            validated["db_board"]["elcb"] = True

        return flags, validated

    def _get_classification_prompt(self) -> str:
        """Get inline classification prompt."""
        return """You are an electrical project classifier for South African contractors.

Analyse the document and classify into EXACTLY ONE category:

- RESIDENTIAL — Houses, apartments, townhouses, estates, residential complexes
- COMMERCIAL — Offices, retail, restaurants, hospitals, schools, warehouses, hotels
- MAINTENANCE — COC inspections, electrical repairs, remedial works, DB upgrades, fault finding

Consider:
- Residential plans show bedrooms, kitchens, bathrooms, garages
- Commercial plans show office areas, reception, server rooms, parking, fire systems
- Maintenance inputs are typically property descriptions, DB board photos, or brief repair requests

Reply with ONLY a JSON object:
{
    "tier": "RESIDENTIAL" | "COMMERCIAL" | "MAINTENANCE",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "subtype": "optional subtype",
    "reasoning": "Brief explanation"
}"""

    def _get_discovery_prompt(
        self,
        tier: ServiceTier,
        custom_prompts: Optional[Dict[str, str]] = None
    ) -> str:
        """Get tier-specific discovery prompt."""
        if custom_prompts and tier.value in custom_prompts:
            return custom_prompts[tier.value]

        try:
            if tier == ServiceTier.RESIDENTIAL:
                from agent.prompts.residential_prompts import DISCOVERY_RESIDENTIAL
                return DISCOVERY_RESIDENTIAL
            elif tier == ServiceTier.COMMERCIAL:
                from agent.prompts.commercial_prompts import DISCOVERY_COMMERCIAL
                return DISCOVERY_COMMERCIAL
            elif tier == ServiceTier.MAINTENANCE:
                from agent.prompts.maintenance_prompts import DISCOVERY_MAINTENANCE
                return DISCOVERY_MAINTENANCE
        except ImportError:
            pass

        # Fallback to inline prompts
        return self._get_inline_discovery_prompt(tier)

    def _get_inline_discovery_prompt(self, tier: ServiceTier) -> str:
        """Get inline discovery prompt for tier."""
        base = """You are a senior South African electrical estimator.
Extract all electrical data from this document following SANS 10142-1 standards.
Respond in valid JSON matching the schema below.
Include confidence scores: HIGH (clearly visible), MEDIUM (inferred), LOW (assumed from standards).
"""

        if tier == ServiceTier.RESIDENTIAL:
            return base + """
Extract for RESIDENTIAL project:
{
    "project": {"dwelling_type": "", "floor_area_m2": 0, "bedrooms": 0, "bathrooms": 0, "floors": 1},
    "rooms": [
        {"room_name": "", "room_type": "", "area_m2": 0,
         "lights": {"count": 0, "confidence": ""},
         "sockets": {"singles": 0, "doubles": 0, "confidence": ""},
         "dedicated_circuits": []}
    ],
    "db_board": {"recommended_ways": 0, "elcb": true, "surge_protection": true},
    "outdoor": {"light_points": 0, "gate_motor": false, "pool": false},
    "total_light_points": 0,
    "total_socket_outlets": 0,
    "dedicated_circuits": []
}"""

        elif tier == ServiceTier.COMMERCIAL:
            return base + """
Extract for COMMERCIAL project:
{
    "project": {"building_type": "", "gfa_m2": 0, "floors": 0},
    "areas": [
        {"name": "", "type": "", "area_m2": 0, "power_density_wm2": 0}
    ],
    "distribution": {"msb_rating_a": 0, "sub_boards": []},
    "emergency": {"emergency_lights": 0, "exit_signs": 0, "fire_alarm": {}},
    "gfa_m2": 0,
    "building_type": ""
}"""

        else:  # MAINTENANCE
            return base + """
Extract for MAINTENANCE/COC project:
{
    "property": {"type": "", "size_m2": 0, "rooms": 0, "age_years": 0},
    "work_type": "coc_inspection|fault_repair|db_upgrade|remedial",
    "existing_installation": {"db_condition": "", "elcb_present": null},
    "defects": [],
    "property_type": "basic|standard|large"
}"""
