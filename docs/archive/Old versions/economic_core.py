
"""
Core Economic Model Functions

This module implements:
- Mincer wage equations
- Employment trajectory calculations (p_t^T and p_t^C)
- Wage growth with premium persistence (exponential decay)
- Lifetime NPV calculations with discounting
- Sector transition dynamics
- Incremental benefit calculations
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from .parameter_registry import ParameterRegistry, PARAMS


@dataclass
class WageProfile:
    """Stores wage trajectory over lifetime"""
    ages: np.ndarray
    wages: np.ndarray
    employment_prob: np.ndarray
    sector: str  # 'formal' or 'informal'
    
    def expected_wages(self) -> np.ndarray:
        """Return expected wages (wage * employment probability)"""
        return self.wages * self.employment_prob


class MincerWageModel:
    """
    Implements Mincer earnings function with sector-specific returns
    
    Formula: ln(wage) = β₀ + β₁*schooling + β₂*experience + β₃*experience²
    
    Adjusted for:
    - Sector (formal vs informal)
    - Gender
    - Urban/rural location
    - State-level variation
    """
    
    def __init__(self, params: ParameterRegistry = PARAMS):
        self.params = params
    
    def calculate_wage(
        self,
        base_wage: float,
        years_schooling: float,
        experience: float,
        sector: str = 'formal',
        gender: str = 'male',
        location: str = 'urban',
        state_multiplier: float = 1.0
    ) -> float:
        """
        Calculate wage using Mincer equation with adjustments
        
        Args:
            base_wage: Baseline wage for reference individual
            years_schooling: Years of education
            experience: Years of work experience
            sector: 'formal' or 'informal'
            gender: 'male' or 'female'
            location: 'urban' or 'rural'
            state_multiplier: State-level wage adjustment
            
        Returns:
            Calculated wage
        """
        # Select appropriate Mincer return
        if sector == 'formal':
            mincer_return = self.params.mincer_return_formal.value
        else:
            mincer_return = self.params.mincer_return_informal.value
        
        # Education effect (log-linear)
        education_premium = np.exp(mincer_return * years_schooling)
        
        # Experience effect (quadratic - inverted U shape)
        # Peak around 20-25 years experience
        exp_coef1 = 0.04  # Linear term
        exp_coef2 = -0.0008  # Quadratic term (negative for inverted U)
        experience_premium = np.exp(exp_coef1 * experience + exp_coef2 * experience**2)
        
        # Apply premiums/penalties
        wage = base_wage * education_premium * experience_premium
        
        # Gender adjustment
        if gender == 'female':
            wage *= self.params.gender_wage_gap.value
        
        # Location adjustment
        if location == 'rural':
            wage /= self.params.urban_rural_wage_premium.value
        
        # State-level adjustment
        wage *= state_multiplier
        
        return wage
    
    def calculate_lifetime_wages(
        self,
        base_wage: float,
        years_schooling: float,
        entry_age: int,
        retirement_age: int,
        sector: str = 'formal',
        gender: str = 'male',
        location: str = 'urban',
        state_multiplier: float = 1.0,
        real_wage_growth: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate wage trajectory over lifetime
        
        Returns:
            (ages, wages) - Arrays of ages and corresponding wages
        """
        ages = np.arange(entry_age, retirement_age + 1)
        wages = np.zeros(len(ages))
        
        # Use sector-specific real wage growth if not provided
        if real_wage_growth is None:
            if sector == 'formal':
                real_wage_growth = self.params.real_wage_growth_formal.value
            else:
                real_wage_growth = self.params.real_wage_growth_informal.value
        
        for i, age in enumerate(ages):
            experience = age - entry_age
            
            # Base wage from Mincer
            wage = self.calculate_wage(
                base_wage, years_schooling, experience,
                sector, gender, location, state_multiplier
            )
            
            # Apply real wage growth
            wage *= (1 + real_wage_growth) ** experience
            
            wages[i] = wage
        
        return ages, wages


class EmploymentTrajectory:
    """
    Models employment probability over lifetime (p_t)
    
    Accounts for:
    - Labor force participation rate (LFPR)
    - Worker population ratio (WPR) / employment rate
    - Unemployment spells and shocks
    - Sector-specific dynamics
    """
    
    def __init__(self, params: ParameterRegistry = PARAMS):
        self.params = params
    
    def calculate_employment_probability(
        self,
        age: int,
        education_level: str,  # 'primary', 'secondary', 'graduate', 'diploma'
        gender: str = 'male',
        location: str = 'urban',
        sector: str = 'formal',
        has_training: bool = False
    ) -> float:
        """
        Calculate probability of being employed at given age
        
        p(employed) = p(in labor force) * p(employed | in labor force)
                   = LFPR * WPR
        """
        # LFPR by gender and location
        if gender == 'male':
            if location == 'urban':
                lfpr = self.params.lfpr_male_urban.value
            else:
                lfpr = self.params.lfpr_male_rural.value
        else:
            if location == 'urban':
                lfpr = self.params.lfpr_female_urban.value
            else:
                lfpr = self.params.lfpr_female_rural.value
        
        # WPR by education
        if education_level in ['graduate', 'diploma']:
            if education_level == 'diploma' or has_training:
                wpr = self.params.wpr_diploma.value
            else:
                wpr = self.params.wpr_graduate.value
        else:
            # Lower education - lower WPR, especially in formal sector
            wpr = 0.50 if sector == 'formal' else 0.70
        
        # Youth face higher unemployment
        if age < 25:
            youth_penalty = 0.85  # 15% lower employment
        else:
            youth_penalty = 1.0
        
        # Employment probability
        employment_prob = lfpr * wpr * youth_penalty
        
        # Cap at reasonable maximum
        return min(employment_prob, 0.95)
    
    def calculate_trajectory(
        self,
        ages: np.ndarray,
        education_level: str,
        gender: str = 'male',
        location: str = 'urban',
        sector: str = 'formal',
        has_training: bool = False,
        unemployment_shock_year: Optional[int] = None
    ) -> np.ndarray:
        """
        Calculate employment probability trajectory over ages
        
        Args:
            unemployment_shock_year: Year when major shock occurs (if any)
        """
        employment_prob = np.zeros(len(ages))
        
        for i, age in enumerate(ages):
            prob = self.calculate_employment_probability(
                age, education_level, gender, location, sector, has_training
            )
            
            # Apply shock if in shock year
            if unemployment_shock_year is not None and age == unemployment_shock_year:
                shock_magnitude = self.params.unemployment_shock_magnitude.value
                prob *= (1 - shock_magnitude)  # Reduce employment by shock amount
            
            employment_prob[i] = prob
        
        return employment_prob


class PremiumPersistence:
    """
    Models exponential decay of wage premiums over time
    
    Initial gains from intervention may diminish as:
    - Skills depreciate
    - Labor market converges
    - Baseline group catches up
    """
    
    @staticmethod
    def apply_decay(
        initial_premium: float,
        years_since_treatment: np.ndarray,
        decay_rate: float
    ) -> np.ndarray:
        """
        Apply exponential decay to premium
        
        Premium(t) = Initial_Premium * exp(-decay_rate * t)
        
        Args:
            initial_premium: Premium at t=0 (percentage, e.g., 0.20 for 20%)
            years_since_treatment: Array of years since intervention
            decay_rate: Annual decay rate (e.g., 0.02 for 2% decay)
            
        Returns:
            Array of premiums over time
        """
        return initial_premium * np.exp(-decay_rate * years_since_treatment)
    
    @staticmethod
    def apply_partial_persistence(
        initial_premium: float,
        years_since_treatment: np.ndarray,
        persistence_rate: float
    ) -> np.ndarray:
        """
        Apply persistent premium (percentage that remains)
        
        Premium(t) = Initial_Premium * persistence_rate for t > threshold
        
        Args:
            persistence_rate: Fraction of premium that persists (e.g., 0.70)
        """
        # Decay to persistence level over first 10 years, then stable
        premium = np.zeros_like(years_since_treatment, dtype=float)
        for i, years in enumerate(years_since_treatment):
            if years <= 10:
                # Linear decay to persistence level
                premium[i] = initial_premium - (initial_premium * (1 - persistence_rate) * years / 10)
            else:
                # Stable at persistence level
                premium[i] = initial_premium * persistence_rate
        return premium


class NPVCalculator:
    """
    Net Present Value calculations for lifetime benefits
    
    Implements discounting, real vs nominal adjustments,
    and incremental benefit calculations
    """
    
    def __init__(self, params: ParameterRegistry = PARAMS):
        self.params = params
    
    def discount_factor(self, years: np.ndarray, rate: Optional[float] = None) -> np.ndarray:
        """
        Calculate discount factor: 1 / (1 + r)^t
        
        Args:
            years: Years into future
            rate: Discount rate (uses default if None)
        """
        if rate is None:
            rate = self.params.social_discount_rate.value
        return 1.0 / np.power(1 + rate, years)
    
    def calculate_present_value(
        self,
        cash_flows: np.ndarray,
        years: np.ndarray,
        discount_rate: Optional[float] = None
    ) -> float:
        """
        Calculate present value of cash flow stream
        
        PV = Σ(CF_t / (1+r)^t)
        """
        df = self.discount_factor(years, discount_rate)
        return np.sum(cash_flows * df)
    
    def calculate_lifetime_npv(
        self,
        treatment_profile: WageProfile,
        control_profile: WageProfile,
        discount_rate: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate lifetime NPV comparing treatment vs control
        
        Returns dict with:
        - treatment_pv: PV of treatment group earnings
        - control_pv: PV of control group earnings
        - incremental_npv: Difference (treatment - control)
        - benefit_cost_ratio: Ratio of incremental benefit to cost
        """
        # Ensure same age range
        assert len(treatment_profile.ages) == len(control_profile.ages)
        
        # Years from present (assuming entry age is year 0)
        years = treatment_profile.ages - treatment_profile.ages[0]
        
        # Expected earnings (wage * employment probability)
        treatment_earnings = treatment_profile.expected_wages()
        control_earnings = control_profile.expected_wages()
        
        # Calculate PVs
        treatment_pv = self.calculate_present_value(treatment_earnings, years, discount_rate)
        control_pv = self.calculate_present_value(control_earnings, years, discount_rate)
        
        # Incremental benefit
        incremental_npv = treatment_pv - control_pv
        
        # Benefit-cost ratio (if control is positive)
        bcr = treatment_pv / control_pv if control_pv > 0 else np.inf
        
        return {
            'treatment_pv': treatment_pv,
            'control_pv': control_pv,
            'incremental_npv': incremental_npv,
            'benefit_cost_ratio': bcr,
            'annual_increment': incremental_npv / len(years)
        }
    
    def calculate_incremental_earnings(
        self,
        treatment_profile: WageProfile,
        control_profile: WageProfile
    ) -> np.ndarray:
        """Calculate year-by-year incremental earnings"""
        return treatment_profile.expected_wages() - control_profile.expected_wages()
    
    def calculate_waterfall_contributions(
        self,
        base_npv: float,
        components: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate waterfall chart components
        
        Args:
            base_npv: Starting NPV
            components: Dict of {component_name: contribution_value}
            
        Returns:
            Dict with cumulative values for waterfall visualization
        """
        waterfall = {}
        cumulative = base_npv
        
        for component, value in components.items():
            waterfall[component] = {
                'value': value,
                'cumulative': cumulative + value
            }
            cumulative += value
        
        return waterfall


class SectorTransition:
    """
    Models transitions between informal and formal sectors
    
    Uses transition matrices and probability calculations
    """
    
    @staticmethod
    def create_transition_matrix(
        p_informal_to_formal: float,
        p_formal_to_informal: float
    ) -> np.ndarray:
        """
        Create 2x2 transition matrix
        
        Matrix[i,j] = P(state j at t+1 | state i at t)
        
        States: [0: informal, 1: formal]
        """
        p_stay_informal = 1 - p_informal_to_formal
        p_stay_formal = 1 - p_formal_to_informal
        
        return np.array([
            [p_stay_informal, p_informal_to_formal],
            [p_formal_to_informal, p_stay_formal]
        ])
    
    @staticmethod
    def simulate_sector_trajectory(
        initial_sector: str,
        years: int,
        transition_matrix: np.ndarray,
        random_seed: Optional[int] = None
    ) -> List[str]:
        """
        Simulate sector transitions over time
        
        Returns:
            List of sectors by year
        """
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Map sectors to indices
        sector_map = {'informal': 0, 'formal': 1}
        reverse_map = {0: 'informal', 1: 'formal'}
        
        trajectory = [initial_sector]
        current_state = sector_map[initial_sector]
        
        for _ in range(years - 1):
            # Sample next state from transition probabilities
            next_state = np.random.choice([0, 1], p=transition_matrix[current_state])
            trajectory.append(reverse_map[next_state])
            current_state = next_state
        
        return trajectory
    
    @staticmethod
    def calculate_steady_state_probabilities(
        transition_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Calculate long-run steady-state sector probabilities
        
        Solves: π = π * P where π is steady state distribution
        """
        eigenvalues, eigenvectors = np.linalg.eig(transition_matrix.T)
        
        # Find eigenvector for eigenvalue = 1
        idx = np.argmax(np.abs(eigenvalues - 1.0) < 1e-8)
        steady_state = np.real(eigenvectors[:, idx])
        
        # Normalize to probabilities
        steady_state /= steady_state.sum()
        
        return steady_state


# Utility functions for common calculations

def calculate_equivalent_years_schooling(test_score_gain_sd: float) -> float:
    """
    Convert test score gain (in SDs) to equivalent years of schooling
    
    Args:
        test_score_gain_sd: Test score gain in standard deviations
        
    Returns:
        Equivalent years of schooling
    """
    conversion_factor = PARAMS.test_score_eyos_conversion.value
    return test_score_gain_sd * conversion_factor


def calculate_test_score_earnings_impact(
    test_score_gain_sd: float,
    base_wage: float
) -> float:
    """
    Calculate earnings impact from test score gain
    
    Args:
        test_score_gain_sd: Test score gain in SDs
        base_wage: Baseline wage
        
    Returns:
        Additional earnings from test score
    """
    elasticity = PARAMS.test_score_earnings_elasticity.value
    earnings_increase_pct = test_score_gain_sd * elasticity
    return base_wage * earnings_increase_pct


def apply_funnel_attrition(
    eligible_population: int,
    application_rate: float,
    selection_rate: float,
    completion_rate: float
) -> Tuple[int, int, int, int]:
    """
    Calculate population at each stage of program funnel
    
    Returns:
        (eligible, applicants, selected, completers)
    """
    applicants = int(eligible_population * application_rate)
    selected = int(applicants * selection_rate)
    completers = int(selected * completion_rate)
    
    return eligible_population, applicants, selected, completers


if __name__ == "__main__":
    # Test core functions
    print("Economic Core Functions - Test Suite")
    print("=" * 70)
    
    # Test Mincer model
    print("\n1. Mincer Wage Model Test")
    mincer = MincerWageModel()
    base_wage = 300000  # Rs 3 lakh
    
    wage_formal = mincer.calculate_wage(base_wage, years_schooling=12, experience=5, sector='formal')
    wage_informal = mincer.calculate_wage(base_wage, years_schooling=12, experience=5, sector='informal')
    
    print(f"   Base wage: Rs {base_wage:,.0f}")
    print(f"   Formal sector (12 yrs school, 5 yrs exp): Rs {wage_formal:,.0f}")
    print(f"   Informal sector (12 yrs school, 5 yrs exp): Rs {wage_informal:,.0f}")
    print(f"   Formal/Informal ratio: {wage_formal/wage_informal:.2f}x")
    
    # Test employment trajectory
    print("\n2. Employment Trajectory Test")
    emp_traj = EmploymentTrajectory()
    
    ages = np.arange(22, 62)
    emp_probs = emp_traj.calculate_trajectory(ages, 'graduate', 'male', 'urban', 'formal')
    
    print(f"   Age range: {ages[0]} to {ages[-1]}")
    print(f"   Avg employment probability: {emp_probs.mean():.2%}")
    print(f"   Employment prob at age 25: {emp_probs[3]:.2%}")
    print(f"   Employment prob at age 45: {emp_probs[23]:.2%}")
    
    # Test NPV calculation
    print("\n3. NPV Calculation Test")
    npv_calc = NPVCalculator()
    
    # Create simple profiles
    ages = np.arange(22, 62)
    years = ages - ages[0]
    
    treatment_wages = np.full(len(ages), 400000)  # Rs 4 lakh/year
    control_wages = np.full(len(ages), 300000)    # Rs 3 lakh/year
    emp_prob = np.full(len(ages), 0.85)
    
    treatment_profile = WageProfile(ages, treatment_wages, emp_prob, 'formal')
    control_profile = WageProfile(ages, control_wages, emp_prob, 'formal')
    
    results = npv_calc.calculate_lifetime_npv(treatment_profile, control_profile)
    
    print(f"   Treatment PV: Rs {results['treatment_pv']:,.0f}")
    print(f"   Control PV: Rs {results['control_pv']:,.0f}")
    print(f"   Incremental NPV: Rs {results['incremental_npv']:,.0f}")
    print(f"   Benefit-Cost Ratio: {results['benefit_cost_ratio']:.2f}")
    
    # Test premium decay
    print("\n4. Premium Persistence Test")
    years_array = np.arange(0, 30)
    
    decay_premium = PremiumPersistence.apply_decay(0.20, years_array, 0.02)
    persistent_premium = PremiumPersistence.apply_partial_persistence(0.20, years_array, 0.70)
    
    print(f"   Initial premium: 20%")
    print(f"   Decay model at year 10: {decay_premium[10]:.1%}")
    print(f"   Persistence model at year 10: {persistent_premium[10]:.1%}")
    print(f"   Decay model at year 25: {decay_premium[25]:.1%}")
    print(f"   Persistence model at year 25: {persistent_premium[25]:.1%}")
    
    print("\n" + "=" * 70)
    print("All tests completed successfully!")
