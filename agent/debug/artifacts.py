"""
AfriPlan Electrical - Debug Artifacts

Save debug artifacts during pipeline execution:
- Page images
- Region crop images
- Extraction results as JSON
- Debug logs

No AI/cloud APIs used.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime
from dataclasses import dataclass, field

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


@dataclass
class DebugConfig:
    """Configuration for debug output."""
    enabled: bool = False
    output_dir: str = "debug_output"
    save_page_images: bool = True
    save_region_crops: bool = True
    save_overlay_images: bool = True
    save_extraction_json: bool = True
    save_text_blocks: bool = True
    image_format: str = "png"
    image_quality: int = 85


class DebugArtifactSaver:
    """
    Saves debug artifacts during pipeline execution.

    Usage:
        saver = DebugArtifactSaver(config)
        saver.setup_run("project_name")
        saver.save_page_image(page_num, image)
        saver.save_extraction_result(result)
        saver.finalize()
    """

    def __init__(self, config: DebugConfig):
        """Initialize the artifact saver."""
        self.config = config
        self.run_dir: Optional[Path] = None
        self.run_id: str = ""
        self.metadata: Dict[str, Any] = {}

    def setup_run(self, project_name: str = "") -> Path:
        """
        Setup a new debug run directory.

        Args:
            project_name: Optional project name for directory naming

        Returns:
            Path to the run directory
        """
        if not self.config.enabled:
            return Path(".")

        # Create timestamp-based run ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:30]
        safe_name = safe_name.strip().replace(" ", "_") or "run"

        self.run_id = f"{timestamp}_{safe_name}"

        # Create directory structure
        self.run_dir = Path(self.config.output_dir) / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        if self.config.save_page_images:
            (self.run_dir / "pages").mkdir(exist_ok=True)

        if self.config.save_region_crops:
            (self.run_dir / "regions").mkdir(exist_ok=True)

        if self.config.save_overlay_images:
            (self.run_dir / "overlays").mkdir(exist_ok=True)

        # Initialize metadata
        self.metadata = {
            "run_id": self.run_id,
            "project_name": project_name,
            "started_at": datetime.now().isoformat(),
            "pages": [],
            "warnings": [],
        }

        logger.info(f"Debug artifacts will be saved to: {self.run_dir}")

        return self.run_dir

    def save_page_image(
        self,
        page_number: int,
        image: Any,
        suffix: str = "",
    ) -> Optional[Path]:
        """
        Save a page image.

        Args:
            page_number: Page number
            image: PIL Image or numpy array
            suffix: Optional suffix for filename

        Returns:
            Path to saved file
        """
        if not self.config.enabled or not self.config.save_page_images:
            return None

        if self.run_dir is None:
            logger.warning("Debug run not initialized")
            return None

        try:
            filename = f"page_{page_number:03d}{suffix}.{self.config.image_format}"
            filepath = self.run_dir / "pages" / filename

            if HAS_PIL:
                if hasattr(image, 'save'):
                    # PIL Image
                    image.save(str(filepath))
                else:
                    # Assume numpy array
                    Image.fromarray(image).save(str(filepath))
            else:
                logger.warning("PIL not available, skipping image save")
                return None

            return filepath

        except Exception as e:
            logger.error(f"Error saving page image: {e}")
            return None

    def save_region_crop(
        self,
        page_number: int,
        region_name: str,
        image: Any,
    ) -> Optional[Path]:
        """
        Save a cropped region image.

        Args:
            page_number: Page number
            region_name: Name of the region (title_block, legend, etc.)
            image: PIL Image or numpy array

        Returns:
            Path to saved file
        """
        if not self.config.enabled or not self.config.save_region_crops:
            return None

        if self.run_dir is None:
            return None

        try:
            filename = f"page_{page_number:03d}_{region_name}.{self.config.image_format}"
            filepath = self.run_dir / "regions" / filename

            if HAS_PIL and hasattr(image, 'save'):
                image.save(str(filepath))
            elif HAS_PIL:
                Image.fromarray(image).save(str(filepath))

            return filepath

        except Exception as e:
            logger.error(f"Error saving region crop: {e}")
            return None

    def save_overlay_image(
        self,
        page_number: int,
        image: Any,
        overlay_type: str = "regions",
    ) -> Optional[Path]:
        """
        Save an image with debug overlays.

        Args:
            page_number: Page number
            image: PIL Image or numpy array with overlays drawn
            overlay_type: Type of overlay (regions, text_blocks, etc.)

        Returns:
            Path to saved file
        """
        if not self.config.enabled or not self.config.save_overlay_images:
            return None

        if self.run_dir is None:
            return None

        try:
            filename = f"page_{page_number:03d}_{overlay_type}_overlay.{self.config.image_format}"
            filepath = self.run_dir / "overlays" / filename

            if HAS_PIL and hasattr(image, 'save'):
                image.save(str(filepath))
            elif HAS_PIL:
                Image.fromarray(image).save(str(filepath))

            return filepath

        except Exception as e:
            logger.error(f"Error saving overlay image: {e}")
            return None

    def save_extraction_json(
        self,
        data: Any,
        filename: str = "extraction_result.json",
    ) -> Optional[Path]:
        """
        Save extraction result as JSON.

        Args:
            data: Data to save (should be JSON-serializable or Pydantic model)
            filename: Output filename

        Returns:
            Path to saved file
        """
        if not self.config.enabled or not self.config.save_extraction_json:
            return None

        if self.run_dir is None:
            return None

        try:
            filepath = self.run_dir / filename

            # Handle Pydantic models
            if hasattr(data, 'model_dump'):
                json_data = data.model_dump()
            elif hasattr(data, 'dict'):
                json_data = data.dict()
            else:
                json_data = data

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str)

            return filepath

        except Exception as e:
            logger.error(f"Error saving extraction JSON: {e}")
            return None

    def save_text_blocks(
        self,
        page_number: int,
        text_blocks: list,
    ) -> Optional[Path]:
        """
        Save text blocks as JSON for debugging.

        Args:
            page_number: Page number
            text_blocks: List of text blocks

        Returns:
            Path to saved file
        """
        if not self.config.enabled or not self.config.save_text_blocks:
            return None

        if self.run_dir is None:
            return None

        try:
            filename = f"page_{page_number:03d}_text_blocks.json"
            filepath = self.run_dir / filename

            # Convert text blocks to serializable format
            blocks_data = []
            for tb in text_blocks:
                if hasattr(tb, 'model_dump'):
                    blocks_data.append(tb.model_dump())
                elif hasattr(tb, '__dict__'):
                    blocks_data.append(tb.__dict__)
                else:
                    blocks_data.append(str(tb))

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(blocks_data, f, indent=2, default=str)

            return filepath

        except Exception as e:
            logger.error(f"Error saving text blocks: {e}")
            return None

    def add_page_metadata(
        self,
        page_number: int,
        page_type: str,
        drawing_number: str = "",
        classification_confidence: float = 0.0,
    ) -> None:
        """Add page metadata to run metadata."""
        if not self.config.enabled:
            return

        self.metadata["pages"].append({
            "page_number": page_number,
            "page_type": page_type,
            "drawing_number": drawing_number,
            "classification_confidence": classification_confidence,
        })

    def add_warning(self, warning: str) -> None:
        """Add a warning to run metadata."""
        if not self.config.enabled:
            return

        self.metadata["warnings"].append(warning)

    def finalize(self) -> Optional[Path]:
        """
        Finalize the debug run and save metadata.

        Returns:
            Path to the metadata file
        """
        if not self.config.enabled or self.run_dir is None:
            return None

        try:
            self.metadata["finished_at"] = datetime.now().isoformat()
            self.metadata["total_pages"] = len(self.metadata["pages"])
            self.metadata["total_warnings"] = len(self.metadata["warnings"])

            filepath = self.run_dir / "run_metadata.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)

            logger.info(f"Debug run finalized: {self.run_dir}")

            return filepath

        except Exception as e:
            logger.error(f"Error finalizing debug run: {e}")
            return None


def save_debug_artifacts(
    config: DebugConfig,
    result: Any,
    project_name: str = "",
) -> Optional[Path]:
    """
    Convenience function to save extraction result as debug artifacts.

    Args:
        config: Debug configuration
        result: Extraction result to save
        project_name: Project name for directory naming

    Returns:
        Path to debug directory
    """
    if not config.enabled:
        return None

    saver = DebugArtifactSaver(config)
    run_dir = saver.setup_run(project_name)
    saver.save_extraction_json(result)
    saver.finalize()

    return run_dir
