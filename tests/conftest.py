"""
Pytest configuration and fixtures for AfriPlan Electrical tests.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_sld_text():
    """Sample SLD page text for testing."""
    return """
    SINGLE LINE DIAGRAM
    DISTRIBUTION BOARD: DB-GF
    MAIN BREAKER: 100A
    SUPPLY FROM: Kiosk Metering Box

    CIRCUIT SCHEDULE
    L1 Bedroom 1 Lights    6pts  360W  1.5mm2  10A
    L2 Bedroom 2 Lights    4pts  240W  1.5mm2  10A
    L3 Kitchen Lights      6pts  360W  1.5mm2  10A
    P1 Bedroom 1 Plugs     4pts  1000W 2.5mm2  20A
    P2 Kitchen Plugs       6pts  1500W 2.5mm2  20A
    AC1 Aircon            1pt   3000W 4mm2    32A
    ISO1 Geyser           1pt   2000W 2.5mm2  20A
    SPARE                 -     -     -       -
    """


@pytest.fixture
def sample_lighting_layout_text():
    """Sample lighting layout text for testing."""
    return """
    LIGHTING LAYOUT - GROUND FLOOR
    DWG NO: WD-AB-02-LIGHTING

    BEDROOM 1  (DB-S1 L1)
    BEDROOM 2  (DB-S1 L2)
    KITCHEN    (DB-S1 L3)
    LIVING ROOM (DB-S1 L4)
    BATHROOM   (DB-S1 L5)

    LEGEND:
    6W LED Downlight
    1-Lever 1-Way Switch
    2-Lever 1-Way Switch
    Day/Night Switch
    """


@pytest.fixture
def sample_register_text():
    """Sample drawing register text for testing."""
    return """
    DRAWING REGISTER

    PROJECT: THE UPGRADING OF WEDELA RETAIL CENTER
    CLIENT: ABC PROPERTY DEVELOPMENT
    CONSULTANT: CHONA MALANGA ENGINEERS

    DRWG NO         TITLE                       REV    DATE
    WD-AB-01-SLD    Ablution Block SLD          A      2025-01-15
    WD-AB-02-LIGHTING Ablution Block Lighting   A      2025-01-16
    WD-AB-03-PLUGS  Ablution Block Plugs        A      2025-01-17
    WD-ECH-01-SLD   Community Hall SLD          A      2025-01-18
    """


@pytest.fixture
def sample_plugs_layout_text():
    """Sample plugs layout text for testing."""
    return """
    PLUGS LAYOUT - GROUND FLOOR
    DWG NO: WD-AB-03-PLUGS

    BEDROOM 1  (DB-S1 P1)
    KITCHEN    (DB-S1 P2)
    LIVING ROOM (DB-S1 P3)

    LEGEND:
    Double Socket @300mm
    Double Socket @1100mm
    CAT 6 Data Point
    20A Isolator
    Floor Box
    """
