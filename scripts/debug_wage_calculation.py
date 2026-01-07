#!/usr/bin/env python3
"""
Debug wage calculation to find why Apprenticeship NPV is still high
"""

from economic_core_v4 import (
    LifetimeNPVCalculator,
    Intervention,
    Gender,
    Location,
    Region,
    Sector,
    EducationLevel
)

# Create calculator
calc = LifetimeNPVCalculator()

# Test parameters
gender = Gender.MALE
location = Location.URBAN
region = Region.WEST
years_schooling = 12
experience = 5

print("="*80)
print("WAGE CALCULATION DEBUG")
print("="*80)
print(f"\nParameters:")
print(f"  Gender: {gender}")
print(f"  Location: {location}")
print(f"  Region: {region}")
print(f"  Education: {years_schooling} years (Higher Secondary)")
print(f"  Experience: {experience} years")

# Get baseline wages
education_level = EducationLevel.HIGHER_SECONDARY
formal_base = calc.wage_model.baseline_wages.get_wage(location, gender, education_level, Sector.FORMAL)
informal_base = calc.wage_model.baseline_wages.get_wage(location, gender, education_level, Sector.INFORMAL)

print(f"\n{'-'*80}")
print(f"BASELINE WAGES FROM PLFS (before any adjustments):")
print(f"  Formal (salaried):  ₹{formal_base:,.0f}")
print(f"  Informal (casual):  ₹{informal_base:,.0f}")
print(f"  Embedded ratio:     {formal_base/informal_base:.2f}x")

# Calculate formal sector wage
formal_wage = calc.wage_model.calculate_wage(
    years_schooling=years_schooling,
    experience=experience,
    sector=Sector.FORMAL,
    gender=gender,
    location=location,
    region=region,
    additional_premium=0.0
)

informal_wage = calc.wage_model.calculate_wage(
    years_schooling=years_schooling,
    experience=experience,
    sector=Sector.INFORMAL,
    gender=gender,
    location=location,
    region=region,
    additional_premium=0.0
)

print(f"\n{'-'*80}")
print(f"CALCULATED WAGES (after experience premium and benefits_adjustment):")
print(f"  Formal:   ₹{formal_wage:,.0f}")
print(f"  Informal: ₹{informal_wage:,.0f}")
print(f"  Ratio:    {formal_wage/informal_wage:.2f}x")

# Check what benefits_adjustment was applied
target_ratio = calc.wage_model.params.FORMAL_MULTIPLIER.value
embedded_ratio = 1.86
benefits_adjustment = target_ratio / embedded_ratio

print(f"\n{'-'*80}")
print(f"BENEFITS ADJUSTMENT:")
print(f"  FORMAL_MULTIPLIER (target): {target_ratio:.2f}")
print(f"  Embedded ratio (PLFS):      {embedded_ratio:.2f}")
print(f"  Benefits adjustment:        {benefits_adjustment:.3f}")

# Check experience premium
import numpy as np
exp_coef1 = calc.wage_model.params.EXPERIENCE_LINEAR.value
exp_coef2 = calc.wage_model.params.EXPERIENCE_QUAD.value
experience_premium = np.exp(exp_coef1 * experience + exp_coef2 * experience**2)

print(f"\n{'-'*80}")
print(f"EXPERIENCE PREMIUM:")
print(f"  Linear coef:  {exp_coef1:.6f}")
print(f"  Quad coef:    {exp_coef2:.6f}")
print(f"  Experience:   {experience} years")
print(f"  Premium:      {experience_premium:.3f}x")

# Now test apprenticeship calculation
print(f"\n{'='*80}")
print(f"APPRENTICESHIP NPV CALCULATION")
print(f"{'='*80}")

app_result = calc.calculate_lnpv(
    intervention=Intervention.APPRENTICESHIP,
    gender=gender,
    location=location,
    region=region
)

print(f"\nResults:")
print(f"  LNPV: ₹{app_result['lnpv']/100000:.2f} Lakhs")
print(f"  Lifetime earnings (treatment): ₹{app_result['lifetime_earnings_treatment']/10000000:.2f} Crores")
print(f"  Lifetime earnings (control): ₹{app_result['lifetime_earnings_control']/10000000:.2f} Crores")
print(f"  P(Formal|Treatment): {app_result['p_formal_treatment']:.1%}")
print(f"  Years worked: {app_result['years_worked']}")

# Calculate what the wage SHOULD be if benefits_adjustment is working
expected_formal_wage = formal_base * experience_premium * benefits_adjustment
print(f"\n{'-'*80}")
print(f"EXPECTED vs ACTUAL:")
print(f"  Expected formal wage: ₹{expected_formal_wage:,.0f}")
print(f"  Actual formal wage:   ₹{formal_wage:,.0f}")
print(f"  Match: {abs(expected_formal_wage - formal_wage) < 1}")

# Let's also check what the wage would be with the OLD approach (double-counting)
old_multiplier = 2.25
old_wage = formal_base * experience_premium * old_multiplier
print(f"\n{'-'*80}")
print(f"COMPARISON WITH OLD APPROACH:")
print(f"  Old approach (2.25x multiplier): ₹{old_wage:,.0f}")
print(f"  New approach (benefits_adj):     ₹{formal_wage:,.0f}")
print(f"  Reduction:                       {(1 - formal_wage/old_wage)*100:.1f}%")

print(f"\n{'='*80}")
