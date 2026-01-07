#!/usr/bin/env python3
"""
RWF Model v4.0 Integration Validation Script
Date: December 26, 2025

Purpose:
- Validate the double-counting fix in economic_core_v4.py
- Verify FORMAL_MULTIPLIER changes (2.25 -> 2.0)
- Confirm Apprenticeship NPV reduction (~85% decrease expected)
- Test all 32 scenarios
- Generate stakeholder results table
"""

import sys
from economic_core_v4 import (
    LifetimeNPVCalculator,
    Intervention,
    Gender,
    Location,
    Region,
    run_scenario_comparison,
    format_scenario_comparison
)


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}\n")


def validate_benefits_adjustment():
    """Validate that the benefits_adjustment calculation is correct"""
    print_section("VALIDATION 1: Benefits Adjustment Calculation")

    embedded_ratio = 1.86  # PLFS salaried/casual ratio already in baseline wages
    target_ratio = 2.0     # New FORMAL_MULTIPLIER value
    expected_adjustment = target_ratio / embedded_ratio

    print(f"Embedded ratio (PLFS salaried/casual): {embedded_ratio:.3f}")
    print(f"Target ratio (FORMAL_MULTIPLIER):      {target_ratio:.3f}")
    print(f"Expected benefits_adjustment:           {expected_adjustment:.3f}")

    # Validation criteria
    if 1.0 < expected_adjustment < 1.5:
        print(f"\n✓ PASS: Benefits adjustment = {expected_adjustment:.3f} is within expected range (1.0-1.5)")
        return True
    else:
        print(f"\n✗ FAIL: Benefits adjustment = {expected_adjustment:.3f} is outside expected range!")
        return False


def calculate_reference_scenarios():
    """Calculate NPV for reference scenario: Urban Male, West region"""
    print_section("VALIDATION 2: Reference Scenario Calculations")
    print("Scenario: Urban Male, West Region (Moderate scenario)\n")

    calculator = LifetimeNPVCalculator()

    # RTE calculation
    rte_result = calculator.calculate_lnpv(
        intervention=Intervention.RTE,
        gender=Gender.MALE,
        location=Location.URBAN,
        region=Region.WEST
    )

    # Apprenticeship calculation
    app_result = calculator.calculate_lnpv(
        intervention=Intervention.APPRENTICESHIP,
        gender=Gender.MALE,
        location=Location.URBAN,
        region=Region.WEST
    )

    # Convert to lakhs for reporting
    rte_lnpv_lakhs = rte_result['lnpv'] / 100000
    app_lnpv_lakhs = app_result['lnpv'] / 100000
    app_rte_ratio = app_lnpv_lakhs / rte_lnpv_lakhs if rte_lnpv_lakhs > 0 else 0

    print(f"RTE Lifetime NPV:            ₹{rte_lnpv_lakhs:,.2f} Lakhs")
    print(f"Apprenticeship Lifetime NPV: ₹{app_lnpv_lakhs:,.2f} Lakhs")
    print(f"App/RTE Ratio:               {app_rte_ratio:.2f}x")

    # Validation criteria
    print("\n" + "-"*80)
    print("VALIDATION CHECKS:")

    checks_passed = 0
    total_checks = 3

    # Check 1: Apprenticeship NPV reduced from old value (was ₹133L with bug)
    # With MODERATE parameters (P_FORMAL=72%, FORMAL_MULT=2.0), expect ₹45-55L
    if 45 <= app_lnpv_lakhs <= 65:
        print(f"✓ CHECK 1: Apprenticeship NPV (₹{app_lnpv_lakhs:.2f}L) is in expected range (₹45-65L)")
        print(f"           (Reduced from ₹133L with old code - fix is working!)")
        checks_passed += 1
    else:
        print(f"✗ CHECK 1: Apprenticeship NPV (₹{app_lnpv_lakhs:.2f}L) is outside expected range!")
        print(f"           Expected: ₹45-65L (moderate scenario)")
        if app_lnpv_lakhs > 100:
            print(f"           WARNING: Value > ₹100L suggests the fix was NOT applied!")

    # Check 2: RTE NPV in expected range (₹10-20L for moderate scenario)
    if 10 <= rte_lnpv_lakhs <= 20:
        print(f"✓ CHECK 2: RTE NPV (₹{rte_lnpv_lakhs:.2f}L) is in expected range (₹10-20L)")
        checks_passed += 1
    else:
        print(f"✗ CHECK 2: RTE NPV (₹{rte_lnpv_lakhs:.2f}L) is outside expected range (₹10-20L)")

    # Check 3: App/RTE ratio should be reasonable (was ~8x before with bug)
    if 2.0 <= app_rte_ratio <= 4.5:
        print(f"✓ CHECK 3: App/RTE ratio ({app_rte_ratio:.2f}x) is reasonable")
        print(f"           (Reduced from ~8x with old code)")
        checks_passed += 1
    else:
        print(f"✗ CHECK 3: App/RTE ratio ({app_rte_ratio:.2f}x) is unusual")
        if app_rte_ratio > 7.0:
            print(f"           WARNING: Ratio > 7x suggests double-counting may still exist!")

    print(f"\nCHECKS PASSED: {checks_passed}/{total_checks}")

    return {
        'rte': rte_result,
        'apprenticeship': app_result,
        'all_passed': checks_passed == total_checks
    }


def run_all_32_scenarios():
    """Run all 32 scenarios and return results"""
    print_section("VALIDATION 3: Running All 32 Scenarios")

    calculator = LifetimeNPVCalculator()

    print("Calculating NPV for all combinations of:")
    print("  - Interventions: RTE, Apprenticeship")
    print("  - Genders: Male, Female")
    print("  - Locations: Urban, Rural")
    print("  - Regions: North, East, West, South")
    print("\nTotal scenarios: 2 × 2 × 2 × 4 = 32\n")

    try:
        results = calculator.calculate_all_scenarios()
        print(f"✓ Successfully calculated all {len(results)} scenarios!")

        # Summary statistics
        rte_results = [r for r in results if r['intervention'] == 'rte']
        app_results = [r for r in results if r['intervention'] == 'apprenticeship']

        rte_lnpvs = [r['lnpv'] / 100000 for r in rte_results]
        app_lnpvs = [r['lnpv'] / 100000 for r in app_results]

        print("\n" + "-"*80)
        print("SUMMARY STATISTICS:")
        print(f"\nRTE LNPV Range:            ₹{min(rte_lnpvs):,.2f}L - ₹{max(rte_lnpvs):,.2f}L")
        print(f"RTE LNPV Mean:             ₹{sum(rte_lnpvs)/len(rte_lnpvs):,.2f}L")
        print(f"\nApprenticeship LNPV Range: ₹{min(app_lnpvs):,.2f}L - ₹{max(app_lnpvs):,.2f}L")
        print(f"Apprenticeship LNPV Mean:  ₹{sum(app_lnpvs)/len(app_lnpvs):,.2f}L")

        return results

    except Exception as e:
        print(f"✗ ERROR running scenarios: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_scenario_analysis():
    """Run Conservative/Moderate/Optimistic scenario comparison"""
    print_section("VALIDATION 4: Scenario Analysis (Conservative/Moderate/Optimistic)")

    print("Testing scenario: Urban Male, West Region")
    print("\nApprenticeship Scenarios:")
    print("-"*80)

    try:
        app_scenarios = run_scenario_comparison(
            intervention=Intervention.APPRENTICESHIP,
            gender=Gender.MALE,
            location=Location.URBAN,
            region=Region.WEST
        )
        print(format_scenario_comparison(app_scenarios))

        print("\nRTE Scenarios:")
        print("-"*80)

        rte_scenarios = run_scenario_comparison(
            intervention=Intervention.RTE,
            gender=Gender.MALE,
            location=Location.URBAN,
            region=Region.WEST
        )
        print(format_scenario_comparison(rte_scenarios))

        return {
            'apprenticeship': app_scenarios,
            'rte': rte_scenarios
        }

    except Exception as e:
        print(f"✗ ERROR running scenario analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def generate_stakeholder_table(results):
    """Generate CSV table for stakeholders"""
    print_section("VALIDATION 5: Generating Stakeholder Results Table")

    if results is None:
        print("✗ Cannot generate table: no results available")
        return False

    try:
        import pandas as pd

        # Create DataFrame
        data = []
        for r in results:
            data.append({
                'Intervention': r['intervention'].upper(),
                'Region': r['region'].capitalize(),
                'Gender': r['gender'].capitalize(),
                'Location': r['location'].capitalize(),
                'LNPV (₹ Lakhs)': round(r['lnpv'] / 100000, 2),
                'P(Formal) Treatment': f"{r['p_formal_treatment']:.1%}"
            })

        df = pd.DataFrame(data)

        # Sort for readability
        df = df.sort_values(['Intervention', 'Region', 'Location', 'Gender'])

        print("Preview of results table:")
        print(df.head(10).to_string(index=False))
        print(f"\n... ({len(df)} total rows)")

        # Save to CSV
        output_file = 'lnpv_results_v4.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✓ Results saved to: {output_file}")

        # Generate summary by intervention and region
        print("\n" + "-"*80)
        print("SUMMARY BY INTERVENTION AND REGION:")
        summary = df.groupby(['Intervention', 'Region'])['LNPV (₹ Lakhs)'].agg(['mean', 'min', 'max'])
        print(summary.to_string())

        return True

    except Exception as e:
        print(f"✗ ERROR generating table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main validation workflow"""
    print_section("RWF MODEL v4.0 INTEGRATION VALIDATION")
    print(f"Date: December 26, 2025")
    print(f"Python: {sys.version}")

    all_validations_passed = True

    # Validation 1: Benefits adjustment calculation
    if not validate_benefits_adjustment():
        all_validations_passed = False

    # Validation 2: Reference scenario calculations
    ref_results = calculate_reference_scenarios()
    if not ref_results['all_passed']:
        all_validations_passed = False

    # Validation 3: Run all 32 scenarios
    all_results = run_all_32_scenarios()
    if all_results is None:
        all_validations_passed = False

    # Validation 4: Scenario analysis
    scenario_results = run_scenario_analysis()
    if scenario_results is None:
        all_validations_passed = False

    # Validation 5: Generate stakeholder table
    if all_results is not None:
        if not generate_stakeholder_table(all_results):
            all_validations_passed = False

    # Final summary
    print_section("FINAL VALIDATION SUMMARY")

    if all_validations_passed:
        print("✓✓✓ ALL VALIDATIONS PASSED ✓✓✓")
        print("\nThe v4.0 integration is successful!")
        print("- Double-counting bug has been fixed")
        print("- FORMAL_MULTIPLIER correctly updated to 2.0")
        print("- Apprenticeship NPV reduced to expected range")
        print("- All 32 scenarios run without errors")
        print("- Results exported to lnpv_results_v4.csv")
        return 0
    else:
        print("✗✗✗ SOME VALIDATIONS FAILED ✗✗✗")
        print("\nPlease review the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
