"""
AfriPlan Electrical - Document Analyzer
Claude Vision API integration for intelligent document classification
"""

import os
import base64
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# Optional imports - graceful degradation if not installed
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import fitz  # PyMuPDF for PDF handling
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ProjectTier(Enum):
    """Project classification tiers matching AfriPlan page structure."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    """Result of document analysis."""
    tier: ProjectTier
    confidence: float  # 0.0 to 1.0
    subtype: Optional[str]
    extracted_data: Dict[str, Any]
    reasoning: str
    warnings: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None


# Classification criteria for each tier
CLASSIFICATION_CRITERIA = {
    ProjectTier.RESIDENTIAL: {
        "keywords": [
            "bedroom", "bathroom", "kitchen", "living room", "garage",
            "house", "residence", "dwelling", "single-phase", "geyser",
            "stove point", "lounge", "en-suite", "patio", "pool",
            "domestic", "home", "flat", "apartment", "townhouse"
        ],
        "subtypes": {
            "new_house": ["new construction", "new build", "proposed", "new house"],
            "renovation": ["renovation", "addition", "extension", "alterations"],
            "solar_backup": ["solar", "battery", "inverter", "backup", "load shedding"],
            "smart_home": ["smart", "automation", "home assistant", "iot"],
        }
    },
    ProjectTier.COMMERCIAL: {
        "keywords": [
            "office", "retail", "shop", "restaurant", "hotel", "clinic",
            "school", "classroom", "reception", "boardroom", "three-phase",
            "tenant", "floor plate", "core", "lift", "escalator", "mall",
            "warehouse", "showroom", "bank", "supermarket"
        ],
        "subtypes": {
            "office": ["office", "boardroom", "reception", "workstation"],
            "retail": ["shop", "store", "mall", "retail", "supermarket"],
            "hospitality": ["hotel", "restaurant", "kitchen", "guest", "lodge"],
            "healthcare": ["clinic", "hospital", "ward", "theatre", "medical"],
            "education": ["school", "classroom", "laboratory", "library", "university"]
        }
    },
    ProjectTier.INDUSTRIAL: {
        "keywords": [
            "factory", "manufacturing", "warehouse", "plant", "motor",
            "mcc", "mv", "medium voltage", "switchgear", "hazardous",
            "mining", "smelter", "conveyor", "compressor", "boiler",
            "production", "assembly", "workshop"
        ],
        "subtypes": {
            "manufacturing": ["factory", "production", "assembly", "manufacturing"],
            "mining": ["mine", "mining", "shaft", "headgear", "concentrator"],
            "heavy_industry": ["smelter", "foundry", "refinery", "processing"],
            "light_industry": ["workshop", "warehouse", "distribution"]
        }
    },
    ProjectTier.INFRASTRUCTURE: {
        "keywords": [
            "township", "street lighting", "road", "municipal", "eskom",
            "substation", "transformer", "solar farm", "wind farm",
            "mini-grid", "rural", "electrification", "bulk supply",
            "reticulation", "public", "government"
        ],
        "subtypes": {
            "township": ["township", "housing development", "bulk supply", "reticulation"],
            "street_lighting": ["street light", "road lighting", "pole", "luminaire"],
            "rural": ["rural", "off-grid", "electrification", "inep"],
            "utility_solar": ["solar farm", "pv plant", "utility scale", "ipp"],
            "minigrid": ["mini-grid", "microgrid", "isolated", "island"]
        }
    }
}


class DocumentAnalyzer:
    """
    Analyzes uploaded documents using Claude Vision API
    to classify project type and extract relevant data.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize analyzer with API key.

        Args:
            api_key: Anthropic API key. If None, attempts to load from
                    environment or Streamlit secrets.
        """
        self.api_key = api_key or self._get_api_key()
        self.client = None
        self.available = False
        self.error = None

        if self.api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.available = True
            except Exception as e:
                self.error = str(e)

    def _get_api_key(self) -> Optional[str]:
        """Retrieve API key from environment or Streamlit secrets."""
        # Priority 1: Environment variable
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return key

        # Priority 2: Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
                return st.secrets['ANTHROPIC_API_KEY']
        except Exception:
            pass

        return None

    def analyze_document(
        self,
        file_bytes: bytes,
        file_type: str,
        filename: str = "document"
    ) -> AnalysisResult:
        """
        Analyze uploaded document using Claude Vision.

        Args:
            file_bytes: Raw file bytes
            file_type: MIME type (image/png, image/jpeg, application/pdf)
            filename: Original filename for context

        Returns:
            AnalysisResult with classification and extracted data
        """
        if not self.available:
            return self._fallback_analysis(filename)

        try:
            # Convert to base64 for API
            if file_type == "application/pdf":
                if not PDF_AVAILABLE:
                    return AnalysisResult(
                        tier=ProjectTier.UNKNOWN,
                        confidence=0.0,
                        subtype=None,
                        extracted_data={},
                        reasoning="PDF support requires PyMuPDF. Install with: pip install PyMuPDF",
                        warnings=["PDF processing unavailable"]
                    )
                images = self._pdf_to_images(file_bytes)
                media_type = "image/png"
            else:
                images = [base64.b64encode(file_bytes).decode('utf-8')]
                media_type = file_type

            # Build prompt
            prompt = self._build_analysis_prompt()

            # Call Claude Vision API
            response = self._call_vision_api(images, media_type, prompt)

            # Parse response
            return self._parse_response(response)

        except Exception as e:
            return AnalysisResult(
                tier=ProjectTier.UNKNOWN,
                confidence=0.0,
                subtype=None,
                extracted_data={},
                reasoning=f"Analysis failed: {str(e)}",
                warnings=["Document analysis encountered an error"]
            )

    def _build_analysis_prompt(self) -> str:
        """Build the analysis prompt for Claude."""
        return """You are an expert electrical engineer analyzing construction/architectural documents for the South African market.

Analyze this document and provide a JSON response with the following structure:

{
    "classification": {
        "tier": "residential|commercial|industrial|infrastructure",
        "confidence": 0.0-1.0,
        "subtype": "specific subtype code (e.g., new_house, office, manufacturing, township)",
        "reasoning": "Brief explanation of classification"
    },
    "extracted_data": {
        "project_name": "if visible, otherwise null",
        "total_area_m2": number or null,
        "num_floors": number or null,
        "rooms": [
            {"name": "Room 1", "type": "bedroom|bathroom|kitchen|living|office|etc", "area_m2": number or null}
        ],
        "electrical_details": {
            "supply_type": "single-phase|three-phase|unknown",
            "estimated_load_kva": number or null,
            "main_breaker_size": "e.g., 60A, 100A" or null,
            "special_requirements": ["list of special items detected like pool pump, geyser, 3-phase equipment, etc"]
        }
    },
    "confidence_factors": {
        "document_quality": "good|fair|poor",
        "detail_level": "high|medium|low",
        "electrical_info_present": true|false
    },
    "warnings": ["any concerns or ambiguities about the classification"]
}

CLASSIFICATION CRITERIA FOR SOUTH AFRICAN PROJECTS:

RESIDENTIAL (pages/1_Residential.py):
- House plans, flats, apartments, townhouses
- Bedrooms, bathrooms, kitchens, living rooms
- Single-phase supply (typically 60A-80A)
- Domestic appliances: geyser, stove, pool pump
- Subtypes: new_house, renovation, solar_backup, smart_home

COMMERCIAL (pages/2_Commercial.py):
- Offices, retail shops, restaurants, hotels, clinics, schools
- Reception areas, boardrooms, open-plan offices
- Three-phase supply (100A+)
- Emergency lighting, fire detection, lifts
- Subtypes: office, retail, hospitality, healthcare, education

INDUSTRIAL (pages/3_Industrial.py):
- Factories, manufacturing plants, mines, warehouses
- Motors, MCC panels, medium voltage equipment
- Large three-phase loads, hazardous areas
- Subtypes: manufacturing, mining, heavy_industry, light_industry

INFRASTRUCTURE (pages/4_Infrastructure.py):
- Township electrification, street lighting
- Solar farms, mini-grids, rural electrification
- Municipal projects, substations
- Subtypes: township, street_lighting, rural, utility_solar, minigrid

If the document is unclear or not an architectural/electrical drawing, indicate low confidence and explain why.
Return ONLY the JSON object, no additional text."""

    def _call_vision_api(
        self,
        images: List[str],
        media_type: str,
        prompt: str
    ) -> str:
        """Call Claude Vision API with images."""

        # Build content array with images
        content = []

        # Add up to 5 pages/images
        for img_b64 in images[:5]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_b64
                }
            })

        content.append({
            "type": "text",
            "text": prompt
        })

        # Call API using claude-sonnet-4-20250514 for good balance of speed and accuracy
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": content}
            ]
        )

        return message.content[0].text

    def _pdf_to_images(self, pdf_bytes: bytes) -> List[str]:
        """Convert PDF pages to base64 images."""
        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Process first 5 pages max
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            # Render at 150 DPI for good quality without huge size
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            images.append(base64.b64encode(img_bytes).decode('utf-8'))

        doc.close()
        return images

    def _parse_response(self, response: str) -> AnalysisResult:
        """Parse Claude's response into AnalysisResult."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            classification = data.get("classification", {})

            tier_str = classification.get("tier", "unknown").lower()
            tier_map = {
                "residential": ProjectTier.RESIDENTIAL,
                "commercial": ProjectTier.COMMERCIAL,
                "industrial": ProjectTier.INDUSTRIAL,
                "infrastructure": ProjectTier.INFRASTRUCTURE,
            }
            tier = tier_map.get(tier_str, ProjectTier.UNKNOWN)

            return AnalysisResult(
                tier=tier,
                confidence=float(classification.get("confidence", 0.0)),
                subtype=classification.get("subtype"),
                extracted_data=data.get("extracted_data", {}),
                reasoning=classification.get("reasoning", ""),
                warnings=data.get("warnings", []),
                raw_response=response
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return AnalysisResult(
                tier=ProjectTier.UNKNOWN,
                confidence=0.0,
                subtype=None,
                extracted_data={},
                reasoning=f"Failed to parse response: {str(e)}",
                warnings=["Response parsing failed"],
                raw_response=response
            )

    def _fallback_analysis(self, filename: str) -> AnalysisResult:
        """Provide basic analysis when API unavailable."""
        filename_lower = filename.lower()

        tier = ProjectTier.UNKNOWN
        subtype = None
        matched_keywords = []

        # Check each tier's keywords
        for project_tier, criteria in CLASSIFICATION_CRITERIA.items():
            for keyword in criteria["keywords"]:
                if keyword in filename_lower:
                    tier = project_tier
                    matched_keywords.append(keyword)

                    # Check subtypes
                    for sub_name, sub_keywords in criteria["subtypes"].items():
                        if any(sk in filename_lower for sk in sub_keywords):
                            subtype = sub_name
                            break
                    break
            if tier != ProjectTier.UNKNOWN:
                break

        confidence = 0.3 if tier != ProjectTier.UNKNOWN else 0.0

        return AnalysisResult(
            tier=tier,
            confidence=confidence,
            subtype=subtype,
            extracted_data={},
            reasoning=f"Basic filename analysis (AI unavailable). Matched: {', '.join(matched_keywords) if matched_keywords else 'none'}",
            warnings=[
                "Full AI analysis unavailable - using basic classification",
                "Configure ANTHROPIC_API_KEY for accurate analysis"
            ]
        )


def get_tier_page_path(tier: ProjectTier) -> str:
    """Get the page path for a given tier."""
    page_map = {
        ProjectTier.RESIDENTIAL: "pages/1_Residential.py",
        ProjectTier.COMMERCIAL: "pages/2_Commercial.py",
        ProjectTier.INDUSTRIAL: "pages/3_Industrial.py",
        ProjectTier.INFRASTRUCTURE: "pages/4_Infrastructure.py",
        ProjectTier.UNKNOWN: "pages/0_Welcome.py"
    }
    return page_map.get(tier, "pages/0_Welcome.py")


def get_tier_display_info(tier: ProjectTier) -> Dict[str, str]:
    """Get display information for a tier."""
    info = {
        ProjectTier.RESIDENTIAL: {
            "icon": "🏠",
            "name": "Residential",
            "description": "Houses, flats, apartments, domestic installations",
            "color": "#22C55E"
        },
        ProjectTier.COMMERCIAL: {
            "icon": "🏢",
            "name": "Commercial",
            "description": "Offices, retail, hospitality, healthcare, education",
            "color": "#3B82F6"
        },
        ProjectTier.INDUSTRIAL: {
            "icon": "🏭",
            "name": "Industrial",
            "description": "Factories, manufacturing, mining, heavy industry",
            "color": "#F59E0B"
        },
        ProjectTier.INFRASTRUCTURE: {
            "icon": "🌍",
            "name": "Infrastructure",
            "description": "Townships, street lighting, solar farms, municipal",
            "color": "#8B5CF6"
        },
        ProjectTier.UNKNOWN: {
            "icon": "❓",
            "name": "Unknown",
            "description": "Classification uncertain - please select manually",
            "color": "#6B7280"
        }
    }
    return info.get(tier, info[ProjectTier.UNKNOWN])
