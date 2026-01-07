"""
RWF Economic Impact Model - Sensitivity Analysis Module
=========================================================
Milestone 3: Uncertainty Quantification & Break-Even Analysis

This module performs:
1. One-way sensitivity analysis (π₀, h, P(Formal), test score)
2. Two-way sensitivity heatmaps
3. Monte Carlo uncertainty quantification
4. Break-even analysis (Max allowable cost at BCR thresholds)
5. Scenario bounds (pessimistic/baseline/optimistic)

Author: RWF Economic Impact Analysis Team
Version: 1.0 (November 2024)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from itertools import product
import warnings
import os

# Import from core module
from economic_core import (
    LifetimeNPVCalculator, ParameterRegistry, MincerWageModel,
    RegionalParameters, BaselineWages, CounterfactualDistribution,
    Gender, Location, Region, Intervention, Sector, DecayFunction,
    EmploymentModel, SectorTransitionModel
)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = "outputs"
VIZ_DIR = f"{OUTPUT_DIR}/visualizations"
HEATMAP_DIR = f"{OUTPUT_DIR}/sensitivity_heatmaps"

# Ensure directories exist
for d in [OUTPUT_DIR, VIZ_DIR, HEATMAP_DIR]:
    os.makedirs(d, exist_ok=True)

# BCR thresholds for break-even analysis
BCR_THRESHOLDS = [1.0, 2.0, 3.0]

# Monte Carlo settings
N_SIMULATIONS = 1000
RANDOM_SEED = 42

# Visualization settings
plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {
    'rte': '#2E86AB',
    'apprenticeship': '#A23B72',
    'formal': '#F18F01',
    'informal': '#C73E1D',
    'baseline': '#3A3A3A'
}

# ============================================================================
# SCENARIO DEFINITIONS (32 scenarios)
# ============================================================================

ALL_SCENARIOS = list(product(
    [Intervention.RTE, Intervention.APPRENTICESHIP],
    [Region.NORTH, Region.SOUTH, Region.EAST, Region.WEST],
    [Gender.MALE, Gender.FEMALE],
    [Location.URBAN, Location.RURAL]
))

def scenario_id(intervention, region, gender, location) -> str:
    """Generate unique scenario identifier."""
    return f"{intervention.value}_{region.value}_{gender.value}_{location.value}"

# ============================================================================
# ONE-WAY SENSITIVITY ANALYSIS
# ============================================================================

class OneWaySensitivity:
    """Performs one-way sensitivity analysis on single parameters."""
    
    def __init__(self, base_params: ParameterRegistry = None):
        self.base_params = base_params or ParameterRegistry()
        self.results = {}
    
    def _create_modified_calculator(self, **param_overrides) -> LifetimeNPVCalculator:
        """Create calculator with modified parameters."""
        params = ParameterRegistry()
        
        # Apply overrides
        for key, value in param_overrides.items():
            if hasattr(params, key):
                getattr(params, key).value = value
        
        return LifetimeNPVCalculator(params=params)
    
    def sweep_initial_premium(self, multipliers: List[float] = None) -> pd.DataFrame:
        """
        Sensitivity on π₀ (initial premium) for both interventions.
        
        Args:
            multipliers: List of multipliers (e.g., [0.7, 0.85, 1.0, 1.15, 1.3])
        """
        if multipliers is None:
            multipliers = [0.7, 0.85, 1.0, 1.15, 1.3]
        
        base_rte = self.base_params.RTE_INITIAL_PREMIUM.value
        base_app = self.base_params.APPRENTICE_INITIAL_PREMIUM.value
        
        results = []
        
        for mult in multipliers:
            # RTE scenarios
            params_rte = ParameterRegistry()
            params_rte.RTE_INITIAL_PREMIUM.value = base_rte * mult
            calc_rte = LifetimeNPVCalculator(params=params_rte)
            
            # Apprenticeship scenarios
            params_app = ParameterRegistry()
            params_app.APPRENTICE_INITIAL_PREMIUM.value = base_app * mult
            calc_app = LifetimeNPVCalculator(params=params_app)
            
            for region in Region:
                for gender in Gender:
                    for location in Location:
                        # RTE
                        res_rte = calc_rte.calculate_lnpv(
                            Intervention.RTE, gender, location, region
                        )
                        results.append({
                            'intervention': 'rte',
                            'region': region.value,
                            'gender': gender.value,
                            'location': location.value,
                            'scenario_id': scenario_id(Intervention.RTE, region, gender, location),
                            'multiplier': mult,
                            'pi0_value': base_rte * mult,
                            'lnpv': res_rte['lnpv']
                        })
                        
                        # Apprenticeship
                        res_app = calc_app.calculate_lnpv(
                            Intervention.APPRENTICESHIP, gender, location, region
                        )
                        results.append({
                            'intervention': 'apprenticeship',
                            'region': region.value,
                            'gender': gender.value,
                            'location': location.value,
                            'scenario_id': scenario_id(Intervention.APPRENTICESHIP, region, gender, location),
                            'multiplier': mult,
                            'pi0_value': base_app * mult,
                            'lnpv': res_app['lnpv']
                        })
        
        df = pd.DataFrame(results)
        self.results['pi0'] = df
        return df
    
    def sweep_halflife(self, halflife_values: List[float] = None) -> pd.DataFrame:
        """
        Sensitivity on h (wage premium half-life).
        Only affects apprenticeship (RTE uses no decay).
        """
        if halflife_values is None:
            halflife_values = [5, 10, 15, 20, 50]  # 50 ≈ infinity
        
        results = []
        
        for h in halflife_values:
            params = ParameterRegistry()
            params.APPRENTICE_DECAY_HALFLIFE.value = h
            calc = LifetimeNPVCalculator(params=params)
            
            for region in Region:
                for gender in Gender:
                    for location in Location:
                        # RTE (unaffected by h, but include for comparison)
                        res_rte = calc.calculate_lnpv(
                            Intervention.RTE, gender, location, region
                        )
                        results.append({
                            'intervention': 'rte',
                            'region': region.value,
                            'gender': gender.value,
                            'location': location.value,
                            'scenario_id': scenario_id(Intervention.RTE, region, gender, location),
                            'halflife': h,
                            'lnpv': res_rte['lnpv']
                        })
                        
                        # Apprenticeship (affected)
                        res_app = calc.calculate_lnpv(
                            Intervention.APPRENTICESHIP, gender, location, region
                        )
                        results.append({
                            'intervention': 'apprenticeship',
                            'region': region.value,
                            'gender': gender.value,
                            'location': location.value,
                            'scenario_id': scenario_id(Intervention.APPRENTICESHIP, region, gender, location),
                            'halflife': h,
                            'lnpv': res_app['lnpv']
                        })
        
        df = pd.DataFrame(results)
        self.results['halflife'] = df
        return df
    
    def sweep_formal_entry(self, delta_pp: List[float] = None) -> pd.DataFrame:
        """
        Sensitivity on P(Formal | Treatment) ± percentage points.
        """
        if delta_pp is None:
            delta_pp = [-0.05, -0.025, 0, 0.025, 0.05]  # ±5pp
        
        base_p_hs = self.base_params.P_FORMAL_HIGHER_SECONDARY.value
        base_p_app = self.base_params.P_FORMAL_APPRENTICE.value
        
        results = []
        
        for delta in delta_pp:
            params = ParameterRegistry()
            params.P_FORMAL_HIGHER_SECONDARY.value = np.clip(base_p_hs + delta, 0.05, 0.95)
            params.P_FORMAL_APPRENTICE.value = np.clip(base_p_app + delta, 0.05, 0.95)
            calc = LifetimeNPVCalculator(params=params)
            
            for intervention in Intervention:
                for region in Region:
                    for gender in Gender:
                        for location in Location:
                            res = calc.calculate_lnpv(
                                intervention, gender, location, region
                            )
                            results.append({
                                'intervention': intervention.value,
                                'region': region.value,
                                'gender': gender.value,
                                'location': location.value,
                                'scenario_id': scenario_id(intervention, region, gender, location),
                                'delta_pp': delta,
                                'p_formal_hs': params.P_FORMAL_HIGHER_SECONDARY.value,
                                'p_formal_app': params.P_FORMAL_APPRENTICE.value,
                                'lnpv': res['lnpv']
                            })
        
        df = pd.DataFrame(results)
        self.results['formal_entry'] = df
        return df
    
    def sweep_test_score(self, test_scores: List[float] = None) -> pd.DataFrame:
        """
        Sensitivity on test score effect (RTE only).
        """
        if test_scores is None:
            test_scores = [0.15, 0.20, 0.23, 0.26, 0.30]  # SD
        
        results = []
        
        for ts in test_scores:
            params = ParameterRegistry()
            params.RTE_TEST_SCORE_GAIN.value = ts
            calc = LifetimeNPVCalculator(params=params)
            
            for region in Region:
                for gender in Gender:
                    for location in Location:
                        res = calc.calculate_lnpv(
                            Intervention.RTE, gender, location, region
                        )
                        results.append({
                            'intervention': 'rte',
                            'region': region.value,
                            'gender': gender.value,
                            'location': location.value,
                            'scenario_id': scenario_id(Intervention.RTE, region, gender, location),
                            'test_score_sd': ts,
                            'lnpv': res['lnpv']
                        })
        
        df = pd.DataFrame(results)
        self.results['test_score'] = df
        return df


# ============================================================================
# TWO-WAY SENSITIVITY ANALYSIS
# ============================================================================

class TwoWaySensitivity:
    """Performs two-way sensitivity analysis for heatmaps."""
    
    def __init__(self, base_params: ParameterRegistry = None):
        self.base_params = base_params or ParameterRegistry()
        self.results = {}
    
    def heatmap_pi0_halflife(
        self,
        pi0_multipliers: List[float] = None,
        halflife_values: List[float] = None,
        scenarios: List[Tuple] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Two-way sensitivity: π₀ × half-life.
        
        Args:
            pi0_multipliers: Multipliers for initial premium
            halflife_values: Half-life values in years
            scenarios: List of (intervention, region, gender, location) tuples
        """
        if pi0_multipliers is None:
            pi0_multipliers = np.linspace(0.5, 1.5, 11)  # 50%-150%
        if halflife_values is None:
            halflife_values = [5, 7, 10, 15, 20, 30]
        if scenarios is None:
            # Default: one representative scenario per intervention
            scenarios = [
                (Intervention.RTE, Region.WEST, Gender.MALE, Location.URBAN),
                (Intervention.APPRENTICESHIP, Region.WEST, Gender.MALE, Location.URBAN),
            ]
        
        base_rte = self.base_params.RTE_INITIAL_PREMIUM.value
        base_app = self.base_params.APPRENTICE_INITIAL_PREMIUM.value
        
        results_by_scenario = {}
        
        for intervention, region, gender, location in scenarios:
            base_pi0 = base_rte if intervention == Intervention.RTE else base_app
            
            grid = np.zeros((len(halflife_values), len(pi0_multipliers)))
            
            for i, h in enumerate(halflife_values):
                for j, mult in enumerate(pi0_multipliers):
                    params = ParameterRegistry()
                    params.APPRENTICE_DECAY_HALFLIFE.value = h
                    
                    if intervention == Intervention.RTE:
                        params.RTE_INITIAL_PREMIUM.value = base_rte * mult
                    else:
                        params.APPRENTICE_INITIAL_PREMIUM.value = base_app * mult
                    
                    calc = LifetimeNPVCalculator(params=params)
                    res = calc.calculate_lnpv(intervention, gender, location, region)
                    grid[i, j] = res['lnpv']
            
            sid = scenario_id(intervention, region, gender, location)
            results_by_scenario[sid] = pd.DataFrame(
                grid,
                index=[f"h={h}" for h in halflife_values],
                columns=[f"{m:.0%}" for m in pi0_multipliers]
            )
        
        self.results['pi0_halflife'] = results_by_scenario
        return results_by_scenario
    
    def heatmap_formal_mincer(
        self,
        p_formal_values: List[float] = None,
        mincer_values: List[float] = None,
        scenarios: List[Tuple] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Two-way sensitivity: P(Formal) × Mincer return.
        """
        if p_formal_values is None:
            p_formal_values = np.linspace(0.10, 0.30, 9)  # 10%-30%
        if mincer_values is None:
            mincer_values = np.linspace(0.05, 0.07, 9)  # 5%-7%
        if scenarios is None:
            scenarios = [
                (Intervention.RTE, Region.WEST, Gender.MALE, Location.URBAN),
                (Intervention.APPRENTICESHIP, Region.WEST, Gender.MALE, Location.URBAN),
            ]
        
        results_by_scenario = {}
        
        for intervention, region, gender, location in scenarios:
            grid = np.zeros((len(mincer_values), len(p_formal_values)))
            
            for i, beta in enumerate(mincer_values):
                for j, p_formal in enumerate(p_formal_values):
                    params = ParameterRegistry()
                    params.MINCER_RETURN_HS.value = beta
                    params.P_FORMAL_HIGHER_SECONDARY.value = p_formal
                    
                    # Also adjust apprentice P(Formal) proportionally
                    base_ratio = 0.75 / 0.20  # baseline ratio
                    params.P_FORMAL_APPRENTICE.value = min(0.95, p_formal * base_ratio)
                    
                    calc = LifetimeNPVCalculator(params=params)
                    res = calc.calculate_lnpv(intervention, gender, location, region)
                    grid[i, j] = res['lnpv']
            
            sid = scenario_id(intervention, region, gender, location)
            results_by_scenario[sid] = pd.DataFrame(
                grid,
                index=[f"β={b:.1%}" for b in mincer_values],
                columns=[f"P(F)={p:.0%}" for p in p_formal_values]
            )
        
        self.results['formal_mincer'] = results_by_scenario
        return results_by_scenario


# ============================================================================
# MONTE CARLO SIMULATION
# ============================================================================

class MonteCarloAnalysis:
    """Enhanced Monte Carlo uncertainty quantification."""
    
    def __init__(self, n_simulations: int = N_SIMULATIONS, seed: int = RANDOM_SEED):
        self.n_simulations = n_simulations
        self.seed = seed
        self.base_params = ParameterRegistry()
        self.results = None
        self.full_samples = None
    
    def _sample_parameters(self) -> Dict[str, float]:
        """Sample from parameter uncertainty distributions."""
        samples = {}
        
        # Tier 1 (highest uncertainty)
        samples['pi0_rte_mult'] = np.random.uniform(0.7, 1.3)
        samples['pi0_app_mult'] = np.random.uniform(0.7, 1.3)
        samples['halflife'] = np.random.uniform(5, 25)
        samples['p_formal_hs'] = np.random.triangular(0.15, 0.20, 0.25)
        samples['p_formal_app'] = np.random.triangular(0.50, 0.75, 0.90)
        samples['test_score'] = np.random.triangular(0.15, 0.23, 0.30)
        
        # Tier 2 (moderate uncertainty)
        samples['mincer_return'] = np.random.normal(0.058, 0.005)
        samples['mincer_return'] = np.clip(samples['mincer_return'], 0.04, 0.08)
        
        # Tier 3 (low uncertainty - keep tighter)
        samples['discount_rate'] = np.random.triangular(0.03, 0.0372, 0.06)
        
        return samples
    
    def run(self) -> pd.DataFrame:
        """Run full Monte Carlo simulation for all 32 scenarios."""
        np.random.seed(self.seed)
        
        all_results = []
        all_samples = []
        
        base_rte = self.base_params.RTE_INITIAL_PREMIUM.value
        base_app = self.base_params.APPRENTICE_INITIAL_PREMIUM.value
        
        for sim in range(self.n_simulations):
            if sim % 100 == 0:
                print(f"  Monte Carlo: {sim}/{self.n_simulations}")
            
            # Sample parameters
            sampled = self._sample_parameters()
            all_samples.append(sampled)
            
            # Create modified parameter registry
            params = ParameterRegistry()
            params.RTE_INITIAL_PREMIUM.value = base_rte * sampled['pi0_rte_mult']
            params.APPRENTICE_INITIAL_PREMIUM.value = base_app * sampled['pi0_app_mult']
            params.APPRENTICE_DECAY_HALFLIFE.value = sampled['halflife']
            params.P_FORMAL_HIGHER_SECONDARY.value = sampled['p_formal_hs']
            params.P_FORMAL_APPRENTICE.value = sampled['p_formal_app']
            params.RTE_TEST_SCORE_GAIN.value = sampled['test_score']
            params.MINCER_RETURN_HS.value = sampled['mincer_return']
            params.SOCIAL_DISCOUNT_RATE.value = sampled['discount_rate']
            
            calc = LifetimeNPVCalculator(params=params)
            
            # Calculate all scenarios
            for intervention, region, gender, location in ALL_SCENARIOS:
                res = calc.calculate_lnpv(intervention, gender, location, region)
                all_results.append({
                    'simulation': sim,
                    'intervention': intervention.value,
                    'region': region.value,
                    'gender': gender.value,
                    'location': location.value,
                    'scenario_id': scenario_id(intervention, region, gender, location),
                    'lnpv': res['lnpv'],
                    **sampled
                })
        
        self.full_samples = pd.DataFrame(all_samples)
        self.results = pd.DataFrame(all_results)
        return self.results
    
    def summarize(self) -> pd.DataFrame:
        """Summarize Monte Carlo results by scenario."""
        if self.results is None:
            raise ValueError("Run simulation first")
        
        summary = self.results.groupby('scenario_id').agg({
            'lnpv': ['mean', 'median', 'std', 
                     lambda x: np.percentile(x, 5),
                     lambda x: np.percentile(x, 25),
                     lambda x: np.percentile(x, 75),
                     lambda x: np.percentile(x, 95),
                     lambda x: (x > 0).mean()]  # P(LNPV > 0)
        }).reset_index()
        
        summary.columns = ['scenario_id', 'mean', 'median', 'std', 
                          'p5', 'p25', 'p75', 'p95', 'prob_positive']
        
        # Add scenario details
        for i, row in summary.iterrows():
            parts = row['scenario_id'].split('_')
            summary.loc[i, 'intervention'] = parts[0]
            summary.loc[i, 'region'] = parts[1]
            summary.loc[i, 'gender'] = parts[2]
            summary.loc[i, 'location'] = parts[3]
        
        return summary


# ============================================================================
# BREAK-EVEN ANALYSIS
# ============================================================================

class BreakEvenAnalyzer:
    """
    Calculate maximum allowable cost per beneficiary at BCR thresholds.
    
    Max_Cost = LNPV / Target_BCR
    """
    
    def __init__(self, bcr_thresholds: List[float] = None):
        self.thresholds = bcr_thresholds or BCR_THRESHOLDS
        self.base_params = ParameterRegistry()
    
    def calculate_baseline_breakeven(self) -> pd.DataFrame:
        """Calculate break-even costs for baseline (point estimate) LNPV."""
        calc = LifetimeNPVCalculator()
        results = []
        
        for intervention, region, gender, location in ALL_SCENARIOS:
            res = calc.calculate_lnpv(intervention, gender, location, region)
            lnpv = res['lnpv']
            
            row = {
                'scenario_id': scenario_id(intervention, region, gender, location),
                'intervention': intervention.value,
                'region': region.value,
                'gender': gender.value,
                'location': location.value,
                'lnpv_baseline': lnpv,
            }
            
            for bcr in self.thresholds:
                row[f'max_cost_bcr{bcr:.0f}'] = lnpv / bcr if lnpv > 0 else 0
            
            # Cost tolerance: difference between BCR=1 and BCR=3
            row['cost_tolerance'] = row['max_cost_bcr1'] - row['max_cost_bcr3']
            
            results.append(row)
        
        df = pd.DataFrame(results)
        
        # Rank by robustness (max_cost at BCR=3)
        df['robustness_rank'] = df['max_cost_bcr3'].rank(ascending=False)
        
        return df
    
    def calculate_monte_carlo_breakeven(
        self, 
        mc_summary: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate break-even costs using Monte Carlo percentiles.
        
        Provides conservative (p5), baseline (median), and optimistic (p95) thresholds.
        """
        results = []
        
        for _, row in mc_summary.iterrows():
            record = {
                'scenario_id': row['scenario_id'],
                'intervention': row['intervention'],
                'region': row['region'],
                'gender': row['gender'],
                'location': row['location'],
            }
            
            # For each LNPV percentile
            for percentile in ['p5', 'median', 'p95']:
                lnpv = row[percentile]
                for bcr in self.thresholds:
                    col_name = f'{percentile}_max_cost_bcr{bcr:.0f}'
                    record[col_name] = lnpv / bcr if lnpv > 0 else 0
            
            results.append(record)
        
        return pd.DataFrame(results)
    
    def regional_comparison(self, breakeven_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate break-even analysis by region."""
        agg = breakeven_df.groupby(['intervention', 'region']).agg({
            'lnpv_baseline': 'mean',
            'max_cost_bcr1': 'mean',
            'max_cost_bcr2': 'mean',
            'max_cost_bcr3': 'mean',
            'cost_tolerance': 'mean',
        }).reset_index()
        
        return agg


# ============================================================================
# SCENARIO BOUNDS (Pessimistic / Baseline / Optimistic)
# ============================================================================

class ScenarioBounds:
    """Calculate LNPV under pessimistic, baseline, and optimistic assumptions."""
    
    def __init__(self):
        self.base_params = ParameterRegistry()
        
        # Define scenario specifications
        self.scenarios = {
            'pessimistic': {
                'selection_bias_discount': 0.6,  # 40% bias → 60% of baseline
                'test_score': 0.15,
                'halflife': 7,
                'p_formal_mult': 0.8,
                'description': 'High selection bias, low school quality, rapid decay'
            },
            'baseline': {
                'selection_bias_discount': 1.0,
                'test_score': 0.23,
                'halflife': 10,
                'p_formal_mult': 1.0,
                'description': 'Point estimates from data'
            },
            'optimistic': {
                'selection_bias_discount': 1.0,
                'test_score': 0.28,
                'halflife': 25,
                'p_formal_mult': 1.15,
                'description': 'No selection bias, high-quality schools, persistent effects'
            }
        }
    
    def calculate_bounds(self) -> pd.DataFrame:
        """Calculate LNPV bounds for all 32 scenarios."""
        results = []
        
        base_p_hs = self.base_params.P_FORMAL_HIGHER_SECONDARY.value
        base_p_app = self.base_params.P_FORMAL_APPRENTICE.value
        
        for scenario_name, spec in self.scenarios.items():
            params = ParameterRegistry()
            params.RTE_TEST_SCORE_GAIN.value = spec['test_score']
            params.APPRENTICE_DECAY_HALFLIFE.value = spec['halflife']
            params.P_FORMAL_HIGHER_SECONDARY.value = base_p_hs * spec['p_formal_mult']
            params.P_FORMAL_APPRENTICE.value = min(0.95, base_p_app * spec['p_formal_mult'])
            
            calc = LifetimeNPVCalculator(params=params)
            
            for intervention, region, gender, location in ALL_SCENARIOS:
                res = calc.calculate_lnpv(intervention, gender, location, region)
                
                # Apply selection bias discount
                adjusted_lnpv = res['lnpv'] * spec['selection_bias_discount']
                
                results.append({
                    'scenario_type': scenario_name,
                    'scenario_id': scenario_id(intervention, region, gender, location),
                    'intervention': intervention.value,
                    'region': region.value,
                    'gender': gender.value,
                    'location': location.value,
                    'lnpv': adjusted_lnpv,
                    'max_cost_bcr3': adjusted_lnpv / 3.0 if adjusted_lnpv > 0 else 0,
                    'description': spec['description']
                })
        
        df = pd.DataFrame(results)
        
        # Pivot for easier comparison
        pivot = df.pivot_table(
            index=['scenario_id', 'intervention', 'region', 'gender', 'location'],
            columns='scenario_type',
            values=['lnpv', 'max_cost_bcr3']
        ).reset_index()
        
        # Flatten column names
        pivot.columns = ['_'.join(col).strip('_') if col[1] else col[0] 
                        for col in pivot.columns]
        
        return pivot


# ============================================================================
# VISUALIZATIONS
# ============================================================================

class Visualizer:
    """Generate all required visualizations."""
    
    def __init__(self, output_dir: str = VIZ_DIR):
        self.output_dir = output_dir
    
    def tornado_diagram(
        self, 
        sensitivity_results: Dict[str, pd.DataFrame],
        scenario_filter: str = None,
        save_path: str = None
    ):
        """
        Create tornado diagram showing parameter impact on LNPV.
        """
        if scenario_filter is None:
            scenario_filter = "rte_west_male_urban"
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        params = []
        low_vals = []
        high_vals = []
        baseline_lnpv = None
        
        # π₀ sensitivity
        if 'pi0' in sensitivity_results:
            df = sensitivity_results['pi0']
            df_filtered = df[df['scenario_id'] == scenario_filter]
            if len(df_filtered) > 0:
                baseline_lnpv = df_filtered[df_filtered['multiplier'] == 1.0]['lnpv'].values[0]
                low = df_filtered[df_filtered['multiplier'] == 0.7]['lnpv'].values[0]
                high = df_filtered[df_filtered['multiplier'] == 1.3]['lnpv'].values[0]
                params.append('Initial Premium (π₀)')
                low_vals.append(low - baseline_lnpv)
                high_vals.append(high - baseline_lnpv)
        
        # Half-life sensitivity (apprenticeship only)
        if 'halflife' in sensitivity_results:
            df = sensitivity_results['halflife']
            app_scenario = scenario_filter.replace('rte', 'apprenticeship')
            df_filtered = df[df['scenario_id'] == app_scenario]
            if len(df_filtered) > 0:
                baseline = df_filtered[df_filtered['halflife'] == 10]['lnpv'].values[0]
                low = df_filtered[df_filtered['halflife'] == 5]['lnpv'].values[0]
                high = df_filtered[df_filtered['halflife'] == 50]['lnpv'].values[0]
                params.append('Premium Half-life (h)')
                low_vals.append(low - baseline)
                high_vals.append(high - baseline)
        
        # Formal entry sensitivity
        if 'formal_entry' in sensitivity_results:
            df = sensitivity_results['formal_entry']
            df_filtered = df[df['scenario_id'] == scenario_filter]
            if len(df_filtered) > 0:
                baseline = df_filtered[df_filtered['delta_pp'] == 0]['lnpv'].values[0]
                low = df_filtered[df_filtered['delta_pp'] == -0.05]['lnpv'].values[0]
                high = df_filtered[df_filtered['delta_pp'] == 0.05]['lnpv'].values[0]
                params.append('P(Formal) ±5pp')
                low_vals.append(low - baseline)
                high_vals.append(high - baseline)
        
        # Test score sensitivity (RTE only)
        if 'test_score' in sensitivity_results and 'rte' in scenario_filter:
            df = sensitivity_results['test_score']
            df_filtered = df[df['scenario_id'] == scenario_filter]
            if len(df_filtered) > 0:
                baseline = df_filtered[df_filtered['test_score_sd'] == 0.23]['lnpv'].values[0]
                low = df_filtered[df_filtered['test_score_sd'] == 0.15]['lnpv'].values[0]
                high = df_filtered[df_filtered['test_score_sd'] == 0.30]['lnpv'].values[0]
                params.append('Test Score Effect (SD)')
                low_vals.append(low - baseline)
                high_vals.append(high - baseline)
        
        if len(params) == 0:
            print("No data for tornado diagram")
            return
        
        # Sort by absolute impact
        impacts = [abs(h - l) for l, h in zip(low_vals, high_vals)]
        sorted_idx = np.argsort(impacts)[::-1]
        
        params = [params[i] for i in sorted_idx]
        low_vals = [low_vals[i] for i in sorted_idx]
        high_vals = [high_vals[i] for i in sorted_idx]
        
        y_pos = np.arange(len(params))
        
        # Plot bars
        for i, (param, low, high) in enumerate(zip(params, low_vals, high_vals)):
            ax.barh(i, low, color=COLORS['informal'], alpha=0.8, label='Low' if i == 0 else '')
            ax.barh(i, high, color=COLORS['formal'], alpha=0.8, label='High' if i == 0 else '')
        
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(params)
        ax.set_xlabel('Change in LNPV (₹)')
        ax.set_title(f'Tornado Diagram: Parameter Impact on LNPV\n({scenario_filter})')
        ax.legend(loc='lower right')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'₹{x/1e5:.1f}L'))
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = f"{self.output_dir}/tornado_diagram.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")
    
    def halflife_lineplot(
        self,
        halflife_results: pd.DataFrame,
        save_path: str = None
    ):
        """Line plot: LNPV vs. half-life for representative scenarios."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter to apprenticeship scenarios (most affected by h)
        df = halflife_results[halflife_results['intervention'] == 'apprenticeship']
        
        # Plot by region
        for region in df['region'].unique():
            df_region = df[(df['region'] == region) & 
                          (df['gender'] == 'male') & 
                          (df['location'] == 'urban')]
            if len(df_region) > 0:
                ax.plot(df_region['halflife'], df_region['lnpv'], 
                       marker='o', label=f'{region.title()}', linewidth=2)
        
        ax.set_xlabel('Premium Half-life (years)')
        ax.set_ylabel('Lifetime NPV (₹)')
        ax.set_title('Apprenticeship LNPV Sensitivity to Wage Premium Decay\n(Urban Male)')
        ax.legend(title='Region')
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'₹{x/1e5:.0f}L'))
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = f"{self.output_dir}/halflife_sensitivity.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")
    
    def heatmap(
        self,
        data: pd.DataFrame,
        title: str,
        save_path: str
    ):
        """Create heatmap from 2D sensitivity grid."""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Convert to numpy for plotting
        values = data.values / 1e5  # Convert to Lakhs
        
        im = ax.imshow(values, cmap='RdYlGn', aspect='auto')
        
        # Labels
        ax.set_xticks(np.arange(len(data.columns)))
        ax.set_yticks(np.arange(len(data.index)))
        ax.set_xticklabels(data.columns, rotation=45, ha='right')
        ax.set_yticklabels(data.index)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('LNPV (₹ Lakhs)')
        
        # Annotate cells
        for i in range(len(data.index)):
            for j in range(len(data.columns)):
                text = ax.text(j, i, f'{values[i, j]:.1f}L',
                              ha='center', va='center', fontsize=8)
        
        ax.set_title(title)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")
    
    def monte_carlo_distribution(
        self,
        mc_results: pd.DataFrame,
        scenario_filter: str = None,
        save_path: str = None
    ):
        """Histogram of LNPV distribution from Monte Carlo."""
        if scenario_filter is None:
            scenario_filter = "rte_west_male_urban"
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        df = mc_results[mc_results['scenario_id'] == scenario_filter]
        
        ax.hist(df['lnpv'] / 1e5, bins=50, color=COLORS['rte'], alpha=0.7, edgecolor='white')
        
        # Add percentile lines
        p5 = np.percentile(df['lnpv'], 5) / 1e5
        p50 = np.percentile(df['lnpv'], 50) / 1e5
        p95 = np.percentile(df['lnpv'], 95) / 1e5
        
        ax.axvline(p5, color='red', linestyle='--', label=f'5th pct: ₹{p5:.1f}L')
        ax.axvline(p50, color='black', linestyle='-', linewidth=2, label=f'Median: ₹{p50:.1f}L')
        ax.axvline(p95, color='green', linestyle='--', label=f'95th pct: ₹{p95:.1f}L')
        
        ax.set_xlabel('Lifetime NPV (₹ Lakhs)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'Monte Carlo Distribution of LNPV\n({scenario_filter}, n={len(df)})')
        ax.legend()
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = f"{self.output_dir}/monte_carlo_distribution.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")
    
    def breakeven_bar_chart(
        self,
        breakeven_df: pd.DataFrame,
        save_path: str = None
    ):
        """Bar chart of max allowable cost by scenario."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        for idx, intervention in enumerate(['rte', 'apprenticeship']):
            ax = axes[idx]
            df = breakeven_df[breakeven_df['intervention'] == intervention].copy()
            
            # Sort by max_cost_bcr3
            df = df.sort_values('max_cost_bcr3', ascending=True)
            
            x = np.arange(len(df))
            width = 0.25
            
            bars1 = ax.barh(x - width, df['max_cost_bcr3'] / 1e5, width, 
                           label='BCR=3 (Highly Cost-Effective)', color=COLORS['formal'])
            bars2 = ax.barh(x, df['max_cost_bcr2'] / 1e5, width,
                           label='BCR=2', color=COLORS['rte'])
            bars3 = ax.barh(x + width, df['max_cost_bcr1'] / 1e5, width,
                           label='BCR=1 (Break-Even)', color=COLORS['informal'])
            
            ax.set_yticks(x)
            labels = [f"{r['region']}_{r['gender']}_{r['location']}" 
                     for _, r in df.iterrows()]
            ax.set_yticklabels(labels, fontsize=8)
            ax.set_xlabel('Max Allowable Cost per Beneficiary (₹ Lakhs)')
            ax.set_title(f'{intervention.upper()}: Break-Even Cost Thresholds')
            ax.legend(loc='lower right')
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = f"{self.output_dir}/breakeven_bar_chart.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")
    
    def regional_boxplot(
        self,
        mc_results: pd.DataFrame,
        save_path: str = None
    ):
        """Box plot comparing LNPV distributions by region."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        for idx, intervention in enumerate(['rte', 'apprenticeship']):
            ax = axes[idx]
            df = mc_results[mc_results['intervention'] == intervention]
            
            # Prepare data for boxplot
            data_by_region = [df[df['region'] == r.value]['lnpv'] / 1e5 
                             for r in Region]
            
            bp = ax.boxplot(data_by_region, labels=[r.value.title() for r in Region])
            
            ax.set_ylabel('Lifetime NPV (₹ Lakhs)')
            ax.set_title(f'{intervention.upper()}: LNPV Distribution by Region')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = f"{self.output_dir}/regional_boxplot.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {save_path}")


# ============================================================================
# NARRATIVE GENERATOR
# ============================================================================

def generate_narrative(
    breakeven_df: pd.DataFrame,
    mc_summary: pd.DataFrame,
    scenario_bounds: pd.DataFrame,
    output_path: str = f"{OUTPUT_DIR}/sensitivity_analysis_narrative.md"
):
    """Generate interpretive narrative document."""
    
    narrative = """# RWF Economic Impact Model: Sensitivity Analysis Report

## Executive Summary

This report presents comprehensive uncertainty quantification for the RightWalk Foundation's 
Lifetime Net Present Value (LNPV) model. Without actual program cost data, we provide 
**break-even analysis** showing the maximum allowable cost per beneficiary at different 
Benefit-Cost Ratio (BCR) thresholds.

---

## Key Findings

### 1. Break-Even Cost Thresholds

The table below shows the **maximum program cost per beneficiary** that maintains cost-effectiveness:

| Intervention | Region | BCR=3 (Highly Effective) | BCR=2 | BCR=1 (Break-Even) |
|--------------|--------|--------------------------|-------|---------------------|
"""
    
    # Add sample rows from breakeven_df
    for intervention in ['rte', 'apprenticeship']:
        for region in ['south', 'west', 'north', 'east']:
            row = breakeven_df[
                (breakeven_df['intervention'] == intervention) & 
                (breakeven_df['region'] == region) &
                (breakeven_df['gender'] == 'male') &
                (breakeven_df['location'] == 'urban')
            ]
            if len(row) > 0:
                row = row.iloc[0]
                narrative += f"| {intervention.upper()} | {region.title()} | ₹{row['max_cost_bcr3']/1e5:.1f}L | ₹{row['max_cost_bcr2']/1e5:.1f}L | ₹{row['max_cost_bcr1']/1e5:.1f}L |\n"
    
    narrative += """
*Note: 1 Lakh (L) = ₹100,000. Values shown for Urban Male scenario.*

### 2. Decision Rule for RWF

**If actual per-beneficiary cost < Max Cost (BCR=3), the intervention is highly cost-effective.**

For example:
- RTE South Urban Male: If program costs < ₹{:.1f}L per beneficiary → BCR > 3:1
- Apprenticeship West Urban Male: If program costs < ₹{:.1f}L per beneficiary → BCR > 3:1

""".format(
        breakeven_df[(breakeven_df['intervention'] == 'rte') & 
                    (breakeven_df['region'] == 'south') &
                    (breakeven_df['gender'] == 'male') &
                    (breakeven_df['location'] == 'urban')]['max_cost_bcr3'].values[0] / 1e5,
        breakeven_df[(breakeven_df['intervention'] == 'apprenticeship') & 
                    (breakeven_df['region'] == 'west') &
                    (breakeven_df['gender'] == 'male') &
                    (breakeven_df['location'] == 'urban')]['max_cost_bcr3'].values[0] / 1e5
    )
    
    narrative += """
### 3. Uncertainty Quantification (Monte Carlo)

From {:,} simulations sampling all uncertain parameters:

| Metric | RTE (median) | Apprenticeship (median) |
|--------|--------------|------------------------|
""".format(N_SIMULATIONS)
    
    rte_summary = mc_summary[mc_summary['intervention'] == 'rte']
    app_summary = mc_summary[mc_summary['intervention'] == 'apprenticeship']
    
    narrative += f"| Median LNPV | ₹{rte_summary['median'].mean()/1e5:.1f}L | ₹{app_summary['median'].mean()/1e5:.1f}L |\n"
    narrative += f"| 5th Percentile | ₹{rte_summary['p5'].mean()/1e5:.1f}L | ₹{app_summary['p5'].mean()/1e5:.1f}L |\n"
    narrative += f"| 95th Percentile | ₹{rte_summary['p95'].mean()/1e5:.1f}L | ₹{app_summary['p95'].mean()/1e5:.1f}L |\n"
    narrative += f"| P(LNPV > 0) | {rte_summary['prob_positive'].mean()*100:.1f}% | {app_summary['prob_positive'].mean()*100:.1f}% |\n"
    
    narrative += """
### 4. Scenario Bounds

Under pessimistic, baseline, and optimistic assumptions:

| Scenario | Assumption | RTE LNPV Range | App LNPV Range |
|----------|------------|----------------|----------------|
| Pessimistic | 40% selection bias, h=7yr, low quality | Lower bound | Lower bound |
| Baseline | Point estimates | Central estimate | Central estimate |
| Optimistic | No bias, h=25yr, high quality | Upper bound | Upper bound |

---

## Methodology Notes

### Parameters Varied in Sensitivity Analysis

**Tier 1 (Highest Uncertainty):**
- Initial wage premium (π₀): ±30%
- Premium half-life (h): 5-50 years
- P(Formal|Treatment): ±5 percentage points
- Test score effect: 0.15-0.30 SD

**Tier 2 (Moderate Uncertainty):**
- Mincer return (β): 5.0%-7.0%

**Tier 3 (Low Uncertainty):**
- Discount rate (δ): 3%-6%

### Limitations

1. **No causal identification**: Estimates are correlation-based, not from RCT
2. **Selection bias**: Treated estimates may be inflated 20-40%
3. **External validity**: NBER RCT from Andhra Pradesh may not generalize
4. **Missing cost data**: BCR cannot be computed without RWF per-beneficiary costs

---

## Recommendations

1. **RTE Intervention**: Robust across scenarios; South/West regions show highest break-even thresholds
2. **Apprenticeship**: Sensitive to half-life assumption; recommend tracking alumni wages over 5+ years
3. **Data Collection Priority**: Obtain per-beneficiary costs to complete BCR calculation
4. **Monitoring**: Track formal sector placement rates to validate P(Formal) assumptions

---

*Generated: Milestone 3 Sensitivity Analysis*
"""
    
    with open(output_path, 'w') as f:
        f.write(narrative)
    
    print(f"Saved: {output_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_milestone3_analysis():
    """Execute complete Milestone 3 analysis pipeline."""
    
    print("="*70)
    print("RWF ECONOMIC IMPACT MODEL - MILESTONE 3")
    print("Sensitivity Analysis & Break-Even Analysis")
    print("="*70)
    
    # Initialize components
    one_way = OneWaySensitivity()
    two_way = TwoWaySensitivity()
    mc = MonteCarloAnalysis(n_simulations=N_SIMULATIONS)
    breakeven = BreakEvenAnalyzer()
    bounds = ScenarioBounds()
    viz = Visualizer()
    
    results = {}
    
    # -------------------------
    # Task 1-4: One-Way Sensitivity
    # -------------------------
    print("\n[1/8] One-way sensitivity: Initial premium (π₀)...")
    df_pi0 = one_way.sweep_initial_premium()
    df_pi0.to_csv(f"{OUTPUT_DIR}/sensitivity_pi0.csv", index=False)
    results['pi0'] = df_pi0
    
    print("[2/8] One-way sensitivity: Half-life (h)...")
    df_halflife = one_way.sweep_halflife()
    df_halflife.to_csv(f"{OUTPUT_DIR}/sensitivity_halflife.csv", index=False)
    results['halflife'] = df_halflife
    
    print("[3/8] One-way sensitivity: Formal entry probability...")
    df_formal = one_way.sweep_formal_entry()
    df_formal.to_csv(f"{OUTPUT_DIR}/sensitivity_formal_entry.csv", index=False)
    results['formal_entry'] = df_formal
    
    print("[4/8] One-way sensitivity: Test score effect...")
    df_testscore = one_way.sweep_test_score()
    df_testscore.to_csv(f"{OUTPUT_DIR}/sensitivity_test_score.csv", index=False)
    results['test_score'] = df_testscore
    
    # -------------------------
    # Task 5: Two-Way Sensitivity
    # -------------------------
    print("[5/8] Two-way sensitivity heatmaps...")
    heatmaps_pi0_h = two_way.heatmap_pi0_halflife()
    for scenario, df in heatmaps_pi0_h.items():
        df.to_csv(f"{HEATMAP_DIR}/heatmap_pi0_h_{scenario}.csv")
        viz.heatmap(df, f"π₀ × Half-life: {scenario}", 
                   f"{HEATMAP_DIR}/heatmap_pi0_h_{scenario}.png")
    
    heatmaps_formal_mincer = two_way.heatmap_formal_mincer()
    for scenario, df in heatmaps_formal_mincer.items():
        df.to_csv(f"{HEATMAP_DIR}/heatmap_formal_mincer_{scenario}.csv")
        viz.heatmap(df, f"P(Formal) × Mincer: {scenario}",
                   f"{HEATMAP_DIR}/heatmap_formal_mincer_{scenario}.png")
    
    # -------------------------
    # Task 6: Monte Carlo
    # -------------------------
    print("[6/8] Monte Carlo simulation...")
    mc_results = mc.run()
    mc_results.to_csv(f"{OUTPUT_DIR}/monte_carlo_full_results.csv", index=False)
    
    mc_summary = mc.summarize()
    mc_summary.to_csv(f"{OUTPUT_DIR}/monte_carlo_distributions.csv", index=False)
    results['mc_summary'] = mc_summary
    
    # -------------------------
    # Task 7: Scenario Bounds
    # -------------------------
    print("[7/8] Scenario bounds (pessimistic/baseline/optimistic)...")
    scenario_bounds_df = bounds.calculate_bounds()
    scenario_bounds_df.to_csv(f"{OUTPUT_DIR}/scenario_bounds.csv", index=False)
    results['scenario_bounds'] = scenario_bounds_df
    
    # -------------------------
    # Task 8: Break-Even Analysis
    # -------------------------
    print("[8/8] Break-even analysis...")
    breakeven_baseline = breakeven.calculate_baseline_breakeven()
    breakeven_baseline.to_csv(f"{OUTPUT_DIR}/breakeven_analysis_32scenarios.csv", index=False)
    results['breakeven'] = breakeven_baseline
    
    breakeven_mc = breakeven.calculate_monte_carlo_breakeven(mc_summary)
    breakeven_mc.to_csv(f"{OUTPUT_DIR}/breakeven_monte_carlo.csv", index=False)
    
    regional_comparison = breakeven.regional_comparison(breakeven_baseline)
    regional_comparison.to_csv(f"{OUTPUT_DIR}/breakeven_comparison_by_region.csv", index=False)
    
    # -------------------------
    # Visualizations
    # -------------------------
    print("\nGenerating visualizations...")
    
    viz.tornado_diagram(one_way.results, "rte_west_male_urban")
    viz.halflife_lineplot(df_halflife)
    viz.monte_carlo_distribution(mc_results, "rte_west_male_urban")
    viz.monte_carlo_distribution(mc_results, "apprenticeship_west_male_urban",
                                f"{VIZ_DIR}/monte_carlo_distribution_app.png")
    viz.breakeven_bar_chart(breakeven_baseline)
    viz.regional_boxplot(mc_results)
    
    # -------------------------
    # Narrative Report
    # -------------------------
    print("\nGenerating narrative report...")
    generate_narrative(breakeven_baseline, mc_summary, scenario_bounds_df)
    
    # -------------------------
    # Summary
    # -------------------------
    print("\n" + "="*70)
    print("MILESTONE 3 COMPLETE")
    print("="*70)
    print(f"\nOutputs saved to: {OUTPUT_DIR}/")
    print("\nDeliverables:")
    print("  ✓ sensitivity_pi0.csv")
    print("  ✓ sensitivity_halflife.csv")
    print("  ✓ sensitivity_formal_entry.csv")
    print("  ✓ sensitivity_test_score.csv")
    print("  ✓ sensitivity_heatmaps/ (4 heatmaps)")
    print("  ✓ monte_carlo_distributions.csv")
    print("  ✓ monte_carlo_full_results.csv")
    print("  ✓ scenario_bounds.csv")
    print("  ✓ breakeven_analysis_32scenarios.csv")
    print("  ✓ breakeven_comparison_by_region.csv")
    print("  ✓ visualizations/ (6 plots)")
    print("  ✓ sensitivity_analysis_narrative.md")
    
    # Print key findings
    print("\n" + "-"*70)
    print("KEY FINDINGS")
    print("-"*70)
    
    # Average break-even by intervention
    avg_be_rte = breakeven_baseline[breakeven_baseline['intervention'] == 'rte']['max_cost_bcr3'].mean()
    avg_be_app = breakeven_baseline[breakeven_baseline['intervention'] == 'apprenticeship']['max_cost_bcr3'].mean()
    
    print(f"\nAverage Max Cost at BCR=3:")
    print(f"  RTE: ₹{avg_be_rte/1e5:.1f} Lakhs per beneficiary")
    print(f"  Apprenticeship: ₹{avg_be_app/1e5:.1f} Lakhs per beneficiary")
    
    print(f"\nMonte Carlo (n={N_SIMULATIONS}):")
    print(f"  RTE median LNPV: ₹{mc_summary[mc_summary['intervention']=='rte']['median'].mean()/1e5:.1f} Lakhs")
    print(f"  App median LNPV: ₹{mc_summary[mc_summary['intervention']=='apprenticeship']['median'].mean()/1e5:.1f} Lakhs")
    
    return results


if __name__ == "__main__":
    results = run_milestone3_analysis()
