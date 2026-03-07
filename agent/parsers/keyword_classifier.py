"""
AfriPlan Electrical - Keyword-Based Page Classifier

Deterministic classification of electrical drawing pages using
weighted keyword matching rules.

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PageType(str, Enum):
    """Page types for electrical drawings."""
    REGISTER = "register"
    SLD = "sld"
    LAYOUT_LIGHTING = "layout_lighting"
    LAYOUT_PLUGS = "layout_plugs"
    LAYOUT_COMBINED = "layout_combined"
    OUTSIDE_LIGHTS = "outside_lights"
    SCHEDULE = "schedule"
    DETAIL = "detail"
    SPECIFICATION = "spec"
    UNKNOWN = "unknown"


@dataclass
class ClassificationRule:
    """A single classification rule with weight."""
    name: str
    keywords: List[str]  # Keywords to match
    weight: float = 1.0  # Contribution to score
    match_type: str = "any"  # "any", "all", "regex"
    target_type: PageType = PageType.UNKNOWN
    negative: bool = False  # If True, presence reduces score

    def matches(self, text: str) -> Tuple[bool, float]:
        """Check if rule matches text and return (matched, score)."""
        text_lower = text.lower()

        if self.match_type == "regex":
            for pattern in self.keywords:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return (True, self.weight)
            return (False, 0.0)

        elif self.match_type == "all":
            for kw in self.keywords:
                if kw.lower() not in text_lower:
                    return (False, 0.0)
            return (True, self.weight)

        else:  # "any"
            for kw in self.keywords:
                if kw.lower() in text_lower:
                    return (True, self.weight)
            return (False, 0.0)


@dataclass
class ClassificationResult:
    """Result of page classification."""
    page_type: PageType = PageType.UNKNOWN
    confidence: float = 0.0
    matched_rules: List[str] = field(default_factory=list)
    keyword_scores: Dict[str, float] = field(default_factory=dict)
    drawing_number: str = ""
    drawing_title: str = ""
    building_block: str = ""


class KeywordClassifier:
    """
    Deterministic page classifier using weighted keyword rules.

    Usage:
        classifier = KeywordClassifier()
        result = classifier.classify(page_text)
    """

    def __init__(self):
        """Initialize classifier with default rules."""
        self.rules = self._build_default_rules()

    def _build_default_rules(self) -> List[ClassificationRule]:
        """Build the default rule set for SA electrical drawings."""
        rules = []

        # === REGISTER PAGE RULES ===
        rules.append(ClassificationRule(
            name="register_explicit",
            keywords=["drawing register", "drwg register", "drawing list"],
            weight=3.0,  # Higher weight - explicit register title is definitive
            match_type="any",
            target_type=PageType.REGISTER,
        ))
        rules.append(ClassificationRule(
            name="register_table_headers",
            keywords=["drwg no", "drawing no", "title", "rev", "date"],
            weight=1.5,
            match_type="all",
            target_type=PageType.REGISTER,
        ))
        rules.append(ClassificationRule(
            name="register_keywords",
            keywords=["project name", "client", "consultant", "revision"],
            weight=1.0,  # Slightly increased
            match_type="any",
            target_type=PageType.REGISTER,
        ))
        rules.append(ClassificationRule(
            name="register_project_client",
            keywords=["project:", "client:"],
            weight=1.2,  # PROJECT: and CLIENT: labels are strong indicators
            match_type="any",
            target_type=PageType.REGISTER,
        ))

        # === SLD PAGE RULES ===
        rules.append(ClassificationRule(
            name="sld_drawing_number",
            keywords=[r"-SLD", r"_SLD"],
            weight=2.0,
            match_type="regex",
            target_type=PageType.SLD,
        ))
        rules.append(ClassificationRule(
            name="sld_explicit",
            keywords=["single line diagram", "schematic diagram", "distribution board"],
            weight=1.8,
            match_type="any",
            target_type=PageType.SLD,
        ))
        rules.append(ClassificationRule(
            name="sld_schedule_headers",
            keywords=["circuit no", "wattage", "wire size", "breaker"],
            weight=1.5,
            match_type="any",
            target_type=PageType.SLD,
        ))
        rules.append(ClassificationRule(
            name="sld_circuit_types",
            keywords=["lighting circuit", "power circuit", "db-", "main breaker"],
            weight=1.2,
            match_type="any",
            target_type=PageType.SLD,
        ))
        rules.append(ClassificationRule(
            name="sld_electrical_terms",
            keywords=["mcb", "mccb", "elcb", "surge", "isolator", "contactor"],
            weight=0.8,
            match_type="any",
            target_type=PageType.SLD,
        ))
        rules.append(ClassificationRule(
            name="sld_cable_ref",
            keywords=[r"\d+mm²", r"\d+mm2"],
            weight=0.7,
            match_type="regex",
            target_type=PageType.SLD,
        ))

        # === LIGHTING LAYOUT RULES ===
        rules.append(ClassificationRule(
            name="lighting_drawing_number",
            keywords=[r"-LIGHTING", r"_LIGHTING", r"-LT-", r"_LT_"],
            weight=2.0,
            match_type="regex",
            target_type=PageType.LAYOUT_LIGHTING,
        ))
        rules.append(ClassificationRule(
            name="lighting_explicit",
            keywords=["lighting layout", "lighting plan", "light layout"],
            weight=1.8,
            match_type="any",
            target_type=PageType.LAYOUT_LIGHTING,
        ))
        rules.append(ClassificationRule(
            name="lighting_fixtures",
            keywords=["downlight", "luminaire", "led panel", "flood light", "bulkhead"],
            weight=1.2,
            match_type="any",
            target_type=PageType.LAYOUT_LIGHTING,
        ))
        rules.append(ClassificationRule(
            name="lighting_switches",
            keywords=["1-lever", "2-lever", "day/night", "switch plate"],
            weight=0.8,
            match_type="any",
            target_type=PageType.LAYOUT_LIGHTING,
        ))

        # === PLUGS LAYOUT RULES ===
        rules.append(ClassificationRule(
            name="plugs_drawing_number",
            keywords=[r"-PLUGS", r"_PLUGS", r"-PWR-", r"-POWER-"],
            weight=2.0,
            match_type="regex",
            target_type=PageType.LAYOUT_PLUGS,
        ))
        rules.append(ClassificationRule(
            name="plugs_explicit",
            keywords=["plugs layout", "power layout", "socket layout", "plug point layout"],
            weight=1.8,
            match_type="any",
            target_type=PageType.LAYOUT_PLUGS,
        ))
        rules.append(ClassificationRule(
            name="plugs_sockets",
            keywords=["double socket", "single socket", "@300mm", "@1100mm", "floor box"],
            weight=1.2,
            match_type="any",
            target_type=PageType.LAYOUT_PLUGS,
        ))
        rules.append(ClassificationRule(
            name="plugs_data",
            keywords=["data point", "cat6", "cat 6", "rj45", "network outlet"],
            weight=0.8,
            match_type="any",
            target_type=PageType.LAYOUT_PLUGS,
        ))

        # === OUTSIDE LIGHTS RULES ===
        rules.append(ClassificationRule(
            name="outside_drawing_number",
            keywords=[r"-OL-", r"_OL_", r"-EXT-", r"-EXTERNAL-"],
            weight=2.0,
            match_type="regex",
            target_type=PageType.OUTSIDE_LIGHTS,
        ))
        rules.append(ClassificationRule(
            name="outside_explicit",
            keywords=["outside lights", "external lighting", "site lighting", "perimeter lighting"],
            weight=1.8,
            match_type="any",
            target_type=PageType.OUTSIDE_LIGHTS,
        ))
        rules.append(ClassificationRule(
            name="outside_elements",
            keywords=["pole light", "bollard", "kiosk", "boundary", "fence line", "guard house"],
            weight=1.0,
            match_type="any",
            target_type=PageType.OUTSIDE_LIGHTS,
        ))

        # === LEGEND PAGE RULES ===
        # Legend pages define symbols - should be detected BEFORE SLD
        rules.append(ClassificationRule(
            name="legend_explicit",
            keywords=["legend", "symbol legend", "electrical legend", "key to symbols"],
            weight=2.5,  # Higher than SLD rules
            match_type="any",
            target_type=PageType.SCHEDULE,  # Use SCHEDULE for legend pages
        ))
        rules.append(ClassificationRule(
            name="legend_category_headers",
            keywords=["switches", "power sockets", "lights", "others"],
            weight=2.2,  # High weight - these are legend section headers
            match_type="any",
            target_type=PageType.SCHEDULE,
        ))
        rules.append(ClassificationRule(
            name="legend_qtys_column",
            keywords=["qtys", "qty", "quantity"],
            weight=1.8,
            match_type="any",
            target_type=PageType.SCHEDULE,
        ))
        rules.append(ClassificationRule(
            name="legend_above_ffl",
            keywords=["above ffl", "above floor", "above finished floor", "@1200mm", "@300mm", "@1100mm", "@2000mm"],
            weight=1.5,  # Symbol height descriptions common in legends
            match_type="any",
            target_type=PageType.SCHEDULE,
        ))
        rules.append(ClassificationRule(
            name="legend_symbol_descriptions",
            keywords=["1 way switch", "2 way switch", "lever switch", "switched socket", "recessed light"],
            weight=1.2,
            match_type="any",
            target_type=PageType.SCHEDULE,
        ))

        # === SCHEDULE PAGE RULES ===
        rules.append(ClassificationRule(
            name="schedule_explicit",
            keywords=["lighting schedule", "fixture schedule", "equipment schedule"],
            weight=1.8,
            match_type="any",
            target_type=PageType.SCHEDULE,
        ))

        # === DETAIL PAGE RULES ===
        rules.append(ClassificationRule(
            name="detail_explicit",
            keywords=["detail", "typical detail", "installation detail", "section detail"],
            weight=1.5,
            match_type="any",
            target_type=PageType.DETAIL,
        ))

        # === NEGATIVE RULES (reduce confidence) ===
        rules.append(ClassificationRule(
            name="not_electrical",
            keywords=["architectural", "structural", "plumbing", "hvac drawing"],
            weight=-1.5,
            match_type="any",
            target_type=PageType.UNKNOWN,
            negative=True,
        ))

        return rules

    def classify(
        self,
        text: str,
        drawing_number: str = "",
    ) -> ClassificationResult:
        """
        Classify a page based on its text content.

        Args:
            text: Page text content
            drawing_number: Drawing number if known (helps classification)

        Returns:
            ClassificationResult with page type, confidence, and matched rules
        """
        result = ClassificationResult()

        # Combine text and drawing number for matching
        full_text = f"{drawing_number} {text}"

        # Score each page type
        type_scores: Dict[PageType, float] = {}
        type_rules: Dict[PageType, List[str]] = {}

        for rule in self.rules:
            matched, score = rule.matches(full_text)
            if matched:
                target = rule.target_type
                if target not in type_scores:
                    type_scores[target] = 0.0
                    type_rules[target] = []

                if rule.negative:
                    # Negative rule - reduces all other scores
                    for t in type_scores:
                        type_scores[t] += score  # score is already negative
                else:
                    type_scores[target] += score
                    type_rules[target].append(rule.name)

                result.keyword_scores[rule.name] = score

        # Find best match
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            best_score = type_scores[best_type]

            # Normalize confidence (0-1 range)
            # Typical max score is around 5-8 for a well-matched page
            confidence = min(1.0, max(0.0, best_score / 5.0))

            if confidence >= 0.2:  # Minimum threshold
                result.page_type = best_type
                result.confidence = confidence
                result.matched_rules = type_rules.get(best_type, [])

        # Try to extract drawing number from text if not provided
        if not drawing_number:
            result.drawing_number = self._extract_drawing_number(text)
        else:
            result.drawing_number = drawing_number

        # Try to detect building block
        result.building_block = self._detect_building_block(full_text)

        return result

    def _extract_drawing_number(self, text: str) -> str:
        """Try to extract drawing number from text."""
        # Common patterns: WD-AB-01-SLD, TJM-E-01-LIGHTING, etc.
        patterns = [
            r'([A-Z]{2,4}-[A-Z]{1,4}-\d{2,3}-[A-Z]+)',  # WD-AB-01-SLD
            r'([A-Z]{2,4}-\d{2,3}-[A-Z]+)',  # TJM-01-LIGHTING
            r'(DWG[\s\-]?NO[\.:]\s*)([\w\-]+)',  # DWG NO: XXX
            r'(DRAWING[\s\-]?NO[\.:]\s*)([\w\-]+)',  # DRAWING NO: XXX
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return the actual drawing number (last group if multiple)
                return match.group(match.lastindex) if match.lastindex else match.group()

        return ""

    def _detect_building_block(self, text: str) -> str:
        """Detect building block from text content."""
        text_lower = text.lower()

        # Building block patterns (from Wedela project)
        block_patterns = [
            (r'WD-AB-|ablution\s+retail', "Ablution Retail Block"),
            (r'WD-ECH-|community\s+hall', "Existing Community Hall"),
            (r'WD-LGH-|large\s+guard', "Large Guard House"),
            (r'WD-SGH-|small\s+guard', "Small Guard House"),
            (r'WD-PB-|pool\s+block|pool\s+facility', "Pool Block"),
            (r'WD-OL-|outside\s+lights?|site\s+lighting', "Site Infrastructure"),
            (r'TJM-|newmark', "NewMark Office Building"),
        ]

        for pattern, block_name in block_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return block_name

        return ""

    def add_rule(self, rule: ClassificationRule) -> None:
        """Add a custom classification rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        original_len = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        return len(self.rules) < original_len

    def get_rules_for_type(self, page_type: PageType) -> List[ClassificationRule]:
        """Get all rules targeting a specific page type."""
        return [r for r in self.rules if r.target_type == page_type]


# Default classifier instance
default_classifier = KeywordClassifier()


def classify_page_text(text: str, drawing_number: str = "") -> ClassificationResult:
    """Convenience function using default classifier."""
    return default_classifier.classify(text, drawing_number)
