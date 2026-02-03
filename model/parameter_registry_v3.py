"""
RightWalk Foundation Economic Impact Model - Parameter Registry
================================================================

VERSION: 3.3
UPDATED: January 18, 2026 (CSV SSOT Sync)
PREVIOUS: January 14, 2026 v3.2 (Phase 1 Alignment 100% COMPLETE)

CHANGES IN v3.3 (Jan 18, 2026 - CSV SSOT Sync):
- FORMAL_MULTIPLIER: 2.0 → 2.25 (ILO 2024: Urban 2.24x, Rural 2.48x)
- P_FORMAL_HIGHER_SECONDARY: 20% → 9.1% (ILO India Employment Report 2024)
- MINCER_RETURN_HS: 5.8% → 7.0% (Mitra 2019 via Chen et al. 2022)
- TEST_SCORE_TO_YEARS: 4.7 → 6.8 (Angrist & Evans 2020 micro-LAYS)
- APPRENTICE_STIPEND_MONTHLY: ₹10,000 → ₹7,000 (Gazette 2019 rates)
- RTE_TEST_SCORE_GAIN range: 0.15-0.30 → 0.10-0.35 (ITT alternative)
- SCENARIO_CONFIGS updated with new P_FORMAL_HIGHER_SECONDARY baseline

CHANGES IN v3.2 (Jan 14, 2026 - Session 2):
- Phase 2 Complete: Task 2.3 - All BASELINE_WAGES sampling_method changed to "fixed"
  * Rationale: PLFS wages are measured data, not estimated parameters
  * Monte Carlo should NOT vary empirically observed wage levels
- Validation: All 8/8 integrity tests pass (validate_model_integrity.py)
- Documentation: RWF_Project_Registry_Comprehensive_updated.md updated to v1.3

CHANGES IN v3.1 (Jan 14, 2026):
- Phase 1 Alignment: Tasks 1.1-1.5 completed (Bug Fixes)
- Phase 1 Alignment: Tasks 2.1-2.3 completed (Parameter Range Alignment)
  * REAL_WAGE_GROWTH range: (0.0, 0.01) → (-0.005, 0.01) [asymmetric]
  * EXPERIENCE_LINEAR range: aligned to v3 (0.005, 0.012)
  * EXPERIENCE_QUAD range: aligned to v3 (-0.0002, -0.00005)
- Phase 1 Alignment: Tasks 3.1-3.3 completed (Scenario Configuration)
  * ParameterRegistry defaults synced with v3 'moderate' scenario
  * P_FORMAL_APPRENTICE: 0.75 → 0.72 (RWF validated)
  * P_FORMAL_HIGHER_SECONDARY: 0.2 → 0.4 (moderate assumption)
  * SCENARIO_CONFIGS['moderate'] → empty dict (uses registry defaults)
  * Added run_official_analysis() wrapper in v4
- Phase 1 Alignment: Task 4.1 completed (Embedded Ratio)
  * Added get_embedded_ratio() function (SECTION 2B)
  * Added EMBEDDED_RATIO constants for all demographics
- Documentation: Progress tracked in phase1_execution_log.md

CHANGES IN v3.0 (Dec 26, 2025):
- FORMAL_MULTIPLIER: 2.25 → 2.0 (conservative midpoint, total compensation)
- FORMAL_MULTIPLIER tier: 3 → 2 (moderate uncertainty due to large NPV impact)
- RTE scenarios updated per Anand: 30%/40%/50% P(Formal|RTE) 
- Fixed double-counting documentation (see economic_core_v4.py for implementation)
- Added FORMAL_MULTIPLIER to scenario configurations

PREVIOUS UPDATES:
- v2.1 (Dec 14, 2025): Scenario Framework Implementation
- v2.0 (Nov 25, 2025): PLFS 2023-24 Data Extraction (Milestone 2)
- P_FORMAL_APPRENTICE validated at 72% (RWF actual data, Nov 2025)

CRITICAL FINDINGS FROM PLFS 2023-24:
- Returns to education declined 32% from 2005-2018 estimates (8.6% → 5.8%)
- Real wage growth stagnated to 0.01% (2020-24) vs. historical 2-3%
- Experience premiums collapsed 78% from literature values
- PLFS formal/informal wage ratio: 1.86× (lower than literature 2.25×)

This registry contains all parameters for the Lifetime Net Present Value (LNPV)
model with complete source documentation and sampling methods for Monte Carlo analysis.

TIER CLASSIFICATION:
- Tier 1 (CRITICAL): Highest uncertainty, largest impact on NPV (formal sector entry, treatment effects)
- Tier 2 (MODERATE): Some uncertainty but reasonable proxies (Mincer returns, wage differentials)
- Tier 3 (REASONABLE): Well-established with low uncertainty (discount rate, working life)

SCENARIO FRAMEWORK (Section 9B - Updated Dec 26, 2025):
- Conservative: 50% apprentice placement, 30% RTE formal entry (per Anand guidance)
- Moderate: 72% apprentice placement (RWF data), 40% RTE formal entry
- Optimistic: 90% apprentice placement, 50% RTE formal entry (capped per Anand)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

# =============================================================================
# PARAMETER METADATA STRUCTURE
# =============================================================================

@dataclass
class Parameter:
    """
    Container for model parameters with full documentation.
    
    Attributes:
        name: Parameter name
        symbol: Mathematical notation
        value: Point estimate (central value)
        unit: Measurement unit
        source: Data source or citation
        tier: Uncertainty tier (1=highest, 3=lowest)
        sensitivity_range: (min, max) for sensitivity analysis
        sampling_method: Distribution type for Monte Carlo ('uniform', 'normal', 'triangular', 'beta')
        sampling_params: Parameters for distribution (e.g., (mean, sd) for normal)
        notes: Additional context, limitations, or caveats
        last_updated: Date of last update
        
        # Sensitivity Analysis Summary (added Jan 2026)
        sensitivity_rank_rte: Rank by NPV impact for RTE intervention (1=highest)
        sensitivity_rank_app: Rank by NPV impact for Apprenticeship intervention (1=highest)
        npv_impact_pct_rte: Percentage NPV swing for RTE (max-min)/baseline*100
        npv_impact_pct_app: Percentage NPV swing for Apprenticeship
        last_sensitivity_run: ISO date of last sensitivity analysis run
    """
    name: str
    symbol: str
    value: float
    unit: str
    source: str
    tier: int
    sensitivity_range: Tuple[float, float]
    sampling_method: str
    sampling_params: Optional[Tuple] = None
    notes: str = ""
    last_updated: str = "2025-12-12"
    # Sensitivity analysis summary fields (Jan 2026)
    sensitivity_rank_rte: Optional[int] = None
    sensitivity_rank_app: Optional[int] = None
    npv_impact_pct_rte: Optional[float] = None
    npv_impact_pct_app: Optional[float] = None
    last_sensitivity_run: Optional[str] = None

# =============================================================================
# SECTION 1: WAGE EQUATION PARAMETERS (Mincer Returns)
# =============================================================================

# CRITICAL UPDATE: Returns to education have DECLINED significantly
# Old value (Agrawal 2012): 8.6% per year
# New value (PLFS 2023-24): 5.8% per year for higher secondary
# This represents 32% decline in returns over 12-year period

MINCER_RETURN_HS = Parameter(
    name="Mincer Return (Higher Secondary)",
    symbol="β₁",
    value=0.07,  # 7.0% per year of schooling - UPDATED Jan 2026
    unit="proportional increase per year",
    source="Mitra (2019) via Chen et al. (2022) - quantile returns 5-9%",
    tier=2,
    sensitivity_range=(0.05, 0.09),  # Mitra 2019: 5% (lowest quantile) to 9% (highest)
    sampling_method="triangular",
    sampling_params=(0.05, 0.07, 0.09),  # (min, mode, max)
    notes="""
    UPDATED Jan 2026: Using Mitra (2019) estimates reported in Chen et al. (2022).

    Key finding: Returns vary by wage quantile:
    - Lowest quantile: 5%
    - Highest quantile: 9%
    - Midpoint: 7% (used as central estimate)

    This is more recent than older 2002-2012 studies showing 9-12% returns.
    The 7% value reflects distributional insight useful for sensitivity modeling.

    Regional variation remains relevant:
    - Urban South/West: ~8% (higher quantiles)
    - Rural North/East: ~5-6% (lower quantiles)

    IMPLICATION: LNPV estimates will be 15-20% higher than using 5.8%.
    The 5-9% range captures meaningful uncertainty in returns.
    """
)

EXPERIENCE_LINEAR = Parameter(
    name="Experience Premium (Linear)",
    symbol="β₂",
    value=0.00885,  # 0.885% per year of experience
    unit="proportional increase per year",
    source="PLFS 2023-24 cross-sectional age-wage profiles",
    tier=3,
    sensitivity_range=(0.005, 0.012),
    sampling_method="uniform",
    sampling_params=(0.005, 0.012),
    notes="""
    MAJOR FINDING: Experience premiums have collapsed 78% from literature values (0.04-0.06).
    
    This reflects:
    - Wage stagnation in informal sector (no experience premium)
    - Flat wage-age profiles even in formal sector (limited progression)
    - Youth cohorts not seeing wage growth that older cohorts experienced
    
    Calculated from PLFS 2023-24 by regressing log(wage) on years of experience
    for workers with higher secondary education (controlling for gender, urban/rural).
    
    This low value means lifetime earnings grow very slowly even with experience.
    Peak earnings occur later (age 50-55) rather than earlier (40-45).
    """
)

EXPERIENCE_QUAD = Parameter(
    name="Experience Premium (Quadratic)",
    symbol="β₃",
    value=-0.000123,  # Concavity parameter
    unit="proportional change per year²",
    source="PLFS 2023-24 cross-sectional age-wage profiles",
    tier=3,
    sensitivity_range=(-0.0002, -0.00005),
    sampling_method="uniform",
    sampling_params=(-0.0002, -0.00005),
    notes="""
    Less negative than literature values (-0.001), indicating less concavity.
    
    Interpretation: Wage-age profile is flatter overall.
    - Peak earnings occur later in career
    - Less wage decline post-peak
    - But combined with low β₂, overall earnings growth is minimal
    
    This parameter has LOW impact on NPV relative to β₁ and β₂.
    """
)

# =============================================================================
# SECTION 2: BASELINE WAGES (2025 Data)
# =============================================================================

# Complete wage matrix: urban/rural × male/female × education level
# Source: PLFS 2023-24 Annual Report

BASELINE_WAGES = {
    'urban_male': {
        'secondary_10yr': Parameter(
            name="Urban Male Baseline Wage (Secondary, 10yr)",
            symbol="W₀_UM_S",
            value=26105,  # ₹26,105/month
            unit="INR/month",
            source="PLFS 2023-24 Table 21 - Average monthly earnings, urban male, secondary education",
            tier=3,
            sensitivity_range=(24000, 28000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Salaried workers, regular wage employment. Base year: 2025. NOT varied in Monte Carlo (measured data)."
        ),
        'higher_secondary_12yr': Parameter(
            name="Urban Male Baseline Wage (Higher Secondary, 12yr)",
            symbol="W₀_UM_HS",
            value=32800,  # ₹32,800/month
            unit="INR/month",
            source="Calculated from secondary wage using 5.8% Mincer return: 26105 × (1.058)² = 32,800",
            tier=3,
            sensitivity_range=(30000, 35000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Key anchor for RTE higher secondary completion scenario. NOT varied in Monte Carlo (measured data)."
        ),
        'casual_informal': Parameter(
            name="Urban Male Casual/Informal Wage",
            symbol="W₀_UM_INF",
            value=13425,  # ₹13,425/month
            unit="INR/month",
            source="PLFS 2023-24 daily casual wage ₹537 × 25 working days",
            tier=3,
            sensitivity_range=(12000, 15000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Counterfactual for informal sector entry. Assumes 25 working days/month. NOT varied in Monte Carlo."
        )
    },
    'urban_female': {
        'secondary_10yr': Parameter(
            name="Urban Female Baseline Wage (Secondary, 10yr)",
            symbol="W₀_UF_S",
            value=19879,
            unit="INR/month",
            source="PLFS 2023-24 Table 21",
            tier=3,
            sensitivity_range=(18000, 22000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Gender wage gap: 24% lower than urban male (₹26,105). NOT varied in Monte Carlo."
        ),
        'higher_secondary_12yr': Parameter(
            name="Urban Female Baseline Wage (Higher Secondary, 12yr)",
            symbol="W₀_UF_HS",
            value=24928,
            unit="INR/month",
            source="Calculated from secondary wage using 5.8% Mincer return",
            tier=3,
            sensitivity_range=(23000, 27000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Gender wage gap persists even at higher education levels. NOT varied in Monte Carlo."
        ),
        'casual_informal': Parameter(
            name="Urban Female Casual/Informal Wage",
            symbol="W₀_UF_INF",
            value=9129,
            unit="INR/month",
            source="PLFS 2023-24 daily casual wage ₹365 × 25 working days",
            tier=3,
            sensitivity_range=(8000, 10500),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Gender + informality double penalty: 32% lower than urban male informal. NOT varied in Monte Carlo."
        )
    },
    'rural_male': {
        'secondary_10yr': Parameter(
            name="Rural Male Baseline Wage (Secondary, 10yr)",
            symbol="W₀_RM_S",
            value=18200,
            unit="INR/month",
            source="PLFS 2023-24 Table 21",
            tier=3,
            sensitivity_range=(16500, 20000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Urban-rural gap: 30% lower than urban male (₹26,105). NOT varied in Monte Carlo."
        ),
        'higher_secondary_12yr': Parameter(
            name="Rural Male Baseline Wage (Higher Secondary, 12yr)",
            symbol="W₀_RM_HS",
            value=22880,
            unit="INR/month",
            source="Calculated from secondary wage using 5.8% Mincer return",
            tier=3,
            sensitivity_range=(21000, 25000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Key anchor for rural RTE scenarios. NOT varied in Monte Carlo."
        ),
        'casual_informal': Parameter(
            name="Rural Male Casual/Informal Wage",
            symbol="W₀_RM_INF",
            value=11100,
            unit="INR/month",
            source="PLFS 2023-24 daily casual wage ₹444 × 25 working days",
            tier=3,
            sensitivity_range=(10000, 12500),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Rural informal wage floor. Agricultural labor-dominated. NOT varied in Monte Carlo."
        )
    },
    'rural_female': {
        'secondary_10yr': Parameter(
            name="Rural Female Baseline Wage (Secondary, 10yr)",
            symbol="W₀_RF_S",
            value=12396,
            unit="INR/month",
            source="PLFS 2023-24 Table 21",
            tier=3,
            sensitivity_range=(11000, 14000),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Lowest formal wage: rural + gender gap. 52% lower than urban male. NOT varied in Monte Carlo."
        ),
        'higher_secondary_12yr': Parameter(
            name="Rural Female Baseline Wage (Higher Secondary, 12yr)",
            symbol="W₀_RF_HS",
            value=15558,
            unit="INR/month",
            source="Calculated from secondary wage using 5.8% Mincer return",
            tier=3,
            sensitivity_range=(14000, 17500),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Even with higher secondary, still 53% lower than urban male. NOT varied in Monte Carlo."
        ),
        'casual_informal': Parameter(
            name="Rural Female Casual/Informal Wage",
            symbol="W₀_RF_INF",
            value=7475,
            unit="INR/month",
            source="PLFS 2023-24 daily casual wage ₹299 × 25 working days",
            tier=3,
            sensitivity_range=(6500, 8500),
            sampling_method="fixed",  # CHANGED Jan 2026: Measured data, not varied in MC
            notes="Lowest counterfactual wage. Many rural women in unpaid family labor (not captured here). NOT varied in Monte Carlo."
        )
    }
}


# =============================================================================
# SECTION 2B: EMBEDDED RATIO CALCULATION
# =============================================================================

def get_embedded_ratio(location: str, gender: str) -> float:
    """Calculate embedded formal/informal wage ratio from PLFS baseline wages."""
    wage_key = f"{location}_{gender}"
    try:
        salaried = BASELINE_WAGES[wage_key]['secondary_10yr'].value
        casual = BASELINE_WAGES[wage_key]['casual_informal'].value
        return salaried / casual
    except:
        return 1.86

EMBEDDED_RATIO_AVERAGE = 1.86

# =============================================================================
# SECTION 3: SECTORAL PARAMETERS
# =============================================================================

FORMAL_MULTIPLIER = Parameter(
    name="[DEPRECATED] Formal vs. Informal Wage Multiplier",
    symbol="lambda_formal",
    value=2.25,  # DEPRECATED - retained for backward compatibility only
    unit="multiplier",
    source="[DEPRECATED] ILO India Employment Report 2024",
    tier=2,
    sensitivity_range=(2.24, 2.48),
    sampling_method="triangular",
    sampling_params=(2.24, 2.25, 2.48),
    notes="""
    ============================================================
    DEPRECATED: January 20, 2026 (Anand guidance Dec 2025)
    ============================================================

    THIS PARAMETER IS NO LONGER USED IN CALCULATIONS.
    Retained for backward compatibility and documentation only.

    REASON FOR DEPRECATION:
    Model was over-specified with 3 inconsistent data sources:
    1. PLFS formal wage: ₹32,800 (urban male HS)
    2. PLFS informal wage: ₹13,425 (urban male casual)
    3. FORMAL_MULTIPLIER: 2.25× (ILO target)

    PLFS embedded ratio = 32,800 / 13,425 = 2.44×
    This ALREADY EXCEEDS the ILO target of 2.25×!

    OLD CALCULATION (ELIMINATED):
    benefits_adjustment = FORMAL_MULTIPLIER / embedded_ratio
                       = 2.25 / 1.86 = 1.21×
    This inflated formal wages by 21% on top of already-high PLFS wages.

    NEW APPROACH (Jan 2026):
    - PLFS wages are Single Source of Truth (SSOT)
    - No benefits_adjustment applied
    - Formal wages = PLFS formal wages (₹32,800)
    - Informal wages = PLFS informal wages (₹13,425)

    See economic_core_v4.py calculate_wage() for implementation.
    """,
    last_updated="2026-01-20"
)


P_FORMAL_HIGHER_SECONDARY = Parameter(
    name="Formal Sector Entry Probability (Higher Secondary)",
    symbol="P(F|HS)",
    value=0.091,  # UPDATED Jan 2026: ILO 2024 shows 9.1% formal for HS youth
    unit="probability",
    source="ILO India Employment Report 2024 - 9.1% formal employment for secondary/HS youth",
    tier=1,  # TIER 1 - CRITICAL PARAMETER
    sensitivity_range=(0.05, 0.15),
    sampling_method="beta",
    sampling_params=(3, 30),  # Beta distribution centered at ~0.09
    notes="""
    CRITICAL UPDATE Jan 2026: Value reduced from 20% to 9.1%.

    ILO India Employment Report 2024 shows only 9.1% of youth with
    secondary/higher secondary education were in formal employment in 2022.

    This is the NATIONAL BASELINE for control group calculations.
    For RTE graduates, use P_FORMAL_RTE instead (higher due to selection effects).

    State heterogeneity:
    - Bihar: ~3% formal
    - Urban Bangalore: ~15% formal
    - National average: 9.1%

    Compare: 36.1% formal for college graduates (ILO 2024)

    MODEL FORMULA: E[Wage] = P_FORMAL_HS × formal_wage + (1-P_FORMAL_HS) × informal_wage
    With P=0.091: 9.1% get formal benefits, 90.9% stay informal.
    """
)

# NEW Jan 2026: Separate P_FORMAL for RTE graduates (Anand guidance Dec 2025)
P_FORMAL_RTE = Parameter(
    name="Formal Sector Entry Probability (RTE Graduates)",
    symbol="P(F|RTE)",
    value=0.30,  # 30% formal entry for RTE graduates
    unit="probability",
    source="RWF assumption: 3.3× national baseline (Anand guidance Dec 2025)",
    tier=1,  # TIER 1 - CRITICAL PARAMETER
    sensitivity_range=(0.20, 0.50),
    sampling_method="beta",
    sampling_params=(6, 14),  # Beta distribution centered at ~0.30
    notes="""
    NEW Jan 2026: RTE graduates assumed to have higher formal sector entry than
    national 9.1% baseline due to:

    1. Selection effects: RTE families are motivated, engaged parents
    2. Urban concentration: RTE schools predominantly in urban areas
    3. Private school networks: Alumni connections, placement support
    4. Quality signaling: Private school credential signals quality to employers

    Anand/Shipra guidance: "70% too high, 30-40% defensible"

    Range 20-50% reflects uncertainty:
    - 20% (lower): Minimal selection effect, 2.2× national baseline
    - 30% (central): Moderate effect, 3.3× national baseline [RECOMMENDED]
    - 50% (upper): Strong effect, 5.5× national baseline (Anand cap)

    This parameter REPLACES P_FORMAL_HIGHER_SECONDARY in RTE calculations.
    Control group still uses P_FORMAL_HIGHER_SECONDARY (9.1%).
    """
)

P_FORMAL_SECONDARY = Parameter(
    name="Formal Sector Entry Probability (Secondary)",
    symbol="P(F|S)",
    value=0.12,
    unit="probability",
    source="PLFS 2023-24 (estimated)",
    tier=1,
    sensitivity_range=(0.08, 0.15),
    sampling_method="beta",
    sampling_params=(3, 22),
    notes="""
    Lower than higher secondary. Used for counterfactual scenarios
    (e.g., RTE dropouts who complete only 10th grade).
    """
)

P_FORMAL_APPRENTICE = Parameter(
    name="Formal Sector Placement (Apprenticeship)",
    symbol="P(F|App)",
    value=0.72,  # 72% employer absorption rate - RWF ACTUAL DATA
    unit="probability",
    source="RWF placement data (validated Nov 2025)",
    tier=1,  # TIER 1 - CRITICAL PARAMETER
    sensitivity_range=(0.50, 0.90),
    sampling_method="beta",
    sampling_params=(15, 5),  # Beta skewed toward high values
    notes="""
    VALIDATED WITH RWF ACTUAL DATA (72% placement rate).
    
    This replaces previous MSDE administrative estimate of 75%.
    Confirmed from RWF's actual apprentice outcomes tracking.
    
    Context:
    - 72% of apprenticeship completers secure formal sector jobs
    - This is P(Formal | Completion), not P(Formal | Started)
    - Represents successful transition from training to formal work
    
    Previous concerns about MSDE data (reporting bias, cream-skimming) 
    are addressed by using RWF's direct operational data.
    
    Note: APPRENTICE_COMPLETION_RATE remains separate parameter (85%)
    which measures P(Completion | Started). Combined effect:
    P(Formal | Started) = 0.72 × 0.85 = 61.2% overall placement rate.
    
    Sensitivity analysis still tests range [50%, 90%] to bound uncertainty.
    """
)

# =============================================================================
# SECTION 4: MACROECONOMIC PARAMETERS
# =============================================================================

# =============================================================================
# SECTION 4B: SECTOR-SPECIFIC WAGE GROWTH (NEW Jan 2026 - Anand guidance)
# =============================================================================
#
# Anand Dec 2025: "In any wage growth the formal sector is higher and informal
# is lower... if you look at income inequality graphs from last 30 years in
# India the inequality is increasing... that basically screams that the hikes
# are higher in formal and informal might be actually negative."
#
# This captures growing inequality: formal workers progress, informal stagnate.
# =============================================================================

REAL_WAGE_GROWTH_FORMAL = Parameter(
    name="Real Wage Growth Rate (Formal Sector)",
    symbol="g_formal",
    value=0.015,  # 1.5% per year
    unit="annual growth rate",
    source="PLFS 2020-24 formal sector trends; India inequality literature",
    tier=2,
    sensitivity_range=(0.005, 0.025),
    sampling_method="triangular",
    sampling_params=(0.005, 0.015, 0.025),
    notes="""
    NEW Jan 2026: Formal sector workers see career progression through:
    - Promotions every 3-5 years (~10-15% jump)
    - Annual increments 5-7% nominal minus 4-5% inflation = 1-2% real
    - Skill accumulation and seniority benefits
    - EPF contributions accumulating

    Even during PLFS 2020-24 aggregate stagnation, formal workers progressed
    within firms. Growing inequality confirms formal pulling away from informal.

    Impact over 40-year career:
    - Year 0: Base wage
    - Year 40: Base × 1.015^40 = Base × 1.81 (81% cumulative growth)

    Evidence:
    - India Gini coefficient: 35.7 (2011) → 47.9 (2021) - rising inequality
    - Top 10% wage growth 2010-2020: ~4% real
    - Formal/informal wage gap widening: 1.86× (2012) → 2.44× (2024)
    """
)

REAL_WAGE_GROWTH_INFORMAL = Parameter(
    name="Real Wage Growth Rate (Informal Sector)",
    symbol="g_informal",
    value=-0.002,  # -0.2% per year (slight decline)
    unit="annual growth rate",
    source="PLFS 2020-24 informal stagnation; India inequality literature",
    tier=2,
    sensitivity_range=(-0.01, 0.005),
    sampling_method="triangular",
    sampling_params=(-0.01, -0.002, 0.005),
    notes="""
    NEW Jan 2026: Informal sector wages stagnate or decline due to:
    - No structured progression or seniority increments
    - Competition from younger/cheaper workers
    - Automation pressure on manual jobs
    - Gig economy race-to-bottom (Uber, delivery platforms)
    - Cash wages don't adjust for inflation

    Impact over 40-year career:
    - Year 0: Base wage
    - Year 40: Base × 0.998^40 = Base × 0.92 (8% cumulative DECLINE)

    Evidence:
    - Bottom 50% wage growth 2010-2020: ~0-1% real
    - Informal workers replaced by younger cohort at same wage
    - No union protection or collective bargaining

    Range captures uncertainty:
    - -1.0%: Gig economy race-to-bottom, automation
    - -0.2%: Moderate stagnation [CENTRAL ESTIMATE]
    - +0.5%: High-growth periods, labor shortage
    """
)

# DEPRECATED: Use REAL_WAGE_GROWTH_FORMAL and REAL_WAGE_GROWTH_INFORMAL instead
REAL_WAGE_GROWTH = Parameter(
    name="[DEPRECATED] Real Wage Growth Rate (Uniform)",
    symbol="g",
    value=0.0001,  # 0.01% - essentially ZERO
    unit="annual growth rate",
    source="PLFS 2020-24 wage data adjusted for CPI inflation (4-6% annually)",
    tier=2,
    sensitivity_range=(-0.005, 0.01),  # Test 0% to 1%
    sampling_method="uniform",
    sampling_params=(0.0, 0.01),
    notes="""
    ⚠️ DEPRECATED Jan 2026: Use REAL_WAGE_GROWTH_FORMAL and REAL_WAGE_GROWTH_INFORMAL.

    Model now uses sector-specific growth rates to capture growing inequality:
    - Formal sector: +1.5%/year (career progression)
    - Informal sector: -0.2%/year (stagnation/decline)

    This legacy parameter is retained for backward compatibility only.

    OLD NOTES (preserved for reference):
    CATASTROPHIC FINDING: Real wages have STAGNATED aggregate-level.
    Old assumption: 2-3% annual real growth
    New reality (2020-24): 0.01% - near zero aggregate

    IMPORTANT - DISCOUNTING METHODOLOGY CLARIFICATION (Dec 2025):
    This parameter represents WITHIN-CAREER wage growth dynamics, NOT an attempt
    to forecast future starting salaries. Our model uses CURRENT (2025) wages as
    baseline and applies this growth rate across the 40-year trajectory. We do NOT
    project what entry-level salaries will be in 2041 - that would require uncertain
    15-year forecasts. Instead, we use today's known wages and let 'g' capture
    the within-career progression. This is standard practice in education economics.
    See discounting_methodology_explanation.md for full details.
    """
)

SOCIAL_DISCOUNT_RATE = Parameter(
    name="Social Discount Rate",
    symbol="δ",
    value=0.05,  # UPDATED Jan 2026: 8.5% per Murty & Panda (2020) Ramsey formula
    unit="annual discount rate",
    source="Murty & Panda (2020) - Ramsey formula p + vg = 8.5% for India",
    tier=2,
    sensitivity_range=(0.03, 0.08),
    sampling_method="uniform",
    sampling_params=(0.03, 0.08),
    notes="""

    - Central value: 5-6% (consistent with extended Ramsey and 40-year horizon)
    - Range: [3%, 8%] for sensitivity analysis
    - 8.5% from original Murty & Panda (2020) assumes historical growth that we are not currently observing

    Sensitivity: Test range [3%, 5%, 8%] to bound uncertainty.
    """
)

INFLATION_RATE = Parameter(
    name="Consumer Price Index (CPI) Inflation",
    symbol="π",
    value=0.0495,  # 4.95% in 2025
    unit="annual inflation rate",
    source="MOSPI CPI dashboard, average 2025",
    tier=3,
    sensitivity_range=(0.04, 0.06),
    sampling_method="triangular",
    sampling_params=(0.04, 0.0495, 0.06),
    notes="""
    Used to deflate nominal wages to real terms.
    India's inflation has moderated from 10-12% (2010-2013) to 4-6% (2020-2024).
    
    Real wage = Nominal wage / (1 + Ï€)^t
    
    Combined with g=0.01%, this means nominal wages grow at ~5% but real wages flat.
    
    IMPORTANT - NOT USED IN NPV CALCULATIONS:
    This parameter is provided for reference but NOT directly used in our NPV model.
    Our model works entirely in REAL (inflation-adjusted) terms:
    - Baseline wages are already real (2025 prices)
    - REAL_WAGE_GROWTH (g=0.01%) captures real wage dynamics
    - SOCIAL_DISCOUNT_RATE (3.72%) is already a real discount rate
    
    We do NOT need to explicitly adjust for inflation because all values are
    already in constant-purchasing-power terms. This inflation rate is documented
    here to show the relationship: nominal growth ≈ 5% = inflation + real growth.
    """
)

# =============================================================================
# SECTION 5: INTERVENTION-SPECIFIC PARAMETERS
# =============================================================================

# --- RTE Intervention ---

RTE_TEST_SCORE_GAIN = Parameter(
    name="RTE Private School Test Score Gain",
    symbol="Δ_RTE",
    value=0.137,  # UPDATED Jan 2026: ITT estimate (was 0.23 ToT)
    unit="standard deviations",
    source="Muralidharan & Sundararaman (2013) NBER RCT w19441 - ITT estimate",
    tier=1,  # TIER 1 - External validity concern
    sensitivity_range=(0.10, 0.20),  # NARROWED Jan 2026 for ITT range
    sampling_method="triangular",
    sampling_params=(0.10, 0.137, 0.20),
    notes="""
    UPDATED Jan 2026: Now using ITT (Intent-to-Treat) estimate per Anand guidance.

    "We should actually think of per child allocated right because we are not
    sure that everybody will complete" - Anand Dec 2025

    ToT vs ITT:
    - ToT (Treatment on Treated): 0.23 SD - effect on those who completed treatment
    - ITT (Intent to Treat): 0.137 SD - effect on all allocated to treatment [NOW USED]

    ITT = ToT × Compliance Rate = 0.23 × 0.596 = 0.137 SD

    MODEL CHAIN (with ITT):
    0.137 SD × 6.8 years/SD = 0.93 equivalent years
    → exp(0.07 × 0.93) = 6.7% wage premium (vs 11.5% with ToT)

    Why ITT is more appropriate:
    - Measures effect "per child allocated" not "per completer"
    - Accounts for non-completion and attribution dilution
    - More conservative and policy-relevant estimate

    Subject heterogeneity in original study:
    - Hindi: 0.55 SD (ToT)
    - English: 0.12 SD (ToT)
    - Math: 0 SD (ToT)

    Range [0.10, 0.20] for ITT captures:
    - Lower (0.10): Low compliance, ~43% completion
    - Central (0.137): Original study compliance 59.6%
    - Upper (0.20): High compliance, ~87% completion
    """
)

RTE_EQUIVALENT_YEARS = Parameter(
    name="Test Score to Equivalent Years of Schooling",
    symbol="years/SD",
    value=4.7,  # 1 SD = 4.7 years of schooling
    unit="years per standard deviation",
    source="World Bank LMIC meta-analysis (Angrist et al. 2021)",
    tier=2,
    sensitivity_range=(4.0, 6.5),
    sampling_method="uniform",
    sampling_params=(4.0, 6.5),
    notes="""
    Global LMIC average. India-specific estimate not available.
    
    Converts: 0.23 SD × 4.7 years/SD = 1.08 equivalent years.
    
    Concern: This conversion assumes test scores → actual degree completion.
    Employers see credentials (degrees), not test scores.
    Effect only realized if test score gains → higher secondary/college completion.
    
    Missing link: Do RTE students have higher completion rates?
    """
)

# DEPRECATED Jan 2026: RTE_INITIAL_PREMIUM is NOT used in the current model.
# RTE treatment effect is calculated via:
#   - RTE_TEST_SCORE_GAIN → TEST_SCORE_TO_YEARS → Mincer return chain
#   - P_FORMAL_HIGHER_SECONDARY × regional scaling
# This parameter is retained for backward compatibility but will be removed in v4.0
RTE_INITIAL_PREMIUM = Parameter(
    name="[DEPRECATED] RTE Intervention Initial Wage Premium",
    symbol="π→π_RTE",
    value=98000,  # ₹98,000/year
    unit="INR/year",
    source="Calculated: (Private school formal wage - Counterfactual weighted avg) at labor market entry",
    tier=1,
    sensitivity_range=(70000, 120000),
    sampling_method="triangular",
    sampling_params=(70000, 98000, 120000),
    notes="""
    ⚠️ DEPRECATED Jan 2026: This parameter is NOT used in economic_core_v4.py.
    The RTE premium is now calculated dynamically via the Mincer chain:
    RTE_TEST_SCORE_GAIN → TEST_SCORE_TO_YEARS → additional years of schooling → wage premium

    This parameter is retained for reference only and will be removed in v4.0.

    Original calculation (Urban Male example):
    - Treatment: ₹32,800/mo × P(Formal|HS)=0.20 × 2.25 formal multiplier = ₹14,760/mo effective
    - Control: Weighted avg of govt (66.8%), low-fee private (30.6%), dropout (2.6%)
    - Premium: (₹14,760 - ₹6,600) × 12 = ₹98,000/year
    """
)

# --- Apprenticeship Intervention ---

# DEPRECATED Jan 2026: VOCATIONAL_PREMIUM has been replaced by APPRENTICE_INITIAL_PREMIUM
# The current model uses direct INR/year premium rather than proportional premium.
# This parameter is retained for backward compatibility but will be removed in v4.0
VOCATIONAL_PREMIUM = Parameter(
    name="[DEPRECATED] Vocational Training Wage Premium",
    symbol="Δ_voc",
    value=0.047,  # 4.7%
    unit="proportional wage increase",
    source="DGT National Tracer Study 2019-20 (ITI graduates proxy)",
    tier=2,
    sensitivity_range=(0.03, 0.06),
    sampling_method="triangular",
    sampling_params=(0.03, 0.047, 0.06),
    notes="""
    ⚠️ DEPRECATED Jan 2026: Replaced by APPRENTICE_INITIAL_PREMIUM (₹84,000/year).

    The current model uses APPRENTICE_INITIAL_PREMIUM in INR/year directly,
    which provides better transparency and easier stakeholder communication.

    Original calculation (retained for reference):
    - Informal wage: ₹11,100/mo (rural male)
    - Formal wage without vocational: ₹11,100 × 2.25 = ₹24,975/mo
    - Formal wage WITH vocational: ₹24,975 × 1.047 = ₹26,150/mo
    """
)

# =============================================================================
# SECTION 2B: PROGRAM COMPLETION AND RETENTION PARAMETERS (ADDED)
# =============================================================================

RTE_SEAT_FILL_RATE = Parameter(
    name="RTE 25% Quota Seat Fill Rate",
    symbol="P_fill",
    value=0.29,  # 29% national average
    unit="proportion",
    source="CAG Audit Report 2014 on RTE Implementation",
    tier=2,
    sensitivity_range=(0.20, 0.40),
    sampling_method="uniform",
    sampling_params=(0.20, 0.40),
    notes="""
    CRITICAL PROGRAM PARAMETER: Only 29% of reserved seats actually filled.
    
    State variation: 10-50% (Punjab: 48%, Bihar: 11%, national: 29%)
    
    Data limitations:
    - CAG audit is dated (2013-14), but no recent comprehensive audit
    - May reflect awareness/application barriers, not demand
    - State-specific data requires special requests from education departments
    
    IMPLICATION: Effective program reach = Fill rate × Retention rate
    If 29% fill and 60% retention → only 17.4% of eligible children get full treatment.
    
    This affects BCR calculation:
    - Per-completer BCR: LNPV / Cost_per_completer
    - Per-eligible BCR: (LNPV × Fill × Retention) / Cost_per_eligible
    """
)

RTE_RETENTION_FUNNEL = Parameter(
    name="RTE Program Retention Through Grade 12",
    symbol="P_retention",
    value=0.60,  # Assumed same as general EWS retention
    unit="proportion",
    source="UDISE+ EWS completion rates as proxy (no RTE-specific tracking)",
    tier=1,  # High uncertainty - NO direct data
    sensitivity_range=(0.50, 0.75),
    sampling_method="triangular",
    sampling_params=(0.50, 0.60, 0.75),
    notes="""
    TIER 1 GAP: No longitudinal tracking of RTE beneficiaries exists.
    
    Assumption: RTE students have same retention as private school average.
    This LIKELY OVERESTIMATES if:
    - RTE students face discrimination/social isolation
    - Families still can't afford textbooks/transport/uniform
    - Schools provide lower quality education to RTE students
    
    Transition stages:
    - Grade 1-8: 70-85% retention
    - Grade 8-10: 70-85% continuation 
    - Grade 10-12: 70-85% continuation
    - Overall: 60% complete Grade 12
    
    Regional variation (ASER):
    - Urban South/West: 65-75%
    - Rural North/East: 50-60%
    
    MODEL IMPACT:
    Program effectiveness = Fill rate × Retention
    29% × 60% = 17.4% effective reach
    
    This is CRITICAL for realistic BCR estimates.
    """
)

APPRENTICE_COMPLETION_RATE = Parameter(
    name="Apprenticeship Program Completion Rate",
    symbol="P_complete",
    value=0.85,  # Independent parameter (unchanged by 72% placement update)
    unit="proportion",
    source="MSDE funnel analysis; independent of placement rate",
    tier=1,  # High uncertainty - MSDE doesn't publish
    sensitivity_range=(0.75, 0.95),
    sampling_method="triangular",
    sampling_params=(0.75, 0.85, 0.95),
    notes="""
    TIER 1 GAP: MSDE tracks but doesn't publish dropout rates.
    
    CLARIFICATION (Dec 2025): This parameter is INDEPENDENT of placement rate.
    - P(Completion | Started) = 85% (this parameter)
    - P(Formal | Completion) = 72% (P_FORMAL_APPRENTICE, updated Nov 2025)
    - P(Formal | Started) = 0.72 × 0.85 = 61.2% (combined effect)
    
    Previous version incorrectly back-calculated from 75% placement assuming
    they were multiplicative. Now clarified:
    - Completion rate (85%) = proportion who finish training
    - Placement rate (72%) = proportion of completers who get formal jobs
    
    Dropout reasons (qualitative):
    - Stipend too low (₹7.5-15k/month, may not cover living costs)
    - Employer mismatch (assigned to unsuitable trade/location)
    - Family pressure (need to contribute income immediately)
    - Poor training quality (some employers use apprentices as cheap labor)
    
    Trade variation (anecdotal):
    - High completion: Manufacturing, engineering trades (80-90%)
    - Low completion: Services, hospitality (70-80%)
    - Average: 85%
    
    MODEL IMPACT:
    Effective LNPV = Base LNPV × Completion rate
    If base LNPV = ₹800k, effective = ₹680k (85% × ₹800k)
    
    BCR calculation:
    - Cost per enrollee = Total cost / Enrollees
    - Cost per completer = Total cost / Completers = Cost per enrollee / 0.85
    
    Sensitivity: Test [75%, 85%, 95%] to bound uncertainty.
    """
)


APPRENTICE_STIPEND_MONTHLY = Parameter(
    name="Apprenticeship Monthly Stipend",
    symbol="S_app",
    value=7000,  # UPDATED Jan 2026: ₹7,000/month per Gazette 2019
    unit="INR/month",
    source="Gazette notification 25 Sep 2019 (Table 5.50 in MSDE Report)",
    tier=3,
    sensitivity_range=(5000, 9000),
    sampling_method="triangular",
    sampling_params=(5000, 7000, 9000),
    notes="""
    UPDATED Jan 2026: Per Gazette notification dated 25th September 2019.

    Stipend rates by educational qualification:
    - Class 5-9 pass: ₹5,000/month
    - Class 10 pass: ₹6,000/month
    - Class 12 pass: ₹7,000/month (midpoint used)
    - Certificate/Diploma: ₹8,000/month
    - Graduate: ₹9,000/month

    Government support: Reimburses up to 25% of stipend (max ₹1,500/month).

    Annual calculation: ₹7,000 × 12 months = ₹84,000/year

    IMPACT ON MODEL:
    - Lower stipend increases Year 0 opportunity cost
    - Counterfactual informal wage (₹168k) - Stipend (₹84k) = -₹84k net cost
    - This cost must be recovered through higher post-training wages
    """
)

APPRENTICE_YEAR_0_OPPORTUNITY_COST = Parameter(
    name="Apprenticeship Year 0 Net Opportunity Cost",
    symbol="OC₀",
    value=-49000,  # Negative value = cost
    unit="INR/year",
    source="Calculated: (Stipend - Counterfactual informal wage). Represents foregone earnings during training.",
    tier=2,
    sensitivity_range=(-80000, -20000),
    sampling_method="triangular",
    sampling_params=(-80000, -49000, -20000),
    notes="""
    CRITICAL: Year 0 represents the 1-year apprenticeship training period.
    
    Calculation (baseline):
    - Stipend received: ₹10,000/month × 12 = ₹120,000/year
    - Counterfactual earnings: ₹14,000/month × 12 = ₹168,000/year
      (informal sector wage for youth with 10th pass, per PLFS 2023-24)
    - Net opportunity cost: ₹120,000 - ₹168,000 = -₹48,000 ≈ -₹49,000
    
    The NEGATIVE value indicates the apprentice earns LESS during training
    than they would have earned in informal work. This is a real economic cost
    that must be recovered through higher post-training wages.
    
    Sensitivity range reflects:
    - Pessimistic (-₹80k): High counterfactual wage, low stipend
      (Urban youth could earn ₹15-16k/month informally)
    - Optimistic (-₹20k): Low counterfactual wage, high stipend
      (Rural youth with limited alternatives)
    - Baseline (-₹49k): National average
    
    IMPACT ON NPV:
    This Year 0 cost reduces total LNPV by approximately ₹45-55k in present
    value terms (depending on discount rate), which is roughly 4-5% of the
    total apprenticeship LNPV.
    
    This parameter was added per feedback from Anand (Dec 2025) to accurately
    model the training year opportunity cost.
    """
)


APPRENTICE_INITIAL_PREMIUM = Parameter(
    name="Apprenticeship Intervention Initial Wage Premium",
    symbol="π→π_App",
    value=84000,  # ₹84,000/year
    unit="INR/year",
    source="Calculated: [(W_formal × P(F|App)) + (W_informal × (1-P(F|App)))] - [W_counterfactual]",
    tier=1,
    sensitivity_range=(50000, 110000),
    sampling_method="triangular",
    sampling_params=(50000, 84000, 110000),
    notes="""
    Calculation (Rural Male, 10th+vocational):
    
    Treatment pathway:
    - 72% formal placement: ₹18,200 × 2.25 × 1.047 = ₹42,900/mo
    - 28% informal fallback: ₹11,100/mo
    - Weighted: 0.72×₹42,900 + 0.28×₹11,100 = ₹33,996/mo
    
    Counterfactual (no apprenticeship):
    - 10% formal entry: ₹18,200 × 2.25 = ₹40,950/mo
    - 90% informal: ₹11,100/mo
    - Weighted: 0.10×₹40,950 + 0.90×₹11,100 = ₹14,085/mo
    
    Premium: (₹33,996 - ₹14,085) × 12 = ₹238,932/year ≈ ₹239k/year
    
    RECONCILIATION WITH ₹84k REGISTRY VALUE:
    The discrepancy (₹239k vs ₹84k) likely reflects:
    1. More conservative vocational premium assumption in ₹84k calculation
    2. Different baseline wage assumptions
    3. Adjustment for Year 0 stipend period (negative premium during training)
    
    Using DAILY wages (more accurate for youth):
    - Treatment: 72% × ₹444/day × 25 × 1.047 × 2.25 = ₹25,200/mo
    - Control: 10% × (₹444×25×2.25) + 90%×(₹444×25) = ₹12,500/mo
    - Premium: (₹25,200 - ₹12,500) × 12 = ₹152k/year
    
    For conservative modeling, ₹84k value may incorporate:
    - Lower vocational premium (3% vs 4.7%)
    - Regional adjustments for lower-formal-sector states
    - Adjustment for stipend year
    
    SENSITIVITY CRITICAL: Test [50%, 72%, 90%] placement rates.
    Updated from 75% to 72% based on RWF actual data (Nov 2025).
    """
)

APPRENTICE_DECAY_HALFLIFE = Parameter(
    name="Apprenticeship Wage Premium Decay Half-Life",
    symbol="h",
    value=10,  # 10 years
    unit="years",
    source="Assumed - no India-specific data available",
    tier=1,  # TIER 1 - CRITICAL UNKNOWN
    sensitivity_range=(5, 50),
    sampling_method="triangular",
    sampling_params=(5, 10, 50),
    notes="""
    TIER 1 GAP: No empirical data on persistence of vocational training premiums in India.

    Half-life determines how long apprenticeship wage advantage persists:
    - h=5 years: Premium decays to 50% after 5 years (pessimistic)
    - h=10 years: Premium decays to 50% after 10 years (baseline)
    - h=50 years: Effectively no decay (optimistic)

    After h years: Premium = Initial Premium × 0.5
    After 2h years: Premium = Initial Premium × 0.25

    NPV SENSITIVITY:
    - h=5 → LNPV ≈ ₹3.5L
    - h=10 → LNPV ≈ ₹8L
    - h=∞ → LNPV ≈ ₹22L

    This parameter interacts critically with APPRENTICE_INITIAL_PREMIUM.
    Two-dimensional sensitivity (π₀, h) required for robust estimates.

    Refinement needed: Tracer studies following apprentices 5-15 years post-completion.
    """
)

P_FORMAL_NO_TRAINING = Parameter(
    name="Formal Sector Entry Probability (Youth Without Vocational Training)",
    symbol="P(F|NoTrain)",
    value=0.10,  # 10%
    unit="probability",
    source="PLFS aggregate estimates (derived, not directly quoted)",
    tier=1,  # TIER 1 - HIGH UNCERTAINTY
    sensitivity_range=(0.05, 0.15),
    sampling_method="beta",
    sampling_params=(3, 27),  # Beta distribution centered at ~0.10
    notes="""
    TIER 1 WEAKNESS: This is the COUNTERFACTUAL for apprenticeship intervention.

    Represents baseline formal sector entry for youth with 10th/12th pass but
    NO vocational training. Critical for calculating apprenticeship treatment effect.

    Calculation approach (NOT verified with PLFS microdata):
    - From PLFS employment distribution tables
    - Filter: Age 18-25, Education=10th/12th, No vocational certification
    - P(Formal) = # in regular salaried / # total employed

    Regional variation (estimated):
    - Urban South/West: 12-15%
    - Rural North/East: 5-8%
    - National average: ~10%

    Bias concerns:
    - Cross-sectional data may not reflect current cohort prospects
    - Selection into vocational training confounds (motivated youth)
    - Definition of "formal" sector unclear in PLFS aggregates

    IMPLICATION FOR MODEL:
    Treatment effect = P(Formal|Apprentice) - P(Formal|NoTrain)
                     = 72% - 10% = 62 percentage points

    If true baseline is 15% (not 10%), treatment effect overstated by 8%.

    Refinement needed: Extract from PLFS microdata with proper controls.
    """
)

# =============================================================================
# SECTION 5B: PROGRAM COST PARAMETERS (ADDED Feb 2026)
# =============================================================================

# Two cost perspectives for BCR calculation:
# (A) Full BCR: RWF direct + government/private co-finance (unlocked funds)
# (B) RWF-only BCR: Only direct spend from RightWalk Foundation

RTE_COST_RWF_ONLY = Parameter(
    name="RTE Cost Per Beneficiary (RWF Direct Only)",
    symbol="C_RTE_RWF",
    value=4000,  # ₹4,000 per beneficiary
    unit="INR/beneficiary",
    source="RWF operational data (Shipra/Anand confirmation Jan 2026)",
    tier=3,
    sensitivity_range=(3000, 5000),
    sampling_method="uniform",
    sampling_params=(3000, 5000),
    notes="""
    RWF's direct spend per RTE beneficiary.
    Includes: outreach, enrollment support, monitoring.
    Does NOT include: government tuition reimbursement, school fees.

    This represents the marginal cost that RWF incurs to place one child
    in a private school under the RTE 25% quota.

    Used for RWF-only BCR calculation to show funder ROI.
    """
)

RTE_COST_TOTAL = Parameter(
    name="RTE Total Cost Per Beneficiary (Full Investment)",
    symbol="C_RTE_TOTAL",
    value=104000,  # ₹1.04 Lakhs total
    unit="INR/beneficiary",
    source="RWF operational data + government fee reimbursement estimates",
    tier=2,
    sensitivity_range=(90000, 120000),
    sampling_method="triangular",
    sampling_params=(90000, 104000, 120000),
    notes="""
    Full investment cost per RTE beneficiary:
    - RWF direct spend: ₹4,000
    - Government unlocked funds: ₹1,00,000 (fee reimbursement over 8 years)
    - Total: ₹1,04,000

    Government fees are reimbursed to schools under RTE Act at state-notified rates.
    Average: ~₹12,500/year × 8 years = ₹1,00,000.

    Used for Full BCR calculation showing total program economics.
    """
)

APPRENTICE_COST_RWF_ONLY = Parameter(
    name="Apprenticeship Cost Per Beneficiary (RWF Direct Only)",
    symbol="C_APP_RWF",
    value=6000,  # ₹6,000 per beneficiary
    unit="INR/beneficiary",
    source="RWF operational data (Shipra/Anand confirmation Jan 2026)",
    tier=3,
    sensitivity_range=(5000, 8000),
    sampling_method="uniform",
    sampling_params=(5000, 8000),
    notes="""
    RWF's direct spend per apprenticeship beneficiary.
    Includes: outreach, enrollment, employer matching, monitoring.
    Does NOT include: government stipend reimbursement, employer contributions.

    This represents the marginal cost that RWF incurs to place one youth
    in a National Apprenticeship Training Scheme (NATS) program.

    Used for RWF-only BCR calculation to show funder ROI.
    """
)

APPRENTICE_COST_TOTAL = Parameter(
    name="Apprenticeship Total Cost Per Beneficiary (Full Investment)",
    symbol="C_APP_TOTAL",
    value=158460,  # ₹1.58 Lakhs total
    unit="INR/beneficiary",
    source="RWF operational data + NATS cost structure",
    tier=2,
    sensitivity_range=(140000, 180000),
    sampling_method="triangular",
    sampling_params=(140000, 158460, 180000),
    notes="""
    Full investment cost per apprenticeship beneficiary:
    - RWF direct spend: ₹6,000
    - Government stipend support: ~₹21,000 (25% of stipend, max ₹1,500/mo × 14 mo)
    - Employer contribution: ~₹131,460 (stipend balance + training costs)
    - Total: ₹1,58,460

    Breakdown:
    - Stipend: ₹7,000/month × 12 months = ₹84,000/year
    - Govt reimburses 25%: ₹21,000
    - Employer pays 75% + training costs: ~₹63,000 + ₹68,460 = ₹131,460

    Used for Full BCR calculation showing total program economics.
    """
)

TEST_SCORE_TO_YEARS = Parameter(
    name="Test Score to Years of Schooling Conversion Factor",
    symbol="years/SD",
    value=6.8,  # UPDATED Jan 2026: Angrist & Evans (2020) micro-LAYS methodology
    unit="years per standard deviation",
    source="Angrist & Evans (2020) micro-LAYS rescaling methodology",
    tier=2,
    sensitivity_range=(4.0, 8.0),
    sampling_method="uniform",
    sampling_params=(4.0, 8.0),
    notes="""
    UPDATED Jan 2026: Using Angrist & Evans (2020) report of 6.8 years/SD.

    Previous value (4.7) based on earlier World Bank pooled estimates.
    The 6.8 value comes from micro-LAYS (Learning-Adjusted Years of Schooling)
    methodology which provides more current conversion factor.

    MODEL CHAIN for RTE:
    - Test score gain: 0.23 SD (from NBER RCT)
    - Equivalent years: 0.23 × 6.8 = 1.56 years (vs old 1.08)
    - Combined with Mincer 7%: exp(0.07 × 1.56) = 11.5% wage premium
    - Old calculation: exp(0.058 × 1.08) = 6.5% wage premium

    India-specific estimate: NOT AVAILABLE

    CAVEAT: Missing link between test scores and actual completion rates.
    Effect only realized if higher scores → higher graduation rates.
    Employers see credentials (degrees), not test scores.

    Sensitivity range 4.0-8.0 captures:
    - Lower bound (4.0): Conservative, older estimates
    - Upper bound (8.0): High-performing education systems
    """
)

LABOR_MARKET_ENTRY_AGE = Parameter(
    name="Labor Market Entry Age",
    symbol="age₀",
    value=22,  # Age 22 for higher secondary graduates
    unit="years",
    source="Standard assumption for post-higher secondary entry",
    tier=3,
    sensitivity_range=(18, 25),
    sampling_method="uniform",
    sampling_params=(18, 25),
    notes="""
    Typical age when higher secondary graduates enter formal labor market.

    Variation by pathway:
    - Apprenticeship: 18-20 years (immediate post-secondary)
    - Higher secondary only: 20-22 years (after 12th grade)
    - College graduates: 22-25 years (after bachelor's)

    This parameter affects NPV base year for discounting.

    For RTE intervention:
    - Child enrolls at age 6 (2025)
    - Completes higher secondary at age 18 (2037)
    - Enters labor market at age 22 (2041) - accounts for job search
    - NPV calculated at age 22 (labor market entry), not age 6 (enrollment)

    See discounting_methodology_explanation.md for full details on base year selection.
    """
)

# =============================================================================
# SECTION 6: COUNTERFACTUAL PARAMETERS
# =============================================================================

COUNTERFACTUAL_SCHOOLING = Parameter(
    name="Counterfactual EWS Schooling Distribution",
    symbol="(p_govt, p_private, p_dropout)",
    value=(0.668, 0.306, 0.026),  # Tuple: (govt %, private %, dropout %)
    unit="probability distribution",
    source="ASER 2023-24 weighted by household wealth quintile",
    tier=2,
    sensitivity_range=None,  # Categorical, use scenario analysis instead
    sampling_method="fixed",
    notes="""
    UPDATED from Milestone 2. Old assumptions:
    - Govt: 70%
    - Private: 20%
    - Dropout: 10%
    
    New reality (ASER 2023-24):
    - Govt: 66.8% (slight decrease)
    - Low-fee private: 30.6% (significant INCREASE)
    - Dropout: 2.6% (major DECREASE)
    
    Interpretation:
    - Post-COVID, EWS families increasingly opt for low-fee private schools
    - Dropout rates have declined (policy success + NFHS data)
    - BUT: More EWS in private schools → RAISES counterfactual baseline
      → LOWERS treatment effect of RTE (placing in private schools)
    
    This is FAVORABLE for model credibility:
    - RTE effect more conservative (not claiming huge gains when control group improving)
    - Reflects reality of India's education landscape evolution
    """
)

# =============================================================================
# SECTION 7: LIFECYCLE PARAMETERS
# =============================================================================

WORKING_LIFE_FORMAL = Parameter(
    name="Working Life Duration (Formal Sector)",
    symbol="T_formal",
    value=40,  # Age 22 to 62
    unit="years",
    source="Statutory retirement age (60-62) minus typical entry age (22 for graduates)",
    tier=3,
    sensitivity_range=(35, 42),
    sampling_method="uniform",
    sampling_params=(35, 42),
    notes="""
    Formal sector has defined retirement age:
    - Government: 60 years (some states 58)
    - Private: 58-60 years (EPFO rules)
    - Recent proposal to raise to 62-65 (not yet implemented)
    
    Entry age:
    - Higher secondary + college: 22 years
    - Apprenticeship: 18-20 years
    
    Use 40 years (age 22-62) as baseline for college-educated.
    Use 42-44 years for apprentices (earlier entry).
    """
)

WORKING_LIFE_INFORMAL = Parameter(
    name="Working Life Duration (Informal Sector)",
    symbol="T_informal",
    value=50,  # Age 15-18 to 65-70
    unit="years",
    source="e-Shram portal data + PLFS elderly employment rates",
    tier=3,
    sensitivity_range=(45, 55),
    sampling_method="uniform",
    sampling_params=(45, 55),
    notes="""
    Informal sector has NO fixed retirement:
    - Entry: Often 15-18 years (child labor, early school dropout)
    - Exit: Work as long as physically able (65-70+)
    - Driven by lack of pensions, savings, social security
    
    Caveat: Later years (60+) likely reduced productivity/income.
    Model should apply productivity discount factor (e.g., 0.5× after age 65).
    """
)

# =============================================================================
# SECTION 8: PARAMETER DEPENDENCIES AND RELATIONSHIPS
# =============================================================================

def get_wage_trajectory(
    baseline_wage: float,
    education_years: float,
    experience_years: float,
    is_formal: bool,
    real_wage_growth: float = REAL_WAGE_GROWTH.value
) -> float:
    """
    Calculate wage at time t using Mincer equation.
    
    W_t = W₀ × exp(β₁×Education + β₂×Exp + β₃×Exp²) × λ_formal^{is_formal} × (1+g)^t
    
    Args:
        baseline_wage: Starting wage (W₀) for reference group
        education_years: Years of schooling beyond reference
        experience_years: Years of work experience
        is_formal: Boolean, formal sector (True) or informal (False)
        real_wage_growth: Annual real wage growth rate (default 0.01%)
    
    Returns:
        float: Predicted wage at time t
    """
    import math
    
    # Mincer equation components
    education_premium = math.exp(
        MINCER_RETURN_HS.value * education_years +
        EXPERIENCE_LINEAR.value * experience_years +
        EXPERIENCE_QUAD.value * (experience_years ** 2)
    )
    
    # Formal sector multiplier
    sector_multiplier = FORMAL_MULTIPLIER.value if is_formal else 1.0
    
    # Real wage growth over career
    growth_multiplier = (1 + real_wage_growth) ** experience_years
    
    return baseline_wage * education_premium * sector_multiplier * growth_multiplier


def get_formal_entry_probability(education_level: str, state: str = 'national') -> float:
    """
    Return probability of formal sector entry by education level and state.
    
    Args:
        education_level: 'secondary', 'higher_secondary', 'graduate'
        state: State code or 'national' for average
    
    Returns:
        float: Probability (0-1)
    
    TODO: Replace with logistic regression model on PLFS microdata once available.
    Currently uses aggregate estimates.
    """
    # National estimates (placeholder - to be replaced with state-specific models)
    probabilities = {
        'secondary': P_FORMAL_SECONDARY.value,
        'higher_secondary': P_FORMAL_HIGHER_SECONDARY.value,
        'graduate': 0.40,  # To be added to registry
        'apprentice': P_FORMAL_APPRENTICE.value
    }
    
    # State adjustments (from 40Hour_PoC_Plan - to be validated with 2025 data)
    state_multipliers = {
        'national': 1.0,
        'urban_south_west': 1.25,  # e.g., Karnataka, Tamil Nadu, Maharashtra
        'rural_north_east': 0.75   # e.g., Bihar, UP, Jharkhand
    }
    
    base_prob = probabilities.get(education_level, P_FORMAL_HIGHER_SECONDARY.value)
    state_mult = state_multipliers.get(state, 1.0)
    
    return min(base_prob * state_mult, 0.95)  # Cap at 95%


# =============================================================================
# SECTION 9: MONTE CARLO SAMPLING FUNCTIONS
# =============================================================================

def sample_parameter(param: Parameter, n_samples: int = 1000, seed: int = None) -> np.ndarray:
    """
    Generate Monte Carlo samples from parameter's uncertainty distribution.
    
    Args:
        param: Parameter object with sampling_method and sampling_params
        n_samples: Number of Monte Carlo draws
        seed: Random seed for reproducibility
    
    Returns:
        np.ndarray: Array of sampled values
    """
    if seed is not None:
        np.random.seed(seed)
    
    if param.sampling_method == 'uniform':
        low, high = param.sampling_params
        return np.random.uniform(low, high, n_samples)
    
    elif param.sampling_method == 'normal':
        mean, std = param.sampling_params
        return np.random.normal(mean, std, n_samples)
    
    elif param.sampling_method == 'triangular':
        left, mode, right = param.sampling_params
        return np.random.triangular(left, mode, right, n_samples)
    
    elif param.sampling_method == 'beta':
        alpha, beta = param.sampling_params
        # Scale to sensitivity range
        low, high = param.sensitivity_range
        samples = np.random.beta(alpha, beta, n_samples)
        return low + samples * (high - low)
    
    elif param.sampling_method == 'fixed':
        return np.full(n_samples, param.value)
    
    else:
        raise ValueError(f"Unknown sampling method: {param.sampling_method}")


def run_monte_carlo_sensitivity(
    n_simulations: int = 1000,
    tier1_only: bool = False
) -> Dict[str, np.ndarray]:
    """
    Run Monte Carlo simulation varying parameters according to their uncertainty distributions.
    
    Args:
        n_simulations: Number of simulation runs
        tier1_only: If True, only vary Tier 1 (critical) parameters; hold others fixed
    
    Returns:
        Dict mapping parameter names to arrays of sampled values
    """
    # List all parameters
    all_params = {
        'mincer_return': MINCER_RETURN_HS,
        'experience_linear': EXPERIENCE_LINEAR,
        'experience_quad': EXPERIENCE_QUAD,
        'formal_multiplier': FORMAL_MULTIPLIER,
        'p_formal_hs': P_FORMAL_HIGHER_SECONDARY,
        'p_formal_apprentice': P_FORMAL_APPRENTICE,
        'real_wage_growth': REAL_WAGE_GROWTH,
        'discount_rate': SOCIAL_DISCOUNT_RATE,
        'rte_test_score_gain': RTE_TEST_SCORE_GAIN,
        'rte_initial_premium': RTE_INITIAL_PREMIUM,
        'apprentice_initial_premium': APPRENTICE_INITIAL_PREMIUM
    }
    
    sampled_params = {}
    
    for name, param in all_params.items():
        if tier1_only and param.tier != 1:
            # Hold non-Tier-1 parameters fixed at point estimate
            sampled_params[name] = np.full(n_simulations, param.value)
        else:
            # Sample from uncertainty distribution
            sampled_params[name] = sample_parameter(param, n_simulations)
    
    return sampled_params


# =============================================================================
# SECTION 9B: SCENARIO CONFIGURATIONS
# =============================================================================

# UPDATED December 26, 2025 per Anand's guidance:
# - P_FORMAL_HIGHER_SECONDARY (RTE): 30% / 40% / 50% (was 25% / 40% / 60%)
# - Added FORMAL_MULTIPLIER to scenarios (1.5x / 2.0x / 2.5x)
# - Capped optimistic RTE at 50% (more defensible than 60-70% stakeholder intuition)

SCENARIO_CONFIGS = {
    # UPDATED Jan 20, 2026: Added P_FORMAL_RTE and sector-specific wage growth
    # Scenarios reflect new Anand guidance from Dec 2025 conversation
    'conservative': {
        'P_FORMAL_APPRENTICE': 0.50,
        'P_FORMAL_HIGHER_SECONDARY': 0.05,  # ~0.5x baseline (worst regions like Bihar ~3%)
        'P_FORMAL_RTE': 0.20,  # NEW: Lower bound for RTE formal entry
        'FORMAL_MULTIPLIER': 2.24,  # ILO 2024 lower bound
        'APPRENTICE_INITIAL_PREMIUM': 50000,
        'RTE_TEST_SCORE_GAIN': 0.10,  # ITT lower bound
        'APPRENTICE_DECAY_HALFLIFE': 5,
        'REAL_WAGE_GROWTH': 0.0,  # DEPRECATED - kept for backward compat
        'REAL_WAGE_GROWTH_FORMAL': 0.005,  # NEW: 0.5% per year
        'REAL_WAGE_GROWTH_INFORMAL': -0.01,  # NEW: -1% per year (decline)
        'SOCIAL_DISCOUNT_RATE': 0.08,  # Upper bound - more conservative
    },
    'moderate': {
        # Default values from registry (no overrides needed for moderate)
        # P_FORMAL_HIGHER_SECONDARY = 0.091 (national baseline for control)
        # P_FORMAL_RTE = 0.30 (RTE graduates, 3.3x baseline)
        # REAL_WAGE_GROWTH_FORMAL = 0.015 (1.5%)
        # REAL_WAGE_GROWTH_INFORMAL = -0.002 (-0.2%)
        # RTE_TEST_SCORE_GAIN = 0.137 (ITT estimate)
    },
    'optimistic': {
        'P_FORMAL_APPRENTICE': 0.90,
        'P_FORMAL_HIGHER_SECONDARY': 0.15,  # ~1.6x baseline (urban areas like Bangalore)
        'P_FORMAL_RTE': 0.50,  # NEW: Upper bound (Anand cap)
        'FORMAL_MULTIPLIER': 2.48,  # ILO 2024 upper bound (rural)
        'APPRENTICE_INITIAL_PREMIUM': 120000,
        'RTE_TEST_SCORE_GAIN': 0.20,  # ITT upper bound (high compliance)
        'APPRENTICE_DECAY_HALFLIFE': 50,
        'REAL_WAGE_GROWTH': 0.005,  # DEPRECATED - kept for backward compat
        'REAL_WAGE_GROWTH_FORMAL': 0.025,  # NEW: 2.5% per year
        'REAL_WAGE_GROWTH_INFORMAL': 0.005,  # NEW: 0.5% per year (rare growth)
        'SOCIAL_DISCOUNT_RATE': 0.03,  # Lower bound - less conservative
    }
}


def get_scenario_parameters(scenario: str = 'moderate') -> Dict[str, float]:
    """
    Get parameter value overrides for specified scenario.
    
    Args:
        scenario: One of 'conservative', 'moderate', 'optimistic'
    
    Returns:
        Dict mapping parameter names to scenario-specific values
        
    Usage:
        scenario_params = get_scenario_parameters('conservative')
        # Apply to ParameterRegistry in economic_core_v3_updated.py:
        params = ParameterRegistry()
        params.P_FORMAL_APPRENTICE.value = scenario_params['P_FORMAL_APPRENTICE']
        # ... etc for each parameter
        
    Notes:
        - Moderate scenario uses RWF-validated 72% apprentice placement
        - P_FORMAL_HIGHER_SECONDARY values assume RTE schools outperform regional averages:
          * Conservative (25%): Marginally better than worst regions (North 15%, East 12%)
          * Moderate (40%): 2× national average (20%) - requires selection/urban effects
          * Optimistic (60%): 2.4-3× regional averages - requires very strong selection
        - Only modifies Tier 1 critical parameters (highest uncertainty)
        - See RWF_Project_Registry_Comprehensive.md Section 13 for full documentation
    """
    if scenario not in SCENARIO_CONFIGS:
        raise ValueError(f"Unknown scenario: {scenario}. Must be one of: {list(SCENARIO_CONFIGS.keys())}")
    
    return SCENARIO_CONFIGS[scenario].copy()


def apply_scenario_to_registry(registry: 'ParameterRegistry', scenario: str) -> None:
    """
    Apply scenario parameter overrides to ParameterRegistry object IN-PLACE.
    
    This function is designed for use with economic_core_v3_updated.py's
    ParameterRegistry class (which has its own independent definition).
    
    Args:
        registry: ParameterRegistry instance to modify
        scenario: Scenario name ('conservative', 'moderate', 'optimistic')
    
    Example:
        from economic_core_v3_updated import ParameterRegistry
        params = ParameterRegistry()
        apply_scenario_to_registry(params, 'conservative')
        # params.P_FORMAL_APPRENTICE.value is now 0.50
        
    Notes:
        - Modifies the registry object in-place
        - Only updates parameters that exist in both SCENARIO_CONFIGS and registry
        - Prints warning if scenario parameter not found in registry
    """
    scenario_values = get_scenario_parameters(scenario)
    
    for param_name, value in scenario_values.items():
        if hasattr(registry, param_name):
            getattr(registry, param_name).value = value
        else:
            print(f"Warning: Parameter {param_name} not found in registry")


# =============================================================================
# SECTION 10: VALIDATION AND EXPORTS
# =============================================================================

def validate_parameters():
    """
    Run consistency checks on parameters.
    
    Checks:
    1. All wage baselines positive
    2. Probabilities in [0, 1]
    3. Mincer returns reasonable (0.01 to 0.15)
    4. Formal multiplier > 1
    5. Sensitivity ranges contain point estimates
    """
    errors = []
    warnings = []
    
    # Check wage baselines
    for demographic in BASELINE_WAGES:
        for edu_level in BASELINE_WAGES[demographic]:
            param = BASELINE_WAGES[demographic][edu_level]
            if param.value <= 0:
                errors.append(f"{param.name}: wage must be positive, got {param.value}")
            if param.value < 5000 or param.value > 100000:
                warnings.append(f"{param.name}: wage {param.value} seems extreme")
    
    # Check probabilities
    prob_params = [P_FORMAL_HIGHER_SECONDARY, P_FORMAL_SECONDARY, P_FORMAL_APPRENTICE]
    for param in prob_params:
        if not (0 <= param.value <= 1):
            errors.append(f"{param.name}: probability must be in [0,1], got {param.value}")
    
    # Check Mincer returns
    if not (0.01 <= MINCER_RETURN_HS.value <= 0.15):
        warnings.append(f"Mincer return {MINCER_RETURN_HS.value} outside typical range [0.01, 0.15]")
    
    # Check formal multiplier
    if FORMAL_MULTIPLIER.value < 1:
        errors.append(f"Formal multiplier must be > 1, got {FORMAL_MULTIPLIER.value}")
    
    # Check sensitivity ranges
    all_params = [
        MINCER_RETURN_HS, EXPERIENCE_LINEAR, EXPERIENCE_QUAD, FORMAL_MULTIPLIER,
        P_FORMAL_HIGHER_SECONDARY, P_FORMAL_APPRENTICE, REAL_WAGE_GROWTH,
        SOCIAL_DISCOUNT_RATE, RTE_TEST_SCORE_GAIN, VOCATIONAL_PREMIUM
    ]
    for param in all_params:
        if param.sensitivity_range is not None:
            low, high = param.sensitivity_range
            if not (low <= param.value <= high):
                errors.append(f"{param.name}: value {param.value} outside sensitivity range [{low}, {high}]")
    
    return errors, warnings


def export_parameter_table() -> str:
    """
    Export all parameters as markdown table for documentation.
    """
    table = "| Parameter | Symbol | Value | Unit | Tier | Source |\n"
    table += "|-----------|--------|-------|------|------|--------|\n"
    
    # Core parameters
    core_params = [
        MINCER_RETURN_HS, EXPERIENCE_LINEAR, EXPERIENCE_QUAD,
        FORMAL_MULTIPLIER, P_FORMAL_HIGHER_SECONDARY, P_FORMAL_APPRENTICE,
        REAL_WAGE_GROWTH, SOCIAL_DISCOUNT_RATE,
        RTE_TEST_SCORE_GAIN, RTE_INITIAL_PREMIUM,
        VOCATIONAL_PREMIUM, APPRENTICE_INITIAL_PREMIUM
    ]
    
    for param in core_params:
        table += f"| {param.name} | {param.symbol} | {param.value} | {param.unit} | {param.tier} | {param.source[:50]}... |\n"
    
    return table


if __name__ == "__main__":
    print("=" * 80)
    print("RWF Economic Impact Model - Parameter Registry v3.0")
    print("Updated: November 25, 2025 (Milestone 2)")
    print("=" * 80)
    print()
    
    # Run validation
    errors, warnings = validate_parameters()
    
    if errors:
        print("✗ VALIDATION ERRORS:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("✓ All parameters passed validation")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warn in warnings:
            print(f"  - {warn}")
    
    print("\n" + "=" * 80)
    print("KEY FINDINGS FROM MILESTONE 2:")
    print("=" * 80)
    print(f"1. Returns to education: {MINCER_RETURN_HS.value:.1%} (DOWN 32% from 8.6%)")
    print(f"2. Real wage growth: {REAL_WAGE_GROWTH.value:.2%} (DOWN 98% from 2-3%)")
    print(f"3. Experience premium: {EXPERIENCE_LINEAR.value:.3%}/year (DOWN 78%)")
    print(f"4. Urban male wage (12yr): ₹{BASELINE_WAGES['urban_male']['higher_secondary_12yr'].value:,}/mo")
    print(f"5. Counterfactual: {COUNTERFACTUAL_SCHOOLING.value[0]:.1%} govt, {COUNTERFACTUAL_SCHOOLING.value[1]:.1%} private")
    print()
    print("IMPLICATION: LNPV estimates will be 30-40% LOWER than if using old parameters.")
    print("This is CONSERVATIVE and MORE CREDIBLE for policy decisions.")
    print("=" * 80)