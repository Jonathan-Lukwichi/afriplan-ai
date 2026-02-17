"""
AfriPlan Electrical v4.0 - Utility Functions

Utility functions shared across all pipeline stages.
Handles JSON parsing, image encoding, cost estimation, and timing.
"""

import json
import re
import base64
import time
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass


def parse_json_safely(text: str) -> Optional[dict]:
    """
    Parse JSON from Claude's response. Handles common issues:
    - Strips markdown backticks (```json ... ```)
    - Removes trailing commas before } or ]
    - Handles single quotes → double quotes
    - Returns None on failure (never raises)
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Strip markdown code fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    # Remove trailing commas (common Claude mistake)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    # Try parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: try array
    match = re.search(r'\[[\s\S]*\]', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string for Claude Vision API."""
    return base64.b64encode(image_bytes).decode("utf-8")


def decode_base64_to_bytes(base64_str: str) -> bytes:
    """Decode base64 string back to bytes."""
    return base64.b64decode(base64_str)


# Claude API pricing (per million tokens) - updated for 2025
CLAUDE_PRICING = {
    # Haiku 4.5 - fast, cheap classification
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    # Sonnet 4 - balanced extraction
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    # Opus 4 - complex reasoning
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    # Legacy models (fallback)
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


def estimate_cost_zar(
    model: str,
    input_tokens: int,
    output_tokens: int,
    usd_to_zar: float = 18.50
) -> float:
    """
    Estimate API cost in South African Rand.

    Args:
        model: Claude model identifier
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        usd_to_zar: USD to ZAR exchange rate (default ~R18.50)

    Returns:
        Estimated cost in ZAR, rounded to 4 decimal places
    """
    pricing = CLAUDE_PRICING.get(model, {"input": 3.0, "output": 15.0})
    input_rate = pricing["input"]
    output_rate = pricing["output"]

    cost_usd = (
        input_tokens / 1_000_000 * input_rate +
        output_tokens / 1_000_000 * output_rate
    )
    return round(cost_usd * usd_to_zar, 4)


def estimate_cost_breakdown(
    model: str,
    input_tokens: int,
    output_tokens: int,
    usd_to_zar: float = 18.50
) -> Dict[str, float]:
    """
    Get detailed cost breakdown.

    Returns dict with:
        - input_cost_zar
        - output_cost_zar
        - total_cost_zar
        - cost_usd
    """
    pricing = CLAUDE_PRICING.get(model, {"input": 3.0, "output": 15.0})

    input_cost_usd = input_tokens / 1_000_000 * pricing["input"]
    output_cost_usd = output_tokens / 1_000_000 * pricing["output"]
    total_usd = input_cost_usd + output_cost_usd

    return {
        "input_cost_zar": round(input_cost_usd * usd_to_zar, 4),
        "output_cost_zar": round(output_cost_usd * usd_to_zar, 4),
        "total_cost_zar": round(total_usd * usd_to_zar, 4),
        "cost_usd": round(total_usd, 6),
    }


class Timer:
    """Context manager for timing operations."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.elapsed_ms = 0
        self._start = None

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.monotonic() - self._start) * 1000)

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed time in seconds."""
        return self.elapsed_ms / 1000.0

    def __repr__(self) -> str:
        return f"Timer({self.name}): {self.elapsed_ms}ms"


@dataclass
class APICallMetrics:
    """Track metrics for an API call."""
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_zar: float
    success: bool
    stage: str

    @classmethod
    def create(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        stage: str,
        success: bool = True
    ) -> "APICallMetrics":
        """Factory method to create metrics with auto-calculated cost."""
        cost = estimate_cost_zar(model, input_tokens, output_tokens)
        return cls(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_zar=cost,
            success=success,
            stage=stage,
        )


def extract_drawing_number(text: str) -> Optional[str]:
    """
    Extract drawing number from page text.

    Common patterns:
    - DWG NO: 123-SLD-01
    - Drawing: ABC-LIGHTING-01
    - No. E-001
    """
    patterns = [
        r'DWG\s*(?:NO|#|:)?\s*[:\s]*([A-Z0-9\-]+)',
        r'DRAWING\s*(?:NO|#|:)?\s*[:\s]*([A-Z0-9\-]+)',
        r'DRG\s*(?:NO|#|:)?\s*[:\s]*([A-Z0-9\-]+)',
        r'NO\.\s*([A-Z0-9\-]+)',
        r'REF\s*[:\s]*([A-Z0-9\-]+)',
    ]

    text_upper = text.upper()
    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            return match.group(1).strip()

    return None


def extract_revision(text: str) -> Optional[str]:
    """Extract revision number from page text."""
    patterns = [
        r'REV\s*[:\s]*([A-Z0-9]+)',
        r'REVISION\s*[:\s]*([A-Z0-9]+)',
        r'R([0-9]+)',
    ]

    text_upper = text.upper()
    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            return match.group(1).strip()

    return None


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Limit length
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def format_currency_zar(amount: float) -> str:
    """Format amount as South African Rand."""
    return f"R{amount:,.2f}"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def merge_fixture_counts(
    base: Dict[str, int],
    additional: Dict[str, int]
) -> Dict[str, int]:
    """Merge two fixture count dictionaries, summing values."""
    result = base.copy()
    for key, value in additional.items():
        result[key] = result.get(key, 0) + value
    return result


def calculate_diversity_factor(num_circuits: int) -> float:
    """
    Calculate diversity factor based on number of circuits.
    Based on SANS 10142-1 guidelines for residential installations.
    """
    if num_circuits <= 5:
        return 1.0
    elif num_circuits <= 10:
        return 0.85
    elif num_circuits <= 20:
        return 0.75
    elif num_circuits <= 50:
        return 0.65
    else:
        return 0.55


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_sa(phone: str) -> bool:
    """Validate South African phone number format."""
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', phone)
    # Check for SA formats: 0XX XXX XXXX or +27 XX XXX XXXX
    patterns = [
        r'^0[1-9][0-9]{8}$',  # 0XX XXX XXXX (10 digits)
        r'^\+27[1-9][0-9]{8}$',  # +27 XX XXX XXXX
        r'^27[1-9][0-9]{8}$',  # 27 XX XXX XXXX (without +)
    ]
    return any(re.match(p, cleaned) for p in patterns)


def generate_quote_number(prefix: str = "AP") -> str:
    """Generate a unique quote number with timestamp."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}"


def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """Split a list into chunks of size n."""
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def flatten(nested: List[List[Any]]) -> List[Any]:
    """Flatten a nested list."""
    return [item for sublist in nested for item in sublist]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def percentage(part: float, whole: float) -> float:
    """Calculate percentage, handling division by zero."""
    return safe_divide(part * 100, whole, 0.0)
