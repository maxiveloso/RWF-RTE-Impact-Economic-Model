# Parameter Sources Review

**Date:** December 24, 2025
**File:** Parameters sources.gsheet
**Google Sheets ID:** 1TFLpSCpj-iOPSfUM56-TfPHtpJQzjSA8uSbamVnLzM8

---

## Access Note

The file `Parameters sources.gsheet` is a Google Sheets document. To review columns I-N for claims verification, you need to:

1. Open the Google Sheet at: https://docs.google.com/spreadsheets/d/1TFLpSCpj-iOPSfUM56-TfPHtpJQzjSA8uSbamVnLzM8
2. Navigate to columns I-N
3. Verify that all parameter claims match the sources cited

---

## Key Parameters to Verify (Based on Code Review)

### Critical Parameters (Tier 1 - Highest Uncertainty)

1. **P_FORMAL_HIGHER_SECONDARY (P(Formal | HS))**
   - **Model value:** 20%
   - **Source claimed:** "PLFS 2023-24 formal employment share by education level"
   - **What to verify in gsheet:**
     - Actual PLFS table reference (e.g., Table 21, Table X)
     - Age range used (22-30? 25-35?)
     - Whether this is national average or region-specific
     - Cross-sectional vs panel data

2. **P_FORMAL_APPRENTICE (P(Formal | Apprenticeship))**
   - **Model value:** 72%
   - **Source claimed:** "RWF placement data (validated Nov 2025)"
   - **What to verify:**
     - Internal RWF tracking data source
     - Sample size (N=?)
     - Cohort years included (2023-2025?)
     - Definition of "formal" placement (EPF registration? Contract employment?)

3. **RTE_TEST_SCORE_GAIN**
   - **Model value:** 0.23 SD
   - **Source claimed:** "Muralidharan & Sundararaman (2015) NBER RCT, Andhra Pradesh"
   - **What to verify:**
     - Full citation: NBER Working Paper No. 21440
     - Table/page number for 0.23 SD finding
     - Subject breakdown (0.55 SD Hindi, 0.12 SD English, 0 math)
     - Whether this is intent-to-treat (ITT) or treatment-on-treated (TOT) effect

4. **TEST_SCORE_TO_YEARS (Equivalent years conversion)**
   - **Model value:** 4.7 years/SD
   - **Source claimed:** "World Bank LMIC pooled estimates (Angrist et al. 2021)"
   - **What to verify:**
     - Full citation needed
     - India-specific estimate vs global average
     - Applicable education level (primary? secondary?)

5. **APPRENTICE_INITIAL_PREMIUM**
   - **Model value:** ₹84,000/year
   - **Source claimed:** "Calculated from placement data; conservative estimate"
   - **What to verify in gsheet:**
     - Calculation methodology documented?
     - Why ₹84k instead of back-of-envelope ₹235k?
     - Assumptions about baseline wages, formal multiplier

---

### Core Wage Parameters (Tier 2-3)

6. **MINCER_RETURN_HS**
   - **Model value:** 5.8% per year
   - **Source claimed:** "PLFS 2023-24 wage differentials"
   - **What to verify:**
     - Calculation: (₹32,800 - ₹26,105) / ₹26,105 / 2 years = 5.8%
     - PLFS table reference
     - Whether this accounts for selection bias (higher-ability students complete 12th)

7. **FORMAL_MULTIPLIER**
   - **Model value:** 2.25×
   - **Source claimed:** "Sharma & Sasikumar (2018), confirmed range 2.0-2.5×"
   - **What to verify in gsheet:**
     - Full citation: Sharma, Alakh N., and S. K. Sasikumar. "Formal and Informal Wage Differentials in Urban India." *Economic and Political Weekly* 53.43 (2018).
     - Whether this is for same education level, same occupation
     - **CRITICAL:** Whether Sharma & Sasikumar compare:
       - (a) Formal salaried wage to informal salaried wage (₹26k to ₹11.5k = 2.26×) ✓
       - (b) Formal salaried wage to casual wage (₹26k to ₹13.4k = 1.94×) ✗
     - This determines if double counting is occurring

8. **REAL_WAGE_GROWTH**
   - **Model value:** 0.01% (near zero)
   - **Source claimed:** "PLFS 2020-24 wage data adjusted for CPI inflation (4-6% annually)"
   - **What to verify:**
     - PLFS tables for 2020, 2021, 2022, 2023, 2024 wage data
     - CPI deflator source (MOSPI Consumer Price Index)
     - Whether growth is calculated for same education cohort (cohort effect vs age effect)

9. **BASELINE_WAGES (All 12 values)**
   - **Source claimed:** "PLFS 2023-24 Table 21 - Average monthly earnings"
   - **What to verify in gsheet columns I-N:**
     - Table 21 exact values match model values
     - Whether "casual" wage is used for informal baseline
     - Whether "regular salaried" wage is used for formal baseline
     - Age range, full-time vs part-time employment definitions

---

### Intervention-Specific Parameters

10. **RTE_INITIAL_PREMIUM**
    - **Model value:** ₹98,000/year
    - **Source claimed:** "Calculated from wage differentials"
    - **What to verify:**
      - Calculation spreadsheet/notes in gsheet
      - Counterfactual distribution assumptions (66.8% govt, 30.6% private, 2.6% dropout)
      - P(Formal) assumptions for each pathway

11. **VOCATIONAL_PREMIUM**
    - **Model value:** 4.7%
    - **Source claimed:** "DGT National Tracer Study 2019-20 (ITI graduates proxy)"
    - **What to verify:**
      - DGT report availability/link
      - ITI vs NATS apprenticeship comparability
      - Cross-sectional vs causal estimate

12. **SOCIAL_DISCOUNT_RATE**
    - **Model value:** 3.72%
    - **Source claimed:** "Murty et al. (2024), Economic and Political Weekly - Ramsey formula for India"
    - **What to verify in gsheet:**
      - Full citation: Murty, M. N., et al. "Estimating Social Discount Rate for India." *Economic and Political Weekly* 59.12 (2024).
      - Whether this is for social welfare programs vs infrastructure
      - Sensitivity range justification (3-8%)

---

## Checklist for Gsheet Review (Columns I-N)

When reviewing the Google Sheet, verify:

### Column I: Source Document
- [ ] Full citation with authors, year, title, journal/publisher
- [ ] DOI or URL for online sources
- [ ] Page numbers or table numbers referenced

### Column J: Data Extraction Method
- [ ] Direct quote from source
- [ ] Calculated from source data (with formula shown)
- [ ] Proxy/assumption justified

### Column K: Data Quality Assessment
- [ ] Sample size (N=?)
- [ ] Representative sample? (National vs regional)
- [ ] Cross-sectional vs panel vs RCT

### Column L: Uncertainty Assessment
- [ ] Tier 1/2/3 classification justified
- [ ] Sensitivity range source (e.g., 95% CI from study)
- [ ] Alternative estimates from other sources

### Column M: Last Verification Date
- [ ] When was source last checked?
- [ ] Whether data has been superseded by newer releases

### Column N: Notes / Caveats
- [ ] External validity concerns documented
- [ ] Selection bias warnings
- [ ] Data limitations acknowledged

---

## Red Flags to Look For

1. **"Assumed" or "No India-specific data"**
   - Indicates Tier 1 weakness
   - Examples: APPRENTICE_DECAY_HALFLIFE (line 308-316)

2. **"Estimated from published aggregates"**
   - May lack microdata validation
   - Examples: P_FORMAL_HIGHER_SECONDARY

3. **"Calculated" without showing calculation**
   - Risk of arithmetic errors or assumption errors
   - Examples: APPRENTICE_INITIAL_PREMIUM (₹84k discrepancy)

4. **Sources older than 5 years**
   - May not reflect current labor market
   - Examples: Sharma & Sasikumar (2018) for 2025 model

5. **Conflicting sources not reconciled**
   - Different studies give different values
   - Example: MINCER_RETURN (8.6% in 2012 vs 5.8% in 2024 - addressed, but check reasoning)

---

## Action Items

1. **Open Google Sheet and verify all claims in columns I-N**
2. **Flag any missing sources or "assumed" values**
3. **For FORMAL_MULTIPLIER specifically:**
   - Check if Sharma & Sasikumar (2018) compares formal-salaried to informal-salaried or to casual
   - This determines if double counting is occurring in the model
4. **For APPRENTICE_INITIAL_PREMIUM:**
   - Request calculation spreadsheet showing ₹84k derivation
   - Reconcile with ₹235k back-of-envelope calculation
5. **For P_FORMAL values:**
   - Request PLFS microdata analysis or regression tables
   - Verify that these are conditional probabilities, not marginal rates

---

## Summary

The Google Sheets file "Parameters sources.gsheet" should contain detailed source documentation in columns I-N. Without access to the actual spreadsheet content, I cannot verify whether all claims are properly sourced.

**Next step:** Open the Google Sheet and cross-check each parameter against the source documentation to identify any unsupported claims or data gaps.
