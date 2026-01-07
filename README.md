# RWF Economic Impact Model

**Lifetime Economic Benefits Estimation for RightWalk Foundation Interventions**

[![Project Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)]()

---

## Overview

This project quantifies the **Lifetime Net Present Value (LNPV)** of two educational interventions implemented by RightWalk Foundation in India:

1. **RTE (Right to Education)** - 25% reservation in private schools for economically weaker sections
2. **NATS (National Apprenticeship Training Scheme)** - Vocational training under the 1961 Apprenticeship Act

**Key Metric**: Economic benefit-cost ratio (BCR) showing rupees of lifetime earnings generated per rupee invested.

**Current Model Version**: v4.0 (December 2025)

---

## Quick Start

### Running the Economic Model

```bash
# Activate environment
source venv/bin/activate

# Run core economic model
cd model/
python economic_core_v4.py
```

**Output**: `model/outputs/lnpv_results_v4.csv` with NPV calculations for all scenarios.

### Running Claim Verification

```bash
# Verify parameter sources against documents
cd verification/scripts/
python verify_claims_batch_mode_v2.py --resume
```

**Output**: `verification/outputs/verification_results.csv` with LLM-verified claims.

---

## Project Structure

```
rwf_model/
│
├── model/                    # 🎯 Core Economic Model (Production)
│   ├── economic_core_v4.py
│   ├── parameter_registry_v3.py
│   └── outputs/
│
├── verification/             # 🔍 Source Verification Pipeline
│   ├── scripts/              # Main verification scripts
│   ├── utilities/            # Helper/analysis tools
│   ├── outputs/              # Verification results (CSVs)
│   └── prompts/              # LLM prompts
│
├── sources/                  # 📄 Source Documents (47 PDFs/TXTs)
│
├── data/                     # 📊 Reference Data
│   ├── param_sources/        # Parameter source mappings
│   └── artifacts_module3/    # Sensitivity analysis outputs
│
├── docs/                     # 📚 Documentation
│   ├── current/              # Active documentation
│   ├── methodology/          # Technical explanations
│   ├── analysis/             # Analysis reports
│   ├── changelogs/           # Project history
│   └── archive/              # Historical/obsolete docs
│
├── scripts/                  # 🛠️ Utilities
├── migrations/               # Database migrations
└── venv/                     # Python environment
```

See detailed structure in each subfolder's README.

---

## Key Features

### Economic Model (v4.0)
- **Mincer wage equation** with PLFS 2023-24 baseline wages
- **Formal/informal sector modeling** with empirical probabilities
- **32 scenario framework** (Conservative/Moderate/Optimistic × demographics)
- **Monte Carlo simulation** support for uncertainty quantification
- **Fixed double-counting bug** (Dec 2025) - reduced apprenticeship NPV by 60%

### Verification Pipeline
- **Automated source-to-claim verification** using LLM (Kimi K2)
- **Local-first strategy** - prioritizes local PDFs over network queries (10x faster)
- **Auto-catalog system** - indexes 48 source documents with metadata
- **Full transparency** - tracks actual source used (local vs Supabase)
- **206 URLs** synced to Supabase across 77 parameters

---

## Documentation Map

### Getting Started
- **[Model README](model/README.md)** - How to run economic calculations
- **[Verification README](verification/README.md)** - How to verify parameter sources
- **[Quick Reference](docs/current/QUICK_REFERENCE.txt)** - Common commands

### Understanding the Model
- **[Project Registry](docs/current/RWF_Project_Registry_Comprehensive_updated.md)** - Complete project history and methodology (SSOT)
- **[Parameter Hierarchy](docs/current/PARAMETER_HIERARCHY_SUMMARY.md)** - 77 parameters by uncertainty tier
- **[Executive Summary](docs/current/EXECUTIVE_SUMMARY_ANANDS_QUESTIONS.md)** - Key findings and stakeholder Q&A

### Methodology
- **[Discounting Methodology](docs/methodology/discounting_methodology_explanation.md)** - NPV calculation approach
- **[Parameter Clarifications](docs/methodology/parameter_registry_clarifications.md)** - How specific values were derived

### Project History
- **[PROJECT_CHANGELOG.md](docs/PROJECT_CHANGELOG.md)** - Complete chronological history (consolidated SSOT)
- **[Changelogs folder](docs/changelogs/)** - Individual session logs

---

## Recent Updates

### 2026-01-06: Source Management Overhaul
- Local-first verification strategy (10x faster)
- Auto-catalog system for 48 source documents
- 206 URLs added to Supabase
- Full source transparency tracking

See [PROJECT_CHANGELOG.md](docs/PROJECT_CHANGELOG.md) for complete history.

### 2025-12-26: V4 Integration
- Fixed formal sector wage double-counting bug
- Reduced apprenticeship NPV from ₹133L to ₹53L (more conservative)
- Updated FORMAL_MULTIPLIER: 2.25 → 2.0
- Validated all 32 scenarios

---

## Key Results (v4.0)

**Reference Scenario: Urban Male, West Region - Moderate**

| Intervention | LNPV | Assumptions |
|-------------|------|-------------|
| RTE | ₹14.37 L | P(Formal)=40%, Test gain=0.23 SD |
| Apprenticeship | ₹53.32 L | P(Formal)=72%, Vocational premium=4.7% |

**Scenario Range**:
- RTE: ₹3.85 L (Conservative) - ₹18.01 L (Optimistic)
- Apprenticeship: ₹19.64 L (Conservative) - ₹55.21 L (Optimistic)

---

## Technology Stack

- **Language**: Python 3.11+
- **Database**: Supabase (PostgreSQL)
- **LLM**: OpenRouter (Kimi K2 Thinking)
- **PDF Processing**: PyPDF2, pdfplumber
- **Data**: PLFS 2023-24, MSDE reports, academic literature

---

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_service_role_key
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=moonshotai/kimi-k2-thinking
SOURCE_DIR=/path/to/sources/
```

---

## Contributing

This is a research project for RightWalk Foundation. For questions or collaboration:

**Project Lead**: Maxi
**Stakeholder**: Anand (RWF)

---

## License

Private research project - Not for public distribution

---

## Project Status

**Last Updated**: January 6, 2026
**Model Version**: v4.0
**Parameters Verified**: 13/77 (in progress)
**Source Documents**: 48 local + 266 URLs in database

---

**For detailed technical documentation, see [docs/](docs/) folder.**
