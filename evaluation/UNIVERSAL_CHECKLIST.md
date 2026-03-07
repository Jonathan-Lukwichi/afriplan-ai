# Universal Extraction Checklist for Electrical Drawings

## Overview

This checklist covers ALL types of electrical drawings and what to extract from each.
Use this when creating ground truth files for the scoring system.

---

## Document Types Identified

| Type | Description | What to Extract |
|------|-------------|-----------------|
| **COVER/REGISTER** | Drawing index, project info | Project name, drawing list |
| **SITE PLAN** | DB locations, cable routes | DB positions, cable lengths |
| **SLD** | Single Line Diagram | DB hierarchy, main breakers |
| **CIRCUIT SCHEDULE** | Tables with circuit details | MCB, cable, points, wattage |
| **LIGHTING LAYOUT** | Light fixture positions | Light counts by type and room |
| **POWER LAYOUT** | Socket/plug positions | Socket counts by type and room |
| **COMBINED LAYOUT** | Lights + power on same drawing | All fixtures |
| **LEGEND** | Symbol key | Symbol-to-meaning mappings |

---

## SECTION 1: PROJECT INFORMATION

Extract from cover page or title block:

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Project Name | "Wedela Recreational Club" | LOW | From title block |
| Client Name | "Yapa Properties" | LOW | From title block |
| Consultant/Engineer | "KABE Consulting" | LOW | From title block |
| Drawing Number | "WD-KIOSK-01-SLD" | MEDIUM | Unique identifier |
| Revision | "RA", "Rev 1" | LOW | Version control |
| Date | "2025-05-26" | LOW | Drawing date |
| Scale | "1:100" | LOW | For measurements |
| Standard | "SANS 10142-1" | MEDIUM | Compliance reference |

---

## SECTION 2: DISTRIBUTION BOARDS

Extract from SLD and schedule pages:

### 2.1 DB Identification

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| DB Name | "DB-KIOSK", "DB-S1" | HIGH | Must match drawing |
| DB Location | "Ground Floor", "Pool Area" | MEDIUM | Physical location |
| DB Type | "Main", "Sub", "Final" | MEDIUM | Hierarchy level |

### 2.2 DB Main Specifications

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Voltage | "400V", "230V" | HIGH | System voltage |
| Phase Configuration | "3PH+N+E", "1PH+N+E" | HIGH | Phase type |
| Main Breaker Rating (A) | 63, 100, 160 | CRITICAL | Main switch size |
| Total Ways | 24, 36, 48 | HIGH | DB board size |
| Spare Ways | 4, 6, 8 | MEDIUM | Future capacity |

### 2.3 Protection Devices

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Has ELCB/RCD | Yes/No | CRITICAL | SANS 10142-1 requirement |
| ELCB Rating (A) | 63, 80 | HIGH | Earth leakage device |
| ELCB Sensitivity (mA) | 30, 100 | HIGH | Trip sensitivity |
| Has Surge Protection | Yes/No | MEDIUM | Type 2 SPD |
| Surge Protection Type | "Type 2" | LOW | SPD classification |

---

## SECTION 3: CIRCUITS

Extract from circuit schedule tables:

### 3.1 Circuit Identification

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Circuit Name | "L1", "P1", "AC-1" | HIGH | Circuit reference |
| Circuit Type | lighting/power/dedicated/spare | CRITICAL | Classification |
| Description | "Lights - Reception" | MEDIUM | What it feeds |

### 3.2 Circuit Electrical Data

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| MCB Rating (A) | 10, 16, 20, 32 | CRITICAL | Breaker size |
| Cable Size (mm²) | 1.5, 2.5, 4.0, 6.0 | CRITICAL | Wire size |
| Cable Type | "SURFIX", "PVC/PVC" | HIGH | Cable specification |
| Phase | "R", "W", "B", "3PH" | MEDIUM | Phase allocation |
| Wattage (W) | 720, 1650, 3680 | HIGH | Load calculation |
| Number of Points | 4, 6, 8, 10 | CRITICAL | Points served |

### 3.3 Circuit Count Summary

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Total Circuits | 24, 36 | CRITICAL | Per DB |
| Lighting Circuits | 8, 12 | HIGH | L-type circuits |
| Power Circuits | 10, 16 | HIGH | P-type circuits |
| Dedicated Circuits | 4, 6 | HIGH | Stove, geyser, AC |
| Spare Circuits | 4, 8 | MEDIUM | Unused ways |
| Sub-feed Circuits | 2, 3 | MEDIUM | Feeds to sub-DBs |

---

## SECTION 4: FIXTURES (Layout Drawings)

Extract from lighting and power layout drawings:

### 4.1 Light Fixtures

| Symbol Type | Example Count | Priority | Notes |
|-------------|---------------|----------|-------|
| LED Downlight | 24 | HIGH | Most common |
| Fluorescent 600x600 | 12 | HIGH | Office standard |
| Fluorescent 600x1200 | 8 | HIGH | Industrial/warehouse |
| Bulkhead Light | 6 | MEDIUM | Exterior/wet areas |
| Exit Sign | 4 | MEDIUM | Emergency |
| Emergency Light | 4 | MEDIUM | Battery backup |
| Floodlight | 2 | MEDIUM | Exterior |
| Batten Light | 6 | MEDIUM | Utility areas |

### 4.2 Power Points (Sockets)

| Symbol Type | Example Count | Priority | Notes |
|-------------|---------------|----------|-------|
| Single Socket | 8 | HIGH | Standard outlet |
| Double Socket | 16 | HIGH | Most common |
| USB Socket | 4 | MEDIUM | Modern offices |
| Floor Box | 2 | MEDIUM | Open plan offices |
| Isolator | 4 | HIGH | Equipment disconnect |
| FCU (Fused Connection Unit) | 2 | MEDIUM | Fixed equipment |

### 4.3 Switches

| Symbol Type | Example Count | Priority | Notes |
|-------------|---------------|----------|-------|
| 1-Lever Switch | 12 | MEDIUM | Single control |
| 2-Lever Switch | 8 | MEDIUM | Dual control |
| 3-Lever Switch | 4 | MEDIUM | Triple control |
| Dimmer Switch | 2 | LOW | Variable lighting |
| PIR/Motion Sensor | 4 | MEDIUM | Auto control |

### 4.4 By Room (Optional but valuable)

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Room Name | "Reception", "Office 1" | MEDIUM | Location reference |
| Room Type | "office", "kitchen", "bathroom" | MEDIUM | Classification |
| Area (m²) | 45.5 | LOW | For W/m² calculations |
| Light Count | 6 | HIGH | Per room |
| Socket Count | 8 | HIGH | Per room |
| Switch Count | 2 | MEDIUM | Per room |

---

## SECTION 5: CABLES (Site Plans & SLDs)

Extract from site plans and SLD pages:

### 5.1 Main Feeds

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| From | "MINI SUB", "MSB" | HIGH | Source |
| To | "DB-MAIN", "DB-KIOSK" | HIGH | Destination |
| Cable Size (mm²) | 95, 70, 50, 35 | CRITICAL | Major cost item |
| Cable Type | "4C+E CU PVC SWA" | HIGH | Specification |
| Length (m) | 50, 100 | HIGH | For costing |
| Installation | "underground", "tray" | MEDIUM | Method |

### 5.2 Sub-feeds

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| From | "DB-MAIN" | HIGH | Source DB |
| To | "DB-S1", "DB-KITCHEN" | HIGH | Destination DB |
| Cable Size (mm²) | 16, 25, 35 | HIGH | Sub-main size |
| Length (m) | 20, 30 | MEDIUM | For costing |

---

## SECTION 6: LEGEND/SYMBOLS

Extract from legend box on drawings:

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Symbol Image | [circle with cross] | HIGH | Visual representation |
| Symbol Meaning | "LED Downlight 15W" | HIGH | What it represents |
| Symbol Code | "DL-1", "SP-2" | MEDIUM | Reference code |

---

## SECTION 7: TOTALS (Summary)

Calculate or extract totals:

| Field | Example | Priority | Notes |
|-------|---------|----------|-------|
| Total DBs | 5 | CRITICAL | Number of boards |
| Total Circuits | 85 | CRITICAL | All circuits |
| Total Lights | 124 | CRITICAL | All light points |
| Total Sockets | 86 | CRITICAL | All socket points |
| Total Switches | 42 | HIGH | All switches |
| Total Cable (m) | 500 | HIGH | Approximate |

---

## QUICK REFERENCE: What to Extract by Document Type

### If you see a COVER/REGISTER page:
- [ ] Project name
- [ ] Client name
- [ ] Drawing list (number, name, revision)

### If you see a SITE PLAN:
- [ ] DB locations (names and positions)
- [ ] Cable routes between DBs
- [ ] Cable sizes for main feeds

### If you see an SLD:
- [ ] DB hierarchy (main → sub → final)
- [ ] Main breaker ratings
- [ ] Feeder cable sizes
- [ ] ELCB/protection devices

### If you see a CIRCUIT SCHEDULE TABLE:
- [ ] Each circuit: name, MCB, cable, points, wattage
- [ ] Total circuit count
- [ ] Spare way count
- [ ] Phase allocation (if shown)

### If you see a LIGHTING LAYOUT:
- [ ] Count each light symbol type
- [ ] Note which room each light is in (if possible)
- [ ] Total light points

### If you see a POWER LAYOUT:
- [ ] Count each socket symbol type
- [ ] Count switches
- [ ] Note isolators and FCUs
- [ ] Total socket points

### If you see a LEGEND:
- [ ] Map each symbol to its meaning
- [ ] Note wattage if specified
- [ ] Note any special symbols

---

## SCORING WEIGHTS

When scoring extractions, use these weights:

| Category | Weight | Fields |
|----------|--------|--------|
| CRITICAL (40%) | 1.0 | MCB ratings, cable sizes, circuit count, total fixtures |
| HIGH (35%) | 0.7 | DB names, circuit types, wattage, protection devices |
| MEDIUM (20%) | 0.4 | Descriptions, locations, phases, installation methods |
| LOW (5%) | 0.1 | Project name, dates, revision, consultant |

---

## EXAMPLE: Scoring a Document

Document has:
- 3 DBs (AI found 3) → CRITICAL ✓
- 45 circuits (AI found 42) → 93% accuracy
- MCB ratings 80% correct → CRITICAL partial
- Cable sizes 70% correct → CRITICAL partial
- 124 lights (AI found 118) → 95% accuracy
- 86 sockets (AI found 90) → 95% accuracy (overcounted)

**Score Calculation:**
- DB count: 100% × 1.0 = 1.0
- Circuit count: 93% × 1.0 = 0.93
- MCB ratings: 80% × 1.0 = 0.80
- Cable sizes: 70% × 1.0 = 0.70
- Light count: 95% × 1.0 = 0.95
- Socket count: 95% × 1.0 = 0.95

**Weighted Average:** (1.0 + 0.93 + 0.80 + 0.70 + 0.95 + 0.95) / 6 = **88.8%**

---

## TIPS FOR CREATING GROUND TRUTH

1. **Start with totals** - Count total lights, sockets, circuits first
2. **Use a PDF reader** - Zoom in on schedule tables
3. **Double-check counts** - Count twice, especially fixtures
4. **Note what's NOT visible** - Mark as `null` if not shown
5. **Be consistent** - Use same naming conventions across documents
6. **Take your time** - 15-30 minutes per document is normal
