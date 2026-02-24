"""
AfriPlan Electrical - Debug Overlays

Draw debug overlays on page images:
- Bounding boxes for detected regions
- Text block highlights
- Classification labels

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Any, Dict

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from agent.models import BoundingBox, PageRegions

logger = logging.getLogger(__name__)


# Color palette for different region types
REGION_COLORS = {
    "title_block": (255, 0, 0, 128),      # Red
    "legend": (0, 255, 0, 128),            # Green
    "schedule": (0, 0, 255, 128),          # Blue
    "main_drawing": (255, 255, 0, 128),    # Yellow
    "notes": (255, 0, 255, 128),           # Magenta
    "default": (128, 128, 128, 128),       # Gray
}

TEXT_BLOCK_COLOR = (255, 165, 0, 100)  # Orange with transparency


def draw_region_overlay(
    image: Any,
    regions: PageRegions,
    include_labels: bool = True,
    line_width: int = 2,
) -> Any:
    """
    Draw bounding boxes around detected regions.

    Args:
        image: PIL Image or numpy array
        regions: PageRegions with detected bounding boxes
        include_labels: Whether to include text labels
        line_width: Line width for boxes

    Returns:
        Image with overlays drawn
    """
    if not HAS_PIL:
        logger.warning("PIL not available, cannot draw overlays")
        return image

    # Convert numpy array to PIL if needed
    if HAS_CV2 and isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    elif hasattr(image, 'copy'):
        pil_image = image.copy()
    else:
        pil_image = image

    # Convert to RGBA for transparency
    if pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')

    # Create overlay layer
    overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to get a font
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Draw each region
    region_list = [
        ("title_block", regions.title_block),
        ("legend", regions.legend),
        ("schedule", regions.schedule),
        ("main_drawing", regions.main_drawing),
        ("notes", regions.notes),
    ]

    for name, bbox in region_list:
        if bbox is None:
            continue

        color = REGION_COLORS.get(name, REGION_COLORS["default"])
        rgb_color = color[:3]
        alpha = color[3]

        # Draw rectangle with transparency
        x0, y0, x1, y1 = int(bbox.x0), int(bbox.y0), int(bbox.x1), int(bbox.y1)

        # Fill with semi-transparent color
        draw.rectangle([x0, y0, x1, y1], fill=color)

        # Draw border
        draw.rectangle([x0, y0, x1, y1], outline=rgb_color, width=line_width)

        # Draw label
        if include_labels:
            label = f"{name} ({bbox.confidence:.2f})"
            # Draw label background
            text_bbox = draw.textbbox((x0, y0 - 20), label, font=font)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 200))
            draw.text((x0, y0 - 20), label, fill=rgb_color, font=font)

    # Composite overlay onto image
    result = Image.alpha_composite(pil_image, overlay)

    return result


def draw_text_blocks_overlay(
    image: Any,
    text_blocks: List[Any],
    color: Tuple[int, int, int, int] = TEXT_BLOCK_COLOR,
    include_text: bool = False,
) -> Any:
    """
    Draw bounding boxes around text blocks.

    Args:
        image: PIL Image or numpy array
        text_blocks: List of text blocks with x0, y0, x1, y1 attributes
        color: Box color (RGBA)
        include_text: Whether to include text content in label

    Returns:
        Image with overlays drawn
    """
    if not HAS_PIL:
        logger.warning("PIL not available, cannot draw overlays")
        return image

    # Convert numpy array to PIL if needed
    if HAS_CV2 and isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    elif hasattr(image, 'copy'):
        pil_image = image.copy()
    else:
        pil_image = image

    # Convert to RGBA for transparency
    if pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')

    # Create overlay layer
    overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to get a small font
    try:
        font = ImageFont.truetype("arial.ttf", 8)
    except:
        font = ImageFont.load_default()

    rgb_color = color[:3]

    for tb in text_blocks:
        if not hasattr(tb, 'x0'):
            continue

        x0 = int(getattr(tb, 'x0', 0))
        y0 = int(getattr(tb, 'y0', 0))
        x1 = int(getattr(tb, 'x1', x0 + 10))
        y1 = int(getattr(tb, 'y1', y0 + 10))

        # Draw filled rectangle
        draw.rectangle([x0, y0, x1, y1], fill=color, outline=rgb_color)

        # Draw text content if requested
        if include_text:
            text = getattr(tb, 'text', '')[:20]  # Truncate
            if text:
                draw.text((x0, y0), text, fill=(0, 0, 0, 255), font=font)

    # Composite overlay onto image
    result = Image.alpha_composite(pil_image, overlay)

    return result


def draw_classification_label(
    image: Any,
    page_type: str,
    confidence: float,
    drawing_number: str = "",
    position: str = "top_left",
) -> Any:
    """
    Draw classification label on image.

    Args:
        image: PIL Image or numpy array
        page_type: Classified page type
        confidence: Classification confidence
        drawing_number: Drawing number if detected
        position: Label position (top_left, top_right, bottom_left, bottom_right)

    Returns:
        Image with label drawn
    """
    if not HAS_PIL:
        return image

    # Convert numpy array to PIL if needed
    if HAS_CV2 and isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    elif hasattr(image, 'copy'):
        pil_image = image.copy()
    else:
        pil_image = image

    draw = ImageDraw.Draw(pil_image)

    # Try to get a font
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    # Build label text
    lines = [
        f"Type: {page_type.upper()}",
        f"Confidence: {confidence:.0%}",
    ]
    if drawing_number:
        lines.append(f"DWG: {drawing_number}")

    label_text = "\n".join(lines)

    # Calculate position
    text_bbox = draw.multiline_textbbox((0, 0), label_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    padding = 10
    img_width, img_height = pil_image.size

    if position == "top_left":
        x, y = padding, padding
    elif position == "top_right":
        x, y = img_width - text_width - padding * 2, padding
    elif position == "bottom_left":
        x, y = padding, img_height - text_height - padding * 2
    else:  # bottom_right
        x, y = img_width - text_width - padding * 2, img_height - text_height - padding * 2

    # Draw background
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=(255, 255, 255, 200)
    )

    # Draw border
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        outline=(0, 0, 0),
        width=1
    )

    # Draw text
    draw.multiline_text((x, y), label_text, fill=(0, 0, 0), font=font)

    return pil_image


def create_comparison_image(
    images: List[Any],
    labels: Optional[List[str]] = None,
    layout: str = "horizontal",
) -> Any:
    """
    Create a comparison image showing multiple images side by side.

    Args:
        images: List of PIL Images or numpy arrays
        labels: Optional labels for each image
        layout: "horizontal" or "vertical"

    Returns:
        Combined image
    """
    if not HAS_PIL or not images:
        return None

    # Convert all to PIL
    pil_images = []
    for img in images:
        if HAS_CV2 and isinstance(img, np.ndarray):
            pil_images.append(Image.fromarray(img))
        else:
            pil_images.append(img)

    # Calculate dimensions
    if layout == "horizontal":
        total_width = sum(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)
        result = Image.new('RGB', (total_width, max_height), (255, 255, 255))

        x_offset = 0
        for i, img in enumerate(pil_images):
            result.paste(img, (x_offset, 0))
            x_offset += img.width
    else:
        max_width = max(img.width for img in pil_images)
        total_height = sum(img.height for img in pil_images)
        result = Image.new('RGB', (max_width, total_height), (255, 255, 255))

        y_offset = 0
        for i, img in enumerate(pil_images):
            result.paste(img, (0, y_offset))
            y_offset += img.height

    return result
