"""
Diagnostic Analysis for RWF Model - Anand's Questions
======================================================

QUESTION 1: How does RTE test score gain affect earnings?
QUESTION 2: Apprentice premium - ₹84k vs ₹240k discrepancy
QUESTION 3: The 2.25× formal multiplier itself
"""

from economic_core_v3_updated import (
    LifetimeNPVCalculator,
    Intervention,
    Gender,
    Location,
    Region,
    MincerWageModel,
    BaselineWages,
    Sector
)

print("="*80)
print("DIAGNOSTIC ANALYSIS - ANAND'S QUESTIONS")
print("="*80)

# Initialize calculator
calc = LifetimeNPVCalculator()

# ============================================================================
# QUESTION 1: RTE Test Score to Earnings Mechanism
# ============================================================================
print("\n" + "="*80)
print("Q1: RTE TEST SCORE GAIN → EARNINGS MECHANISM")
print("="*80)

print("\nStep 1: Test Score Gain")
test_score_gain = calc.params.RTE_TEST_SCORE_GAIN.value
print(f"  RTE test score gain: {test_score_gain} SD")

print("\nStep 2: Convert to Equivalent Years of Schooling")
years_per_sd = calc.params.TEST_SCORE_TO_YEARS.value
equivalent_years = test_score_gain * years_per_sd
print(f"  Conversion factor: {years_per_sd} years/SD")
print(f"  Equivalent years: {test_score_gain} × {years_per_sd} = {equivalent_years:.2f} years")

print("\nStep 3: Apply to Education Level")
base_education = 12  # Higher secondary
effective_education = base_education + equivalent_years
print(f"  Base education: {base_education} years (higher secondary)")
print(f"  Effective education: {effective_education:.2f} years")

print("\nStep 4: Calculate Wage Impact via Mincer Equation")
mincer_return = calc.params.MINCER_RETURN_HS.value
wage_premium = (1 + mincer_return) ** equivalent_years - 1
print(f"  Mincer return: {mincer_return:.1%} per year")
print(f"  Wage premium: (1.058)^{equivalent_years:.2f} - 1 = {wage_premium:.1%}")

print("\nStep 5: Example - Urban Male, West Region")
base_wage = calc.wage_model.baseline_wages.urban_male_higher_secondary
print(f"  Base wage (12 years): ₹{base_wage:,.0f}/month")
treatment_wage = base_wage * (1 + wage_premium)
print(f"  Treatment wage (effective {effective_education:.2f} years): ₹{treatment_wage:,.0f}/month")
print(f"  Monthly gain: ₹{treatment_wage - base_wage:,.0f}")
print(f"  Annual gain (before formal multiplier): ₹{(treatment_wage - base_wage)*12:,.0f}")

print("\nStep 6: Formal Sector Effect")
formal_mult = calc.params.FORMAL_MULTIPLIER.value
p_formal_rte = calc.wage_model.regional.get_p_formal(Region.WEST)
print(f"  P(Formal | RTE): {p_formal_rte:.1%}")
print(f"  Formal multiplier: {formal_mult}×")
print(f"  Expected wage (treatment): ₹{treatment_wage * p_formal_rte * formal_mult + treatment_wage * (1-p_formal_rte):,.0f}/month")
print(f"  Expected wage (control): ₹{base_wage * p_formal_rte * formal_mult + base_wage * (1-p_formal_rte):,.0f}/month")

# ============================================================================
# QUESTION 2: Apprentice Premium Calculation
# ============================================================================
print("\n" + "="*80)
print("Q2: APPRENTICE PREMIUM - ₹84k vs ₹240k DISCREPANCY")
print("="*80)

print("\nScenario: Rural Male, West Region")

# Get apprentice trajectories
treatment_wages, p_formal_app = calc.calculate_treatment_trajectory(
    Intervention.APPRENTICESHIP,
    Gender.MALE,
    Location.RURAL,
    Region.WEST
)

control_wages = calc.calculate_control_trajectory(
    Gender.MALE,
    Location.RURAL,
    Region.WEST
)

# Year 0 analysis (training year)
print("\nYear 0 (Training Year):")
print(f"  Treatment receives: ₹{treatment_wages[0]:,.0f}/year (stipend)")
print(f"  Control earns: ₹{control_wages[0]:,.0f}/year (informal work)")
print(f"  Opportunity cost: ₹{treatment_wages[0] - control_wages[0]:,.0f}/year")

# Year 1 analysis (first working year)
print("\nYear 1 (First Working Year Post-Training):")
print(f"  Treatment wage: ₹{treatment_wages[1]:,.0f}/year")
print(f"  Control wage: ₹{control_wages[1]:,.0f}/year")
print(f"  Year 1 premium: ₹{treatment_wages[1] - control_wages[1]:,.0f}/year")

# Detailed breakdown
print("\nDetailed Premium Calculation:")
wage_model = calc.wage_model
baseline = calc.wage_model.baseline_wages

# Rural male baseline wages
rural_male_secondary_monthly = baseline.rural_male_secondary
rural_male_informal_monthly = baseline.rural_male_casual

print(f"\n  Baseline Wages (Rural Male):")
print(f"    Secondary (formal): ₹{rural_male_secondary_monthly:,.0f}/month")
print(f"    Casual (informal): ₹{rural_male_informal_monthly:,.0f}/month")

# Treatment pathway
formal_mult = calc.params.FORMAL_MULTIPLIER.value
voc_premium = calc.params.VOCATIONAL_PREMIUM.value
p_formal_apprentice = calc.params.P_FORMAL_APPRENTICE.value

formal_wage_with_voc = rural_male_secondary_monthly * formal_mult * (1 + voc_premium)
informal_wage = rural_male_informal_monthly

treatment_expected_monthly = p_formal_apprentice * formal_wage_with_voc + (1 - p_formal_apprentice) * informal_wage
print(f"\n  Treatment Pathway:")
print(f"    P(Formal | Apprentice): {p_formal_apprentice:.1%}")
print(f"    Formal wage (with {voc_premium:.1%} vocational premium): ₹{formal_wage_with_voc:,.0f}/month")
print(f"    Informal fallback: ₹{informal_wage:,.0f}/month")
print(f"    Expected wage: {p_formal_apprentice:.1%} × ₹{formal_wage_with_voc:,.0f} + {(1-p_formal_apprentice):.1%} × ₹{informal_wage:,.0f}")
print(f"                 = ₹{treatment_expected_monthly:,.0f}/month")
print(f"                 = ₹{treatment_expected_monthly * 12:,.0f}/year")

# Control pathway
p_formal_control = 0.10  # From counterfactual
control_formal_monthly = rural_male_secondary_monthly * formal_mult
control_informal_monthly = rural_male_informal_monthly
control_expected_monthly = p_formal_control * control_formal_monthly + (1 - p_formal_control) * control_informal_monthly

print(f"\n  Control Pathway (No Apprenticeship):")
print(f"    P(Formal | No training): {p_formal_control:.1%}")
print(f"    Formal wage: ₹{control_formal_monthly:,.0f}/month")
print(f"    Informal: ₹{control_informal_monthly:,.0f}/month")
print(f"    Expected wage: {p_formal_control:.1%} × ₹{control_formal_monthly:,.0f} + {(1-p_formal_control):.1%} × ₹{control_informal_monthly:,.0f}")
print(f"                 = ₹{control_expected_monthly:,.0f}/month")
print(f"                 = ₹{control_expected_monthly * 12:,.0f}/year")

# Premium
annual_premium = (treatment_expected_monthly - control_expected_monthly) * 12
print(f"\n  Annual Premium:")
print(f"    (₹{treatment_expected_monthly:,.0f} - ₹{control_expected_monthly:,.0f}) × 12 = ₹{annual_premium:,.0f}/year")

print(f"\n  Registry Value: ₹{calc.params.APPRENTICE_INITIAL_PREMIUM.value:,.0f}/year")
print(f"\n  DISCREPANCY: ₹{annual_premium:,.0f} (calculated) vs ₹{calc.params.APPRENTICE_INITIAL_PREMIUM.value:,.0f} (registry)")
print(f"  Ratio: {annual_premium / calc.params.APPRENTICE_INITIAL_PREMIUM.value:.2f}×")

# ============================================================================
# QUESTION 3: The 2.25× Formal Multiplier
# ============================================================================
print("\n" + "="*80)
print("Q3: THE 2.25× FORMAL MULTIPLIER - JUSTIFICATION")
print("="*80)

print("\nChecking formal multiplier in action:")
print(f"  Formal multiplier parameter: {formal_mult}×")

# Test across different demographics
print("\nFormal vs Informal Wage Ratios (for 10 years schooling):")
demographics = [
    (Gender.MALE, Location.URBAN, "Urban Male"),
    (Gender.MALE, Location.RURAL, "Rural Male"),
    (Gender.FEMALE, Location.URBAN, "Urban Female"),
    (Gender.FEMALE, Location.RURAL, "Rural Female"),
]

for gender, location, label in demographics:
    informal_wage = wage_model.calculate_wage(
        years_schooling=10,
        experience=0,
        sector=Sector.INFORMAL,
        gender=gender,
        location=location,
        region=Region.WEST
    )

    formal_wage = wage_model.calculate_wage(
        years_schooling=10,
        experience=0,
        sector=Sector.FORMAL,
        gender=gender,
        location=location,
        region=Region.WEST
    )

    ratio = formal_wage / informal_wage
    print(f"  {label}:")
    print(f"    Informal: ₹{informal_wage:,.0f}/month")
    print(f"    Formal: ₹{formal_wage:,.0f}/month")
    print(f"    Ratio: {ratio:.2f}×")
    print(f"    Expected ratio: {formal_mult:.2f}×")
    print()

# ============================================================================
# RECALCULATE WITH FORMAL MULTIPLIER = 1.0
# ============================================================================
print("="*80)
print("SENSITIVITY: RECALCULATE APPRENTICE NPV WITH MULTIPLIER = 1.0")
print("="*80)

# Create a new calculator with modified formal multiplier
calc_no_multiplier = LifetimeNPVCalculator()
calc_no_multiplier.wage_model.params.FORMAL_MULTIPLIER.value = 1.0

result_baseline = calc.calculate_lnpv(
    Intervention.APPRENTICESHIP,
    Gender.MALE,
    Location.RURAL,
    Region.WEST
)

result_no_mult = calc_no_multiplier.calculate_lnpv(
    Intervention.APPRENTICESHIP,
    Gender.MALE,
    Location.RURAL,
    Region.WEST
)

print(f"\nNPV with 2.25× multiplier: ₹{result_baseline['lnpv']:,.0f}")
print(f"NPV with 1.0× multiplier: ₹{result_no_mult['lnpv']:,.0f}")
print(f"Difference: ₹{result_baseline['lnpv'] - result_no_mult['lnpv']:,.0f}")
print(f"Impact: {(result_baseline['lnpv'] - result_no_mult['lnpv']) / result_baseline['lnpv']:.1%} reduction")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
