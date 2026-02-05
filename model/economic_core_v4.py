"""
RightWalk Foundation Economic Impact Model - Core Engine v4.0
=============================================================

VERSION: 4.3
UPDATED: January 18, 2026 (CSV SSOT Sync)
PREVIOUS: v4.2 January 14, 2026 (Phase 1 Alignment)

CSV SSOT SYNC (Jan 18, 2026):
- FORMAL_MULTIPLIER: 2.0 → 2.25 (ILO 2024: Urban 2.24x, Rural 2.48x)
- P_FORMAL_HIGHER_SECONDARY: 20% → 9.1% (ILO India Employment Report 2024)
- MINCER_RETURN_HS: 5.8% → 7.0% (Mitra 2019 via Chen et al. 2022)
- TEST_SCORE_TO_YEARS: 4.7 → 6.8 (Angrist & Evans 2020 micro-LAYS)
- APPRENTICE_STIPEND_MONTHLY: ₹10,000 → ₹7,000 (Gazette 2019 rates)
- RTE_TEST_SCORE_GAIN range: 0.15-0.30 → 0.10-0.35 (ITT alternative)

PHASE 1 ALIGNMENT (Jan 14, 2026):
- All 8/8 validation tests pass (validate_model_integrity.py)
- DEPRECATED markers added to: RTE_INITIAL_PREMIUM, VOCATIONAL_PREMIUM,
  APPRENTICE_YEAR_0_OPPORTUNITY_COST, WORKING_LIFE_INFORMAL
- MonteCarloSimulator.sample_parameters() rewritten with explicit clamping:
  * Probabilities clamped to [0.0, 1.0]
  * REAL_WAGE_GROWTH clamped to [-0.005, 0.01]
  * Added P_FORMAL_NO_TRAINING and FORMAL_MULTIPLIER to sampling
- calculate_apprentice_control_trajectory() uses P_FORMAL_NO_TRAINING
- calculate_lnpv() routes to intervention-specific counterfactual
- RTE P(Formal) calculation: base × regional_multiplier, capped at 90%

CRITICAL FIXES IN v4.0 (Dec 26, 2025):
- FIXED: Double-counting of formal sector premium
  * Baseline wages already differentiate formal (salaried) vs informal (casual)
  * PLFS embedded ratio: ~1.86x (salaried/casual wages)
  * Changed formal_multiplier to benefits_adjustment_factor
  * Now calculates: target_ratio (2.0) / embedded_ratio (1.86) = 1.075x adjustment
- UPDATED: Formal multiplier value 2.25 -> 2.0 (conservative midpoint)
- UPDATED: RTE scenarios 30%/40%/50% per Anand's guidance (Dec 2025)
- FIXED: Apprenticeship premium no longer inflated by 8.4x

PREVIOUS VERSIONS:
- v3.0 (Dec 2024): Scenario framework, Monte Carlo, stakeholder output
- v2.0 (Nov 2025): Gap Analysis fixes (P(Formal) dead code, regional adjustments)
- v1.0: Initial PLFS 2023-24 integration

PARAMETER SUMMARY (Jan 18, 2026 CSV SSOT):
- Mincer returns: 7.0% (Mitra 2019: range 5-9% by quantile)
- Experience premium: 0.885%/year (down 78% from literature)
- Real wage growth: 0.01% (essentially stagnant)
- Formal/informal wage ratio: 2.25x (ILO 2024 total compensation)
- Social discount rate: 8.5% (Murty & Panda 2020 Ramsey formula)
- P(Formal|HS): 9.1% (ILO 2024 youth formal employment)

ARCHITECTURE NOTE ON FORMAL SECTOR DIFFERENTIAL:
The model uses PLFS baseline wages that already differentiate by sector:
  - Informal: casual wages (e.g., Rs 13,425 urban male)
  - Formal: salaried wages (e.g., Rs 26,105 urban male)
  - Embedded ratio: ~1.86x (varies by demographic)

The FORMAL_MULTIPLIER (2.0x) represents TARGET total compensation ratio.
Applied as BENEFITS ADJUSTMENT: target_ratio / embedded_ratio
  - If target = 2.0x and embedded = 1.86x: adjustment = 1.075x
  - Captures EPF (24%), ESI (4%), gratuity not in PLFS cash wages

Author: RWF Economic Impact Analysis Team
Version: 4.3 (January 18, 2026)
Status: CSV SSOT SYNC COMPLETE
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import warnings

# SSOT Import: parameter_registry_v3 is the Single Source of Truth for parameters
# UPDATED Jan 2026: Mandatory import (no silent fallback)
# FIXED Jan 20, 2026: Use relative import for package compatibility
try:
    # Relative import when used as package
    from .parameter_registry_v3 import (
        get_embedded_ratio,
        EMBEDDED_RATIO_AVERAGE,
        get_scenario_parameters,
        SCENARIO_CONFIGS,
    )
except ImportError:
    # Absolute import when run directly
    from parameter_registry_v3 import (
        get_embedded_ratio,
        EMBEDDED_RATIO_AVERAGE,
        get_scenario_parameters,
        SCENARIO_CONFIGS,
    )


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
    Source: RWF_Parameter_Update_Nov2025.md
    """
    
    # ----
    # CORE MINCER EQUATION PARAMETERS (UPDATED)
    # ----
    
    # Mincer return to education (per year of schooling)
    # UPDATED Jan 2026: 5.8% → 7.0% per Mitra (2019) via Chen et al. (2022)
    # Returns vary by quantile: 5% (lowest) to 9% (highest), midpoint 7%
    MINCER_RETURN_HS: Parameter = field(default_factory=lambda: Parameter(
        value=0.07,
        min_val=0.05,
        max_val=0.09,
        tier=2,
        source="Mitra (2019) via Chen et al. (2022) - quantile returns 5-9%",
        unit="%/year",
        description="Return to higher secondary education per year"
    ))
    
    # Experience premium (linear term)
    # OLD: 4-6%, NEW: 0.885% (â†“78%)
    EXPERIENCE_LINEAR: Parameter = field(default_factory=lambda: Parameter(
        value=0.00885,
        min_val=0.005,
        max_val=0.012,
        tier=3,
        source="PLFS 2023-24 age-wage profiles",
        unit="%/year",
        description="Linear experience premium coefficient"
    ))
    
    # Experience premium (quadratic term)
    # OLD: -0.1%, NEW: -0.0123% (â†‘88% less negative)
    EXPERIENCE_QUAD: Parameter = field(default_factory=lambda: Parameter(
        value=-0.000123,
        min_val=-0.0002,
        max_val=-5e-05,
        tier=3,
        source="PLFS 2023-24 age-wage profiles",
        unit="%/yearÂ²",
        description="Quadratic experience coefficient (diminishing returns)"
    ))
    
    # Formal sector wage multiplier
    # UPDATED Jan 2026: 2.0 → 2.25 per ILO India Employment Report 2024
    # Urban: ₹12,616/₹5,635 = 2.24x; Rural: ~2.48x; using 2.25 as midpoint
    FORMAL_MULTIPLIER: Parameter = field(default_factory=lambda: Parameter(
        value=2.25,
        min_val=2.24,
        max_val=2.48,
        tier=2,
        source="ILO India Employment Report 2024 - Urban 2.24x, Rural 2.48x",
        unit="×",
        description="Total compensation multiplier for formal vs informal sector"
    ))
    
    # NEW Jan 2026: Sector-specific wage growth (Anand guidance Dec 2025)
    # "In any wage growth the formal sector is higher and informal is lower"
    REAL_WAGE_GROWTH_FORMAL: Parameter = field(default_factory=lambda: Parameter(
        value=0.015,  # 1.5% per year for formal sector
        min_val=0.005,
        max_val=0.025,
        tier=2,
        source="PLFS 2020-24 formal sector trends; inequality literature",
        unit="%/year",
        description="Annual real wage growth rate for FORMAL sector (promotions, increments)"
    ))

    REAL_WAGE_GROWTH_INFORMAL: Parameter = field(default_factory=lambda: Parameter(
        value=-0.002,  # -0.2% per year for informal sector (slight decline)
        min_val=-0.01,
        max_val=0.005,
        tier=2,
        source="PLFS 2020-24 informal stagnation; inequality literature",
        unit="%/year",
        description="Annual real wage growth rate for INFORMAL sector (stagnation/decline)"
    ))

    # DEPRECATED: Use REAL_WAGE_GROWTH_FORMAL and REAL_WAGE_GROWTH_INFORMAL
    REAL_WAGE_GROWTH: Parameter = field(default_factory=lambda: Parameter(
        value=0.0001,
        min_val=-0.005,
        max_val=0.01,
        tier=2,
        source="[DEPRECATED] PLFS 2020-24 wage stagnation",
        unit="%/year",
        description="[DEPRECATED] Use sector-specific rates instead"
    ))
    
    # ----
    # FORMAL SECTOR ENTRY PROBABILITIES (TIER 1 - HIGHEST UNCERTAINTY)
    # ----
    
    # UPDATED Jan 2026: ILO India Employment Report 2024 shows only 9.1% of youth
    # with secondary/higher secondary education were in formal employment in 2022
    # This is the NATIONAL BASELINE for control group calculations
    P_FORMAL_HIGHER_SECONDARY: Parameter = field(default_factory=lambda: Parameter(
        value=0.091,  # ILO 2024: 9.1% formal employment for HS graduates
        min_val=0.05,
        max_val=0.15,
        tier=1,
        source="ILO India Employment Report 2024 - youth formal employment rate",
        unit="%",
        description="P(Formal | Higher Secondary completion) - NATIONAL BASELINE for control"
    ))

    # NEW Jan 2026: RTE graduates have higher formal entry than national baseline
    # Anand guidance: "70% too high, 30-40% defensible"
    P_FORMAL_RTE: Parameter = field(default_factory=lambda: Parameter(
        value=0.30,  # 30% formal entry for RTE graduates (3.3× baseline)
        min_val=0.20,
        max_val=0.50,
        tier=1,
        source="RWF assumption: 3.3× national baseline (Anand guidance Dec 2025)",
        unit="%",
        description="P(Formal | RTE graduation) - higher due to selection/networks"
    ))

    P_FORMAL_SECONDARY: Parameter = field(default_factory=lambda: Parameter(
        value=0.12,
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
        source="MSDE reports (assumed, not verified)",
        unit="%",
        description="P(Formal | Apprenticeship completion)"
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
    # UPDATED Jan 2026: Now using ITT (Intent-to-Treat) estimate per Anand guidance
    # "We should think of per child allocated, not per completer"
    RTE_TEST_SCORE_GAIN: Parameter = field(default_factory=lambda: Parameter(
        value=0.137,  # ITT estimate (was 0.23 ToT)
        min_val=0.10,
        max_val=0.20,  # Narrowed range for ITT
        tier=1,
        source="NBER RCT (Muralidharan & Sundararaman 2013) - ITT estimate",
        unit="SD",
        description="Test score improvement per child ALLOCATED to RTE (ITT, not ToT)"
    ))
    
    # UPDATED Jan 2026: Angrist & Evans (2020) report 6.8 years/SD via micro-LAYS methodology
    TEST_SCORE_TO_YEARS: Parameter = field(default_factory=lambda: Parameter(
        value=6.8,
        min_val=4.0,
        max_val=8.0,
        tier=2,
        source="Angrist & Evans (2020) micro-LAYS methodology",
        unit="years/SD",
        description="Equivalent years of schooling per SD test gain"
    ))
    
    # DEPRECATED Jan 2026: RTE effect modeled via schooling years (test score -> years conversion)
    # Retained for backwards compatibility only. Value is NOT used in calculations.
    RTE_INITIAL_PREMIUM: Parameter = field(default_factory=lambda: Parameter(
        value=98000,
        min_val=80000,
        max_val=120000,
        tier=1,
        source="DEPRECATED - Calculated from wage differentials",
        unit="INR/year",
        description="DEPRECATED: Initial annual wage premium for RTE beneficiary. "
                    "RTE effect is now modeled through test_score_gain × years_per_SD."
    ))
    
    # Apprenticeship parameters
    # DEPRECATED Jan 2026: Use APPRENTICE_INITIAL_PREMIUM instead
    # Retained for backwards compatibility only. Value is NOT used in calculations.
    VOCATIONAL_PREMIUM: Parameter = field(default_factory=lambda: Parameter(
        value=0.047,
        min_val=0.03,
        max_val=0.06,
        tier=2,
        source="DEPRECATED - NSSO vocational training studies",
        unit="%",
        description="DEPRECATED: Wage premium for vocational training. "
                    "Use APPRENTICE_INITIAL_PREMIUM instead for apprenticeship wage premium."
    ))
    
    # UPDATED Jan 2026: Gazette notification 2019 - stipend by education level
    # Class 5-9: ₹5k, Class 10: ₹6k, Class 12: ₹7k, Certificate: ₹8k, Graduate: ₹9k
    APPRENTICE_STIPEND_MONTHLY: Parameter = field(default_factory=lambda: Parameter(
        value=7000,
        min_val=5000,
        max_val=9000,
        tier=3,
        source="Gazette notification 2019 - stipend rates by education level",
        unit="INR/month",
        description="Monthly stipend during 1-year apprenticeship training"
    ))
    
    # DEPRECATED Jan 2026: Now calculated endogenously from stipend vs counterfactual wage
    # Retained for backwards compatibility only. Value is NOT used in calculations.
    APPRENTICE_YEAR_0_OPPORTUNITY_COST: Parameter = field(default_factory=lambda: Parameter(
        value=-49000,
        min_val=-80000,
        max_val=-20000,
        tier=2,
        source="DEPRECATED - Calculated: Stipend - Counterfactual informal wage",
        unit="INR/year",
        description="DEPRECATED: Year 0 net opportunity cost. "
                    "Now calculated endogenously in calculate_treatment_trajectory() from "
                    "APPRENTICE_STIPEND_MONTHLY × 12 vs counterfactual informal wage."
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
    
    # UPDATED Jan 2026: Murty & Panda (2020) derive 8.5% using Ramsey formula (p + vg)
    # Alternative extended formula yields 6%. Using 8.5% for long-run investment projects.
    SOCIAL_DISCOUNT_RATE: Parameter = field(default_factory=lambda: Parameter(
        value=0.05,
        min_val=0.03,
        max_val=0.08,
        tier=2,
        source="Murty & Panda (2020) - Ramsey formula 8.5% for India",
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
    
    # DEPRECATED Jan 2026: Model uses WORKING_LIFE_FORMAL for all trajectories
    # Retained for backwards compatibility only. Value is NOT used in calculations.
    WORKING_LIFE_INFORMAL: Parameter = field(default_factory=lambda: Parameter(
        value=47,
        min_val=45,
        max_val=50,
        tier=3,
        source="DEPRECATED - Extended working life in informal sector",
        unit="years",
        description="DEPRECATED: Working life duration for informal sector. "
                    "Model now uses WORKING_LIFE_FORMAL for all trajectory calculations."
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
    
    From RWF_Parameter_Update_Nov2025.md Section 2.3.
    
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
        
        # =====================================================================
        # ELIMINATED Jan 20, 2026: benefits_adjustment REMOVED per Anand guidance
        # =====================================================================
        #
        # Anand Dec 2025: "You have over specified in the model... you have taken
        # the formal to informal ratio, and you have taken two data sources...
        # all three right now are not consistent so one of them you can let go"
        #
        # PROBLEM IDENTIFIED:
        # - PLFS baseline wages ALREADY differentiate by sector:
        #   * Formal: Rs 32,800 (urban male HS)
        #   * Informal: Rs 13,425 (urban male casual)
        #   * Ratio: 32,800 / 13,425 = 2.44× (exceeds ILO target 2.25×!)
        # - Applying additional 1.21× adjustment caused over-specification
        # - Effective ratio was 2.44 × 1.21 = 2.95× (inflated)
        #
        # SOLUTION: Trust PLFS wages as SINGLE SOURCE OF TRUTH
        # - Wages already differentiate formal/informal by sector parameter
        # - No additional benefits_adjustment needed
        # - FORMAL_MULTIPLIER parameter retained for documentation only
        #
        # IMPACT:
        # - Apprenticeship NPV: -15% to -20% (mostly formal workers)
        # - RTE NPV: -5% to -10% (only 30% formal with P_FORMAL_RTE)
        # =====================================================================

        # Calculate final wage (NO benefits_adjustment - PLFS wages are SSOT)
        wage = (base_wage *
                education_premium *
                experience_premium *
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
        # AUTO-SELECT wage growth by sector if not explicitly provided
        # NEW Jan 2026: Sector-specific growth rates (Anand guidance)
        # Formal sector sees career progression; informal stagnates/declines
        if real_wage_growth is None:
            if sector == Sector.FORMAL:
                real_wage_growth = self.params.REAL_WAGE_GROWTH_FORMAL.value  # 1.5%
            else:
                real_wage_growth = self.params.REAL_WAGE_GROWTH_INFORMAL.value  # -0.2%
        
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
    
    LNPV = SUM_{t=0}^{T} [E[Earnings_t]^Treatment - E[Earnings_t]^Control] / (1 + discount)^t
    
    DISCOUNTING METHODOLOGY (Per Anand feedback, Dec 2025):
    ========================================================
    BASE YEAR: Year of labor market entry (age 22 for RTE, age 18-20 for apprenticeship)
    
    The model uses CURRENT (2025) salary levels and discounts the 40-year earnings
    trajectory from labor market entry, NOT from intervention year. This approach:
    
    1. AVOIDS complexity of forecasting wage inflation 15+ years ahead
       - For RTE: Child enrolls at age 6 (2025), enters labor market at 22 (2041)
       - Projecting 2041 salaries requires forecasting 16 years of wage inflation
       - Such forecasts are highly uncertain and add little value
    
    2. STANDARD PRACTICE in education economics
       - Cross-intervention comparisons use common salary baseline
       - Focus is on DIFFERENTIAL effects, not absolute salary levels
       - Real wage growth (0.01% in our model) captures within-career dynamics
    
    3. SIMPLIFIES stakeholder communication
       - "Rs 22.8L NPV" means "in today's rupees, at labor market entry"
       - No need to explain inflation forecasting assumptions
    
    4. FOR INTERVENTION-YEAR COMPARISON: Use adjustment utility
       - If comparing costs incurred in 2025 to benefits starting 2041:
         NPV_2025 = NPV_2041 / (1 + discount)^16
       - See adjust_npv_to_intervention_year() utility function
    
    IMPORTANT: This is NOT "ignoring inflation" - it's using current prices as
    the reference frame, which is standard practice for long-term cost-benefit
    analysis when comparing multiple interventions with different time horizons.
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
            # UPDATED Jan 2026: Use P_FORMAL_RTE (separate from national baseline)
            # RTE graduates have HIGHER formal entry than national 9.1% baseline
            # due to: selection effects, urban concentration, private school networks
            #
            # Formula: p_formal = P_FORMAL_RTE × regional_multiplier
            # - P_FORMAL_RTE = 0.30 default (3.3× national baseline)
            # - regional scaling still applies (urban areas have higher formal %)
            #
            # Anand guidance: "70% too high, 30-40% defensible"
            base_p_formal = self.params.P_FORMAL_RTE.value  # 0.30 (NEW: RTE-specific)
            regional_p = self.wage_model.regional.p_formal_hs[region]
            national_avg = sum(self.wage_model.regional.p_formal_hs.values()) / 4
            regional_multiplier = regional_p / national_avg
            p_formal = min(0.90, base_p_formal * regional_multiplier)  # Cap at 90%

            # RTE: Effective years of schooling increased by test score gains
            years_schooling = 12 + (self.params.RTE_TEST_SCORE_GAIN.value *
                                   self.params.TEST_SCORE_TO_YEARS.value)
            initial_premium = 0  # Premium captured in education effect
            decay = DecayFunction.NONE
            halflife = float('inf')
            
        else:  # Apprenticeship
            # DOCUMENTED (Gap Analysis 4.3): P(Formal) for apprenticeship uses
            # national employer absorption rate (75%) and does NOT apply regional
            # adjustments. This reflects that placement is through specific employers
            # (MSDE data) rather than general labor markets, so absorption rates are
            # more uniform nationally.
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
            
            # YEAR 0 IMPLEMENTATION (Open Loop OL-03 - Dec 2025):
            # During the 1-year apprenticeship training, participant receives stipend
            # rather than full wage. This creates an opportunity cost that reduces NPV.
            
            # Calculate Year 0 stipend (treatment group receives this)
            year_0_stipend_annual = self.params.APPRENTICE_STIPEND_MONTHLY.value * 12
        
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
        
        # For apprenticeship: prepend Year 0 stipend to the trajectory
        # This extends the trajectory from 40 to 41 years (Year 0 + Years 1-40)
        if intervention == Intervention.APPRENTICESHIP:
            expected_wages = np.concatenate([[year_0_stipend_annual], expected_wages])
            # Adjust entry age to reflect training year (age 18-20 typical for apprentice start)
            entry_age = int(self.params.LABOR_MARKET_ENTRY_AGE.value) - 1
        else:
            entry_age = int(self.params.LABOR_MARKET_ENTRY_AGE.value)
        
        # Apply unemployment probability
        expected_wages = self.employment_model.apply_unemployment_shock(
            expected_wages,
            entry_age=entry_age
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

    def calculate_apprentice_control_trajectory(
        self,
        gender: Gender,
        location: Location,
        region: Region
    ) -> np.ndarray:
        """
        Calculate expected wage trajectory for APPRENTICESHIP control group.

        ADDED Jan 2026: Separate counterfactual for apprenticeship intervention.

        The apprenticeship control group represents youth who:
        - Have 10th/12th pass education (no vocational training)
        - Enter labor market directly without formal skills training
        - Face P(Formal) = P_FORMAL_NO_TRAINING (~10% national, region-adjusted)

        This is DIFFERENT from RTE control which uses schooling pathway distribution
        (govt school, low-fee private, dropout).

        Returns:
            Array of annual wages over working life
        """
        working_years = int(self.params.WORKING_LIFE_FORMAL.value)

        # Use P_FORMAL_NO_TRAINING as base, with regional adjustment
        base_p_formal = self.params.P_FORMAL_NO_TRAINING.value  # 0.10 default
        p_formal = self.wage_model.regional.adjust_p_formal_control(region, base_p_formal)
        p_formal = max(0.03, min(0.25, p_formal))  # Clamp to reasonable range

        # Generate formal pathway trajectory (10th/12th education, no vocational)
        formal_wages = self.wage_model.generate_wage_trajectory(
            years_schooling=10,  # Secondary education
            sector=Sector.FORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )

        # Generate informal pathway trajectory
        informal_wages = self.wage_model.generate_wage_trajectory(
            years_schooling=10,
            sector=Sector.INFORMAL,
            gender=gender,
            location=location,
            region=region,
            working_years=working_years
        )

        # Weighted average based on P(Formal | No Training)
        expected_wages = p_formal * formal_wages + (1 - p_formal) * informal_wages

        # Apply unemployment
        expected_wages = self.employment_model.apply_unemployment_shock(
            expected_wages,
            entry_age=int(self.params.LABOR_MARKET_ENTRY_AGE.value)
        )

        return expected_wages

    def calculate_npv(
        self,
        wage_differential: np.ndarray,
        discount_rate: float = None
    ) -> float:
        """
        Calculate NPV of wage differential stream.
        
        NPV = SUM_{t=0}^{T} differential_t / (1 + discount)^t
        
        DISCOUNTING BASE YEAR: t=0 is labor market entry year (age 22 for RTE).
        - Differential already in "current 2025 prices" (no inflation projection)
        - Discounting captures time preference only, not inflation adjustment
        - For comparison to intervention-year costs, see adjust_npv_to_intervention_year()
        
        This approach is standard in education CBA to avoid uncertain long-term
        wage inflation forecasts while maintaining comparability across interventions.
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
        
        For APPRENTICESHIP: Handles Year 0 stipend period where:
        - Treatment receives stipend (Ã¢â€šÂ¹120k/year)
        - Control earns informal wage (Ã¢â€šÂ¹168k/year) 
        - This creates a negative premium in Year 0 that reduces NPV
        
        Returns dictionary with detailed results.
        """
        treatment_wages, p_formal_treatment = self.calculate_treatment_trajectory(
            intervention, gender, location, region
        )

        # UPDATED Jan 2026: Use intervention-specific counterfactual
        # - RTE: Schooling pathway distribution (govt, low-fee private, dropout)
        # - Apprenticeship: Youth without vocational training (P_FORMAL_NO_TRAINING)
        if intervention == Intervention.APPRENTICESHIP:
            control_wages = self.calculate_apprentice_control_trajectory(
                gender, location, region
            )
            # Extend control trajectory to match treatment length
            # Treatment has Year 0 (stipend) + Years 1-40 (work) = 41 years
            # Control should also have 41 years, with Year 0 being informal wage
            education_level = EducationLevel.SECONDARY  # 10th pass typical
            year_0_counterfactual_monthly = self.wage_model.baseline_wages.get_wage(
                location, gender, education_level, Sector.INFORMAL
            )
            year_0_counterfactual_annual = year_0_counterfactual_monthly * 12
            # Prepend Year 0 to control trajectory
            control_wages = np.concatenate([[year_0_counterfactual_annual], control_wages])
        else:  # RTE
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

        UPDATED Jan 20, 2026:
        - Added P_FORMAL_RTE (new RTE-specific formal entry probability)
        - Added REAL_WAGE_GROWTH_FORMAL and REAL_WAGE_GROWTH_INFORMAL
        - Previous: P_FORMAL_NO_TRAINING and REAL_WAGE_GROWTH added

        Only Tier 1 and Tier 2 parameters are varied.
        Tier 3 (baseline wages, working life) are held constant.
        """
        sampled = ParameterRegistry()

        # Helper function for clamped sampling
        def sample_clamped(param, min_val=None, max_val=None):
            val = param.sample(distribution)
            if min_val is not None:
                val = max(min_val, val)
            if max_val is not None:
                val = min(max_val, val)
            return val

        # Sample Tier 1 parameters (highest uncertainty) with explicit clamping
        sampled.P_FORMAL_HIGHER_SECONDARY.value = sample_clamped(
            base_params.P_FORMAL_HIGHER_SECONDARY, 0.0, 1.0
        )
        # NEW Jan 2026: RTE-specific formal entry probability
        sampled.P_FORMAL_RTE.value = sample_clamped(
            base_params.P_FORMAL_RTE, 0.0, 1.0
        )
        sampled.P_FORMAL_APPRENTICE.value = sample_clamped(
            base_params.P_FORMAL_APPRENTICE, 0.0, 1.0
        )
        sampled.P_FORMAL_NO_TRAINING.value = sample_clamped(
            base_params.P_FORMAL_NO_TRAINING, 0.0, 1.0
        )
        sampled.RTE_TEST_SCORE_GAIN.value = sample_clamped(
            base_params.RTE_TEST_SCORE_GAIN, 0.0, 1.0
        )
        sampled.APPRENTICE_INITIAL_PREMIUM.value = sample_clamped(
            base_params.APPRENTICE_INITIAL_PREMIUM, 0, None
        )
        sampled.APPRENTICE_DECAY_HALFLIFE.value = sample_clamped(
            base_params.APPRENTICE_DECAY_HALFLIFE, 1, 100
        )

        # Sample Tier 2 parameters
        sampled.MINCER_RETURN_HS.value = sample_clamped(
            base_params.MINCER_RETURN_HS, 0.01, 0.15
        )
        sampled.SOCIAL_DISCOUNT_RATE.value = sample_clamped(
            base_params.SOCIAL_DISCOUNT_RATE, 0.01, 0.15
        )
        # NEW Jan 2026: Sector-specific wage growth
        sampled.REAL_WAGE_GROWTH_FORMAL.value = sample_clamped(
            base_params.REAL_WAGE_GROWTH_FORMAL, -0.01, 0.05
        )
        sampled.REAL_WAGE_GROWTH_INFORMAL.value = sample_clamped(
            base_params.REAL_WAGE_GROWTH_INFORMAL, -0.02, 0.02
        )
        # DEPRECATED but kept for backward compat
        sampled.REAL_WAGE_GROWTH.value = sample_clamped(
            base_params.REAL_WAGE_GROWTH, -0.005, 0.01
        )
        sampled.FORMAL_MULTIPLIER.value = sample_clamped(
            base_params.FORMAL_MULTIPLIER, 1.0, 3.0
        )

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
# SECTION 10A: SCENARIO COMPARISON UTILITIES
# ====

def run_scenario_comparison(
    intervention: Intervention,
    gender: Gender,
    location: Location,
    region: Region
) -> Dict[str, Dict]:
    """
    Run LNPV calculation for all three scenarios (Conservative/Moderate/Optimistic).
    
    This utility enables transparent communication of model uncertainty by showing
    results under different parameter assumptions. The moderate scenario uses
    RWF-validated data where available (e.g., 72% apprentice placement).
    
    Args:
        intervention: RTE or APPRENTICESHIP
        gender: MALE or FEMALE
        location: URBAN or RURAL
        region: NORTH/SOUTH/EAST/WEST
    
    Returns:
        Dict with results for each scenario:
        {
            'conservative': {...lnpv results...},
            'moderate': {...lnpv results...},
            'optimistic': {...lnpv results...}
        }
        
    Example:
        results = run_scenario_comparison(
            Intervention.APPRENTICESHIP,
            Gender.MALE,
            Location.URBAN,
            Region.WEST
        )
        print(format_scenario_comparison(results))
    
    Notes:
        - Moderate scenario uses RWF-validated 72% apprentice placement
        - P(Formal|RTE) values reflect different assumptions about selection effects
        - Range captures uncertainty in Tier 1 critical parameters
    """
    from parameter_registry_v3 import get_scenario_parameters
    
    results = {}
    
    for scenario_name in ['conservative', 'moderate', 'optimistic']:
        # Create fresh ParameterRegistry
        params = ParameterRegistry()
        
        # Apply scenario overrides
        scenario_values = get_scenario_parameters(scenario_name)
        for param_name, value in scenario_values.items():
            if hasattr(params, param_name):
                getattr(params, param_name).value = value
        
        # Calculate LNPV with scenario parameters
        calculator = LifetimeNPVCalculator(params=params)
        result = calculator.calculate_lnpv(intervention, gender, location, region)
        result['scenario'] = scenario_name
        results[scenario_name] = result
    
    return results


def format_scenario_comparison(results: Dict[str, Dict]) -> str:
    """
    Format scenario comparison results as readable table.
    
    Args:
        results: Output from run_scenario_comparison()
    
    Returns:
        Formatted string table showing LNPV, P(Formal), and lifetime earnings
        across all three scenarios
        
    Example output:
        ================================================================================
        SCENARIO COMPARISON RESULTS
        ================================================================================
        
        Intervention: APPRENTICESHIP
        Demographics: male / urban / west
        
        Scenario         LNPV      P(Formal)   Lifetime Earnings
        --------------------------------------------------------------------------------
        Conservative     Rs 52.3L      50.0%              Rs 78.5L
        Moderate        Rs 104.7L      72.0%             Rs 132.8L
        Optimistic      Rs 156.2L      90.0%             Rs 185.3L
        ================================================================================
    """
    output = "\n" + "="*80 + "\n"
    output += "SCENARIO COMPARISON RESULTS\n"
    output += "="*80 + "\n\n"
    
    intervention = results['moderate']['intervention']
    output += f"Intervention: {intervention.upper()}\n"
    output += f"Demographics: {results['moderate']['gender']} / "
    output += f"{results['moderate']['location']} / {results['moderate']['region']}\n\n"
    
    output += f"{'Scenario':<15} {'LNPV':>15} {'P(Formal)':>12} {'Lifetime Earnings':>20}\n"
    output += "-"*80 + "\n"
    
    for scenario in ['conservative', 'moderate', 'optimistic']:
        r = results[scenario]
        lnpv = r['lnpv']
        p_formal = r['p_formal_treatment']
        lifetime = r['treatment_lifetime_earnings']
        
        output += f"{scenario.capitalize():<15} "
        output += f"{format_currency(lnpv):>15} "
        output += f"{p_formal:>11.1%} "
        output += f"{format_currency(lifetime):>20}\n"
    
    output += "="*80 + "\n"
    
    # Add interpretation notes
    output += "\nNOTES:\n"
    output += "- Moderate scenario uses RWF-validated 72% apprentice placement rate\n"
    output += "- P(Formal|RTE) assumptions:\n"
    output += "  * Conservative (25%): Marginally better than worst regions\n"
    output += "  * Moderate (40%): 2Ã— national average (requires selection/urban effects)\n"
    output += "  * Optimistic (60%): Near stakeholder intuition (requires strong selection)\n"
    output += "- Range reflects uncertainty in Tier 1 critical parameters\n"
    output += "- All scenarios use PLFS 2023-24 baseline wages and 5.8% Mincer returns\n"
    
    return output


def run_scenario_comparison_batch(
    intervention: Intervention,
    demographics: List[Tuple[Gender, Location, Region]] = None
) -> Dict[str, Dict[str, Dict]]:
    """
    Run scenario comparison for multiple demographic groups.
    
    Args:
        intervention: RTE or APPRENTICESHIP
        demographics: List of (gender, location, region) tuples
                     If None, runs for all 16 demographic combinations
    
    Returns:
        Nested dict: {demographic_key: {scenario: results}}
        
    Example:
        # Run for specific demographics
        demographics = [
            (Gender.MALE, Location.URBAN, Region.WEST),
            (Gender.FEMALE, Location.RURAL, Region.SOUTH)
        ]
        batch_results = run_scenario_comparison_batch(
            Intervention.APPRENTICESHIP,
            demographics
        )
    """
    if demographics is None:
        # Generate all 16 combinations
        demographics = [
            (gender, location, region)
            for gender in Gender
            for location in Location
            for region in Region
        ]
    
    batch_results = {}
    
    for gender, location, region in demographics:
        demo_key = f"{gender.value}_{location.value}_{region.value}"
        batch_results[demo_key] = run_scenario_comparison(
            intervention, gender, location, region
        )
    
    return batch_results


def run_official_analysis(
    intervention: Intervention,
    demographics: List[Tuple[Gender, Location, Region]] = None
) -> Dict[str, Dict[str, Dict]]:
    """
    OFFICIAL analysis function that returns scenario comparison results.
    
    This is the RECOMMENDED function for stakeholder reports and external use.
    It returns results for all three scenarios (Conservative/Moderate/Optimistic)
    showing the range of plausible outcomes under different assumptions.
    
    Args:
        intervention: RTE or APPRENTICESHIP
        demographics: List of (gender, location, region) tuples
                    If None, runs for all 16 demographic combinations
    
    Returns:
        Nested dict: {demographic_key: {scenario: results}}
        
    Example:
        results = run_official_analysis(Intervention.RTE)
        
        # Access moderate scenario for urban males in South
        moderate_npv = results['male_urban_south']['moderate']['lnpv']
        
    Notes:
        - Moderate scenario uses RWF-validated 72% apprentice placement
        - Range (Conservative/Optimistic) captures Tier 1 parameter uncertainty
        - All scenarios use PLFS 2023-24 wage data (5.8% Mincer returns)
        
    DEPRECATION NOTE:
    - run_baseline_analysis() is deprecated - returns single point estimate
    - Use run_official_analysis() instead for comprehensive scenario analysis
    """
    return run_scenario_comparison_batch(intervention, demographics)



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
# SECTION 11B: DUAL BCR CALCULATOR (ADDED Feb 2026)
# ====

class DualBCRCalculator:
    """
    Calculate DUAL Benefit-Cost Ratios for interventions.

    Provides two BCR perspectives:
    (A) Full BCR: Total investment (RWF + government + private co-finance)
    (B) RWF-only BCR: Only direct RWF spend (funder ROI perspective)

    BCR Formula:
        BCR = PV(benefits) / PV(costs)

    Where:
        PV(benefits) = Σ_{t=0}^{T} (incremental_benefit_t) / (1 + r)^t
        PV(costs) = Σ_{t=0}^{T} (cost_t) / (1 + r)^t

    For simplicity, costs are assumed upfront (Year 0), so:
        PV(costs) ≈ cost_per_beneficiary (no discounting needed)

    EARNINGS TREATMENT (Feb 2026):
        - Model uses GROSS pre-tax earnings (Mincer wage equation standard)
        - This is consistent with human capital literature and PLFS wage data
        - For net-of-tax sensitivity, use tax_adjustment parameter (0.85-0.90)
        - Numerator: PV of incremental lifetime earnings (treatment - control)
        - Denominator: Program costs (upfront, no discounting)

    Added: February 2026 per task requirements
    """

    # Default costs from parameter_registry_v3.py
    DEFAULT_COSTS = {
        Intervention.RTE: {
            'rwf_only': 4000,      # ₹4,000 RWF direct
            'total': 104000,       # ₹1.04L total investment
        },
        Intervention.APPRENTICESHIP: {
            'rwf_only': 6000,      # ₹6,000 RWF direct
            'total': 158460,       # ₹1.58L total investment
        }
    }

    def __init__(
        self,
        params: ParameterRegistry = None,
        npv_calculator: LifetimeNPVCalculator = None
    ):
        self.params = params or ParameterRegistry()
        self.npv_calculator = npv_calculator or LifetimeNPVCalculator(self.params)

    def calculate_dual_bcr(
        self,
        intervention: Intervention,
        gender: Gender,
        location: Location,
        region: Region,
        rwf_cost: float = None,
        total_cost: float = None,
        discount_rate: float = None
    ) -> Dict:
        """
        Calculate both BCR perspectives for a single scenario.

        Args:
            intervention: RTE or APPRENTICESHIP
            gender: MALE or FEMALE
            location: URBAN or RURAL
            region: NORTH/SOUTH/EAST/WEST
            rwf_cost: RWF direct cost (if None, uses default)
            total_cost: Total investment cost (if None, uses default)
            discount_rate: Social discount rate (if None, uses registry default)

        Returns:
            Dict with LNPV and both BCR calculations
        """
        # Use default costs if not provided
        if rwf_cost is None:
            rwf_cost = self.DEFAULT_COSTS[intervention]['rwf_only']
        if total_cost is None:
            total_cost = self.DEFAULT_COSTS[intervention]['total']

        # Calculate LNPV
        lnpv_result = self.npv_calculator.calculate_lnpv(
            intervention, gender, location, region, discount_rate
        )

        lnpv = lnpv_result['lnpv']

        # Calculate both BCRs
        bcr_full = lnpv / total_cost if total_cost > 0 else 0
        bcr_rwf_only = lnpv / rwf_cost if rwf_cost > 0 else 0

        # Decision recommendations
        def get_recommendation(bcr):
            if bcr >= 10:
                return "EXCEPTIONAL"
            elif bcr >= 3:
                return "HIGHLY COST-EFFECTIVE"
            elif bcr >= 1:
                return "COST-EFFECTIVE"
            else:
                return "NOT COST-EFFECTIVE"

        return {
            **lnpv_result,
            # Cost inputs
            'rwf_cost': rwf_cost,
            'total_cost': total_cost,
            # BCR calculations
            'bcr_full': bcr_full,
            'bcr_rwf_only': bcr_rwf_only,
            # Recommendations
            'recommendation_full': get_recommendation(bcr_full),
            'recommendation_rwf_only': get_recommendation(bcr_rwf_only),
            # Multiplier effect (how much RWF unlocks)
            'unlocked_ratio': total_cost / rwf_cost if rwf_cost > 0 else 0,
        }

    def run_sensitivity_analysis(
        self,
        intervention: Intervention,
        gender: Gender = Gender.MALE,
        location: Location = Location.URBAN,
        region: Region = Region.WEST,
        discount_rates: List[float] = None,
        time_horizons: List[int] = None,
        rwf_costs: List[float] = None,
        total_costs: List[float] = None,
        tax_adjustment: float = 1.0
    ) -> Dict:
        """
        Run sensitivity analysis across discount rates and time horizons.

        Args:
            intervention: RTE or APPRENTICESHIP
            gender, location, region: Demographics for baseline
            discount_rates: List of rates to test (default: [0.03, 0.05, 0.08])
            time_horizons: List of years to test (default: [20, 30, 35, 40])
            rwf_costs: List of RWF costs to test
            total_costs: List of total costs to test
            tax_adjustment: Multiplier for net-of-tax analysis (default: 1.0 = gross)
                           Use 0.85-0.90 for approximate net-of-tax earnings

        Returns:
            Dict with sensitivity matrices
        """
        # Defaults
        if discount_rates is None:
            discount_rates = [0.03, 0.05, 0.08]  # Low, Central, High
        if time_horizons is None:
            time_horizons = [20, 30, 35, 40]  # Years of working life (incl. 20yr per checklist)
        if rwf_costs is None:
            rwf_costs = [self.DEFAULT_COSTS[intervention]['rwf_only']]
        if total_costs is None:
            total_costs = [self.DEFAULT_COSTS[intervention]['total']]

        results = {
            'intervention': intervention.value,
            'demographic': f"{gender.value}_{location.value}_{region.value}",
            'tax_adjustment': tax_adjustment,
            'earnings_basis': 'gross' if tax_adjustment == 1.0 else f'net (adj={tax_adjustment})',
            'discount_rate_sensitivity': [],
            'time_horizon_sensitivity': [],
            'cost_sensitivity': [],
        }

        # Sensitivity across discount rates
        for rate in discount_rates:
            result = self.calculate_dual_bcr(
                intervention, gender, location, region,
                discount_rate=rate
            )
            # Apply tax adjustment to LNPV
            adj_lnpv = result['lnpv'] * tax_adjustment
            adj_bcr_full = adj_lnpv / result['total_cost'] if result['total_cost'] > 0 else 0
            adj_bcr_rwf = adj_lnpv / result['rwf_cost'] if result['rwf_cost'] > 0 else 0

            results['discount_rate_sensitivity'].append({
                'discount_rate': rate,
                'lnpv': adj_lnpv,
                'lnpv_gross': result['lnpv'],
                'bcr_full': adj_bcr_full,
                'bcr_rwf_only': adj_bcr_rwf,
            })

        # Sensitivity across time horizons
        for horizon in time_horizons:
            # Create modified params with different working life
            modified_params = ParameterRegistry()
            modified_params.WORKING_LIFE_FORMAL.value = horizon
            modified_calc = DualBCRCalculator(params=modified_params)

            result = modified_calc.calculate_dual_bcr(
                intervention, gender, location, region
            )
            # Apply tax adjustment
            adj_lnpv = result['lnpv'] * tax_adjustment
            adj_bcr_full = adj_lnpv / result['total_cost'] if result['total_cost'] > 0 else 0
            adj_bcr_rwf = adj_lnpv / result['rwf_cost'] if result['rwf_cost'] > 0 else 0

            results['time_horizon_sensitivity'].append({
                'time_horizon_years': horizon,
                'lnpv': adj_lnpv,
                'lnpv_gross': result['lnpv'],
                'bcr_full': adj_bcr_full,
                'bcr_rwf_only': adj_bcr_rwf,
            })

        # Sensitivity across cost inputs
        for rwf_cost in rwf_costs:
            for total_cost in total_costs:
                result = self.calculate_dual_bcr(
                    intervention, gender, location, region,
                    rwf_cost=rwf_cost, total_cost=total_cost
                )
                # Apply tax adjustment
                adj_lnpv = result['lnpv'] * tax_adjustment
                adj_bcr_full = adj_lnpv / total_cost if total_cost > 0 else 0
                adj_bcr_rwf = adj_lnpv / rwf_cost if rwf_cost > 0 else 0

                results['cost_sensitivity'].append({
                    'rwf_cost': rwf_cost,
                    'total_cost': total_cost,
                    'lnpv': adj_lnpv,
                    'lnpv_gross': result['lnpv'],
                    'bcr_full': adj_bcr_full,
                    'bcr_rwf_only': adj_bcr_rwf,
                })

        return results

    def run_tax_sensitivity(
        self,
        intervention: Intervention,
        gender: Gender = Gender.MALE,
        location: Location = Location.URBAN,
        region: Region = Region.WEST,
        tax_adjustments: List[float] = None
    ) -> Dict:
        """
        Run sensitivity analysis across tax adjustment scenarios.

        Compares gross vs net-of-tax earnings impact on BCR.

        Args:
            intervention: RTE or APPRENTICESHIP
            gender, location, region: Demographics for baseline
            tax_adjustments: List of multipliers (default: [1.0, 0.90, 0.85])
                            1.0 = gross earnings, 0.85 = ~15% effective tax

        Returns:
            Dict with tax sensitivity results
        """
        if tax_adjustments is None:
            tax_adjustments = [1.0, 0.90, 0.85]

        # Get baseline gross LNPV
        baseline = self.calculate_dual_bcr(intervention, gender, location, region)

        results = {
            'intervention': intervention.value,
            'demographic': f"{gender.value}_{location.value}_{region.value}",
            'lnpv_gross': baseline['lnpv'],
            'tax_sensitivity': []
        }

        for adj in tax_adjustments:
            adj_lnpv = baseline['lnpv'] * adj
            adj_bcr_full = adj_lnpv / baseline['total_cost'] if baseline['total_cost'] > 0 else 0
            adj_bcr_rwf = adj_lnpv / baseline['rwf_cost'] if baseline['rwf_cost'] > 0 else 0

            results['tax_sensitivity'].append({
                'tax_adjustment': adj,
                'earnings_basis': 'gross' if adj == 1.0 else f'net (~{int((1-adj)*100)}% tax)',
                'lnpv': adj_lnpv,
                'bcr_full': adj_bcr_full,
                'bcr_rwf_only': adj_bcr_rwf,
            })

        return results

    def calculate_all_scenarios(
        self,
        rwf_cost: float = None,
        total_cost: float = None
    ) -> List[Dict]:
        """
        Calculate dual BCRs for all demographic scenarios.

        Returns list of 32 scenario results (2 interventions × 4 regions × 2 genders × 2 locations).
        """
        results = []

        for intervention in Intervention:
            # Use intervention-specific defaults if not provided
            _rwf_cost = rwf_cost or self.DEFAULT_COSTS[intervention]['rwf_only']
            _total_cost = total_cost or self.DEFAULT_COSTS[intervention]['total']

            for region in Region:
                for gender in Gender:
                    for location in Location:
                        result = self.calculate_dual_bcr(
                            intervention, gender, location, region,
                            rwf_cost=_rwf_cost, total_cost=_total_cost
                        )
                        results.append(result)

        return results

    def format_dual_bcr_table(self, results: List[Dict] = None) -> str:
        """
        Format dual BCR results as readable table.

        Args:
            results: List of scenario results (if None, calculates all)

        Returns:
            Formatted string table
        """
        if results is None:
            results = self.calculate_all_scenarios()

        output = "\n" + "=" * 100 + "\n"
        output += "DUAL BCR ANALYSIS RESULTS\n"
        output += "=" * 100 + "\n\n"

        output += f"{'Intervention':<15} {'Demographics':<25} {'LNPV':>12} "
        output += f"{'BCR (Full)':>12} {'BCR (RWF)':>12} {'Unlock':>8}\n"
        output += "-" * 100 + "\n"

        for r in results:
            demo = f"{r['gender']}_{r['location']}_{r['region']}"
            output += f"{r['intervention']:<15} {demo:<25} "
            output += f"{format_currency(r['lnpv']):>12} "
            output += f"{r['bcr_full']:>11.1f}× "
            output += f"{r['bcr_rwf_only']:>11.1f}× "
            output += f"{r['unlocked_ratio']:>7.1f}×\n"

        output += "=" * 100 + "\n"

        # Summary statistics
        rte_results = [r for r in results if r['intervention'] == 'rte']
        app_results = [r for r in results if r['intervention'] == 'apprenticeship']

        output += "\nSUMMARY STATISTICS:\n"
        output += "-" * 50 + "\n"

        if rte_results:
            output += f"RTE:\n"
            output += f"  LNPV Range: {format_currency(min(r['lnpv'] for r in rte_results))} - "
            output += f"{format_currency(max(r['lnpv'] for r in rte_results))}\n"
            output += f"  BCR (Full) Range: {min(r['bcr_full'] for r in rte_results):.1f}× - "
            output += f"{max(r['bcr_full'] for r in rte_results):.1f}×\n"
            output += f"  BCR (RWF-only) Range: {min(r['bcr_rwf_only'] for r in rte_results):.1f}× - "
            output += f"{max(r['bcr_rwf_only'] for r in rte_results):.1f}×\n"
            output += f"  Average LNPV: {format_currency(np.mean([r['lnpv'] for r in rte_results]))}\n"
            output += f"  Average BCR (Full): {np.mean([r['bcr_full'] for r in rte_results]):.1f}×\n"
            output += f"  Average BCR (RWF-only): {np.mean([r['bcr_rwf_only'] for r in rte_results]):.1f}×\n"

        if app_results:
            output += f"\nApprenticeship:\n"
            output += f"  LNPV Range: {format_currency(min(r['lnpv'] for r in app_results))} - "
            output += f"{format_currency(max(r['lnpv'] for r in app_results))}\n"
            output += f"  BCR (Full) Range: {min(r['bcr_full'] for r in app_results):.1f}× - "
            output += f"{max(r['bcr_full'] for r in app_results):.1f}×\n"
            output += f"  BCR (RWF-only) Range: {min(r['bcr_rwf_only'] for r in app_results):.1f}× - "
            output += f"{max(r['bcr_rwf_only'] for r in app_results):.1f}×\n"
            output += f"  Average LNPV: {format_currency(np.mean([r['lnpv'] for r in app_results]))}\n"
            output += f"  Average BCR (Full): {np.mean([r['bcr_full'] for r in app_results]):.1f}×\n"
            output += f"  Average BCR (RWF-only): {np.mean([r['bcr_rwf_only'] for r in app_results]):.1f}×\n"

        output += "=" * 100 + "\n"

        return output


def run_dual_bcr_analysis(
    discount_rates: List[float] = None,
    rwf_costs_rte: List[float] = None,
    rwf_costs_app: List[float] = None
) -> Dict:
    """
    Run comprehensive dual BCR analysis with sensitivity.

    This is the MAIN ENTRY POINT for dual BCR calculations.

    Args:
        discount_rates: Rates to test (default: [0.03, 0.05, 0.08])
        rwf_costs_rte: RWF costs to test for RTE (default: [4000, 6000])
        rwf_costs_app: RWF costs to test for Apprenticeship (default: [4000, 6000])

    Returns:
        Comprehensive results dict with all scenarios and sensitivity analysis
    """
    if discount_rates is None:
        discount_rates = [0.03, 0.05, 0.08]
    if rwf_costs_rte is None:
        rwf_costs_rte = [4000, 6000]  # As requested by user
    if rwf_costs_app is None:
        rwf_costs_app = [4000, 6000]  # As requested by user

    calculator = DualBCRCalculator()

    print("\n" + "=" * 80)
    print("DUAL BCR ANALYSIS - RWF Economic Impact Model")
    print("=" * 80)
    print("\nRunning comprehensive analysis...")

    # 1. Baseline all scenarios
    all_results = calculator.calculate_all_scenarios()

    # 2. Sensitivity analysis for each intervention
    sensitivity_rte = calculator.run_sensitivity_analysis(
        intervention=Intervention.RTE,
        discount_rates=discount_rates,
        rwf_costs=rwf_costs_rte
    )

    sensitivity_app = calculator.run_sensitivity_analysis(
        intervention=Intervention.APPRENTICESHIP,
        discount_rates=discount_rates,
        rwf_costs=rwf_costs_app
    )

    # Print formatted results
    print(calculator.format_dual_bcr_table(all_results))

    # Print sensitivity summary
    print("\n" + "=" * 80)
    print("SENSITIVITY ANALYSIS: DISCOUNT RATES")
    print("=" * 80)
    print(f"\n{'Rate':>8} {'RTE LNPV':>15} {'RTE BCR':>12} {'App LNPV':>15} {'App BCR':>12}")
    print("-" * 65)

    for i, rate in enumerate(discount_rates):
        rte_data = sensitivity_rte['discount_rate_sensitivity'][i]
        app_data = sensitivity_app['discount_rate_sensitivity'][i]
        print(f"{rate:>7.0%} {format_currency(rte_data['lnpv']):>15} "
              f"{rte_data['bcr_full']:>11.1f}× "
              f"{format_currency(app_data['lnpv']):>15} "
              f"{app_data['bcr_full']:>11.1f}×")

    print("=" * 80)

    return {
        'all_scenarios': all_results,
        'sensitivity_rte': sensitivity_rte,
        'sensitivity_app': sensitivity_app,
        'discount_rates_tested': discount_rates,
        'rwf_costs_tested_rte': rwf_costs_rte,
        'rwf_costs_tested_app': rwf_costs_app,
    }


# ====
# SECTION 12: UTILITY FUNCTIONS AND MAIN INTERFACE
# ====

def format_currency(value: float) -> str:
    """Format value as Indian Rupees."""
    if abs(value) >= 1e7:
        return f"Rs {value/1e7:.2f} Cr"
    elif abs(value) >= 1e5:
        return f"Rs {value/1e5:.2f} L"
    elif abs(value) >= 1e3:
        return f"Rs {value/1e3:.1f}K"
    else:
        return f"Rs {value:.0f}"


def adjust_npv_to_intervention_year(
    npv_at_entry: float,
    years_to_entry: int,
    discount_rate: float = 0.0372
) -> float:
    """
    Convert NPV from labor market entry year to intervention year.
    
    Use case: Comparing benefits (at labor market entry) to costs (at intervention).
    
    Args:
        npv_at_entry: NPV calculated at labor market entry (our standard output)
        years_to_entry: Years from intervention to labor market entry
                       - RTE: 16 years (enroll age 6 â†’ entry age 22)
                       - Apprenticeship: 0-2 years (start age 18-20 â†’ entry age 18-20)
        discount_rate: Social discount rate (default 3.72%)
    
    Returns:
        NPV in intervention-year terms (further discounted)
    
    Example:
        RTE intervention in 2025 â†’ labor market entry 2041 (16 years)
        NPV_2041 = Rs 22.8L (in 2025 prices, at 2041 entry)
        NPV_2025 = 22.8L / (1.0372)^16 = Rs 12.2L
        
        Interpretation: The Rs 22.8L benefit starting in 2041 is worth
        Rs 12.2L in "2025 intervention-year terms" after accounting for
        the 16-year delay before benefits begin.
    
    Note: This adjustment is OPTIONAL and only needed for specific comparisons.
    Standard LNPV outputs use labor market entry as base year, which is
    appropriate for cross-intervention comparison and policy analysis.
    """
    if years_to_entry < 0:
        raise ValueError("years_to_entry must be non-negative")
    
    if years_to_entry == 0:
        return npv_at_entry  # No adjustment needed
    
    # Additional discounting for delay between intervention and labor market entry
    adjustment_factor = (1 + discount_rate) ** years_to_entry
    npv_at_intervention = npv_at_entry / adjustment_factor
    
    return npv_at_intervention


def demonstrate_npv_conversion():
    """
    Demonstrate NPV conversion between different base years.
    
    Shows how to interpret NPV values and convert between reference frames.
    """
    # Example: RTE intervention
    npv_at_entry_rte = 2280000  # Rs 22.8L at labor market entry (age 22)
    years_rte = 16  # Age 6 enrollment â†’ age 22 entry
    
    npv_at_intervention_rte = adjust_npv_to_intervention_year(
        npv_at_entry_rte, years_rte
    )
    
    print("\n" + "="*70)
    print("NPV CONVERSION EXAMPLE: RTE Intervention")
    print("="*70)
    print(f"Scenario: Child enrolls at age 6 (2025), enters labor market at age 22 (2041)")
    print(f"\nNPV at labor market entry (2041): {format_currency(npv_at_entry_rte)}")
    print(f"  â†’ This is our standard output")
    print(f"  â†’ In '2025 prices' (no inflation projection)")
    print(f"  â†’ Base year = 2041 (when earnings start)")
    print(f"\nNPV at intervention year (2025): {format_currency(npv_at_intervention_rte)}")
    print(f"  â†’ Further discounted by 16 years (delay before benefits)")
    print(f"  â†’ Useful for comparing to 2025 program costs")
    print(f"  â†’ Reduction: {(1 - npv_at_intervention_rte/npv_at_entry_rte)*100:.1f}%")
    
    # Example: Apprenticeship intervention
    npv_at_entry_app = 10400000  # Rs 1.04Cr at labor market entry (age 18-20)
    years_app = 0  # Immediate labor market entry after 1-year training
    
    npv_at_intervention_app = adjust_npv_to_intervention_year(
        npv_at_entry_app, years_app
    )
    
    print("\n" + "="*70)
    print("NPV CONVERSION EXAMPLE: Apprenticeship Intervention")
    print("="*70)
    print(f"Scenario: Youth starts training at age 18-20, enters market after 1 year")
    print(f"\nNPV at labor market entry: {format_currency(npv_at_entry_app)}")
    print(f"NPV at intervention year: {format_currency(npv_at_intervention_app)}")
    print(f"  â†’ Same value (years_to_entry = 0)")
    print(f"  â†’ Apprenticeship benefits start immediately after training")
    print("="*70)
    print("\nKEY INSIGHT: RTE has longer delay â†’ larger discount adjustment")
    print(f"RTE discount factor: {1/(1.0372**16):.3f} (16 years)")
    print(f"Apprenticeship discount factor: {1/(1.0372**0):.3f} (0 years)")
    print("="*70)


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
    print("\nInitializing RWF Economic Impact Model v4.1...")
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
    
    # Run scenario comparison examples
    print("\n" + "="*80)
    print("SCENARIO COMPARISON EXAMPLES")
    print("="*80)
    
    # Example 1: Apprenticeship (Urban Male, West)
    print("\nExample 1: Apprenticeship - Urban Male, West")
    app_scenarios = run_scenario_comparison(
        intervention=Intervention.APPRENTICESHIP,
        gender=Gender.MALE,
        location=Location.URBAN,
        region=Region.WEST
    )
    print(format_scenario_comparison(app_scenarios))
    
    # Example 2: RTE (Rural Female, South)
    print("\nExample 2: RTE - Rural Female, South")
    rte_scenarios = run_scenario_comparison(
        intervention=Intervention.RTE,
        gender=Gender.FEMALE,
        location=Location.RURAL,
        region=Region.SOUTH
    )
    print(format_scenario_comparison(rte_scenarios))
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)