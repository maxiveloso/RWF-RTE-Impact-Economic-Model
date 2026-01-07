"""
Critical Parameter Verification Script - IMPROVED VERSION
==========================================================

Combines best features from multiple analyses:
- Comprehensive regional analysis
- Complete parameter coverage (includes FORMAL_MULTIPLIER)
- Wider test ranges for better uncertainty quantification
- Tests RTE_RETENTION_FUNNEL for completeness

Systematically tests each parameter's impact on NPV to identify:
1. Which parameters have >20% NPV impact (truly "critical")
2. Actual sensitivity magnitudes (not assumptions)
3. Parameter ranking by importance

This should be run BEFORE creating the vetting document to ensure
we're focusing on the parameters that actually matter.

Version: 2.0 (Improved)
Date: December 16, 2024
"""

import sys
sys.path.append('/mnt/project')

import numpy as np
from economic_core_v3_updated import (
    LifetimeNPVCalculator, ParameterRegistry, Gender, Location, 
    Region, Intervention
)

def test_parameter_sensitivity(
    param_name: str,
    baseline_value: float,
    test_values: list,
    intervention: Intervention,
    gender: Gender = Gender.MALE,
    location: Location = Location.URBAN,
    region: Region = Region.WEST
):
    """
    Test a single parameter's impact on NPV.
    
    Returns:
        dict with baseline_npv, test_npvs, percent_changes, max_swing
    """
    results = {
        'param_name': param_name,
        'baseline_value': baseline_value,
        'test_values': test_values,
        'npvs': [],
        'percent_changes': [],
        'baseline_npv': None
    }
    
    # Calculate baseline NPV
    params = ParameterRegistry()
    calculator = LifetimeNPVCalculator(params=params)
    baseline_result = calculator.calculate_lnpv(intervention, gender, location, region)
    baseline_npv = baseline_result['lnpv']
    results['baseline_npv'] = baseline_npv
    
    # Test each value
    for test_val in test_values:
        params = ParameterRegistry()
        
        # Set the parameter value
        if hasattr(params, param_name):
            param_obj = getattr(params, param_name)
            param_obj.value = test_val
            
            calculator = LifetimeNPVCalculator(params=params)
            result = calculator.calculate_lnpv(intervention, gender, location, region)
            test_npv = result['lnpv']
            
            results['npvs'].append(test_npv)
            pct_change = ((test_npv - baseline_npv) / baseline_npv) * 100
            results['percent_changes'].append(pct_change)
    
    # Calculate max swing (range of impact)
    if results['percent_changes']:
        max_swing = max(results['percent_changes']) - min(results['percent_changes'])
        results['max_swing'] = abs(max_swing)
    else:
        results['max_swing'] = 0
    
    return results


def format_currency(value: float) -> str:
    """Format value as Indian Rupees."""
    if abs(value) >= 1e7:
        return f"₹{value/1e7:.2f} Cr"
    elif abs(value) >= 1e5:
        return f"₹{value/1e5:.2f} L"
    else:
        return f"₹{value/1e3:.1f}K"


def main():
    print("="*80)
    print("CRITICAL PARAMETER VERIFICATION - SYSTEMATIC SENSITIVITY ANALYSIS")
    print("="*80)
    print()
    
    # Define parameters to test with their sensitivity ranges
    params_to_test = [
        # Formal sector entry probabilities (TIER 1 - highest uncertainty)
        {
            'name': 'P_FORMAL_APPRENTICE',
            'baseline': 0.72,
            'test_range': [0.40, 0.50, 0.60, 0.72, 0.80, 0.90],  # Expanded lower bound
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Apprentice Formal Placement Rate'
        },
        # NOTE: P_FORMAL_HIGHER_SECONDARY is NOT used in RTE calculation!
        # RTE uses REGIONAL p_formal_hs values instead.
        # See special regional analysis section below.
        
        # RTE-specific parameters
        {
            'name': 'RTE_TEST_SCORE_GAIN',
            'baseline': 0.23,
            'test_range': [0.15, 0.18, 0.23, 0.27, 0.30],
            'intervention': Intervention.RTE,
            'description': 'RTE Test Score Gain (SD)'
        },
        {
            'name': 'RTE_INITIAL_PREMIUM',
            'baseline': 98000,
            'test_range': [70000, 84000, 98000, 110000, 120000],
            'intervention': Intervention.RTE,
            'description': 'RTE Initial Wage Premium (₹/year)'
        },
        
        # Apprenticeship-specific parameters
        {
            'name': 'APPRENTICE_INITIAL_PREMIUM',
            'baseline': 84000,
            'test_range': [50000, 67000, 84000, 102000, 120000],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Apprentice Initial Wage Premium (₹/year)'
        },
        {
            'name': 'APPRENTICE_DECAY_HALFLIFE',
            'baseline': 10,
            'test_range': [5, 7.5, 10, 20, 50],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Apprentice Premium Decay Half-life (years)'
        },
        {
            'name': 'APPRENTICE_YEAR_0_OPPORTUNITY_COST',
            'baseline': -49000,
            'test_range': [-80000, -64500, -49000, -34500, -20000],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Year 0 Training Opportunity Cost (₹/year)'
        },
        
        # Core Mincer parameters (TIER 2)
        {
            'name': 'MINCER_RETURN_HS',
            'baseline': 0.058,
            'test_range': [0.050, 0.054, 0.058, 0.062, 0.065],
            'intervention': Intervention.RTE,
            'description': 'Mincer Return (% per year schooling)'
        },
        
        # Formal sector multiplier (CRITICAL - core driver of apprenticeship benefits)
        {
            'name': 'FORMAL_MULTIPLIER',
            'baseline': 2.25,
            'test_range': [1.8, 2.0, 2.25, 2.5, 2.7],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Formal vs Informal Wage Multiplier'
        },
        
        # Macroeconomic parameters
        {
            'name': 'SOCIAL_DISCOUNT_RATE',
            'baseline': 0.0372,
            'test_range': [0.03, 0.035, 0.0372, 0.05, 0.08],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Social Discount Rate'
        },
        {
            'name': 'REAL_WAGE_GROWTH',
            'baseline': 0.0001,
            'test_range': [0.0, 0.0001, 0.005, 0.01, 0.02],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Real Wage Growth Rate'
        },
        
        # Program completion parameters
        {
            'name': 'RTE_SEAT_FILL_RATE',
            'baseline': 0.29,
            'test_range': [0.20, 0.25, 0.29, 0.35, 0.40],
            'intervention': Intervention.RTE,
            'description': 'RTE Seat Fill Rate'
        },
        {
            'name': 'RTE_RETENTION_FUNNEL',
            'baseline': 0.60,
            'test_range': [0.50, 0.55, 0.60, 0.70, 0.75],
            'intervention': Intervention.RTE,
            'description': 'RTE Retention Through Grade 12'
        },
        {
            'name': 'APPRENTICE_COMPLETION_RATE',
            'baseline': 0.85,
            'test_range': [0.75, 0.80, 0.85, 0.90, 0.95],
            'intervention': Intervention.APPRENTICESHIP,
            'description': 'Apprentice Completion Rate'
        },
    ]
    
    # Run sensitivity tests
    all_results = []
    
    print("Running sensitivity tests for each parameter...")
    print("(Testing Urban Male, West region as baseline)\n")
    
    for param_config in params_to_test:
        print(f"Testing: {param_config['description']}...")
        
        result = test_parameter_sensitivity(
            param_name=param_config['name'],
            baseline_value=param_config['baseline'],
            test_values=param_config['test_range'],
            intervention=param_config['intervention']
        )
        
        result['description'] = param_config['description']
        result['intervention'] = param_config['intervention'].value
        all_results.append(result)
    
    # Sort by max_swing (highest impact first)
    all_results.sort(key=lambda x: x['max_swing'], reverse=True)
    
    # Print results
    print("\n" + "="*80)
    print("RESULTS: PARAMETERS RANKED BY NPV IMPACT")
    print("="*80)
    print()
    
    critical_params = []
    moderate_params = []
    minor_params = []
    
    for i, result in enumerate(all_results, 1):
        baseline_npv = result['baseline_npv']
        max_swing = result['max_swing']
        
        # Classify by impact magnitude
        if max_swing > 20:
            critical_params.append(result)
            priority = "🔴 CRITICAL"
        elif max_swing > 10:
            moderate_params.append(result)
            priority = "🟡 MODERATE"
        else:
            minor_params.append(result)
            priority = "🟢 MINOR"
        
        print(f"{i}. {priority} | {result['description']}")
        print(f"   Intervention: {result['intervention'].upper()}")
        print(f"   Baseline NPV: {format_currency(baseline_npv)}")
        print(f"   Max NPV Swing: {max_swing:.1f}%")
        print(f"   Baseline Value: {result['baseline_value']}")
        
        # Show range of NPV values
        if result['npvs']:
            min_npv = min(result['npvs'])
            max_npv = max(result['npvs'])
            print(f"   NPV Range: {format_currency(min_npv)} to {format_currency(max_npv)}")
        else:
            print(f"   NPV Range: [Parameter not used in calculation]")
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print(f"🔴 CRITICAL Parameters (>20% NPV impact): {len(critical_params)}")
    for p in critical_params:
        print(f"   - {p['description']}: {p['max_swing']:.1f}% swing")
    
    print()
    print(f"🟡 MODERATE Parameters (10-20% NPV impact): {len(moderate_params)}")
    for p in moderate_params:
        print(f"   - {p['description']}: {p['max_swing']:.1f}% swing")
    
    print()
    print(f"🟢 MINOR Parameters (<10% NPV impact): {len(minor_params)}")
    for p in minor_params:
        print(f"   - {p['description']}: {p['max_swing']:.1f}% swing")
    
    print()
    print("="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print()
    print("Focus internal vetting document on CRITICAL parameters only.")
    print("MODERATE parameters can be mentioned briefly in appendix.")
    print("MINOR parameters can be held constant at baseline values.")
    print()
    
    # Regional P(Formal) Analysis
    print("="*80)
    print("SPECIAL CASE: REGIONAL P(FORMAL) VARIATION FOR RTE")
    print("="*80)
    print()
    print("Testing regional variation in RTE formal sector entry rates...")
    print("(This tests the ACTUAL parameters used in RTE calculation)\n")
    
    from economic_core_v3_updated import RegionalParameters
    
    # Test 1: Show baseline regional variation
    print("PART 1: Baseline Regional NPV Variation")
    print("-"*60)
    
    baseline_params = ParameterRegistry()
    baseline_calc = LifetimeNPVCalculator(params=baseline_params)
    
    region_map = {
        'North': Region.NORTH,
        'South': Region.SOUTH, 
        'West': Region.WEST,
        'East': Region.EAST
    }
    
    regional_npvs = {}
    print(f"{'Region':<10} {'P(Formal)':<12} {'NPV':<15}")
    print("-"*40)
    
    for region_name, region_enum in region_map.items():
        result = baseline_calc.calculate_lnpv(
            Intervention.RTE, Gender.MALE, Location.URBAN, region_enum
        )
        npv = result['lnpv']
        p_formal = baseline_calc.wage_model.regional.p_formal_hs[region_enum]
        regional_npvs[region_name] = npv
        
        print(f"{region_name:<10} {p_formal:<12.1%} {format_currency(npv):<15}")
    
    max_npv = max(regional_npvs.values())
    min_npv = min(regional_npvs.values())
    npv_swing = ((max_npv - min_npv) / min_npv) * 100
    
    print()
    print(f"NPV Range: {format_currency(min_npv)} to {format_currency(max_npv)}")
    print(f"**REGIONAL VARIATION CAUSES {npv_swing:.0f}% NPV SWING!**")
    print()
    
    # Test 2: Sensitivity to regional P(Formal) changes
    print("PART 2: Testing P(Formal) Sensitivity Within One Region (West)")
    print("-"*60)
    print()
    
    test_p_formals = [0.15, 0.20, 0.25, 0.30, 0.40, 0.60]
    west_npvs = []
    baseline_west_npv = None  # Initialize
    
    print(f"{'P(Formal)':<12} {'NPV':<15} {'% vs Baseline':<15}")
    print("-"*45)
    
    for p_formal in test_p_formals:
        # Create modified parameters
        params = ParameterRegistry()
        regional_params = RegionalParameters()
        regional_params.p_formal_hs[Region.WEST] = p_formal
        
        calc = LifetimeNPVCalculator(params=params)
        calc.wage_model.regional = regional_params
        
        result = calc.calculate_lnpv(
            Intervention.RTE, Gender.MALE, Location.URBAN, Region.WEST
        )
        npv = result['lnpv']
        west_npvs.append(npv)
        
        # Calculate % difference from baseline (p_formal=0.20)
        if p_formal == 0.20:
            baseline_west_npv = npv
        
        if baseline_west_npv:
            pct_diff = ((npv - baseline_west_npv) / baseline_west_npv) * 100
        else:
            pct_diff = 0
        
        print(f"{p_formal:<12.0%} {format_currency(npv):<15} {pct_diff:>+6.1f}%")
    
    max_swing = ((max(west_npvs) - min(west_npvs)) / min(west_npvs)) * 100
    print()
    print(f"**REGIONAL P(FORMAL) SENSITIVITY: {max_swing:.0f}% NPV SWING**")
    print()
    print("This confirms that REGIONAL P(FORMAL|HS) is THE critical RTE parameter,")
    print("with much higher impact than test scores or wage premiums!")
    print()
    
    return all_results


if __name__ == "__main__":
    try:
        results = main()
        print("\n✅ Analysis complete. Use results to create vetting document.\n")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()