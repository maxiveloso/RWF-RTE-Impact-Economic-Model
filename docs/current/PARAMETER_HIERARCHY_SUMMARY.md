# RWF Model Parameters - Complete Hierarchy

**Generated:** December 28, 2025  
**Purpose:** Clear mapping of all parameters to their role in the NPV calculation

---

## CATEGORY SUMMARY

| Category | Count | Description | NPV Impact |
|----------|-------|-------------|------------|
| **0-VETTING** | 7 | Critical parameters requiring internal validation | **Drives 80%+ of uncertainty** |
| **1A-CORE_MODEL** | 13 | Core Mincer/NPV calculation parameters | Direct NPV impact |
| **1B-BASELINE_WAGES** | 7 | PLFS baseline wage data | Direct NPV impact |
| **1C-REGIONAL** | 5 | Regional adjustment parameters | Moderate NPV impact |
| **2-FUNNEL** | 8 | Counterfactual/funnel parameters | Indirect NPV impact |
| **3-CONTEXT** | 20 | Context/validation data | Not in NPV calculation |
| **4-DATA_GAP** | 16 | Data gaps requiring future validation | Not currently used |
| **5-OTHER** | 1 | Supporting documentation | - |

---

## 0-VETTING: Critical Parameters (7)

These are THE decision parameters from `Critical_Parameters_Internal_Vetting.md`.  
**Combined impact: 438% to 72% NPV swing depending on parameter.**

| Parameter | Model Variable | Value | Source | NPV Swing |
|-----------|---------------|-------|--------|-----------|
| **P(Formal\|RTE)** | `p_formal_hs` (regional) | 30/40/50% | Assumed (no tracer data) | **438%** |
| **P(Formal\|Apprentice)** | `P_FORMAL_APPRENTICE` | 72% | **RWF actual data** | 72% |
| **Formal Multiplier** | `FORMAL_MULTIPLIER` | 2.0× | Literature (Sharma 2018) | 46% |
| **Premium Decay** | `APPRENTICE_DECAY_HALFLIFE` | 10 yr | Assumed (no India data) | 21% |
| **Apprentice Premium** | `APPRENTICE_INITIAL_PREMIUM` | ₹84k | Calculated | 14% |
| **RTE Test Score** | `RTE_TEST_SCORE_GAIN` | 0.23 SD | Muralidharan RCT (NBER) | 11% |
| **Apprentice Stipend** | `APPRENTICE_STIPEND_MONTHLY` | ₹10k/mo | MSDE/Apprentices Act | ~0% |

---

## 1A-CORE_MODEL: Mincer/NPV Parameters (13)

These parameters are used directly in wage trajectory and NPV calculations.

| Parameter | Model Variable | Value | Source | Location in Code |
|-----------|---------------|-------|--------|------------------|
| **Mincer Return (HS)** | `MINCER_RETURN_HS` | 5.8% | PLFS 2023-24 | `calculate_wage()` |
| **Experience Linear** | `EXPERIENCE_LINEAR` | 0.885% | PLFS 2023-24 | `calculate_wage()` |
| **Experience Quadratic** | `EXPERIENCE_QUAD` | -0.0123% | PLFS 2023-24 | `calculate_wage()` |
| **Real Wage Growth** | `REAL_WAGE_GROWTH` | 0.01% | PLFS 2020-24 | `generate_wage_trajectory()` |
| **Social Discount Rate** | `SOCIAL_DISCOUNT_RATE` | 3.72% | Murty et al. 2024 (EPW) | `calculate_npv()` |
| **Working Life (Formal)** | `WORKING_LIFE_FORMAL` | 40 yr | Standard | Trajectory length |
| **Working Life (Informal)** | `WORKING_LIFE_INFORMAL` | 47 yr | Standard | Trajectory length |
| **Test Score → Years** | `TEST_SCORE_TO_YEARS` | 4.7 yr/SD | World Bank LMIC | RTE education premium |
| **Vocational Premium** | `VOCATIONAL_PREMIUM` | 4.7% | DGT Tracer Study | Apprentice wages |
| **Entry Age** | `LABOR_MARKET_ENTRY_AGE` | 22 yr | Standard | Trajectory start |

*Note: Returns to Education appears multiple times in CSV for different education levels.*

---

## 1B-BASELINE_WAGES: PLFS Wage Data (7)

Source: PLFS 2023-24 Table 21. Used in `BaselineWages` class.

| Demographic | Salaried (Formal proxy) | Casual (Informal) | Ratio |
|-------------|------------------------|-------------------|-------|
| Urban Male | ₹26,105 / ₹32,800 | ₹13,425 | 1.94× |
| Urban Female | ₹19,879 / ₹24,928 | ₹9,129 | 2.18× |
| Rural Male | ₹18,200 / ₹22,880 | ₹11,100 | 1.64× |
| Rural Female | ₹12,396 / ₹15,558 | ₹7,475 | 1.66× |

*Secondary / Higher Secondary wages shown. Average embedded ratio: 1.86×*

---

## 1C-REGIONAL: Regional Adjustments (5)

Source: `RegionalParameters` class. Applied to wages and P(Formal).

| Region | Mincer Multiplier | P(Formal\|HS) | Wage Premium |
|--------|------------------|---------------|--------------|
| North | 0.914 (5.3%) | 15% | -5% |
| South | 1.069 (6.2%) | 25% | +10% |
| West | 1.000 (5.8%) | 20% | +5% |
| East | 0.879 (5.1%) | 12% | -15% |

---

## 2-FUNNEL: Counterfactual & Funnel Parameters (8)

These shape the control group and program reach calculations.

| Parameter | Value | Source | Usage |
|-----------|-------|--------|-------|
| **EWS Counterfactual Distribution** | 66.8% govt / 30.6% private / 2.6% dropout | ASER 2023-24 | Control trajectory |
| **P(Formal\|Govt School)** | 12% | PLFS estimate | Control trajectory |
| **P(Formal\|Low-fee Private)** | 15% | PLFS estimate | Control trajectory |
| **P(Formal\|Dropout)** | 5% | PLFS estimate | Control trajectory |
| **RTE Seat Fill Rate** | 29% | CAG Audit 2014 | Program reach |
| **RTE Retention Funnel** | 60% | UDISE+ proxy | Program reach |
| **Apprentice Completion Rate** | 85% | MSDE estimate | Program reach |
| **P(Formal\|Secondary)** | 11% | PLFS estimate | Control pathway |

---

## 3-CONTEXT: Validation & Background Data (20)

**NOT used in NPV calculation.** Useful for context, validation, and stakeholder communication.

| Category | Parameters | Purpose |
|----------|------------|---------|
| **Labor Market** | Unemployment rates (overall, youth), LFPR, employment shares | Macro context |
| **Learning Outcomes** | ASER private school advantage (reading, math) | RTE validation |
| **Demographics** | Life expectancy, CPI inflation | Background |
| **Gender** | FLFP elasticity, gender wage gap | Equity analysis |
| **Sector** | Formal sector growth, employment share | Trend context |

---

## 4-DATA_GAP: Parameters Needing Validation (16)

These are documented gaps that could improve model accuracy if filled.

| Parameter | Gap Type | Priority | Estimated Cost |
|-----------|----------|----------|----------------|
| **RTE Program Cost per Student** | RWF internal data needed | HIGH (for BCR) | ₹0 (internal) |
| **Apprenticeship Program Cost** | RWF internal data needed | HIGH (for BCR) | ₹0 (internal) |
| **Urban EWS Enrollment Pattern** | ASER rural-only limitation | MEDIUM | - |
| **Skill Obsolescence Rate** | No India longitudinal data | LOW | Expensive |
| **COVID Learning Loss Persistence** | Limited post-COVID data | LOW | Future research |
| **RTE Discrimination Effects** | Qualitative only | MEDIUM | ₹2-3L survey |
| **Equivalent Years Validation India** | India-specific conversion needed | MEDIUM | Academic research |

---

## FLOW: How Parameters Enter NPV Calculation

```
TIER 0-VETTING (Critical Decisions)
       ↓
   P(Formal|RTE) → RTE treatment trajectory
   P(Formal|Apprentice) → Apprentice treatment trajectory
   Formal Multiplier → benefits_adjustment factor
   RTE Test Score → Education premium (via Mincer)
   Apprentice Premium → Initial wage differential
   Premium Decay → Long-term premium persistence
       ↓
TIER 1A-CORE (Wage Equation)
       ↓
   Mincer coefficients → Wage = f(education, experience)
   Real wage growth → Trajectory over 40 years
   Discount rate → NPV = Σ differential / (1+δ)^t
       ↓
TIER 1B-WAGES (Baseline)
       ↓
   PLFS wages by demographic → Starting point for trajectories
       ↓
TIER 1C-REGIONAL (Adjustments)
       ↓
   Regional multipliers → Adjust wages and P(Formal) by region
       ↓
TIER 2-FUNNEL (Control Group)
       ↓
   Counterfactual distribution → What happens without intervention
   Program reach → Per-completer vs per-eligible adjustment
       ↓
   ══════════════════════════════════════════════════════════
                         NPV OUTPUT
   ══════════════════════════════════════════════════════════
       ↓
TIER 3-CONTEXT (Validation only - not in calculation)
TIER 4-DATA_GAP (Future improvements)
```

---

## KEY INSIGHT: Parameter Uncertainty Concentration

**80%+ of NPV uncertainty comes from just 3 parameters:**

1. **P(Formal|RTE)** - 438% swing, NO direct validation
2. **P(Formal|Apprentice)** - 72% swing, validated with RWF data ✓
3. **Formal Multiplier** - 46% swing, literature-supported ✓

**Recommendation:** Prioritize RTE tracer study (₹3-5L) to reduce the 438% uncertainty.

---

## FILES REFERENCE

| File | Content |
|------|---------|
| `Parameters_sources_REORGANIZED.csv` | Full CSV with Category column added |
| `parameter_registry_v3.py` | Python parameter definitions with sources |
| `economic_core_v4.py` | NPV calculation using parameters |
| `Critical_Parameters_Internal_Vetting.md` | 7 vetting parameters detailed |

