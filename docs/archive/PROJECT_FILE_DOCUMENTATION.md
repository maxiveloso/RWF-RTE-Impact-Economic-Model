# RWF Project - Complete File Documentation

**Project:** RightWalk Foundation Lifetime Economic Benefits Estimation
**Date:** January 4, 2026
**Purpose:** Document all files and their roles in the claim verification pipeline and economic model

---

## 📂 Directory Structure

```
rwf_model/
├── src/                          # Source code & model files
│   ├── key scripts/              # Core economic model (v4)
│   ├── param_sources/            # Parameter source references
│   ├── Old versions/             # Historical code versions
│   └── [documentation files]     # Analysis & methodology docs
│
├── sources/                      # PDF/TXT source documents (47 files)
├── venv/                         # Python virtual environment
│
├── [claim verification scripts]  # NEW: Pipeline created Jan 4, 2026
├── [output files]                # CSV reports and logs
└── [configuration]               # .env, settings
```

---

## 🎯 CLAIM VERIFICATION PIPELINE (Created Today)

### Purpose
Automate the verification of 77 model parameters against their source documents using LLM analysis.

### Core Scripts

#### 1. `process_local_pdfs.py` ⭐
**Purpose:** Extract text from local PDFs/TXTs and match them to the Supabase `sources` table

**What it does:**
1. Scans `sources/` directory for PDF and TXT files (found 47 files)
2. Extracts full text using PyPDF2 (for PDFs) or direct read (for TXTs)
3. Parses filenames to extract: authors, year, keywords
4. Matches files to database URLs using citation/year/author matching
5. Calculates SHA256 hash for deduplication
6. Inserts unique documents into `source_documents` table
7. Generates `pdf_mapping.csv` report

**Input:** Files in `sources/` directory
**Output:**
- Database: `source_documents` table (12 unique docs inserted)
- File: `pdf_mapping.csv` (mapping report)

**Key Algorithm:**
```python
Score-based matching:
  - Author in citation: +2 points
  - Year in citation: +2 points
  - Keywords in URL: +1 point each
  - Match if score >= 3
```

**Run:** `python process_local_pdfs.py`

---

#### 2. `verify_claims.py` ⭐⭐⭐
**Purpose:** Use LLM to verify each parameter's claimed value against its source document

**What it does:**
1. Loads all 77 parameters with their 'original' sources from Supabase
2. For each parameter with available document (37 found):
   - Retrieves full text from `source_documents` (filtered by URL)
   - Builds verification request with claim details
   - Calls OpenRouter API (Kimi K2 model) with expert prompt
   - Parses LLM JSON response for verification status
   - Determines match_type: exact/approximate/not_found/contradictory
   - Calculates confidence score (0-1)
   - Flags for human review if confidence < 0.6
   - Inserts result into `claim_verification_log` table
3. Generates `verification_results.csv` (exported separately)

**Input:**
- Database: `parameters`, `sources`, `source_documents`
- File: `LLM_Prompt_Expert.md` (system prompt)

**Output:**
- **Database: `claim_verification_log` table** ⭐ PRIMARY OUTPUT
- File: `verification_results.csv` (exported via separate script)
- File: `verification_run.log` (live progress)

**Current Status:** Processed 13/37 parameters (crashed, needs restart with fix)

**Run:** `python verify_claims.py`

---

### Supporting Scripts

#### 3. `test_connection.py`
**Purpose:** Quick health check for Supabase connection
**Output:** Console - prints parameter/source counts
**Run:** `python test_connection.py`

#### 4. `check_documents.py`
**Purpose:** View all documents inserted in `source_documents` table
**Output:** Console - lists 12 documents with page/word counts
**Run:** `python check_documents.py`

#### 5. `check_verification_status.py`
**Purpose:** Check verification progress in database
**Output:** Console - shows verification stats by match_type
**Run:** `python check_verification_status.py`

#### 6. `export_verification_results.py` ⭐
**Purpose:** Export verification results from database to CSV
**Output:** `verification_results.csv` (13 records as of now)
**Run:** `python export_verification_results.py`

#### 7. `verify_claims_test.py`
**Purpose:** Test verification setup (first 3 parameters only)
**Output:** Console - validation check
**Run:** `python verify_claims_test.py`

---

### Output Files

#### `pdf_mapping.csv` ✅ Complete
**Created by:** `process_local_pdfs.py`
**Purpose:** Maps local PDF/TXT files to database URLs
**Columns:**
- `local_filename` - File name in `sources/`
- `matched_url` - URL from `sources` table (if matched)
- `match_confidence` - high/none
- `extraction_status` - success/failed
- `num_sources_linked` - How many parameters reference this document
- `num_pages`, `num_words` - Document stats
- `document_id` - UUID in database (if inserted)
- `error` - Error message (if any)

**Key Stats:**
- 47 files processed
- 20 matched to URLs
- 12 inserted into database (unique by URL)
- 27 unmatched (need manual review)

---

#### `verification_results.csv` ✅ Partial (13/37)
**Created by:** `export_verification_results.py` (from database)
**Purpose:** Human-readable verification results
**Columns:**
- `parameter_name` - Friendly parameter name
- `claim_value` - Value being verified
- `source_document` - Which PDF/TXT was used
- `source_url` - Source URL
- `match_type` - exact/approximate/not_found/contradictory/ambiguous
- `confidence` - 0-100%
- `extracted_snippet` - Evidence from document (first 200 chars)
- `needs_review` - YES/NO
- `llm_model` - Model used (kimi-k2-thinking)
- `verified_at` - Timestamp

**Current Stats:**
- 13 parameters verified
- 4 exact matches (90% confidence)
- 6 ambiguous (30% confidence)
- 3 not found (30% confidence)
- 9 flagged for human review

**Location to view results:**
1. **CSV file:** `verification_results.csv` (export anytime with export script)
2. **Supabase:** `claim_verification_log` table (permanent record)
3. **Console:** Run `check_verification_status.py`

---

#### `verification_run.log`
**Created by:** `verify_claims.py` (live output)
**Purpose:** Real-time progress log during verification
**Contents:** Parameter-by-parameter progress, LLM responses, errors
**View:** `tail -f verification_run.log`

---

### Configuration

#### `.env` 🔒 SENSITIVE
**Purpose:** Credentials and API keys
**Contents:**
```bash
SUPABASE_URL=https://msytuetfqdchbehzichh.supabase.co
SUPABASE_KEY=[service_role_key]
OPENROUTER_API_KEY=[your_key]
OPENROUTER_MODEL=moonshotai/kimi-k2-thinking
SOURCE_DIR=/path/to/sources/
```

**⚠️ DO NOT COMMIT TO GIT**

---

## 📊 ECONOMIC MODEL FILES (/src)

### Core Model (v4) - Latest Production Code

#### `/src/key scripts/economic_core_v4.py` ⭐⭐⭐
**Purpose:** Core economic calculations for RTE and NATS interventions
**What it does:**
- Implements Mincer wage equation: `W = exp(β₀ + β₁×S + β₂×Exp + β₃×Exp²)`
- Calculates lifetime wages for formal and informal sectors
- Computes NPV using discount rate (3.72%)
- Handles two intervention pathways:
  - **RTE:** Right to Education (private school vouchers)
  - **NATS:** National Apprenticeship Training Scheme
- Outputs LNPV (Lifetime Net Present Value) for each intervention

**Key Functions:**
- `calculate_formal_wage()` - Formal sector wages with Mincer returns
- `calculate_informal_wage()` - Informal sector wages (casual labor)
- `calculate_rte_lnpv()` - RTE intervention LNPV
- `calculate_nats_lnpv()` - NATS intervention LNPV
- `run_model()` - Main entry point

**Input:** Parameter registry (v3)
**Output:** Economic impact estimates
**Status:** ✅ Production (v4 integrated Dec 26, 2025)

---

#### `/src/key scripts/parameter_registry_v3.py` ⭐⭐
**Purpose:** Central registry of all 77 model parameters
**What it does:**
- Defines ALL parameters as Python constants
- Organized by category:
  - Economic fundamentals (Mincer returns, discount rate)
  - Labor market structure (formal/informal probabilities)
  - Intervention effects (RTE test scores, NATS placement)
  - Geographic (state multipliers)
  - Temporal (working life duration)
- Maps to CSV row numbers for Supabase sync
- Includes parameter metadata (friendly names, categories)

**Key Constants:**
```python
MINCER_RETURN_HS = 0.058  # 5.8% per year
DISCOUNT_RATE = 0.0372    # 3.72% social discount rate
P_FORMAL_HS = 0.20        # 20% formal employment probability
RTE_TEST_SCORE_GAIN = 0.23  # 0.23 SD gain
```

**Status:** ✅ Production (v3)

---

### Historical Versions

#### `/src/Old versions/`
Contains previous iterations:
- `economic_core.py` - Original version
- `economic_core_v2.py`, `v3.py` - Intermediate updates
- `parameter_registry.py`, `v2.py` - Parameter evolution

**Purpose:** Version history, rollback capability
**Status:** Archived (reference only)

---

### Analysis & Documentation Files

#### `/src/LLM_Prompt_Expert.md` ⭐⭐
**Purpose:** Expert economist prompt for claim verification
**What it contains:**
- Economist persona definition (specializations: India labor, education, econometrics)
- Project context (RWF model methodology)
- Critical parameter knowledge (PLFS 2023-24 findings, key values)
- Verification methodology:
  - 5 search strategies (keyword, conceptual, proxy, structural, cross-validation)
  - Parameter type classifications (literal, derived, inferred, contextual)
  - Evidence strength criteria (strong/moderate/weak/none)
- Output format specification (JSON schema)
- Example verifications

**Used by:** `verify_claims.py` (loaded as system prompt)
**Status:** ✅ Active

---

#### `/src/PARAMETER_HIERARCHY_SUMMARY.md`
**Purpose:** Explains parameter categorization (Tier 1/2/3) by uncertainty
**Contents:**
- Tier 1 (High uncertainty): 18 parameters
- Tier 2 (Medium): 22 parameters
- Tier 3 (Low/Data-derived): 37 parameters
- Sensitivity analysis priorities

---

#### `/src/EXECUTIVE_SUMMARY_ANANDS_QUESTIONS.md`
**Purpose:** Answers to key stakeholder questions
**Topics:**
- Why NPV is lower than expected
- PLFS 2023-24 vs literature discrepancies
- Formal sector probability rationale
- Data quality assessment

---

#### `/src/RWF_CODE_CHANGELOG.md`
**Purpose:** Version history and code evolution
**Contents:** Changes from v1 → v4 (parameter updates, bug fixes, methodology)

---

#### `/src/README_V4_INTEGRATION.md`, `V4_INTEGRATION_SUMMARY.md`
**Purpose:** Documentation of v4 model integration (Dec 2025)
**Changes:** Parameter registry restructure, economic core updates

---

#### `/src/BEFORE_AFTER_COMPARISON.md`
**Purpose:** Compare v3 vs v4 results
**Shows:** NPV differences, parameter changes

---

#### `/src/discounting_methodology_explanation.md`
**Purpose:** Explains NPV discounting methodology
**Topics:** Social discount rate, present value calculations, time horizon

---

#### `/src/parameter_registry_clarifications.md`
**Purpose:** Clarifies specific parameter derivations
**Examples:** How initial wage premiums are calculated

---

#### `/src/parameter_sources_review.md`, `analysis_anands_questions.md`
**Purpose:** Analysis of parameter sources and validation

---

### Data Files

#### `/src/lnpv_results_v4.csv`
**Purpose:** Model output (LNPV calculations)
**Generated by:** `economic_core_v4.py`
**Contents:** NPV results for RTE and NATS

---

#### `/src/param_sources/`
Parameter source tracking (pre-Supabase):
- `Parameters sources - Latest.csv` - Parameter-source mapping
- `zotero_urls_*.csv/txt` - Zotero bibliography exports

**Status:** Migrated to Supabase `sources` table

---

### Utility Scripts

#### `/src/validate_v4_integration.py`
**Purpose:** Validate v4 model calculations
**Run:** Checks parameter loading, model execution

#### `/src/verify_critical_params.py`
**Purpose:** Deep-dive verification of Tier 1 parameters
**Run:** Manual verification workflow

#### `/src/debug_wage_calculation.py`
**Purpose:** Debug wage calculation logic
**Run:** Step-by-step wage computation

#### `/src/diagnostic_analysis.py`
**Purpose:** Model diagnostics and sensitivity checks

#### `/src/test_prompts_implementation.py`
**Purpose:** Test LLM prompt variations (experimental)

---

## 🗄️ DATABASE SCHEMA (Supabase)

### Tables Used by Claim Verification

#### `parameters` (77 records)
**Purpose:** All model parameters
**Key columns:**
- `id` (UUID, PK)
- `python_const_name` (e.g., "MINCER_RETURN_HS")
- `friendly_name` (human-readable)
- `original_value` (claim to verify)
- `csv_row_number` (legacy mapping)
- `verification_status` (to be updated after verification)

---

#### `sources` (114 records)
**Purpose:** Source citations for parameters
**Key columns:**
- `id` (UUID, PK)
- `parameter_id` (FK → parameters)
- `url` (source document URL)
- `citation` (formatted citation, e.g., "Chen et al. (2022)")
- `year` (publication year)
- `source_type` ('original' | 'external' | 'alternative')
- `url_accessible` (boolean)

**Critical:** One parameter can have multiple sources (1:N relationship)

---

#### `source_documents` (12 records) ⭐ NEW
**Purpose:** Full-text storage of source documents
**Created by:** `process_local_pdfs.py`
**Key columns:**
- `id` (UUID, PK)
- `original_url` (UNIQUE - one document per URL)
- `local_filename` (e.g., "PLFS_Annual_Report_23_24.pdf")
- `file_type` ('pdf' | 'txt')
- `full_text` (extracted text, searchable)
- `num_pages`, `num_words` (document stats)
- `content_hash` (SHA256 for deduplication)
- `extraction_status` ('success' | 'failed' | 'partial')
- `processed_at` (timestamp)

**Critical:** One document can be referenced by MULTIPLE sources
**Example:** PLFS 2023-24 → 13 different parameters

**Current documents:**
1. PLFS 2023-24 (13 refs) - 572 pages, 287k words
2. MSDE Annual Reports - multiple years
3. Muralidharan NBER paper - 56 pages
4. Chen IZA paper - 48 pages
5. World Bank reports
6. NITI Aayog reports
7. ILO employment reports

---

#### `claim_verification_log` (13 records) ⭐⭐⭐ PRIMARY OUTPUT
**Purpose:** LLM verification results
**Created by:** `verify_claims.py`
**Key columns:**
- `id` (UUID, PK)
- `parameter_id` (FK → parameters)
- `source_id` (FK → sources)
- `source_document_id` (FK → source_documents)
- `claim_text` (parameter friendly name)
- `claim_value` (value being verified)
- `verification_method` ('llm' | 'regex' | 'manual')
- **`match_type`** ('exact' | 'approximate' | 'not_found' | 'contradictory' | 'ambiguous')
- **`confidence_score`** (0.0 - 1.0)
- `extracted_snippet` (evidence text from document)
- `llm_model` ('moonshotai/kimi-k2-thinking')
- `llm_raw_response` (full LLM JSON response)
- `llm_interpretation` (derivation logic)
- `llm_confidence_reason` (why this confidence level)
- **`needs_human_review`** (boolean - TRUE if confidence < 0.6)
- `verified_at` (timestamp)
- `processing_time_ms` (API latency)

**This is WHERE TO FIND VERIFICATION RESULTS** ⭐

---

## 📍 WHERE TO FIND VERIFICATION OUTPUTS

### Option 1: Supabase Dashboard (RECOMMENDED)
1. Go to: https://supabase.com/dashboard/project/msytuetfqdchbehzichh
2. Click "Table Editor" in sidebar
3. Select `claim_verification_log` table
4. View all 13 verification records
5. Filter by:
   - `needs_human_review = true` (9 records need review)
   - `match_type = 'exact'` (4 high-confidence matches)
   - `confidence_score > 0.8` (reliable verifications)

**Columns to check:**
- `match_type` - Was claim verified?
- `confidence_score` - How confident is LLM?
- `extracted_snippet` - Evidence found in document
- `llm_raw_response` - Full LLM analysis (JSON)
- `needs_human_review` - Should human verify this?

---

### Option 2: CSV Export
**File:** `verification_results.csv`
**Generate:** Run `python export_verification_results.py`
**Open in:** Excel, Google Sheets, or text editor

**Current contents:** 13 verified parameters (4 exact, 6 ambiguous, 3 not found)

---

### Option 3: Python Script
**File:** `check_verification_status.py`
**Run:** `python check_verification_status.py`
**Output:** Console summary of verification stats

---

### Option 4: SQL Query (Advanced)
```sql
-- View all verifications with parameter details
SELECT
  p.friendly_name,
  p.original_value,
  cv.match_type,
  cv.confidence_score,
  cv.needs_human_review,
  cv.extracted_snippet,
  sd.local_filename
FROM claim_verification_log cv
JOIN parameters p ON cv.parameter_id = p.id
JOIN source_documents sd ON cv.source_document_id = sd.id
ORDER BY cv.verified_at DESC;
```

---

## 🔄 WORKFLOW SUMMARY

### Complete Pipeline Flow

```
1. SOURCE DOCUMENTS (47 PDFs/TXTs)
   ↓
2. process_local_pdfs.py
   ↓ (extracts text, matches to URLs)
3. source_documents table (12 unique docs)
   ↓
4. verify_claims.py
   ↓ (LLM verification with expert prompt)
5. claim_verification_log table (13 verified, 24 pending)
   ↓
6. export_verification_results.py
   ↓
7. verification_results.csv (human-readable)
```

---

## 🎯 NEXT STEPS

### Immediate
1. ✅ **Fix and restart verification** - Bug fixed in `verify_claims.py`
2. ⏳ **Complete verification** - 24 parameters remaining (of 37 total)
3. ⏳ **Review flagged parameters** - 9 need human verification

### Manual Review Queue (from database)
**Query:** `SELECT * FROM claim_verification_log WHERE needs_human_review = true`

**High priority:**
- Ambiguous matches (confidence 30%)
- Not found claims
- Contradictory evidence

### After Verification Complete
1. Update `parameters.verification_status` based on results
2. Document unverified parameters (no source documents available)
3. Manual verification for 27 unmatched PDFs
4. Sensitivity analysis on low-confidence parameters

---

## 📝 FILE MANIFEST

### Root Directory
```
process_local_pdfs.py          # PDF extraction & DB insertion
verify_claims.py               # LLM claim verification
test_connection.py             # Supabase connection test
check_documents.py             # View inserted documents
check_verification_status.py   # Verification progress
export_verification_results.py # Export to CSV
verify_claims_test.py          # Test verification setup

pdf_mapping.csv                # PDF→URL mapping report
verification_results.csv       # Verification results (CSV)
verification_run.log           # Live verification log

CLAIM_VERIFICATION_README.md   # Pipeline documentation
PROJECT_FILE_DOCUMENTATION.md  # This file

.env                           # Credentials (DO NOT COMMIT)
```

### /src Directory
```
key scripts/
  economic_core_v4.py          # Core economic model
  parameter_registry_v3.py     # Parameter definitions

LLM_Prompt_Expert.md           # Verification prompt
PARAMETER_HIERARCHY_SUMMARY.md # Parameter tiers
EXECUTIVE_SUMMARY_ANANDS_QUESTIONS.md
RWF_CODE_CHANGELOG.md
README_V4_INTEGRATION.md
V4_INTEGRATION_SUMMARY.md
BEFORE_AFTER_COMPARISON.md
discounting_methodology_explanation.md
parameter_registry_clarifications.md
parameter_sources_review.md
analysis_anands_questions.md

lnpv_results_v4.csv            # Model output

param_sources/                 # Legacy source tracking
  Parameters sources - Latest.csv
  zotero_urls_*.csv/txt

Old versions/                  # Historical code
  economic_core.py, v2.py, v3.py
  parameter_registry.py, v2.py

validate_v4_integration.py     # Model validation
verify_critical_params.py      # Manual verification
debug_wage_calculation.py      # Wage calculation debugger
diagnostic_analysis.py         # Model diagnostics
test_prompts_implementation.py # LLM prompt testing
```

---

## 🆘 QUICK REFERENCE

**View verification results:**
```bash
# Option 1: Console
python check_verification_status.py

# Option 2: CSV
python export_verification_results.py
cat verification_results.csv

# Option 3: Supabase
# Go to dashboard → claim_verification_log table
```

**Re-run verification:**
```bash
source venv/bin/activate
python verify_claims.py
```

**Process new PDFs:**
```bash
# Add PDFs to sources/ directory, then:
python process_local_pdfs.py
```

**Check what's in database:**
```bash
python check_documents.py           # View documents
python check_verification_status.py # View verifications
```

---

**Documentation Version:** 1.0
**Last Updated:** January 4, 2026, 9:10 PM
**Status:** ✅ Complete (13/37 parameters verified, pipeline operational)
