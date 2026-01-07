# RWF Economic Model - Core

**Production economic model for lifetime benefits calculation**

---

## Overview

This folder contains the production-ready economic model (v4.0) that calculates Lifetime Net Present Value (LNPV) for RWF interventions.

---

## Files

### Core Model Files

**`economic_core_v4.py`** ⭐ Main calculation engine
- Implements Mincer wage equation
- Formal/informal sector modeling
- NPV discounting (3.72% social discount rate)
- Scenario framework (Conservative/Moderate/Optimistic)
- RTE and NATS pathway calculations

**`parameter_registry_v3.py`** ⭐ Parameter definitions
- All 77 model parameters as Python constants
- Organized by category (economic, labor market, intervention effects)
- Scenario configurations
- Sensitivity ranges (min/max)
- Tier classifications (1=high uncertainty, 3=data-derived)

### Outputs

**`outputs/lnpv_results_v4.csv`** - Model results
- 32 scenarios (demographics × assumption levels)
- LNPV for RTE and Apprenticeship
- Formatted for stakeholder review

---

## Usage

### Basic Run

```bash
# Activate environment
source ../venv/bin/activate

# Run model
python economic_core_v4.py
```

**Output**: Results written to `outputs/lnpv_results_v4.csv`

### Running Specific Scenarios

```python
from economic_core_v4 import run_model
from parameter_registry_v3 import get_scenario_parameters

# Get moderate scenario parameters
params = get_scenario_parameters('moderate')

# Run model for specific demographic
results = run_model(
    region='west',
    gender='male',
    residence='urban',
    scenario_params=params
)

print(f"RTE NPV: ₹{results['rte_lnpv']/100000:.2f} L")
print(f"Apprenticeship NPV: ₹{results['apprentice_lnpv']/100000:.2f} L")
```

### Running All 32 Scenarios

```python
from economic_core_v4 import run_scenario_comparison

# Generates full comparison table
results_df = run_scenario_comparison()
results_df.to_csv('outputs/scenario_comparison.csv', index=False)
```

---

## Key Parameters

### Economic Fundamentals
- `MINCER_RETURN_HS = 0.058` - 5.8% returns to higher secondary education (PLFS 2023-24)
- `DISCOUNT_RATE = 0.0372` - 3.72% social discount rate
- `REAL_WAGE_GROWTH = 0.0001` - Flat real wages (PLFS finding)

### Labor Market Structure
- `P_FORMAL_HS = 0.20` - 20% formal sector probability for higher secondary (control)
- `P_FORMAL_APPRENTICE = 0.72` - 72% formal placement after apprenticeship (RWF data)
- `FORMAL_MULTIPLIER = 2.0` - Total compensation ratio (formal/informal)

### Intervention Effects
- `RTE_TEST_SCORE_GAIN = 0.23` - 0.23 SD test score improvement (Muralidharan NBER)
- `TEST_SCORE_TO_YEARS = 4.7` - Years of schooling equivalent per SD (Evans & Yuan)
- `VOCATIONAL_PREMIUM = 0.047` - 4.7% wage premium for vocational training (DGT)

See `parameter_registry_v3.py` for complete list and sources.

---

## Model Architecture

### Mincer Wage Equation

```
W = exp(β₀ + β₁×S + β₂×Exp + β₃×Exp²) × formal_adjustment × (1 + additional_premium)
```

Where:
- `β₁` (returns to schooling) = 5.8% per year (PLFS 2023-24)
- `β₂` (experience) = 0.885% per year (PLFS)
- `β₃` (experience²) = -0.015% (concave returns)
- `formal_adjustment` = Benefits adjustment (1.075× for formal sector)
- `additional_premium` = RTE test score or vocational training effect

### NPV Calculation

```
NPV = Σ(t=1 to T) [Wage_t - Cost_t] / (1 + r)^t
```

Where:
- `T` = 40 years (working life from age 18-58)
- `r` = 3.72% (social discount rate)
- `Wage_t` = Expected wage in year t (formal × P(Formal) + informal × P(Informal))
- `Cost_t` = Intervention cost (for RTE: private school fees; for NATS: training stipend)

---

## Scenarios

### Scenario Framework

**Three assumption levels** × **8 demographics** = 32 scenarios

**Assumption Levels**:
1. **Conservative** - Lower bound estimates
   - RTE: P(Formal)=30%, FORMAL_MULT=1.5×
   - Apprentice: P(Formal)=50%, FORMAL_MULT=1.5×

2. **Moderate** - Base case (most likely)
   - RTE: P(Formal)=40%, FORMAL_MULT=2.0×
   - Apprentice: P(Formal)=72%, FORMAL_MULT=2.0×

3. **Optimistic** - Upper bound estimates
   - RTE: P(Formal)=50%, FORMAL_MULT=2.5×
   - Apprentice: P(Formal)=90%, FORMAL_MULT=2.5×

**Demographics**: Urban/Rural × Male/Female × 4 regions (North/South/East/West)

---

## Recent Changes (v4.0)

### December 26, 2025

**Critical Fix**: Formal sector wage double-counting
- **Problem**: Applied FORMAL_MULTIPLIER (2.25×) on top of wages that already differentiated formal/informal
- **Impact**: Apprenticeship NPV overstated by 8.4×
- **Solution**: Changed to benefits adjustment approach
  - Embedded ratio from PLFS: 1.86× (salaried/casual wages)
  - Target ratio: 2.0× (total compensation including benefits)
  - Adjustment factor: 2.0/1.86 = 1.075× (modest uplift)
- **Result**: Apprenticeship NPV reduced from ₹133L to ₹53L (more realistic)

**Parameter Updates**:
- FORMAL_MULTIPLIER: 2.25 → 2.0 (conservative midpoint)
- Tier: 3 → 2 (upgraded due to 40% NPV impact)
- Sensitivity range: (2.0, 2.5) → (1.5, 2.5)

See `../docs/changelogs/RWF_CODE_CHANGELOG.md` for complete history.

---

## Validation

**Run validation script**:
```bash
python ../docs/archive/validate_v4_integration.py
```

**Checks**:
- ✓ Parameter loading
- ✓ Wage calculations
- ✓ NPV computation
- ✓ Scenario comparison
- ✓ Output file generation

---

## Outputs Interpretation

**LNPV in lakhs (L)**:
- 1 L = ₹100,000
- Example: ₹14.37 L = ₹14,37,000 = ₹1.437 million

**Benefit-Cost Ratio (BCR)**:
```
BCR = LNPV / Total Program Cost

For RTE:
- LNPV = ₹14.37 L (moderate scenario)
- Cost = ₹4.5 L (private school fees over 10 years)
- BCR = 3.2:1 (highly cost-effective)
```

---

## Dependencies

```python
# Core
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

# From project
from parameter_registry_v3 import get_scenario_parameters
```

No external API calls - runs offline.

---

## Troubleshooting

**Import error**: `ModuleNotFoundError: No module named 'parameter_registry_v3'`
- Make sure you're in the `model/` directory when running
- Or add to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

**Wrong results**: NPV seems too high/low
- Check scenario parameters match expectations
- Validate against reference scenario (Urban Male West - Moderate)
- Run validation script

**Missing output file**
- Check file permissions in `outputs/` directory
- Ensure `outputs/` folder exists

---

## Further Reading

- **[Parameter Hierarchy](../docs/current/PARAMETER_HIERARCHY_SUMMARY.md)** - Understanding uncertainty tiers
- **[Discounting Methodology](../docs/methodology/discounting_methodology_explanation.md)** - NPV calculation details
- **[Executive Summary](../docs/current/EXECUTIVE_SUMMARY_ANANDS_QUESTIONS.md)** - Key findings and Q&A

---

**Last Updated**: January 6, 2026
**Version**: v4.0
**Status**: ✅ Production Ready
