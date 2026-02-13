"""
AfriPlan AI - Prompts Package

Contains specialized prompts for each service tier:
- system_prompt: Shared SA electrical domain knowledge
- residential_prompts: Room-by-room extraction
- commercial_prompts: Area-based extraction
- maintenance_prompts: COC/defect extraction
"""

from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT
from agent.prompts.residential_prompts import DISCOVERY_RESIDENTIAL
from agent.prompts.commercial_prompts import DISCOVERY_COMMERCIAL
from agent.prompts.maintenance_prompts import DISCOVERY_MAINTENANCE

__all__ = [
    'SA_ELECTRICAL_SYSTEM_PROMPT',
    'DISCOVERY_RESIDENTIAL',
    'DISCOVERY_COMMERCIAL',
    'DISCOVERY_MAINTENANCE',
]
