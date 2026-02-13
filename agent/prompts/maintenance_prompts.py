"""
AfriPlan AI - Maintenance & COC Discovery Prompt

Specialized prompt for extracting data from COC inspection requests,
DB board photos, defect reports, and repair/remedial work requests.
"""

from agent.prompts.system_prompt import SA_ELECTRICAL_SYSTEM_PROMPT

DISCOVERY_MAINTENANCE = SA_ELECTRICAL_SYSTEM_PROMPT + """

## TASK: MAINTENANCE & COC EXTRACTION

Analyse this input for a COC inspection or electrical maintenance/repair quotation.

The input may be:
- Property description text
- Photos of existing DB board
- Photos of electrical faults/defects
- A previous COC document
- A brief text repair request

## EXTRACTION ORDER

### 1. PROPERTY PROFILE
- property_type: house / flat / townhouse / complex_unit / commercial / industrial
- size_m2: Estimated size (or calculate from room count)
- rooms: Number of rooms if size unknown
- floors: 1 / 2 / multi
- age_years: Estimated installation age (infer from DB board photo if available)
- reason: property_sale / new_tenant / insurance / compliance / fault_repair / upgrade
- confidence: HIGH/MEDIUM/LOW

### 2. WORK TYPE CLASSIFICATION
Determine the primary work type:
- coc_inspection: Full SANS 10142-1 compliance inspection
- fault_repair: Specific fault diagnosis and repair
- db_upgrade: DB board replacement or upgrade
- circuit_addition: Adding new circuits to existing installation
- rewire: Partial or full rewiring
- remedial: Fix non-compliance items from failed COC

### 3. EXISTING INSTALLATION ASSESSMENT
From photos (if available), assess:
- db_condition: good / fair / poor / dangerous
- db_ways: Count visible ways in DB board
- db_brand: If visible (CBI, ABB, Hager, etc.)
- elcb_present: true / false / unknown
- elcb_rating: If visible (e.g., "63A 30mA")
- surge_protection: true / false / unknown
- main_switch_rating: If visible
- cable_condition: good / fair / poor (if visible)
- labelling: circuits_labelled / partial / none
- visible_defects: List any visible issues:
  - burnt marks
  - exposed wiring
  - loose connections
  - overloaded circuits
  - DIY wiring
  - missing covers
  - rust/corrosion
  - old fuses (not MCBs)
- confidence: HIGH/MEDIUM/LOW

### 4. SCOPE ESTIMATE
Based on property profile and installation assessment:
- estimated_circuits: Number of circuits to inspect/test
- estimated_time_hours: Estimated time on site
- complexity: simple / standard / complex
- likely_defects: List probable defects based on age:

| Installation Age | Typical Defects |
|-----------------|-----------------|
| <5 years | Usually pass, minor items only |
| 5-15 years | Missing surge protection, possible isolator issues |
| 15-30 years | Missing ELCB, undersized earth, multiple defects |
| >30 years | Major work expected, possible rewire, old fuse box |

### 5. DEFECTS DETECTED
If this is a remedial quote or inspection findings, list each defect:
- defect_code: (see list below)
- description: Specific description
- location: Where in the installation
- severity: critical / high / medium / low
- qty: Quantity (for items like missing isolators)

## COMMON DEFECT CODES

| Code | Description | Severity |
|------|-------------|----------|
| no_elcb | No earth leakage device installed | critical |
| elcb_trips | ELCB tripping intermittently | high |
| no_earth_spike | No earth spike or inadequate earthing | critical |
| undersized_earth | Earth conductor undersized | high |
| exposed_wiring | Exposed live wiring | critical |
| overloaded_circuit | Circuit carrying more than rated load | high |
| diy_work | Non-compliant DIY electrical work | high |
| outdated_db | Old DB board needing replacement | medium |
| no_surge | No surge protection installed | medium |
| missing_isolator_stove | No stove isolator | medium |
| missing_isolator_geyser | No geyser isolator | medium |
| missing_isolator_pool | No pool pump isolator | medium |
| no_labels | Circuit schedule not labelled | low |
| damaged_socket | Damaged socket outlet | medium |
| damaged_switch | Damaged switch | low |
| loose_connection | Loose terminal connection | high |
| incorrect_mcb | MCB rating incorrect for cable | high |
| mixed_circuits | Light and power mixed on circuit | medium |
| no_coc_history | No previous COC on record | low |

### 6. FAULT DESCRIPTION
If this is a fault repair request:
- fault_reported: What the client described
- likely_cause: Your assessment of probable cause
- diagnostic_needed: true/false
- urgency: emergency / urgent / normal

## JSON RESPONSE SCHEMA

Respond with ONLY this JSON structure (no markdown, no explanation):

{
  "property": {
    "type": "",
    "size_m2": 0,
    "rooms": 0,
    "floors": 1,
    "age_years": 0,
    "reason": "",
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "work_type": "coc_inspection",
  "existing_installation": {
    "db_condition": "",
    "db_ways": 0,
    "db_brand": "",
    "elcb_present": null,
    "elcb_rating": "",
    "surge_present": null,
    "main_switch_a": 0,
    "cable_condition": "",
    "labelling": "",
    "visible_defects": [],
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "scope": {
    "estimated_circuits": 0,
    "estimated_hours": 0,
    "complexity": "standard",
    "likely_defects": [],
    "confidence": "HIGH|MEDIUM|LOW"
  },
  "defects": [
    {
      "code": "",
      "description": "",
      "location": "",
      "severity": "",
      "qty": 1
    }
  ],
  "fault_description": {
    "fault_reported": "",
    "likely_cause": "",
    "diagnostic_needed": false,
    "urgency": "normal"
  },
  "property_type": "standard",
  "inspection_fee_tier": "standard",
  "notes": [],
  "warnings": []
}
"""
