# NPV Discounting Methodology - Stakeholder Explanation

**Date:** December 14, 2024  
**Audience:** RWF Leadership, Board Members, External Stakeholders  
**Purpose:** Explain why we use "labor market entry" as NPV base year

---

## Executive Summary

**Our NPV estimates (e.g., ₹22.8L for RTE) are calculated using:**
- **Base year:** When benefits start (labor market entry at age 22)
- **Salary baseline:** Current 2025 wages (not projected 2041 wages)
- **Why:** Standard practice in education economics; avoids uncertain long-term forecasts

**This is NOT "ignoring inflation"** — it's using today's prices as the reference frame for comparability across interventions.

---

## The Two Approaches Compared

### ❌ APPROACH A: Project Future Salaries (NOT USED)

```
1. Forecast 2041 salaries (requires 16-year wage inflation forecast)
2. Calculate NPV in 2041 terms
3. Discount back to 2025

Problems:
- Requires forecasting India's wage inflation through 2041 (highly uncertain)
- Different interventions need different forecast horizons
- Introduces compounding forecast errors
- Harder to compare across interventions with different timelines
```

### ✅ APPROACH B: Use Current Salaries (OUR METHOD)

```
1. Use 2025 salaries as baseline ("today's rupees")
2. Calculate NPV at labor market entry (2041 for RTE)
3. [Optional] Convert to intervention year if needed

Benefits:
- No long-term wage forecasting needed
- All interventions use same salary baseline → apples-to-apples comparison
- Standard practice in education CBA literature
- Simpler stakeholder communication
```

---

## Worked Example: RTE Intervention

### Timeline
- **2025:** Child age 6 enrolls in RTE program
- **2041:** Child age 22 enters labor market
- **2041-2081:** 40-year working life (ages 22-62)

### Our Calculation

**Step 1:** Use 2025 wage data
- Urban male with higher secondary: ₹32,800/month
- This is ACTUAL current data, not a forecast

**Step 2:** Calculate wage trajectory (2041-2081)
```
Year 1 (2041): ₹32,800/mo × Formal multiplier × Education premium
Year 2 (2042): Year 1 wage × (1 + 0.01%) [minimal real growth]
...
Year 40 (2081): ...
```

**Step 3:** Discount trajectory to labor market entry (2041)
```
NPV_2041 = Σ [Year_t earnings] / (1.0372)^t
         = ₹22.8 lakhs (in 2025 prices, at 2041 entry)
```

### Interpretation

**₹22.8L means:** 
> "If this child enters the labor market in 2041 earning 2025-level salaries, the present value of their incremental lifetime earnings (at 2041 entry) is ₹22.8L in today's rupees."

**It does NOT mean:**
- ~~"We predict 2041 salaries will be the same as 2025"~~ → No prediction made
- ~~"We're ignoring inflation"~~ → We're using real (inflation-adjusted) framework
- ~~"Benefits start immediately"~~ → Base year is 2041, not 2025

---

## Converting to Intervention-Year Terms (Optional)

**If stakeholders want:** "What's the ₹22.8L worth in 2025 terms?"

**Answer:** Use additional discounting for the 16-year delay:

```python
NPV_2025 = ₹22.8L / (1.0372)^16
         = ₹12.2L
```

**Interpretation:**
> "The ₹22.8L benefit starting in 2041 is worth ₹12.2L in '2025 intervention-year terms' after accounting for the 16-year delay."

**When to use:**
- Comparing 2025 intervention costs to 2025-equivalent benefits
- Board asking: "What's the bang-for-buck in today's terms?"

**When NOT to use:**
- Comparing RTE vs Apprenticeship (different timelines → stick to entry-year NPV)
- Academic publications (standard is entry-year NPV)
- Policy analysis (entry-year is clearer reference point)

---

## Visual Diagram

```
Timeline for RTE:
2025          2041                                    2081
 |             |                                       |
 v             v                                       v
Enroll      Enter         [40-year working life]    Retire
Age 6      Age 22                                   Age 62

 |-------------|----------------------------------------|
    16 years         40 years of earnings trajectory
    (no earnings)    (discounted to age 22 entry)


Our NPV base year: ▲ (Age 22, year 2041)
                   Use 2025 wages, discount 40 years forward

Alternative base: ▲ (Age 6, year 2025)  
                 Would need to forecast 2041 wages, then discount 56 years forward
                 → More uncertain, less standard
```

---

## Why This Matters: Cross-Intervention Comparison

**Scenario:** Comparing RTE vs Apprenticeship

### Using Entry-Year NPV (Our Method) ✅

| Intervention    | Entry Age | NPV Base Year | NPV Value    |
|-----------------|-----------|---------------|--------------|
| RTE             | 22        | 2041          | ₹22.8L       |
| Apprenticeship  | 18-20     | 2025-2027     | ₹104L        |

**Both use 2025 salary baseline** → Direct comparison of intervention effects
- "Apprenticeship delivers 4.6× higher NPV per beneficiary"
- Clear policy insight

### Using Intervention-Year NPV (Alternative)

| Intervention    | NPV (2025 terms) | Calculation              |
|-----------------|------------------|--------------------------|
| RTE             | ₹12.2L           | ₹22.8L / (1.0372)^16     |
| Apprenticeship  | ₹104L            | No adjustment needed     |

**Problem:** Now comparison is confusing
- "Why does RTE look worse? Just because benefits start later?"
- Loses clarity of treatment effect size

---

## Academic Justification

This approach follows:

1. **Becker (1964)** - Human Capital Theory
   - Education as investment with delayed returns
   - NPV calculated at "start of returns" (labor market entry)

2. **Card (1999, 2001)** - Returns to Education Literature
   - Standard to use current wage data
   - Cross-sectional analysis of wage differentials

3. **Psacharopoulos & Patrinos (2018)** - World Bank Reviews
   - "Use current earnings data as proxy for future earnings"
   - Avoid compounding forecast uncertainty

4. **Heckman et al. (2010)** - Perry Preschool Study
   - 40-year follow-up, NPV at program end (age 27)
   - Same principle: discount from when measurable benefits start

---

## Common Questions

### Q1: "Aren't we ignoring inflation?"

**No.** We're using a **real (inflation-adjusted) framework**:
- Salaries are in "constant 2025 rupees" 
- Discount rate (3.72%) is a **real rate** (already adjusted for inflation)
- This is standard practice in long-term CBA

Think of it like: "How much value does this intervention create, measured in rupees of constant purchasing power?"

### Q2: "Won't wages actually be higher in 2041?"

**Maybe, maybe not.** But forecasting is risky:
- **Optimistic scenario:** Wages grow 3%/year → 2041 wages are 60% higher
- **Pessimistic scenario:** Wage stagnation continues → 2041 wages similar to 2025
- **Our approach:** Use today's known wages; focus on treatment EFFECT (differential)

The key insight: *We care about DIFFERENTIAL impact (treatment vs control), not absolute salary levels.* Even if all wages rise 60%, the RTE premium should rise proportionally.

### Q3: "How do we compare to intervention costs in 2025?"

Use the **conversion utility** (optional):
```python
NPV_2025 = adjust_npv_to_intervention_year(
    npv_at_entry=22.8L, 
    years_to_entry=16
)
# Result: ₹12.2L
```

Then compare: 
- Cost per RTE beneficiary: ₹X
- Benefit (2025 terms): ₹12.2L
- BCR (2025 terms) = 12.2L / X

### Q4: "Why not just use Year 0 = Intervention?"

**Three reasons:**

1. **Cleaner conceptually:** "When do benefits start?" → Age 22 entry
2. **Standard practice:** Education economics literature uses entry-year NPV
3. **Comparability:** RTE (16-year delay) vs Apprenticeship (0-year delay) need common reference

The intervention-year adjustment is always available via utility function if needed.

---

## Recommendations for Different Audiences

### For Board Members
**Keep it simple:**
> "We calculate NPV using today's salaries and discount from when earnings actually start. This is the standard approach in education economics and avoids having to forecast what salaries will be 15+ years from now."

**If they ask for intervention-year NPV:**
> "The ₹22.8L becomes ₹12.2L when we account for the 16-year delay before benefits begin. We typically report the ₹22.8L because it's clearer for comparing interventions."

### For Funders/Donors
**Emphasize rigor:**
> "Our methodology follows World Bank and academic best practices. We use current wage data as baseline, which is more reliable than long-term forecasts and enables direct comparison across interventions with different timelines."

### For Academic/Policy Audiences
**Be technical:**
> "NPV calculated at labor market entry using current wage differentials and 3.72% real social discount rate. This approach follows Card (1999), Heckman et al. (2010), and Psacharopoulos & Patrinos (2018). For intervention-year comparison, apply additional discounting factor (1+δ)^t where t is years to entry."

### For Internal Team
**Document clearly:**
> "Base year = age 22 entry. Use 2025 PLFS wages. Discount 40 years forward. If needed for costs comparison, convert using adjust_npv_to_intervention_year() function with years_to_entry=16 for RTE."

---

## Summary: Three Key Numbers

For RTE intervention:

1. **₹22.8 lakhs** - Standard NPV (at labor market entry, age 22)
   - Use this for: Intervention comparison, academic papers, policy briefs
   
2. **₹12.2 lakhs** - Intervention-year NPV (at enrollment, age 6)
   - Use this for: Comparing to 2025 program costs, board presentations
   
3. **₹10.6 lakhs** - Control group lifetime earnings
   - Use this for: Showing absolute impact (treatment earns ₹33.4L vs ₹10.6L control)

**All three are correct** — they just use different reference points. Choose based on your audience and purpose.

---

## Technical Appendix: Formula Summary

### Standard NPV (Labor Market Entry Base)
```
NPV_entry = Σ_{t=0}^{40} [W_t^treatment - W_t^control] / (1+δ)^t

Where:
- W_t = wage in year t (using 2025 baseline levels)
- δ = 0.0372 (real social discount rate)
- t=0 is age 22 (labor market entry)
```

### Intervention-Year NPV (Optional Conversion)
```
NPV_intervention = NPV_entry / (1+δ)^k

Where:
- k = years from intervention to labor market entry
- For RTE: k=16 (age 6→22)
- For Apprenticeship: k≈0 (age 18-20→18-20)
```

### Real Wage Growth Within Trajectory
```
W_t = W_0 × (1+g)^t × [Mincer factors]

Where:
- g = 0.0001 (0.01% real growth - essentially flat)
- Captures within-career dynamics, NOT forecasting future salary levels
```

---

**Bottom Line:** We use current salaries and discount from labor market entry because it's simpler, more standard, and more reliable than forecasting 15-year wage inflation. If stakeholders need intervention-year comparison, we can convert using the utility function.
