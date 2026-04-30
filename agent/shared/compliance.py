"""
Compliance flags — emitted by both pipelines' EVALUATE stages.

A ComplianceFlag is a structured finding referenced to a clause in a
South African standard. Both the PDF and DXF evaluators raise the same
shape so the cross-comparison layer can treat them uniformly.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ComplianceFlag(BaseModel):
    """
    A single compliance finding raised against an extraction.

    Examples:
        rule_code="SANS-10142-1:2017-7.12.2.1"
        rule_title="Maximum 10 final-circuit points"
        severity=Severity.WARNING
        message="Circuit P1 has 14 sockets (max 10)"
        location="DB-PFA / P1"
        suggested_fix="Split into P1A and P1B"
    """

    rule_code: str
    rule_title: str
    severity: Severity = Severity.WARNING
    message: str
    location: str = ""
    suggested_fix: str = ""
    auto_corrected: bool = False
    corrected_value: Optional[str] = None

    @property
    def is_blocking(self) -> bool:
        """A pipeline gate fails if any blocking flag is present."""
        return self.severity == Severity.CRITICAL


class ComplianceReport(BaseModel):
    """Aggregate of all compliance flags for one extraction."""

    flags: list[ComplianceFlag] = Field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == Severity.INFO)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0
