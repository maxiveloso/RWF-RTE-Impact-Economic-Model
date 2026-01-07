# RWF Economic Impact Model: Sensitivity Analysis Report

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
| RTE | South | ₹11.9L | ₹17.9L | ₹35.7L |
| RTE | West | ₹9.1L | ₹13.7L | ₹27.4L |
| RTE | North | ₹5.8L | ₹8.6L | ₹17.3L |
| RTE | East | ₹4.0L | ₹6.0L | ₹12.1L |
| APPRENTICESHIP | South | ₹47.6L | ₹71.4L | ₹142.8L |
| APPRENTICESHIP | West | ₹46.3L | ₹69.4L | ₹138.8L |
| APPRENTICESHIP | North | ₹42.2L | ₹63.3L | ₹126.6L |
| APPRENTICESHIP | East | ₹38.1L | ₹57.2L | ₹114.3L |

*Note: 1 Lakh (L) = ₹100,000. Values shown for Urban Male scenario.*

### 2. Decision Rule for RWF

**If actual per-beneficiary cost < Max Cost (BCR=3), the intervention is highly cost-effective.**

For example:
- RTE South Urban Male: If program costs < ₹11.9L per beneficiary → BCR > 3:1
- Apprenticeship West Urban Male: If program costs < ₹46.3L per beneficiary → BCR > 3:1


### 3. Uncertainty Quantification (Monte Carlo)

From 1,000 simulations sampling all uncertain parameters:

| Metric | RTE (median) | Apprenticeship (median) |
|--------|--------------|------------------------|
| Median LNPV | ₹15.8L | ₹86.9L |
| 5th Percentile | ₹13.1L | ₹63.2L |
| 95th Percentile | ₹18.4L | ₹110.4L |
| P(LNPV > 0) | 100.0% | 100.0% |

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
