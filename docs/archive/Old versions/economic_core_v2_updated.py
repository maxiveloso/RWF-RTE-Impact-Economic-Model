"""
RightWalk Foundation Economic Impact Model - Core Engine v2.0
====

CORRECTED VERSION incorporating PLFS 2023-24 parameters from Milestone 2.

Key Changes from v1.0:
- Mincer returns: 8.6% â†’ 5.8% (â†“32%)
- Experience premium: 4% â†’ 0.885% (â†“78%)
- Real wage growth: 2-3% â†’ 0.01% (â†“98%)
- Full 32-scenario structure (2 interventions Ã— 4 regions Ã— 4 demographics)
- Monte Carlo simulation support for sensitivity analysis

UPDATES in v2.0 (Gap Analysis Implementation):
- Fixed RTE P(Formal) dead code assignment (Section 4.1)
- Clarified apprentice premium calculation and normalization (Section 4.2)
- Documented apprenticeship P(Formal) uniform assumption (Section 4.3)
- Added regional adjustments to counterfactual P(Formal) (Section 4.4)

Author: RWF Economic Impact Analysis Team
Version: 2.0 (November 2024)
Status: APPROVED FOR IMPLEMENTATION
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import warnings


# ====
# SECTION 1: ENUMERATIONS AND TYPE DEFINITIONS
# ====

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"


class Location(Enum):
    URBAN = "urban"
    RURAL = "rural"


class Sector(Enum):
    FORMAL = "formal"
    INFORMAL = "informal"


class Region(Enum):
    NORTH = "north"   # UP, Bihar, Punjab, Haryana, Delhi
    SOUTH = "south"   # TN, Karnataka, AP, Telangana, Kerala
    WEST = "west"    # Maharashtra, Gujarat, Goa, Rajasthan
    EAST = "east"    # WB, Odisha, Jharkhand, Chhattisgarh


class Intervention(Enum):
    RTE = "rte"    # Right to Education 25% reservation
    APPRENTICESHIP = "apprenticeship"  # National Apprenticeship Training Scheme


class EducationLevel(Enum):
    PRIMARY = 5    # 5 years
    SECONDARY = 10    # 10 years
    HIGHER_SECONDARY = 12 # 12 years
    TERTIARY = 16    # 16 years


class DecayFunction(Enum):
    NONE = "none"    # No decay (h = infinity)
    EXPONENTIAL = "exponential" # Exponential decay with half-life
    LINEAR = "linear"    # Linear decay to zero


# ====
# SECTION 2: PARAMETER REGISTRY (Updated with PLFS 2023-24)
# ====

@dataclass
class Parameter:
    """Single parameter with metadata for Monte Carlo sampling."""
    value: float
    min_val: float
    max_val: float
    tier: int  # 1 = highest uncertainty, 3 = most reliable
    source: str
    unit: str = ""
    description: str = ""
    
    def sample(self, distribution: str = "uniform") -> float:
        """Sample from uncertainty distribution for Monte Carlo."""
        if distribution == "uniform":
            return np.random.uniform(self.min_val, self.max_val)
        elif distribution == "triangular":
            return np.random.triangular(self.min_val, self.value, self.max_val)
        elif distribution == "normal":
            std = (self.max_val - self.min_val) / 4  # 95% within range
            return np.clip(np.random.normal(self.value, std), 
                          self.min_val, self.max_val)
        else:
            return self.value


@dataclass
class ParameterRegistry:
    """
    Centralized parameter registry with PLFS 2023-24 values.
    
    CRITICAL: These values supersede ALL previous specifications.
    Source: RWF_Parameter_Update_Nov2024.md
    """
    
    # ----
    # CORE MINCER EQUATION PARAMETERS (UPDATED)
    # ----
    
    # Mincer return to education (per year of schooling)
    # OLD: 8.6%, NEW: 5.8% (â†“32%)
    MINCER_RETURN_HS: Parameter = field(default_factory=lambda: Parameter(
        value=0.058,
        min_val=0.050,
        max_val=0.065,
        tier=2,
        source="PLFS 2023-24 wage differentials",
        unit="%/year",
        description="Return to higher secondary education per year"
    ))
    
    # Experience premium (linear term)
    # OLD: 4-6%, NEW: 0.885% (â†“78%)
    EXPERIENCE_LINEAR: Parameter = field(default_factory=lambda: Parameter(
        value=0.00885,
        min_val=0.005,
        max_val=0.015,
        tier=3,
        source="PLFS 2023-24 age-wage profiles",
        unit="%/year",
        description="Linear experience premium coefficient"
    ))
    
    # Experience premium (quadratic term)
    # OLD: -0.1%, NEW: -0.0123% (â†‘88% less negative)
    EXPERIENCE_QUAD: Parameter = field(default_factory=lambda: Parameter(
        value=-0.000123,
        min_val=-0.0003,
        max_val=-0.00005,
        tier=3,
        source="PLFS 2023-24 age-wage profiles",
        unit="%/yearÂ²",
        description="Quadratic experience coefficient (diminishing returns)"
    ))
    
    # Formal sector wage multiplier
    FORMAL_MULTIPLIER: Parameter = field(default_factory=lambda: Parameter(
        value=2.25,
        min_val=2.0,
        max_val=2.5,
        tier=3,
        source="Literature: formal-informal wage differentials",
        unit="Ã—",
        description="Wage premium for formal vs informal sector"
    ))
    
    # Real wage growth rate
    # OLD: 2-3%, NEW: 0.01% (â†“98%)
    REAL_WAGE_GROWTH: Parameter = field(default_factory=lambda: Parameter(
        value=0.0001,
        min_val=-0.005,
        max_val=0.005,
        tier=2,
        source="PLFS 2020-24 wage stagnation",
        unit="%/year",
        description="Annual real wage growth rate"
    ))
    
    # ----
    # FORMAL SECTOR ENTRY PROBABILITIES (TIER 1 - HIGHEST UNCERTAINTY)
    # ----
    
    P_FORMAL_HIGHER_SECONDARY: Parameter = field(default_factory=lambda: Parameter(
        value=0.20,
        min_val=0.15,
        max_val=0.25,
        tier=1,
        source="PLFS aggregate estimates",
        unit="%",
        description="P(Formal | Higher Secondary completion)"
    ))
    
    P_FORMAL_SECONDARY: Parameter = field(default_factory=lambda: Parameter(
        value=0.11,
        min_val=0.08,
        max_val=0.14,
        tier=1,
        source="PLFS aggregate estimates",
        unit="%",
        description="P(Formal | Secondary completion)"
    ))
    
    P_FORMAL_APPRENTICE: Parameter = field(default_factory=lambda: Parameter(
        value=0.72,
        min_val=0.50,
        max_val=0.90,
        tier=1,
        source="RWF placement data (validated Nov 2024)",
        unit="%",
        description="P(Formal | Apprenticeship completion) - RWF actual data"
    ))
    
    P_FORMAL_NO_TRAINING: Parameter = field(default_factory=lambda: Parameter(
        value=0.10,
        min_val=0.05,
        max_val=0.15,
        tier=1,
        source="PLFS aggregate estimates",
        unit="%",
        description="P(Formal | No formal training)"
    ))
    
    # ----
    # INTERVENTION-SPECIFIC PARAMETERS
    # ----
    
    # RTE parameters
    RTE_TEST_SCORE_GAIN: Parameter = field(default_factory=lambda: Parameter(
        value=0.23,
        min_val=0.15,
        max_val=0.30,
        tier=1,
        source="NBER RCT (Muralidharan & Sundararaman)",
        unit="SD",
        description="Test score improvement from private school (std dev)"
    ))
    
    TEST_SCORE_TO_YEARS: Parameter = field(default_factory=lambda: Parameter(
        value=4.7,
        min_val=4.0,
        max_val=6.5,
        tier=2,
        source="World Bank LMIC pooled estimates",
        unit="years/SD",
        description="Equivalent years of schooling per SD test gain"
    ))
    
    RTE_INITIAL_PREMIUM: Parameter = field(default_factory=lambda: Parameter(
        value=98000,
        min_val=80000,
        max_val=120000,
        tier=1,
        source="Calculated from wage differentials",
        unit="INR/year",
        description="Initial annual wage premium for RTE beneficiary"
    ))
    
    # Apprenticeship parameters
    VOCATIONAL_PREMIUM: Parameter = field(default_factory=lambda: Parameter(
        value=0.047,
        min_val=0.03,
        max_val=0.06,
        tier=2,
        source="NSSO vocational training studies",
        unit="%",
        description="Wage premium for vocational training"
    ))
    
    # UPDATED: Expanded range to [50k, 120k] per Gap Analysis Section 4.2
    APPRENTICE_INITIAL_PREMIUM: Parameter = field(default_factory=lambda: Parameter(
        value=84000,
        min_val=50000,   # Conservative lower bound
        max_val=120000,  # Optimistic upper bound
        tier=1,
        source="Calculated from placement data; conservative estimate (see Gap Analysis 4.2)",
        unit="INR/year",
        description="Initial annual wage premium for apprentice. "
                    "NOTE: Back-of-envelope calculation gives ~â‚¹235k/year, but we use "
                    "conservative â‚¹84k for modeling. Sensitivity range: [â‚¹50k, â‚¹120k]."
    ))
    
    APPRENTICE_DECAY_HALFLIFE: Parameter = field(default_factory=lambda: Parameter(
        value=10,
        min_val=5,
        max_val=50,  # Capped at 50 years for Monte Carlo (effectively no decay)
        tier=1,
        source="Assumed - no India-specific data",
        unit="years",
        description="Half-life of apprenticeship wage premium decay"
    ))
    
    # ----
    # MACROECONOMIC PARAMETERS
    # ----
    
    SOCIAL_DISCOUNT_RATE: Parameter = field(default_factory=lambda: Parameter(
        value=0.0372,
        min_val=0.03,
        max_val=0.08,
        tier=3,
        source="Murty et al. (2024) NABARD working paper",
        unit="%/year",
        description="Social discount rate for NPV calculations"
    ))
    
    WORKING_LIFE_FORMAL: Parameter = field(default_factory=lambda: Parameter(
        value=40,
        min_val=38,
        max_val=42,
        tier=3,
        source="Standard retirement age assumptions",
        unit="years",
        description="Working life duration for formal sector (age 22-62)"
    ))
    
    WORKING_LIFE_INFORMAL: Parameter = field(default_factory=lambda: Parameter(
        value=47,
        min_val=45,
        max_val=50,
        tier=3,
        source="Extended working life in informal sector",
        unit="years",
        description="Working life duration for informal sector (age 18-65+)"
    ))
    
    LABOR_MARKET_ENTRY_AGE: Parameter = field(default_factory=lambda: Parameter(
        value=22,
        min_val=18,
        max_val=25,
        tier=3,
        source="Post-higher secondary entry",
        unit="years",
        description="Typical labor market entry age"
    ))


# ====
# SECTION 3: BASELINE WAGE DATA (PLFS 2023-24)
# ====

@dataclass
class BaselineWages:
    """
    Baseline monthly wages in INR from PLFS 2023-24 Table 21.
    
    Structure: wages[location][gender][education_level]
    All values in INR per month.
    """
    
    # Urban wages
    urban_male_secondary: float = 26105
    urban_male_higher_secondary: float = 32800
    urban_male_casual: float = 13425
    
    urban_female_secondary: float = 19879
    urban_female_higher_secondary: float = 24928
    urban_female_casual: float = 9129
    
    # Rural wages
    rural_male_secondary: float = 18200
    rural_male_higher_secondary: float = 22880
    rural_male_casual: float = 11100
    
    rural_female_secondary: float = 12396
    rural_female_higher_secondary: float = 15558
    rural_female_casual: float = 7475
    
    def get_wage(self, location: Location, gender: Gender, 
                 education: EducationLevel, sector: Sector) -> float:
        """
        Get baseline monthly wage for given demographic.
        
        For informal sector, returns casual wage.
        For formal sector, returns education-appropriate salaried wage.
        """
        prefix = f"{location.value}_{gender.value}"
        
        if sector == Sector.INFORMAL:
            return getattr(self, f"{prefix}_casual")
        
        if education.value >= EducationLevel.HIGHER_SECONDARY.value:
            return getattr(self, f"{prefix}_higher_secondary")
        else:
            return getattr(self, f"{prefix}_secondary")
    
    def get_wage_nested(self) -> Dict:
        """Return nested dictionary format for programmatic access."""
        return {
            Location.URBAN: {
                Gender.MALE: {
                    EducationLevel.SECONDARY: self.urban_male_secondary,
                    EducationLevel.HIGHER_SECONDARY: self.urban_male_higher_secondary,
                    'casual': self.urban_male_casual
                },
                Gender.FEMALE: {
                    EducationLevel.SECONDARY: self.urban_female_secondary,
                    EducationLevel.HIGHER_SECONDARY: self.urban_female_higher_secondary,
                    'casual': self.urban_female_casual
                }
            },
            Location.RURAL: {
                Gender.MALE: {
                    EducationLevel.SECONDARY: self.rural_male_secondary,
                    EducationLevel.HIGHER_SECONDARY: self.rural_male_higher_secondary,
                    'casual': self.rural_male_casual
                },
                Gender.FEMALE: {
                    EducationLevel.SECONDARY: self.rural_female_secondary,
                    EducationLevel.HIGHER_SECONDARY: self.rural_female_higher_secondary,
                    'casual': self.rural_female_casual
                }
            }
        }


# ====
# SECTION 4: REGIONAL ADJUSTMENTS
# ====

@dataclass
class RegionalParameters:
    """
    Region-specific parameter adjustments.
    
    From RWF_Parameter_Update_Nov2024.md Section 2.3.
    
    UPDATED: Added p_formal_control_multipliers for Gap Analysis Section 4.4.
    """
    
    # Regional Mincer return multipliers (relative to national 5.8%)
    mincer_multipliers: Dict[Region, float] = field(default_factory=lambda: {
        Region.NORTH: 0.914,  # 5.3% / 5.8%
        Region.SOUTH: 1.069,  # 6.2% / 5.8%
        Region.WEST: 1.000,   # 5.8% / 5.8%
        Region.EAST: 0.879,   # 5.1% / 5.8%
    })
    
    # Regional P(Formal | Higher Secondary)
    p_formal_hs: Dict[Region, float] = field(default_factory=lambda: {
        Region.NORTH: 0.15,
        Region.SOUTH: 0.25,
        Region.WEST: 0.20,
        Region.EAST: 0.12,
    })
    
    # Regional wage premiums (additive)
    wage_premiums: Dict[Region, float] = field(default_factory=lambda: {
        Region.NORTH: -0.05,
        Region.SOUTH: 0.10,
        Region.WEST: 0.05,
        Region.EAST: -0.15,
    })
    
    # ADDED: Regional multipliers for control-group P(Formal) (Gap Analysis 4.4)
    # These adjust national-average P(Formal) values for counterfactual pathways
    # to reflect regional labor market conditions.
    p_formal_control_multipliers: Dict[Region, float] = field(default_factory=lambda: {
        Region.NORTH: 0.90,   # Slightly below national average
        Region.SOUTH: 1.20,   # Stronger formal sector
        Region.WEST: 1.00,    # At national average
        Region.EAST: 0.80,    # Weaker formal sector
    })
    
    def get_mincer_return(self, region: Region, base_return: float) -> float:
        """Get region-specific Mincer return."""
        return base_return * self.mincer_multipliers[region]
    
    def get_p_formal(self, region: Region) -> float:
        """Get region-specific P(Formal | HS)."""
        return self.p_formal_hs[region]
    
    def adjust_wage(self, base_wage: float, region: Region) -> float:
        """Apply regional wage premium."""
        return base_wage * (1 + self.wage_premiums[region])
    
    def adjust_p_formal_control(self, region: Region, base_p: float) -> float:
        """
        Adjust control-group P(Formal) using regional multiplier.
        
        This ensures counterfactual trajectories reflect regional labor market
        conditions, preventing overstatement of treatment effects in high-formal
        regions (e.g., South) and understatement in low-formal regions (e.g., East).
        
        Added per Gap Analysis Section 4.4.
        """
        return base_p * self.p_formal_control_multipliers[region]


# ====
# SECTION 5: COUNTERFACTUAL SCHOOLING DISTRIBUTION
# ====

@dataclass
class CounterfactualDistribution:
    """
    Schooling distribution for EWS children without RTE intervention.
    
    Updated from ASER 2023-24 data.
    
    NOTE (Gap Analysis 4.4): p_formal_government, p_formal_low_fee_private, 
    and p_formal_dropout are national averages. In the updated implementation,
    these values are adjusted by region-specific multipliers in 
    RegionalParameters.adjust_p_formal_control() to reflect local labor market
    conditions. Without this adjustment, treatment effects would be overstated
    in high-formal regions (e.g., South: 0.12 â†’ 0.14) and understated in 
    low-formal regions (e.g., East: 0.12 â†’ 0.10).
    """
    
    p_government_school: float = 0.668   # 66.8%
    p_low_fee_private: float = 0.306    # 30.6%
    p_dropout: float = 0.026    # 2.6%
    
    # P(Formal) for each counterfactual pathway (national averages)
    p_formal_government: float = 0.12    # Assumes secondary completion
    p_formal_low_fee_private: float = 0.15
    p_formal_dropout: float = 0.05
    
    def validate(self) -> bool:
        """Ensure probabilities sum to 1."""
        total = self.p_government_school + self.p_low_fee_private + self.p_dropout
        return abs(total - 1.0) < 0.001
    
    def get_weighted_p_formal(self, region: Region = None, 
                             regional_params: RegionalParameters = None) -> float:
        """
        Calculate weighted average P(Formal) for control group.
        
        If region and regional_params are provided, applies regional adjustment.
        Otherwise returns national average.
        """
        if region is not None and regional_params is not None:
            p_formal_govt = regional_params.adjust_p_formal_control(
                region, self.p_formal_government
            )
            p_formal_lfp = regional_params.adjust_p_formal_control(
                region, self.p_formal_low_fee_private
            )
            p_formal_dropout = regional_params.adjust_p_formal_control(
                region, self.p_formal_dropout
            )
        else:
            p_formal_govt = self.p_formal_government
            p_formal_lfp = self.p_formal_low_fee_private
            p_formal_dropout = self.p_formal_dropout
        
        return (
            self.p_government_school * p_formal_govt +
            self.p_low_fee_private * p_formal_lfp +
            self.p_dropout * p_formal_dropout
        )


# ====
# SECTION 6: MINCER WAGE MODEL
# ====

class MincerWageModel:
    """
    Mincer earnings function implementation with PLFS 2023-24 parameters.
    
    Core equation:
    W_t = exp(Î²â‚€ + Î²â‚Ã—Education + Î²â‚‚Ã—Experience + Î²â‚ƒÃ—ExperienceÂ²) Ã— I(Formal) Ã— FM
    
    Where:
    - Î²â‚ = 0.058 (Mincer return)
    - Î²â‚‚ = 0.00885 (experience linear)
    - Î²â‚ƒ = -0.000123 (experience quadratic)
    - FM = 2.25 (formal sector multiplier)
    """
    
    def __init__(self, params: ParameterRegistry = None, 
                 baseline_wages: BaselineWages = None,
                 regional_params: RegionalParameters = None):
        self.params = params or ParameterRegistry()
        self.baseline_wages = baseline_wages or BaselineWages()
        self.regional = regional_params or RegionalParameters()
    
    def calculate_wage(
        self,
        years_schooling: float,
        experience: float,
        sector: Sector,
        gender: Gender,
        location: Location,
        region: Region = Region.WEST,
        additional_premium: float = 0.0
    ) -> float:
        """
        Calculate monthly wage using Mincer equation.
        
        Args:
            years_schooling: Years of education completed
            experience: Years of work experience
            sector: Formal or informal
            gender: Male or female
            location: Urban or rural
            region: Geographic region (North/South/East/West)
            additional_premium: Any intervention-specific premium (proportional)
        
        Returns:
            Monthly wage in INR
        """
        # Get region-adjusted Mincer return
        base_return = self.params.MINCER_RETURN_HS.value
        mincer_return = self.regional.get_mincer_return(region, base_return)
        
        # Get experience coefficients (CORRECTED VALUES)
        exp_coef1 = self.params.EXPERIENCE_LINEAR.value    # 0.00885
        exp_coef2 = self.params.EXPERIENCE_QUAD.value    # -0.000123
        
        # Education premium (relative to baseline education level of 12 years)
        education_years_diff = years_schooling - 12
        education_premium = np.exp(mincer_return * education_years_diff)
        
        # Experience premium (inverted U-shape)
        experience_premium = np.exp(exp_coef1 * experience + exp_coef2 * experience**2)
        
        # Get baseline wage for demographic
        education_level = (EducationLevel.HIGHER_SECONDARY 
                          if years_schooling >= 12 
                          else EducationLevel.SECONDARY)
        
        base_wage = self.baseline_wages.get_wage(
            location, gender, education_level, sector
        )
        
        # Apply regional adjustment
        base_wage = self.regional.adjust_wage(base_wage, region)
        
        # Apply formal sector multiplier if applicable
        if sector == Sector.FORMAL:
            formal_multiplier = self.params.FORMAL_MULTIPLIER.value  # 2.25Ã—
        else:
            formal_multiplier = 1.0
        
        # Calculate final wage
        wage = (base_wage * 
                education_premium * 
                experience_premium * 
                formal_multiplier * 
                (1 + additional_premium))
        
        return wage
    
    def generate_wage_trajectory(
        self,
        years_schooling: float,
        sector: Sector,
        gender: Gender,
        location: Location,
        region: Region = Region.WEST,
        working_years: int = 40,
        real_wage_growth: float = None,
        initial_premium: float = 0.0,
        premium_decay: DecayFunction = DecayFunction.NONE,
        decay_halflife: float = 10.0
    ) -> np.ndarray:
        """
        Generate complete wage trajectory over working life.
        
        Args:
            years_schooling: Years of education
            sector: Employment sector
            gender: Gender
            location: Urban/rural
            region: Geographic region
            working_years: Total years of work
            real_wage_growth: Annual real wage growth rate
            initial_premium: Initial intervention premium (proportion)
            premium_decay: How the premium decays over time
            decay_halflife: Half-life for exponential decay
        
        Returns:
            Array of annual wages (monthly Ã— 12)
        """
        if real_wage_growth is None:
            real_wage_growth = self.params.REAL_WAGE_GROWTH.value
        
        wages = np.zeros(working_years)
        
        for t in range(working_years):
            # Calculate decay factor for intervention premium
            if premium_decay == DecayFunction.NONE:
                decay_factor = 1.0
            elif premium_decay == DecayFunction.EXPONENTIAL:
                decay_factor = np.exp(-np.log(2) / decay_halflife * t)
            elif premium_decay == DecayFunction.LINEAR:
                decay_factor = max(0, 1 - t / (2 * decay_halflife))
            else:
                decay_factor = 1.0
            
            current_premium = initial_premium * decay_factor
            
            # Calculate monthly wage
            monthly_wage = self.calculate_wage(
                years_schooling=years_schooling,
                experience=t,
                sector=sector,
                gender=gender,
                location=location,
                region=region,
                additional_premium=current_premium
            )
            
            # Apply real wage growth
            monthly_wage *= (1 + real_wage_growth) ** t
            
            # Annual wage
            wages[t] = monthly_wage * 12
        
        return wages


# ====
# SECTION 7: EMPLOYMENT PROBABILITY MODEL
# ====

class EmploymentModel:
    """
    Model for employment probabilities including unemployment shocks.
    """
    
    def __init__(self, params: ParameterRegistry = None):
        self.params = params or ParameterRegistry()
        
        # Age-specific unemployment rates (approximate from PLFS)
        self.unemployment_by_age = {
            (18, 25): 0.15,   # Youth: 15%
            (26, 35): 0.05,   # Prime age: 5%
            (36, 55): 0.04,   # Mid-career: 4%
            (56, 65): 0.08,   # Near retirement: 8%
        }
    
    def get_unemployment_rate(self, age: int, education: EducationLevel) -> float:
        """
        Get unemployment rate for given age and education.
        
        Higher education slightly reduces unemployment.
        """
        base_rate = 0.05  # Default
        
        for (min_age, max_age), rate in self.unemployment_by_age.items():
            if min_age <= age <= max_age:
                base_rate = rate
                break
        
        # Education adjustment (modest effect)
        if education.value >= 12:
            base_rate *= 0.9  # 10% reduction for HS+
        
        return base_rate
    
    def get_employment_probability(self, age: int, 
                                   education: EducationLevel) -> float:
        """Get probability of being employed."""
        return 1 - self.get_unemployment_rate(age, education)
    
    def apply_unemployment_shock(
        self,
        wages: np.ndarray,
        entry_age: int = 22,
        education: EducationLevel = EducationLevel.HIGHER_SECONDARY
    ) -> np.ndarray:
        """
        Apply unemployment probability to wage trajectory.
        
        Returns expected earnings accounting for unemployment risk.
        """
        adjusted_wages = np.zeros_like(wages)
        
        for t, wage in enumerate(wages):
            age = entry_age + t
            p_employed = self.get_employment_probability(age, education)
            adjusted_wages[t] = wage * p_employed
        
        return adjusted_wages


# ====
# SECTION 8: SECTOR TRANSITION MODEL
# ====

class SectorTransitionModel:
    """
    Model for formal/informal sector transitions.
    
    Base case: Absorbing states (once in formal, stay formal).
    Sensitivity: Allow transition probabilities.
    """
    
    def __init__(self, absorbing: bool = True):
        self.absorbing = absorbing
        
        # Transition probabilities (if not absorbing)
        # P(Formal_t | Formal_{t-1})
        self.p_formal_stay = 0.95
        # P(Formal_t | Informal_{t-1})
        self.p_informal_to_formal = 0.03
    
    def simulate_sector_trajectory(
        self,
        initial_sector: Sector,
        years: int,
        seed: int = None
    ) -> List[Sector]:
        """
        Simulate sector trajectory over working life.
        
        If absorbing=True, returns initial sector for all years.
        If absorbing=False, simulates Markov transitions.
        """
        if seed is not None:
            np.random.seed(seed)
        
        trajectory = [initial_sector]
        
        if self.absorbing:
            return [initial_sector] * years
        
        for t in range(1, years):
            current = trajectory[-1]
            
            if current == Sector.FORMAL:
                next_sector = (Sector.FORMAL 
                             if np.random.random() < self.p_formal_stay 
                             else Sector.INFORMAL)
            else:
                next_sector = (Sector.FORMAL 
                             if np.random.random() < self.p_informal_to_formal 
                             else Sector.INFORMAL)
            
            trajectory.append(next_sector)
        
        return trajectory
    
    def get_expected_formal_years(
        self,
        initial_p_formal: float,
        total_years: int
    ) -> float:
        """
        Calculate expected years in formal sector.
        
        For absorbing states: E[formal years] = p_formal Ã— total_years
        """
        if self.absorbing:
            return initial_p_formal * total_years
        
        # For Markov model, would need to solve the transition dynamics
        # Simplified: approximate as absorbing for now
        return initial_p_formal * total_years


# ====
# SECTION 9: LIFETIME NPV CALCULATOR
# ====

class LifetimeNPVCalculator:
    """
    Calculate Lifetime Net Present Value (LNPV) of intervention effects.
    
    LNPV = Î£_{t=0}^{T} [E[Earnings_t]^Treatment - E[Earnings_t]^Control] / (1 + Î´)^t
    """
    
    def __init__(
        self,
        params: ParameterRegistry = None,
        wage_model: MincerWageModel = None,
        employment_model: EmploymentModel = None,
        sector_model: SectorTransitionModel = None,
        counterfactual: CounterfactualDistribution = None
    ):
        self.params = params or ParameterRegistry()
        self.wage_model = wage_model or MincerWageModel(self.params)
        self.employment_model = employment_model or EmploymentModel(self.params)
        self.sector_model = sector_model or SectorTransitionModel(absorbing=True)
        self.counterfactual = counterfactual or CounterfactualDistribution()
    
    def calculate_treatment_trajectory(
        self,
        intervention: Intervention,
        gender: Gender,
        location: Location,
        region: Region
    ) -> Tuple[np.ndarray, float]:
        """
        Calculate expected wage trajectory for treatment group.
        
        Returns:
            Tuple of (wage_trajectory, p_formal)
        """
        if intervention == Intervention.RTE:
            # FIXED (Gap Analysis 4.1): Use region-specific P(Formal | HS) directly.
            # Previous code had dead assignment to P_FORMAL_HIGHER_SECONDARY.value
            # which was immediately overwritten. Now we use only regional value.
            p_formal = self.wage_model.regional.get_p_formal(region)
            
            # RTE: Effective years of schooling increased by test score gains
            years_schooling = 12 + (self.params.RTE_TEST_SCORE_GAIN.value * 
                                   self.params.TEST_SCORE_TO_YEARS.value)
            initial_premium = 0  # Premium captured in education effect
            decay = DecayFunction.NONE
            halflife = float('inf')
            
        else:  # Apprenticeship
            # DOCUMENTED (Gap Analysis 4.3): P(Formal) for apprenticeship uses
            # national employer absorption rate (72% from RWF actual data) and does NOT 
            # apply regional adjustments. This reflects that placement is through specific 
            # employers (validated with RWF operational data) rather than general labor 
            # markets, so absorption rates are more uniform nationally.
            p_formal = self.params.P_FORMAL_APPRENTICE.value
            
            years_schooling = 12
            
            # CLARIFIED (Gap Analysis 4.2): Calculate relative premium.
            # We convert the annual apprentice premium (INR/year) into a proportional
            # uplift over a notional annual baseline of 12 months Ã— â‚¹20,000 = â‚¹240,000.
            # With registry value â‚¹84,000: 84,000 / 240,000 â‰ˆ 0.35 â‡’ ~35% initial premium.
            #
            # NOTE: Back-of-envelope calculation in documentation gives ~â‚¹235k/year
            # premium, but we intentionally use conservative â‚¹84k for modeling.
            # Sensitivity range [â‚¹50k, â‚¹120k] is captured in parameter min/max values.
            initial_premium = (self.params.APPRENTICE_INITIAL_PREMIUM.value / 
                              (12 * 20000))
            
            decay = DecayFunction.EXPONENTIAL
            halflife = self.params.APPRENTICE_DECAY_HALFLIFE.value
        
        working_years = int(self.params.WORKING_LIFE_FORMAL.value)
        
        # Generate trajectories for formal and informal pathways
        formal_wages = self.wage_model.generate_wage_trajectory(
            years_schooling=years_schooling,
            sector=Sector.FORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years,
            initial_premium=initial_premium,
            premium_decay=decay,
            decay_halflife=halflife
        )
        
        informal_wages = self.wage_model.generate_wage_trajectory(
            years_schooling=years_schooling,
            sector=Sector.INFORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years,
            initial_premium=0,  # No premium in informal
            premium_decay=DecayFunction.NONE
        )
        
        # Expected wages = weighted by sector probability
        expected_wages = p_formal * formal_wages + (1 - p_formal) * informal_wages
        
        # Apply unemployment probability
        expected_wages = self.employment_model.apply_unemployment_shock(
            expected_wages,
            entry_age=int(self.params.LABOR_MARKET_ENTRY_AGE.value)
        )
        
        return expected_wages, p_formal
    
    def calculate_control_trajectory(
        self,
        gender: Gender,
        location: Location,
        region: Region
    ) -> np.ndarray:
        """
        Calculate expected wage trajectory for control group.
        
        Uses counterfactual schooling distribution with regional P(Formal) adjustments.
        
        UPDATED (Gap Analysis 4.4): Now applies regional multipliers to control-group
        P(Formal) values to reflect local labor market conditions. This prevents
        overstatement of treatment effects in high-formal regions (e.g., South) and
        understatement in low-formal regions (e.g., East).
        """
        working_years = int(self.params.WORKING_LIFE_FORMAL.value)
        
        # Calculate weighted average across counterfactual pathways
        total_wages = np.zeros(working_years)
        
        # UPDATED: Apply regional adjustment to all control P(Formal) values
        # Government school pathway (national average: 0.12, region-adjusted)
        p_formal_govt = self.wage_model.regional.adjust_p_formal_control(
            region, self.counterfactual.p_formal_government
        )
        govt_formal = self.wage_model.generate_wage_trajectory(
            years_schooling=10,  # Secondary completion
            sector=Sector.FORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        govt_informal = self.wage_model.generate_wage_trajectory(
            years_schooling=10,
            sector=Sector.INFORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        govt_wages = p_formal_govt * govt_formal + (1 - p_formal_govt) * govt_informal
        total_wages += self.counterfactual.p_government_school * govt_wages
        
        # Low-fee private pathway (national average: 0.15, region-adjusted)
        p_formal_lfp = self.wage_model.regional.adjust_p_formal_control(
            region, self.counterfactual.p_formal_low_fee_private
        )
        lfp_formal = self.wage_model.generate_wage_trajectory(
            years_schooling=11,  # Partial HS
            sector=Sector.FORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        lfp_informal = self.wage_model.generate_wage_trajectory(
            years_schooling=11,
            sector=Sector.INFORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        lfp_wages = p_formal_lfp * lfp_formal + (1 - p_formal_lfp) * lfp_informal
        total_wages += self.counterfactual.p_low_fee_private * lfp_wages
        
        # Dropout pathway (national average: 0.05, region-adjusted)
        p_formal_dropout = self.wage_model.regional.adjust_p_formal_control(
            region, self.counterfactual.p_formal_dropout
        )
        dropout_formal = self.wage_model.generate_wage_trajectory(
            years_schooling=5,  # Primary only
            sector=Sector.FORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        dropout_informal = self.wage_model.generate_wage_trajectory(
            years_schooling=5,
            sector=Sector.INFORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )
        dropout_wages = (p_formal_dropout * dropout_formal + 
                        (1 - p_formal_dropout) * dropout_informal)
        total_wages += self.counterfactual.p_dropout * dropout_wages
        
        # Apply unemployment
        total_wages = self.employment_model.apply_unemployment_shock(
            total_wages,
            entry_age=int(self.params.LABOR_MARKET_ENTRY_AGE.value)
        )
        
        return total_wages
    
    def calculate_npv(
        self,
        wage_differential: np.ndarray,
        discount_rate: float = None
    ) -> float:
        """
        Calculate NPV of wage differential stream.
        
        NPV = Î£_{t=0}^{T} differential_t / (1 + Î´)^t
        """
        if discount_rate is None:
            discount_rate = self.params.SOCIAL_DISCOUNT_RATE.value
        
        npv = 0
        for t, diff in enumerate(wage_differential):
            npv += diff / ((1 + discount_rate) ** t)
        
        return npv
    
    def calculate_lnpv(
        self,
        intervention: Intervention,
        gender: Gender,
        location: Location,
        region: Region,
        discount_rate: float = None
    ) -> Dict:
        """
        Calculate complete LNPV for a single scenario.
        
        Returns dictionary with detailed results.
        """
        treatment_wages, p_formal_treatment = self.calculate_treatment_trajectory(
            intervention, gender, location, region
        )
        
        control_wages = self.calculate_control_trajectory(
            gender, location, region
        )
        
        wage_differential = treatment_wages - control_wages
        
        lnpv = self.calculate_npv(wage_differential, discount_rate)
        
        return {
            'intervention': intervention.value,
            'region': region.value,
            'gender': gender.value,
            'location': location.value,
            'lnpv': lnpv,
            'treatment_lifetime_earnings': treatment_wages.sum(),
            'control_lifetime_earnings': control_wages.sum(),
            'p_formal_treatment': p_formal_treatment,
            'annual_differential': wage_differential,
            'discount_rate': discount_rate or self.params.SOCIAL_DISCOUNT_RATE.value
        }
    
    def calculate_all_scenarios(self) -> List[Dict]:
        """
        Calculate LNPV for all 32 scenarios.
        
        2 interventions Ã— 4 regions Ã— 4 demographics = 32 scenarios
        """
        results = []
        
        for intervention in Intervention:
            for region in Region:
                for gender in Gender:
                    for location in Location:
                        result = self.calculate_lnpv(
                            intervention, gender, location, region
                        )
                        results.append(result)
        
        return results


# ====
# SECTION 10: MONTE CARLO SENSITIVITY ANALYSIS
# ====

class MonteCarloSimulator:
    """
    Monte Carlo simulation for sensitivity analysis.
    
    Samples from parameter uncertainty distributions and computes
    LNPV distribution to quantify model uncertainty.
    """
    
    def __init__(self, n_simulations: int = 1000, seed: int = 42):
        self.n_simulations = n_simulations
        self.seed = seed
    
    def sample_parameters(self, base_params: ParameterRegistry,
                         distribution: str = "triangular") -> ParameterRegistry:
        """
        Create parameter registry with sampled values.
        
        Only Tier 1 parameters are varied (highest uncertainty).
        """
        sampled = ParameterRegistry()
        
        # Sample Tier 1 parameters
        sampled.P_FORMAL_HIGHER_SECONDARY.value = \
            base_params.P_FORMAL_HIGHER_SECONDARY.sample(distribution)
        sampled.P_FORMAL_APPRENTICE.value = \
            base_params.P_FORMAL_APPRENTICE.sample(distribution)
        sampled.RTE_TEST_SCORE_GAIN.value = \
            base_params.RTE_TEST_SCORE_GAIN.sample(distribution)
        sampled.APPRENTICE_INITIAL_PREMIUM.value = \
            base_params.APPRENTICE_INITIAL_PREMIUM.sample(distribution)
        sampled.APPRENTICE_DECAY_HALFLIFE.value = \
            base_params.APPRENTICE_DECAY_HALFLIFE.sample(distribution)
        
        # Sample Tier 2 parameters with lower variance
        sampled.MINCER_RETURN_HS.value = \
            base_params.MINCER_RETURN_HS.sample(distribution)
        sampled.SOCIAL_DISCOUNT_RATE.value = \
            base_params.SOCIAL_DISCOUNT_RATE.sample(distribution)
        
        return sampled
    
    def run_simulation(
        self,
        intervention: Intervention,
        gender: Gender,
        location: Location,
        region: Region,
        base_params: ParameterRegistry = None
    ) -> Dict:
        """
        Run Monte Carlo simulation for single scenario.
        
        Returns distribution of LNPV estimates.
        """
        np.random.seed(self.seed)
        
        if base_params is None:
            base_params = ParameterRegistry()
        
        lnpv_samples = []
        
        for i in range(self.n_simulations):
            # Sample parameters
            sampled_params = self.sample_parameters(base_params)
            
            # Create calculator with sampled parameters
            calculator = LifetimeNPVCalculator(params=sampled_params)
            
            # Calculate LNPV
            result = calculator.calculate_lnpv(
                intervention, gender, location, region
            )
            
            lnpv_samples.append(result['lnpv'])
        
        lnpv_array = np.array(lnpv_samples)
        
        return {
            'intervention': intervention.value,
            'region': region.value,
            'gender': gender.value,
            'location': location.value,
            'mean': np.mean(lnpv_array),
            'median': np.median(lnpv_array),
            'std': np.std(lnpv_array),
            'p5': np.percentile(lnpv_array, 5),
            'p25': np.percentile(lnpv_array, 25),
            'p75': np.percentile(lnpv_array, 75),
            'p95': np.percentile(lnpv_array, 95),
            'samples': lnpv_array
        }


# ====
# SECTION 11: BENEFIT-COST RATIO CALCULATOR
# ====

class BenefitCostCalculator:
    """
    Calculate Benefit-Cost Ratios for interventions.
    
    BCR = LNPV / Program Cost per Beneficiary
    """
    
    def __init__(self, npv_calculator: LifetimeNPVCalculator = None):
        self.npv_calculator = npv_calculator or LifetimeNPVCalculator()
    
    def calculate_bcr(
        self,
        lnpv: float,
        cost_per_beneficiary: float
    ) -> float:
        """Calculate simple BCR."""
        if cost_per_beneficiary <= 0:
            raise ValueError("Cost must be positive")
        return lnpv / cost_per_beneficiary
    
    def evaluate_intervention(
        self,
        intervention: Intervention,
        cost_per_beneficiary: float,
        gender: Gender,
        location: Location,
        region: Region
    ) -> Dict:
        """
        Complete evaluation with BCR and decision.
        
        Decision rules:
        - BCR > 3: Highly cost-effective
        - BCR > 1: Cost-effective
        - BCR < 1: Not cost-effective
        """
        result = self.npv_calculator.calculate_lnpv(
            intervention, gender, location, region
        )
        
        bcr = self.calculate_bcr(result['lnpv'], cost_per_beneficiary)
        
        if bcr > 3:
            recommendation = "HIGHLY COST-EFFECTIVE"
        elif bcr > 1:
            recommendation = "COST-EFFECTIVE"
        else:
            recommendation = "NOT COST-EFFECTIVE"
        
        return {
            **result,
            'cost_per_beneficiary': cost_per_beneficiary,
            'bcr': bcr,
            'recommendation': recommendation
        }


# ====
# SECTION 12: UTILITY FUNCTIONS AND MAIN INTERFACE
# ====

def format_currency(value: float) -> str:
    """Format value as Indian Rupees."""
    if abs(value) >= 1e7:
        return f"â‚¹{value/1e7:.2f} Cr"
    elif abs(value) >= 1e5:
        return f"â‚¹{value/1e5:.2f} L"
    elif abs(value) >= 1e3:
        return f"â‚¹{value/1e3:.1f}K"
    else:
        return f"â‚¹{value:.0f}"


def print_scenario_results(results: List[Dict]):
    """Print formatted results for all scenarios."""
    print("\n" + "="*80)
    print("RWF ECONOMIC IMPACT MODEL - LNPV RESULTS")
    print("="*80)
    print(f"{'Intervention':<15} {'Region':<8} {'Gender':<8} {'Location':<8} {'LNPV':>15}")
    print("-"*80)
    
    for r in results:
        print(f"{r['intervention']:<15} {r['region']:<8} {r['gender']:<8} "
              f"{r['location']:<8} {format_currency(r['lnpv']):>15}")
    
    print("="*80)


def run_baseline_analysis() -> List[Dict]:
    """
    Run baseline LNPV analysis for all 32 scenarios.
    
    This is the main entry point for generating results.
    """
    print("\nInitializing RWF Economic Impact Model v2.0...")
    print("Using PLFS 2023-24 parameters (Milestone 2 update)")
    print("Gap Analysis fixes applied (Sections 4.1-4.4)")
    print("-"*50)
    
    calculator = LifetimeNPVCalculator()
    results = calculator.calculate_all_scenarios()
    
    print_scenario_results(results)
    
    # Summary statistics
    lnpv_values = [r['lnpv'] for r in results]
    print(f"\nSummary Statistics:")
    print(f"  Mean LNPV: {format_currency(np.mean(lnpv_values))}")
    print(f"  Median LNPV: {format_currency(np.median(lnpv_values))}")
    print(f"  Min LNPV: {format_currency(np.min(lnpv_values))}")
    print(f"  Max LNPV: {format_currency(np.max(lnpv_values))}")
    
    return results


def run_sensitivity_analysis(
    intervention: Intervention = Intervention.RTE,
    n_simulations: int = 1000
) -> Dict:
    """
    Run Monte Carlo sensitivity analysis.
    """
    print(f"\nRunning Monte Carlo sensitivity analysis...")
    print(f"Intervention: {intervention.value}")
    print(f"Simulations: {n_simulations}")
    print("-"*50)
    
    simulator = MonteCarloSimulator(n_simulations=n_simulations)
    
    # Run for baseline scenario (Urban Male, West)
    results = simulator.run_simulation(
        intervention=intervention,
        gender=Gender.MALE,
        location=Location.URBAN,
        region=Region.WEST
    )
    
    print(f"\nMonte Carlo Results ({intervention.value}, Urban Male, West):")
    print(f"  Mean LNPV: {format_currency(results['mean'])}")
    print(f"  Median LNPV: {format_currency(results['median'])}")
    print(f"  Std Dev: {format_currency(results['std'])}")
    print(f"  5th Percentile: {format_currency(results['p5'])}")
    print(f"  95th Percentile: {format_currency(results['p95'])}")
    print(f"  90% CI: [{format_currency(results['p5'])}, {format_currency(results['p95'])}]")
    
    return results


# ====
# MAIN EXECUTION
# ====

if __name__ == "__main__":
    # Run baseline analysis
    baseline_results = run_baseline_analysis()
    
    # Run sensitivity analysis for RTE
    print("\n" + "="*80)
    rte_sensitivity = run_sensitivity_analysis(
        intervention=Intervention.RTE,
        n_simulations=500
    )
    
    # Run sensitivity analysis for Apprenticeship
    print("\n" + "="*80)
    app_sensitivity = run_sensitivity_analysis(
        intervention=Intervention.APPRENTICESHIP,
        n_simulations=500
    )
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)