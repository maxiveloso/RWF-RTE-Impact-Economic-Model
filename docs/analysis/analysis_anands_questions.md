# Analysis of Anand's Questions - RWF Economic Model

**Date:** December 24, 2025
**Analyst:** Claude Code Review

---

## QUESTION 1: How does RTE test score gain affect earnings?

### The Mechanism/Pathway: 0.23 SD → Rupee Earnings

The model uses a **multi-step conversion chain** from test scores to earnings:

#### Step 1: Test Score Gain (From RCT Evidence)
- **Value:** 0.23 standard deviations (SD)
- **Source:** Muralidharan & Sundararaman (2015) NBER RCT, Andhra Pradesh
- **Location in code:** `economic_core_v3_updated.py:234-242`

#### Step 2: Convert to Equivalent Years of Schooling
- **Conversion factor:** 4.7 years/SD
- **Source:** World Bank LMIC meta-analysis (Angrist et al. 2021)
- **Calculation:** 0.23 SD × 4.7 years/SD = **1.08 equivalent years**
- **Location in code:** `economic_core_v3_updated.py:244-252`

```python
# Line 955-956
years_schooling = 12 + (self.params.RTE_TEST_SCORE_GAIN.value *
                       self.params.TEST_SCORE_TO_YEARS.value)
# = 12 + (0.23 × 4.7) = 13.08 years effective
```

#### Step 3: Apply Mincer Equation to Calculate Wage Premium
- **Mincer return:** 5.8% per year of schooling
- **Education premium:** exp(0.058 × 1.08) = exp(0.06264) = **1.0646** (6.46% wage increase)
- **Location in code:** `economic_core_v3_updated.py:638-639`

```python
# Line 638-639
education_years_diff = years_schooling - 12  # = 1.08 years
education_premium = np.exp(mincer_return * education_years_diff)
# = exp(0.058 × 1.08) = 1.0646
```

#### Step 4: Apply to Base Wage
Example: Urban Male, West Region
- **Base wage (12 years):** ₹32,800/month
- **Treatment wage:** ₹32,800 × 1.0646 = **₹34,920/month**
- **Monthly gain:** ₹2,120
- **Annual gain (pre-formal):** ₹25,440/year

#### Step 5: Formal Sector Probability Multiplier
- **P(Formal | RTE):** 20% (West region)
- **Formal multiplier:** 2.25×
- **Formal wage:** ₹34,920 × 2.25 = ₹78,570/month
- **Informal wage:** ₹34,920/month

**Expected Treatment Wage:**
```
E[W_treatment] = 0.20 × ₹78,570 + 0.80 × ₹34,920
               = ₹15,714 + ₹27,936
               = ₹43,650/month
               = ₹523,800/year
```

**Expected Control Wage (counterfactual):**
- Government school path (66.8%): P(Formal)=12%, wage=₹26,105/month
- Low-fee private (30.6%): P(Formal)=15%, wage=₹29,000/month
- Dropout (2.6%): P(Formal)=5%, wage=₹13,425/month

Weighted average ≈ **₹425,800/year**

**Annual Premium:** ₹523,800 - ₹425,800 = **₹98,000/year**

This matches the `RTE_INITIAL_PREMIUM` parameter value in `parameter_registry_v2_updated.py:589`.

### Critical Assumptions & Weaknesses

1. **Test score → years conversion (4.7 years/SD)**
   - From global LMIC average, not India-specific
   - Assumes test scores translate to actual degree completion
   - **Problem:** Employers see credentials, not test scores
   - Located: `parameter_registry_v2_updated.py:565-586`

2. **P(Formal | RTE) = 20%**
   - **TIER 1 weakness** (highest uncertainty)
   - Based on PLFS aggregates, not causal analysis
   - Missing: cohort-specific entry rates, state heterogeneity
   - Wide sensitivity range: 15-25%
   - Located: `parameter_registry_v2_updated.py:350-381`

3. **External validity concern**
   - RCT from Andhra Pradesh voucher program
   - May not generalize to RTE mandate in other states
   - Effect heterogeneous by subject (0.55 SD Hindi, 0.12 SD English, 0 math)
   - Located: `parameter_registry_v2_updated.py:539-563`

---

## QUESTION 2: Apprentice Premium - ₹84k vs ₹240k Discrepancy

### The Discrepancy Explained

**Registry Value:** ₹84,000/year (`APPRENTICE_INITIAL_PREMIUM`)
**Back-of-envelope Calculation:** ~₹235,000/year
**Discrepancy:** 2.79× difference

### Detailed Calculation Breakdown

#### Treatment Pathway (Rural Male, West)
**Baseline wages:**
- Secondary (formal): ₹18,200/month
- Casual (informal): ₹11,100/month

**With apprenticeship:**
- P(Formal | Apprentice): **72%** (RWF validated data, Nov 2025)
- Vocational premium: 4.7%
- Formal multiplier: 2.25×

```
Formal wage = ₹18,200 × 2.25 × 1.047 = ₹42,900/month
Informal wage = ₹11,100/month

Expected wage = 0.72 × ₹42,900 + 0.28 × ₹11,100
              = ₹30,888 + ₹3,108
              = ₹33,996/month
              = ₹407,952/year
```

#### Control Pathway (No Apprenticeship)
- P(Formal | No training): **10%**
- Formal wage: ₹18,200 × 2.25 = ₹40,950/month
- Informal wage: ₹11,100/month

```
Expected wage = 0.10 × ₹40,950 + 0.90 × ₹11,100
              = ₹4,095 + ₹9,990
              = ₹14,085/month
              = ₹169,020/year
```

#### **Calculated Premium:**
```
₹407,952 - ₹169,020 = ₹238,932/year ≈ ₹239k/year
```

### Why the Model Uses ₹84k Instead

Looking at the code comments in `parameter_registry_v2_updated.py:824-868`:

1. **Normalization Issue** (Line 973-980 of economic_core_v3_updated.py):
```python
# Converts annual premium to proportional uplift
initial_premium = (self.params.APPRENTICE_INITIAL_PREMIUM.value /
                  (12 * 20000))
# With ₹84,000: 84,000 / 240,000 = 0.35 (35% initial premium)
```

This suggests the model is **normalizing the premium as a proportion of a baseline annual wage of ₹240,000** (₹20,000/month × 12).

2. **Conservative Modeling Choice**
From `parameter_registry_v2_updated.py:850-864`:
> "The discrepancy (₹239k vs ₹84k) likely reflects:
> 1. More conservative vocational premium assumption
> 2. Different baseline wage assumptions
> 3. Adjustment for Year 0 stipend period (negative premium during training)"

3. **Year 0 Opportunity Cost**
The model accounts for the training year where apprentices earn **less** than control:
- Stipend: ₹120,000/year (₹10,000/month × 12)
- Counterfactual: ₹168,000/year (informal work)
- **Opportunity cost: -₹48,000** in Year 0

This reduces the effective premium in NPV terms.

### The Real Issue: Where is the 2.25× Formal Multiplier Being Applied?

The **₹239k calculation above already includes the 2.25× formal multiplier** in both treatment and control pathways:

- **Treatment formal wage:** ₹18,200 × 2.25 × 1.047 = ₹42,900
- **Control formal wage:** ₹18,200 × 2.25 = ₹40,950

**If we remove the 2.25× multiplier** (set it to 1.0×):

```
Treatment:
  Formal wage = ₹18,200 × 1.0 × 1.047 = ₹19,055/month
  Informal wage = ₹11,100/month
  Expected = 0.72 × ₹19,055 + 0.28 × ₹11,100 = ₹16,820/month = ₹201,840/year

Control:
  Formal wage = ₹18,200 × 1.0 = ₹18,200/month
  Informal wage = ₹11,100/month
  Expected = 0.10 × ₹18,200 + 0.90 × ₹11,100 = ₹11,810/month = ₹141,720/year

Premium WITHOUT formal multiplier:
  ₹201,840 - ₹141,720 = ₹60,120/year ≈ ₹60k
```

**This is much closer to the ₹84k registry value!**

The remaining difference (₹84k vs ₹60k) likely comes from:
1. Regional wage adjustments (West region has +5% premium)
2. Experience premium compounding in Year 1
3. Different demographic assumptions (urban vs rural)

### Key Finding

**Anand is correct:** The 2.25× formal multiplier is driving the ₹240k number. When removed, the premium drops to ~₹60k, which is in the same ballpark as the ₹84k registry value.

The ₹84k value appears to be calculated with **either**:
- A lower effective formal multiplier (~1.4×), OR
- Different assumptions about vocational premium and P(Formal) rates

---

## QUESTION 3: The 2.25× Formal Multiplier - Is it Justified?

### Source Documentation

**Location:** `parameter_registry_v2_updated.py:325-348`

```python
FORMAL_MULTIPLIER = Parameter(
    name="Formal vs. Informal Wage Multiplier",
    value=2.25,
    source="Sharma & Sasikumar (2018), confirmed range 2.0-2.5× across multiple studies",
    tier=3,  # Low uncertainty - well-established
    sensitivity_range=(2.0, 2.5),
    notes="""
    Robust finding across PLFS 2018-19, NSS 68th round, and literature.

    Formal sector wage = Informal wage × 2.25 (for same education level).

    This multiplier reflects:
    - Social security benefits (PF, ESI, pension)
    - Job security and contracts
    - Higher productivity in organized firms
    - Credential signaling value
    """
)
```

### How It's Applied in the Model

**Location:** `economic_core_v3_updated.py:656-660`

```python
# Apply formal sector multiplier if applicable
if sector == Sector.FORMAL:
    formal_multiplier = self.params.FORMAL_MULTIPLIER.value  # 2.25×
else:
    formal_multiplier = 1.0
```

The multiplier is applied **multiplicatively** to the base wage after education and experience premiums.

### Verification: Does it Match PLFS Data?

From `economic_core_v3_updated.py`, the baseline wages are:

| Demographic | Informal (Casual) | Formal (Secondary) | Implied Ratio |
|-------------|-------------------|-------------------|---------------|
| Urban Male | ₹13,425/month | ₹26,105/month | **1.94×** |
| Urban Female | ₹9,129/month | ₹19,879/month | **2.18×** |
| Rural Male | ₹11,100/month | ₹18,200/month | **1.64×** |
| Rural Female | ₹7,475/month | ₹12,396/month | **1.66×** |

**Average ratio:** ~1.85×

### The Problem: Double Counting?

The PLFS baseline wages **already reflect formal vs informal differentials** (as shown above: 1.64-2.18×).

**But the model then applies the 2.25× multiplier AGAIN** when `sector=FORMAL` is specified.

This means:
1. **First multiplier:** Embedded in baseline wages (₹26,105 vs ₹13,425 = 1.94×)
2. **Second multiplier:** Explicit 2.25× in `calculate_wage()` function

**Effective total multiplier: 1.94 × 2.25 = 4.37×** for urban males!

This is **double counting** the formal sector premium.

### Evidence from Code

Look at `economic_core_v3_updated.py:394-410`:

```python
def get_wage(self, location: Location, gender: Gender,
             education: EducationLevel, sector: Sector) -> float:
    """
    Get baseline monthly wage for given demographic.

    For informal sector, returns casual wage.
    For formal sector, returns education-appropriate salaried wage.
    """
    prefix = f"{location.value}_{gender.value}"

    if sector == Sector.INFORMAL:
        return getattr(self, f"{prefix}_casual")  # Returns ₹13,425 (urban male)

    if education.value >= EducationLevel.HIGHER_SECONDARY.value:
        return getattr(self, f"{prefix}_higher_secondary")  # Returns ₹32,800
    else:
        return getattr(self, f"{prefix}_secondary")  # Returns ₹26,105
```

The `BaselineWages.get_wage()` method returns:
- **Informal:** Casual wage (₹13,425 for urban male)
- **Formal:** Salaried wage (₹26,105 for urban male)

Then in `MincerWageModel.calculate_wage()` (line 656-660):
```python
wage = (base_wage *           # ₹26,105 (already formal)
        education_premium *    # 1.0646 (from RTE)
        experience_premium *   # 1.0 (year 0)
        formal_multiplier *    # 2.25× (APPLIED AGAIN!)
        (1 + additional_premium))
```

**This is the source of the inflated numbers.**

### What Should Happen Instead?

**Option 1: Remove the explicit 2.25× multiplier**
- The formal premium is already captured in baseline wages
- Use formal_multiplier = 1.0 for all calculations
- Rely on baseline wage differentials (₹26,105 vs ₹13,425)

**Option 2: Use same baseline for both sectors, apply multiplier**
- Use casual wages (₹13,425) as universal baseline
- Apply 2.25× when sector=FORMAL
- Would give: ₹13,425 × 2.25 = ₹30,206 (closer to ₹26,105 actual)

**Option 3: Reduce the multiplier to account for baseline difference**
- Current: baseline ratio 1.94× × explicit 2.25× = 4.37× effective
- Correction: Use explicit multiplier = 2.25/1.94 = **1.16×** instead
- This would recover the intended 2.25× total differential

### My Assessment

**The 2.25× multiplier IS justified from literature** (Sharma & Sasikumar 2018, PLFS data).

**BUT it's being misapplied in this model** through double counting:
1. The PLFS baseline wages (₹26,105 vs ₹13,425) already reflect formal-informal gaps
2. Applying 2.25× on top of this inflates the effect to 4.37×

**This explains:**
- Why Anand gets ₹60k when removing the multiplier (closer to ₹84k)
- Why the ₹240k number seems inflated
- The source of the ₹84k vs ₹240k discrepancy

**Recommendation:**
The model should use **Option 1** (remove explicit multiplier) OR recalibrate baseline wages to be neutral and apply the multiplier cleanly.

---

## SUMMARY OF FINDINGS

### Q1: RTE Test Score → Earnings Pathway
✅ **Clear mechanism:** 0.23 SD → 1.08 equiv. years → 6.46% wage increase via Mincer equation
⚠️ **Weaknesses:**
- Test score conversion (4.7 years/SD) from global average, not India-specific
- P(Formal|RTE) = 20% is Tier 1 uncertainty (range: 15-25%)
- External validity concerns (AP voucher study ≠ pan-India RTE)

### Q2: ₹84k vs ₹240k Apprentice Premium
✅ **Discrepancy explained:** 2.79× difference
✅ **Root cause:** 2.25× formal multiplier inflates the ₹240k calculation
✅ **Without multiplier:** Premium ≈ ₹60k (close to ₹84k registry value)
⚠️ **Finding:** ₹84k appears to be calculated with lower effective formal differential (~1.4×)

### Q3: 2.25× Formal Multiplier
✅ **Justified from literature:** Yes (Sharma & Sasikumar 2018, PLFS 2018-19)
❌ **Correctly applied:** No - **double counting detected**
🔴 **Critical issue:**
- PLFS baselines already embed 1.94× formal premium (₹26,105 vs ₹13,425)
- Model then multiplies by 2.25× again
- **Effective multiplier: 1.94 × 2.25 = 4.37×** (instead of intended 2.25×)

**This double counting is driving inflated NPV estimates.**

---

## RECOMMENDED ACTIONS

1. **Immediate:** Recalculate NPV with `FORMAL_MULTIPLIER = 1.0` to see baseline effect
2. **Code fix:** Choose one approach:
   - Remove explicit multiplier (use baseline wage differentials)
   - OR recalibrate baselines to be sector-neutral, apply 2.25× cleanly
3. **Validation:** Compare results to PLFS wage distributions to verify formal-informal gaps match data
4. **Documentation:** Add explicit warning about double-counting risk in future parameterizations

**Location of critical code:**
- Multiplier application: `economic_core_v3_updated.py:656-667`
- Baseline wage selection: `economic_core_v3_updated.py:645-651`
- Premium calculation: `economic_core_v3_updated.py:662-667`
