# Parameter Registry Clarifications - Discounting Methodology

**Date:** December 14, 2024  
**Purpose:** Clarify how REAL_WAGE_GROWTH and INFLATION_RATE relate to discounting approach

---

## Key Clarifications

### 1. REAL_WAGE_GROWTH Parameter (g = 0.01%)

**What it represents:**
- WITHIN-CAREER wage growth dynamics
- How wages evolve over the 40-year working life
- Applied to the earnings trajectory AFTER labor market entry

**What it does NOT represent:**
- Forecasting future starting salaries
- Projecting what 2041 entry wages will be
- Attempting to predict long-term wage inflation

**Example:**
```python
# Year 0 (age 22, 2041): Entry wage using 2025 PLFS data
W_0 = Rs 32,800/month (from PLFS 2023-24)

# Year 1 (age 23, 2042): Within-career growth
W_1 = W_0 × (1 + 0.0001) = Rs 32,803/month  # Almost no change

# Year 40 (age 62, 2081): After 40 years of 0.01% growth
W_40 = W_0 × (1.0001)^40 = Rs 32,932/month  # Only 0.4% higher
```

**Interpretation:**
The 0.01% real wage growth captures the STAGNATION of real wages in India's current labor market. This is applied across the career trajectory but does NOT mean we're forecasting 2041 salaries - we're using 2025 salaries as baseline and showing they barely grow in real terms.

### 2. INFLATION_RATE Parameter (π = 4.95%)

**Role in the model:**
- DOCUMENTATION ONLY - not directly used in NPV calculations
- Shows relationship: nominal growth ≈ inflation + real growth

**Why it's not used:**
Our entire model works in REAL (inflation-adjusted) terms:
1. Baseline wages → Already in real terms (2025 constant prices)
2. REAL_WAGE_GROWTH → Already inflation-adjusted
3. SOCIAL_DISCOUNT_RATE → Already a real discount rate (3.72%)

**What this means:**
```
Nominal wage growth ≈ 5% per year
  = Inflation (4.95%) + Real growth (0.01%)
  
But we skip the nominal → real conversion by working directly in real terms:
  W_t = W_0 × (1 + g)^t  [where g = 0.01%, already real]
```

**No double-counting:**
- We do NOT inflate wages by 4.95% then deflate by 4.95%
- We work directly with real growth of 0.01%
- This is standard practice in long-term CBA

### 3. Discounting Methodology Summary

**Three components work together:**

1. **Baseline wages (2025):** Use current PLFS data
   - Urban male HS: Rs 32,800/month
   - This is our "real wage" reference point

2. **Real wage growth (0.01%):** Within-career trajectory
   - W_t = W_0 × (1.0001)^t × [Mincer factors]
   - Captures stagnation, not forecasting

3. **Real discount rate (3.72%):** Time preference
   - NPV = Σ W_t / (1.0372)^t
   - Already accounts for social time preference
   - No additional inflation adjustment needed

**Result:** NPV in "constant 2025 rupees at labor market entry"
- Easy to interpret
- Standard practice
- Avoids uncertain long-term forecasts

---

## Common Misunderstandings (and Corrections)

### ❌ "You're assuming zero wage growth"

**✓ Correction:** 
We're documenting that real wages have STAGNATED (0.01% growth based on PLFS 2020-24 data). This is an empirical finding, not an assumption. The model reflects observed reality.

### ❌ "You're ignoring inflation"

**✓ Correction:**
We work entirely in real (inflation-adjusted) terms. The 4.95% inflation is already "baked in" - we use real wages and real discount rates. This is standard practice.

### ❌ "Wages will be higher in 2041"

**✓ Correction:**
We don't forecast 2041 nominal wages. We use 2025 real wages and project their trajectory in constant-purchasing-power terms. Whether nominal wages rise 50% or stay flat, the REAL wage (purchasing power) is what matters for welfare analysis.

### ❌ "The 0.01% growth means you think wages won't change"

**✓ Correction:**
The 0.01% captures WITHIN-CAREER dynamics (how wage-age profiles evolve). It's not about forecasting future starting salaries - it's about showing that workers today don't experience significant real wage growth over their careers due to labor market stagnation.

---

## Technical Notes

### Relationship Between Parameters

```
Nominal wage at time t:
  W_nominal(t) = W_0_nominal × (1 + nominal_growth)^t
  
  Where nominal_growth ≈ inflation + real_growth
                      ≈ 4.95% + 0.01%
                      ≈ 5%

Real wage at time t (what we model):
  W_real(t) = W_0_real × (1 + real_growth)^t
            = W_0_real × (1.0001)^t
            ≈ W_0_real  [essentially flat]

Key insight: We skip the nominal calculation entirely and work directly with real values.
```

### Why This Approach is Conservative

Using 2025 wages (not projecting 2041 wages) tends to be CONSERVATIVE because:
1. If real wages actually grow 1-2%/year (optimistic scenario), our NPV underestimates
2. If real wages stay flat (pessimistic scenario), our NPV is accurate
3. We're not banking on optimistic wage forecasts

This makes our BCR estimates more robust and defensible.

### When to Adjust This Approach

You might want to use nominal projections if:
1. Comparing to NOMINAL cost streams (but better to convert costs to real)
2. Stakeholders specifically request nominal projections
3. Publishing in venue that requires nominal calculations

For RWF purposes (intervention comparison, BCR analysis), the real framework is:
- More standard
- More conservative
- Less dependent on uncertain forecasts
- Easier to explain

---

## Summary for Documentation

**Add to parameter_registry_v2_updated.py notes:**

**REAL_WAGE_GROWTH:** 
"This represents within-career wage dynamics, NOT forecasting of future starting salaries. Model uses 2025 wages as baseline; 'g' shows career trajectory is essentially flat in real terms. Standard practice in education economics."

**INFLATION_RATE:**
"Documentation only - not used in NPV calculations. Model works entirely in real terms (baseline wages, real growth, real discount rate). This inflation rate shows relationship: nominal ≈ 5% = 4.95% inflation + 0.01% real."

---

**Bottom line:** Our discounting methodology is rigorous, conservative, and follows academic best practices. The key is that we work in real terms throughout, avoiding the need for uncertain long-term nominal wage forecasts.
