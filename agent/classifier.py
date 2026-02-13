"""
AfriPlan AI - Tier Classification Module

Stage 2 of the pipeline: Fast project classification using Claude Haiku 4.5.
Routes documents to: residential, commercial, or maintenance tiers.

Cost: ~R0.18 per classification
Speed: ~100-500ms typical
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ServiceTier(Enum):
    """The 3 service tiers supported by AfriPlan v3.0."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result from tier classification."""
    tier: ServiceTier
    confidence: float  # 0.0 to 1.0
    subtype: Optional[str]
    reasoning: str
    keywords_matched: List[str]


# Classification prompt for Claude Haiku
CLASSIFICATION_PROMPT = """You are an electrical project classifier for South African contractors.

Your task is to classify electrical project documents into the correct service tier.

## Service Tiers

### RESIDENTIAL
For homes, apartments, townhouses, and domestic installations.
Keywords: bedroom, bathroom, kitchen, lounge, dining, garage, geyser, stove point,
domestic, house, home, villa, cottage, flat, apartment, townhouse, estate, single-phase (60A typical)

Subtypes:
- new_house: New residential build
- renovation: Existing house renovation/upgrade
- coc_compliance: Certificate of Compliance work (if domestic)
- solar_backup: Solar/battery installation for home
- security: Security system installation
- smart_home: Home automation

### COMMERCIAL
For offices, retail, hospitality, healthcare, education, and business premises.
Keywords: office, retail, shop, store, restaurant, hotel, hospital, clinic, school,
university, warehouse, factory showroom, reception, boardroom, server room,
three-phase, tenant fit-out, NMD calculation

Subtypes:
- office: Office building/space
- retail: Shop or shopping center
- hospitality: Hotel, restaurant, lodge
- healthcare: Hospital, clinic, medical facility
- education: School, university, training center
- warehouse: Distribution/storage facility
- mixed_use: Multiple use types

### MAINTENANCE
For COC inspections, fault repairs, DB upgrades, and remedial electrical work.
Keywords: COC, certificate of compliance, inspection, defect, repair, fault finding,
tripping, earth leakage, rewire, upgrade, remedial, DB board replacement,
condition assessment, compliance check

Subtypes:
- coc_inspection: Full COC inspection
- fault_repair: Specific fault diagnosis and repair
- db_upgrade: DB board replacement/upgrade
- remedial: Fix non-compliance items
- rewire: Partial or full rewiring

## Instructions

1. Analyze the uploaded document (floor plan, specification, photo, or description)
2. Look for visual cues: room labels, equipment symbols, building scale
3. Consider the document type: architectural drawing, electrical drawing, photo, specification
4. Determine the most likely tier based on evidence
5. Assign confidence: HIGH (very clear), MEDIUM (probable), LOW (uncertain)

## Response Format

Respond with ONLY a valid JSON object:
{
    "tier": "RESIDENTIAL" | "COMMERCIAL" | "MAINTENANCE",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "subtype": "specific subtype from list above",
    "reasoning": "Brief explanation of classification decision",
    "keywords_found": ["list", "of", "matching", "keywords"]
}"""


# Keyword mappings for fallback classification
TIER_KEYWORDS: Dict[ServiceTier, Dict[str, List[str]]] = {
    ServiceTier.RESIDENTIAL: {
        "primary": [
            "bedroom", "bathroom", "kitchen", "lounge", "dining",
            "garage", "geyser", "stove point", "house", "home",
            "villa", "cottage", "flat", "apartment", "townhouse"
        ],
        "secondary": [
            "domestic", "single-phase", "60a", "estate", "dwelling",
            "residential", "pool pump", "gate motor", "underfloor"
        ],
        "subtypes": {
            "new_house": ["new build", "new house", "construction"],
            "renovation": ["renovation", "upgrade", "extension", "addition"],
            "solar_backup": ["solar", "battery", "inverter", "backup power"],
            "security": ["alarm", "cctv", "access control", "electric fence"],
            "smart_home": ["smart", "automation", "wifi", "zigbee"]
        }
    },
    ServiceTier.COMMERCIAL: {
        "primary": [
            "office", "retail", "shop", "store", "restaurant",
            "hotel", "hospital", "clinic", "school", "warehouse"
        ],
        "secondary": [
            "three-phase", "nmd", "tenant", "fit-out", "reception",
            "boardroom", "server room", "emergency lighting", "fire alarm",
            "commercial", "business", "industrial"
        ],
        "subtypes": {
            "office": ["office", "boardroom", "meeting room"],
            "retail": ["shop", "store", "retail", "mall"],
            "hospitality": ["hotel", "restaurant", "lodge", "guest"],
            "healthcare": ["hospital", "clinic", "medical", "pharmacy"],
            "education": ["school", "university", "college", "training"],
            "warehouse": ["warehouse", "distribution", "storage", "logistics"]
        }
    },
    ServiceTier.MAINTENANCE: {
        "primary": [
            "coc", "certificate", "compliance", "inspection",
            "defect", "repair", "fault", "tripping"
        ],
        "secondary": [
            "earth leakage", "rewire", "upgrade", "remedial",
            "db board", "condition", "assessment", "check"
        ],
        "subtypes": {
            "coc_inspection": ["coc", "certificate", "compliance", "inspection"],
            "fault_repair": ["fault", "repair", "fix", "tripping", "not working"],
            "db_upgrade": ["db board", "upgrade", "replace", "new board"],
            "remedial": ["remedial", "defect", "rectify", "non-compliance"],
            "rewire": ["rewire", "replace wiring", "old wiring"]
        }
    }
}


class TierClassifier:
    """
    Classifies electrical projects into service tiers.

    Uses Claude Haiku 4.5 for fast, low-cost classification.
    Falls back to keyword matching when API unavailable.
    """

    def __init__(self, client=None):
        """
        Initialize the classifier.

        Args:
            client: Anthropic client instance (optional)
        """
        self.client = client

    def classify_with_api(
        self,
        images: List[str],
        text_content: str,
        filename: str
    ) -> ClassificationResult:
        """
        Classify using Claude Haiku API.

        Args:
            images: List of base64-encoded images
            text_content: Extracted text from document
            filename: Original filename

        Returns:
            ClassificationResult with tier and confidence
        """
        if not self.client:
            return self.classify_from_keywords(text_content, filename)

        try:
            # Build message content
            content = []

            # Add first image (sufficient for classification)
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

            # Call Haiku
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                system=CLASSIFICATION_PROMPT,
                messages=[{"role": "user", "content": content}]
            )

            # Parse response
            response_text = response.content[0].text
            result = self._parse_response(response_text)

            tier = self._string_to_tier(result.get("tier", "unknown"))
            confidence = self._confidence_to_float(result.get("confidence", "medium"))

            return ClassificationResult(
                tier=tier,
                confidence=confidence,
                subtype=result.get("subtype"),
                reasoning=result.get("reasoning", ""),
                keywords_matched=result.get("keywords_found", [])
            )

        except Exception as e:
            # Fallback to keyword matching
            return self.classify_from_keywords(
                text_content,
                filename,
                error_reason=str(e)
            )

    def classify_from_keywords(
        self,
        text_content: str,
        filename: str,
        error_reason: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify using keyword matching (fallback method).

        Args:
            text_content: Text to analyze
            filename: Filename to analyze
            error_reason: Optional error that triggered fallback

        Returns:
            ClassificationResult with tier and confidence
        """
        combined_text = f"{filename} {text_content}".lower()

        scores: Dict[ServiceTier, float] = {
            ServiceTier.RESIDENTIAL: 0,
            ServiceTier.COMMERCIAL: 0,
            ServiceTier.MAINTENANCE: 0,
        }

        matched_keywords: Dict[ServiceTier, List[str]] = {
            ServiceTier.RESIDENTIAL: [],
            ServiceTier.COMMERCIAL: [],
            ServiceTier.MAINTENANCE: [],
        }

        best_subtype: Dict[ServiceTier, str] = {}

        # Score each tier
        for tier, keywords in TIER_KEYWORDS.items():
            # Primary keywords (higher weight)
            for kw in keywords["primary"]:
                if kw in combined_text:
                    scores[tier] += 2.0
                    matched_keywords[tier].append(kw)

            # Secondary keywords (lower weight)
            for kw in keywords["secondary"]:
                if kw in combined_text:
                    scores[tier] += 1.0
                    matched_keywords[tier].append(kw)

            # Find best subtype
            for subtype, subtype_kws in keywords["subtypes"].items():
                for kw in subtype_kws:
                    if kw in combined_text:
                        best_subtype[tier] = subtype
                        break

        # Find winning tier
        winning_tier = max(scores, key=scores.get)
        winning_score = scores[winning_tier]
        total_score = sum(scores.values())

        # Calculate confidence
        if winning_score == 0:
            # No keywords matched - default to residential
            winning_tier = ServiceTier.RESIDENTIAL
            confidence = 0.2
            reasoning = "No matching keywords found - defaulted to residential"
        elif total_score > 0:
            confidence = min(0.6, winning_score / 10)  # Cap at 0.6 for keyword-based
            if winning_score >= 5:
                confidence = 0.5
            elif winning_score >= 3:
                confidence = 0.4
            else:
                confidence = 0.3

            reasoning = f"Keyword match (score: {winning_score:.1f})"
            if error_reason:
                reasoning += f" | API fallback due to: {error_reason}"
        else:
            confidence = 0.2
            reasoning = "Low confidence classification"

        return ClassificationResult(
            tier=winning_tier,
            confidence=confidence,
            subtype=best_subtype.get(winning_tier),
            reasoning=reasoning,
            keywords_matched=matched_keywords[winning_tier]
        )

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response from Claude."""
        import json

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
            # Try to extract JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {}

    def _string_to_tier(self, tier_str: str) -> ServiceTier:
        """Convert string to ServiceTier enum."""
        tier_map = {
            "residential": ServiceTier.RESIDENTIAL,
            "commercial": ServiceTier.COMMERCIAL,
            "maintenance": ServiceTier.MAINTENANCE,
            "unknown": ServiceTier.UNKNOWN,
        }
        return tier_map.get(tier_str.lower(), ServiceTier.UNKNOWN)

    def _confidence_to_float(self, confidence_str: str) -> float:
        """Convert confidence string to float."""
        confidence_map = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.4,
        }
        return confidence_map.get(confidence_str.lower(), 0.5)
