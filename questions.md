# Expert Electrical Engineer Interview Questions

## Purpose

This document contains strategic questions for validating the **AfriPlan Electrical** quotation platform against South African electrical standards and industry practices.

**Meeting Context:** Interview with an expert electrical engineer/project manager with 30+ years experience in electrical quotations for residential, commercial, and maintenance projects in South Africa.

**Goal:** Validate our app's calculations, assumptions, and pricing against real-world industry practice to ensure reliability and credibility.

---

## Section 1: SANS 10142-1:2017 Compliance

### Q1.1 - Light Point Load
**Question:** Is 50W per light point still a valid assumption for LED-era load calculations, or should we use a different figure?

> **Why we need this:** App uses 50W/light point for all load calculations. Older standards used 100W for incandescent. Need to confirm modern LED assumption is acceptable.

---

### Q1.2 - Plug Point Load
**Question:** Is 250W per plug point the correct demand figure, or does SANS 10142-1 specify something different?

> **Why we need this:** App uses 250W/plug for diversified load calculations. Some sources cite 200W. Need authoritative figure.

---

### Q1.3 - Diversity Factor
**Question:** Is a flat 50% diversity factor acceptable for residential final circuits, or should we use the tabulated values from SANS 10142-1 Table 1?

> **Why we need this:** App applies blanket 50% diversity to all lighting + power loads. SANS 10142-1 has tabulated values by load type and number of points. This significantly affects supply sizing.

---

### Q1.4 - Lighting Circuit Limit
**Question:** What is the maximum number of points per lighting circuit? We use 10 - is this correct?

> **Why we need this:** App limits circuits to 10 points based on SANS 10142-1. Need confirmation.

---

### Q1.5 - Power Circuit Limit
**Question:** What is the maximum number of points per power circuit? We use 10 - is this correct?

> **Why we need this:** Same assumption as lighting circuits - need validation.

---

### Q1.6 - Earth Leakage Protection
**Question:** Is a 30mA ELCB (RCD) mandatory on ALL circuits, or only certain circuit types?

> **Why we need this:** App always includes 63A 30mA ELCB in every residential BQ. Need to confirm this is mandatory, not optional.

---

### Q1.7 - Surge Protection
**Question:** Is surge protection (Type 1, Type 2, or Type 1+2) mandatory in SANS 10142-1, or only recommended?

> **Why we need this:** App includes Type 2 SPD in every quote. Need to know if mandatory or recommended, and whether Type 1+2 is required in lightning-prone areas (Highveld).

---

### Q1.8 - DB Board Spare Ways
**Question:** What percentage of spare DB ways should be allowed for future expansion? We use 15% minimum.

> **Why we need this:** App adds 2 extra ways but doesn't strictly verify 15% rule. Need industry standard.

---

### Q1.9 - Voltage Drop Limits
**Question:** For voltage drop calculations, is 5% total (2.5% sub-mains + 2.5% final) the correct limit?

> **Why we need this:** App uses this split for compliance checking. Need confirmation of correct interpretation.

---

### Q1.10 - Temperature Derating
**Question:** Are the mV/A/m values in SANS 10142-1 Annexure B based on 30°C ambient temperature? What derating should apply for typical SA conditions (35-40°C)?

> **Why we need this:** App uses raw table values without temperature correction. SA climate regularly exceeds 30°C - this is a potential safety concern.

---

## Section 2: Dedicated Circuits & Special Requirements

### Q2.1 - Stove Circuit
**Question:** Is a dedicated 32A circuit mandatory for electric stoves, or can smaller stoves share circuits?

> **Why we need this:** App always specifies 32A dedicated stove circuit. Need to know if this applies to all stoves or only above a certain kW rating.

---

### Q2.2 - Stove Phase Requirement
**Question:** Is 3-phase recommended or required for stove circuits in residential?

> **Why we need this:** App offers both single-phase and 3-phase options. Need guidance on when each is appropriate.

---

### Q2.3 - Geyser Circuit Size
**Question:** What size dedicated circuit is required for geysers? We specify 20A with timer - is this correct?

> **Why we need this:** App uses 2.5mm cable on 20A circuit for geysers. Need validation.

---

### Q2.4 - Geyser Load Limit
**Question:** At what geyser size (litres or kW) does a 20A circuit become undersized?

> **Why we need this:** App assumes 3kW geyser load. 200L and 250L geysers may exceed this.

---

### Q2.5 - Geyser Timer Requirement
**Question:** Is a geyser timer/switch legally required, or just recommended for energy savings?

> **Why we need this:** App includes geyser timer in all geyser circuits. Need to know if mandatory.

---

### Q2.6 - Outdoor Socket IP Rating
**Question:** What are the IP rating requirements for outdoor sockets (pool pumps, garden, etc.)?

> **Why we need this:** App specifies IP65 for pool pump circuits. Need confirmation of minimum requirement.

---

### Q2.7 - Pool Pump Earthing
**Question:** Are there specific earthing requirements for pool pump circuits beyond standard earthing (e.g., equipotential bonding)?

> **Why we need this:** App treats pool pump as standard dedicated circuit. May need additional safety requirements.

---

## Section 3: Cable Sizing & Installation

### Q3.1 - Average Cable Run Length
**Question:** What is a realistic average cable run length per point for:
- (a) Single-storey house?
- (b) Double-storey house?
- (c) Apartment/flat?

> **Why we need this:** App uses flat 8m per point for ALL residential projects. This is likely inaccurate and affects material quantities significantly.

---

### Q3.2 - Cable Wastage Factor
**Question:** When calculating cable runs, what percentage should be added for wastage/terminations?

> **Why we need this:** App doesn't include explicit wastage factor. Industry practice may be 10-15%.

---

### Q3.3 - Temperature Derating Factor
**Question:** In SA climate conditions (ambient 30-40°C), what derating factor should be applied to cable current ratings?

> **Why we need this:** App uses 30°C ambient ratings without correction. Need specific derating factors for SA conditions.

---

### Q3.4 - Grouping Derating Factor
**Question:** What grouping derating factor should be applied when multiple cables run together in conduit?

> **Why we need this:** App doesn't apply grouping factors. This affects cable sizing for current-carrying capacity.

---

### Q3.5 - Conduit Quantity Estimate
**Question:** What is the typical conduit quantity per point? We estimate 2 x 4m lengths (8m) per point.

> **Why we need this:** Need validation of conduit estimation for accurate BQ generation.

---

### Q3.6 - Renovation Cable Factor
**Question:** For renovation/rewiring projects, should cable quantities be multiplied by a factor? What factor?

> **Why we need this:** App uses complexity factors (1.0 to 1.5x) but they're applied to total cost, not cable-specific. May need separate cable multiplier.

---

## Section 4: NRS 034 ADMD & Supply Sizing

### Q4.1 - Current ADMD Values
**Question:** Are these ADMD values still current for NRS 034?

| Dwelling Type | Our ADMD Value |
|---------------|----------------|
| RDP/Low cost | 1.5-2.0 kVA |
| Standard house | 3.5-4.0 kVA |
| Medium house | 5.0-6.0 kVA |
| Large house | 8.0-10.0 kVA |
| Luxury estate | 12.0-15.0 kVA |

> **Why we need this:** App uses these values for supply sizing. Need validation against current NRS 034 revision.

---

### Q4.2 - Three-Phase Threshold
**Question:** At what supply current does Eskom typically offer three-phase instead of single-phase?

> **Why we need this:** App switches to 3-phase only above 100A. In practice, Eskom may offer 3-phase from 60A or 80A in urban areas.

---

### Q4.3 - Multi-Dwelling Diversity
**Question:** For multi-dwelling developments, are these diversity factors correct?

| Number of Units | Our Diversity Factor |
|-----------------|---------------------|
| 1-5 units | 1.0 (no diversity) |
| 6-10 units | 0.85 |
| 11-20 units | 0.75 |
| 21-50 units | 0.65 |
| 51+ units | 0.55 |

> **Why we need this:** App uses stepped factors instead of NRS 034 formula-based approach. Need to know if this is acceptable.

---

### Q4.4 - Alternative Geyser ADMD Reduction
**Question:** What ADMD reduction is appropriate for solar geysers vs gas geysers?

> **Why we need this:** App uses -0.5 kVA for solar, -1.0 kVA for gas. Need validation of these reductions.

---

## Section 5: COC & Compliance

### Q5.1 - COC Fee Structure
**Question:** What is the typical COC inspection fee structure? Per point, per circuit, or flat fee?

> **Why we need this:** App uses R2,200 flat fee for residential COC. Industry may use different pricing models.

---

### Q5.2 - Common COC Failures
**Question:** What are the most common COC failures you see in the field?

> **Why we need this:** Need to ensure app flags critical compliance items and includes necessary components in every quote.

---

### Q5.3 - Earth Loop Impedance Testing
**Question:** Is earth loop impedance testing (Zs measurement) required for every COC, or only in certain cases?

> **Why we need this:** App calculates Zs but need to know when it's actually tested in practice.

---

### Q5.4 - Supply Impedance Value
**Question:** What supply impedance (Ze) value should be assumed for calculations? We use 0.35 ohms.

> **Why we need this:** App hardcodes supply impedance at 0.35 ohms. This varies by distance from substation. Need guidance on appropriate assumptions.

---

### Q5.5 - MCB Types
**Question:** Are Type B MCBs standard in SA, or are Type C common for certain applications?

> **Why we need this:** App uses Type B Zs values for earth fault calculations. Type C breakers have different requirements (approximately half the Zs limit).

---

## Section 6: Labour Rates & Pricing

### Q6.1 - Current Labour Rates
**Question:** What are current (2025/2026) labour rates for:

| Task | Our Rate | Your Rate |
|------|----------|-----------|
| Light point installation (complete) | R280 | ? |
| Power point installation (complete) | R320 | ? |
| DB board installation | R1,500 | ? |
| Stove circuit (complete) | R1,800 | ? |
| Geyser circuit (complete) | R1,500 | ? |

> **Why we need this:** App uses these labour rates - need validation against current market rates.

---

### Q6.2 - Regional Rate Variation
**Question:** Do labour rates vary significantly by region (Gauteng vs Cape Town vs Durban)?

> **Why we need this:** App uses single national rate. May need regional adjustments for accuracy.

---

### Q6.3 - Complexity Multipliers
**Question:** What complexity multiplier would you apply for:

| Project Type | Our Factor | Your Factor |
|--------------|------------|-------------|
| New build on slab | 1.0x (baseline) | ? |
| New build on raft/suspended | 1.1x | ? |
| Renovation with easy access | 1.2x | ? |
| Renovation with chasing required | 1.35x | ? |
| Complete rewire | 1.5x | ? |

> **Why we need this:** App uses 1.0 to 1.5x range - need validation from experienced contractor.

---

### Q6.4 - Profit Margin
**Question:** What is a typical contractor profit margin on electrical work?

> **Why we need this:** App allows 10-50% margin slider. Need to know realistic range for competitive quoting.

---

### Q6.5 - Payment Terms
**Question:** What payment terms are standard in the industry?

| Our Options | Description |
|-------------|-------------|
| 40/40/20 | 40% deposit, 40% progress, 20% completion |
| 50/30/20 | 50% deposit, 30% progress, 20% completion |
| 30/30/30/10 | Progress payments with retention |

> **Why we need this:** Need to confirm these are industry-standard terms.

---

## Section 7: Commercial & Industrial

### Q7.1 - Commercial Load Densities
**Question:** What W/m² load density figures do you use for commercial buildings?

| Load Type | Our Value | Your Value |
|-----------|-----------|------------|
| Office lighting | 17 W/m² | ? |
| Office small power | 25 W/m² | ? |
| Office HVAC | 120 W/m² | ? |
| Retail lighting | 30 W/m² | ? |
| Healthcare lighting | 65 W/m² | ? |

> **Why we need this:** Need industry validation of commercial load factors for accurate sizing.

---

### Q7.2 - HVAC Load Reality
**Question:** Is 120 W/m² for HVAC realistic, or has efficiency improved this figure?

> **Why we need this:** Modern energy-efficient buildings may use 60-80 W/m². Using 120 W/m² could significantly oversize systems.

---

### Q7.3 - Industrial Motor Cable Runs
**Question:** For industrial motor loads, what is a typical average cable run per motor?

> **Why we need this:** App uses 30m per motor - likely too generic. Underground mining could be hundreds of metres.

---

### Q7.4 - Power Factor Correction Ratio
**Question:** What power factor correction ratio (kVAr per kW of motor load) is typical?

> **Why we need this:** App uses 0.4 kVAr/kW rule of thumb. Need validation or alternative method.

---

### Q7.5 - Transformer Sizing for Motors
**Question:** For MV installations (11kV), what are typical transformer sizing considerations for motor starting?

> **Why we need this:** App sizes transformer on running load only, not starting kVA. Motor starting can demand 6-7x full load current.

---

## Section 8: Quotation Best Practices

### Q8.1 - Professional Quote Requirements
**Question:** What information must a professional electrical quotation include to be taken seriously by clients?

> **Why we need this:** Ensure app output meets professional standards and includes all expected elements.

---

### Q8.2 - Common Quote Errors
**Question:** What are the most common errors you see in competitor quotes?

> **Why we need this:** Avoid common pitfalls in app-generated quotes.

---

### Q8.3 - Provisional Sums & PC Items
**Question:** How do you handle provisional sums and prime cost items in quotations?

> **Why we need this:** App doesn't currently support PC/PS items. May need to add this feature.

---

### Q8.4 - Quote Validity
**Question:** Should quotations include validity periods? What is standard?

> **Why we need this:** App doesn't include quote validity. Need to know if this is expected (e.g., "Valid for 30 days").

---

### Q8.5 - Variations Handling
**Question:** How do you handle variations and scope changes after quote acceptance?

> **Why we need this:** App generates static quotes without variation mechanism. May need to add variation clause or process.

---

### Q8.6 - Supporting Documentation
**Question:** What documentation do you provide with quotations (technical drawings, cable schedules, etc.)?

> **Why we need this:** App exports PDF/Excel but no technical drawings. May need to enhance output.

---

### Q8.7 - Plan-Based vs Site-Measured Accuracy
**Question:** In your experience, what percentage accuracy can be achieved from plan-based quotations vs site-measured quotes?

> **Why we need this:** Critical for setting realistic user expectations. If plan-based is typically 70-80% accurate, users need to know this upfront.

---

### Q8.8 - Software Quote Credibility
**Question:** What would make you trust a software-generated quotation? What would make you reject it?

> **Why we need this:** Direct feedback on what makes app output credible or not in the eyes of an experienced professional.

---

## Notes Section

*Use this space to record the expert's answers during the meeting.*

### Key Takeaways:
1.
2.
3.
4.
5.

### Items Requiring App Updates:
1.
2.
3.
4.
5.

### Standards Documents to Obtain:
1.
2.
3.

---

## Document Info

**Created:** February 2026
**Platform:** AfriPlan Electrical v2.0
**Purpose:** Expert validation meeting preparation
**Author:** JLWanalytics
