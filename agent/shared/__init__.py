"""
agent.shared — Types used by BOTH the PDF pipeline and the DXF pipeline.

This module is the only place the two pipelines are allowed to share
code. Anything specific to one pipeline lives in
agent.pdf_pipeline.models or agent.dxf_pipeline.models.

Importing rule (CI-enforced):
  - agent.pdf_pipeline.*  may import from agent.shared.*
  - agent.dxf_pipeline.*  may import from agent.shared.*
  - agent.shared.*        may NOT import from either pipeline
"""

from agent.shared.boq import (
    BQSection,
    ItemConfidence,
    BQLineItem,
    BillOfQuantities,
)
from agent.shared.project import (
    ProjectMetadata,
    ContractorProfile,
    SiteConditions,
    LabourRates,
    SystemParameters,
    PhaseConfig,
    BreakerType,
    CableMaterial,
    InstallationMethod,
    EquipmentStatus,
)
from agent.shared.compliance import (
    Severity,
    ComplianceFlag,
)

__all__ = [
    "BQSection",
    "ItemConfidence",
    "BQLineItem",
    "BillOfQuantities",
    "ProjectMetadata",
    "ContractorProfile",
    "SiteConditions",
    "LabourRates",
    "SystemParameters",
    "PhaseConfig",
    "BreakerType",
    "CableMaterial",
    "InstallationMethod",
    "EquipmentStatus",
    "Severity",
    "ComplianceFlag",
]
