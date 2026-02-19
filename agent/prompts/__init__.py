"""
AfriPlan AI v4.2 - Prompts Package

Contains specialized prompts for each service tier:
- system_prompt: Shared SA electrical domain knowledge
- residential_prompts: Room-by-room extraction
- commercial_prompts: Area-based extraction
- maintenance_prompts: COC/defect extraction

v4.2 additions:
- page_classifier_prompt: Fast page type classification
- legend_prompt: Legend/key extraction before counting
- plugs_layout_prompt: Dedicated plugs/sockets extraction
- lighting_layout_prompt: Dedicated lighting extraction
- sld_prompt: SLD/circuit schedule extraction
"""

from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT
from agent.prompts.residential_prompts import DISCOVERY_RESIDENTIAL
from agent.prompts.commercial_prompts import DISCOVERY_COMMERCIAL
from agent.prompts.maintenance_prompts import DISCOVERY_MAINTENANCE

# v4.2 - Enhanced extraction prompts
from agent.prompts.page_classifier_prompt import (
    get_page_classifier_prompt,
    PAGE_CLASSIFIER_SCHEMA
)
from agent.prompts.legend_prompt import (
    get_legend_prompt,
    LEGEND_SCHEMA
)
from agent.prompts.plugs_layout_prompt import (
    get_plugs_layout_prompt,
    get_prompt as get_plugs_prompt
)
from agent.prompts.lighting_layout_prompt import (
    get_lighting_layout_prompt,
    get_prompt as get_lighting_prompt
)

__all__ = [
    # System
    'SA_ELECTRICAL_SYSTEM_PROMPT',
    # Tier-specific discovery
    'DISCOVERY_RESIDENTIAL',
    'DISCOVERY_COMMERCIAL',
    'DISCOVERY_MAINTENANCE',
    # v4.2 enhanced prompts
    'get_page_classifier_prompt',
    'PAGE_CLASSIFIER_SCHEMA',
    'get_legend_prompt',
    'LEGEND_SCHEMA',
    'get_plugs_layout_prompt',
    'get_plugs_prompt',
    'get_lighting_layout_prompt',
    'get_lighting_prompt',
]
