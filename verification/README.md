# Source Verification Pipeline

**Automated LLM-based verification of parameter claims against source documents**

---

## Overview

This pipeline verifies that the 77 model parameters can be traced back to their claimed source documents using:
1. **Local PDF/TXT documents** (48 files in `/sources`)
2. **Supabase database** with 266 source URLs
3. **LLM verification** (Kimi K2 Thinking model)

**Key Innovation**: Local-first strategy prioritizes fast local file lookups over network queries (10x speedup).

---

## Quick Start

### Full Verification Run

```bash
# From project root
cd verification/scripts/

# Run batch verification (recommended)
python verify_claims_batch_mode_v2.py --resume
```

**What happens**:
1. Auto-builds catalog of 48 local source files (if needed)
2. Queries Supabase for 77 parameters
3. For each parameter:
   - Tries local files FIRST (0.2-0.5s)
   - Falls back to Supabase if needed (3-5s)
   - Sends claim + document to LLM
   - Receives verification result (exact/approximate/not_found)
4. Saves results to database + CSV

**Output**: `outputs/verification_results.csv` with source tracking

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CATALOG BUILD (Auto)                                     │
│    sources/ (48 PDFs/TXTs) → sources_catalog.json           │
│    - Extract metadata (authors, year, keywords)             │
│    - Build search index                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. DOCUMENT LOOKUP STRATEGY (Local-First)                   │
│    For each parameter:                                       │
│    ├─ 0. LOCAL exact match (filename/author/year)           │
│    ├─ 1. Supabase by source_document_id                     │
│    ├─ 2. Supabase by URL                                    │
│    ├─ 3. LOCAL fuzzy match (catalog-powered)                │
│    └─ 4. Supabase fuzzy match                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. LLM VERIFICATION                                          │
│    - Claim: "Parameter X = Y"                                │
│    - Document: Full text from source                         │
│    - Prompt: Expert economist persona (prompts/LLM_Prompt_Expert.md) │
│    - Model: Kimi K2 Thinking (moonshotai)                   │
│    - Output: match_type, confidence, evidence snippet       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. RESULTS STORAGE                                           │
│    - Database: claim_verification_log table                  │
│    - CSV: verification_results.csv                           │
│    - Tracking: source_url, source_location, source_document │
└─────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
verification/
├── scripts/                  # Main verification scripts
│   ├── verify_claims_batch_mode_v2.py  ⭐ Recommended (13x faster)
│   ├── verify_claims.py                 Legacy single-threaded
│   ├── verify_claims_v1_1.py            Legacy with local support
│   ├── build_sources_catalog.py         Catalog builder
│   ├── process_local_pdfs.py            PDF text extraction
│   └── ocr_processor.py                 OCR for scanned PDFs
│
├── utilities/                # Helper tools
│   ├── check_*.py            # Database/status checks
│   ├── analyze_*.py          # Analysis scripts
│   ├── update_*.py           # Database update scripts
│   └── export_verification_results.py  # CSV export
│
├── outputs/                  # Results
│   ├── verification_results.csv        # Main output
│   ├── sources_catalog.json            # Auto-generated index
│   ├── pdf_mapping.csv                 # Local file mapping
│   └── [other CSVs]
│
└── prompts/
    └── LLM_Prompt_Expert.md  # Expert economist system prompt
```

---

## Key Scripts

### Main Verification Scripts

**`verify_claims_batch_mode_v2.py`** ⭐ RECOMMENDED
- Batch processing with progress tracking
- Auto-catalog rebuild
- Resume capability (`--resume` flag)
- Source transparency tracking
- 13x faster than single-threaded version

**Usage**:
```bash
python verify_claims_batch_mode_v2.py --resume
```

**`verify_claims.py`** (Legacy)
- Original single-threaded version
- No catalog support
- Use only for debugging

**`verify_claims_v1_1.py`** (Legacy)
- Adds local file support to legacy version
- Slower than batch mode
- Kept for compatibility

### Support Scripts

**`build_sources_catalog.py`**
- Scans `/sources` folder
- Extracts metadata from filenames and PDFs
- Builds `outputs/sources_catalog.json`
- **Auto-runs** when verification scripts detect outdated catalog

**Manual rebuild**:
```bash
python build_sources_catalog.py
```

**Output**:
```json
{
  "filename": "evans_yuan_2019_learning_outcomes.pdf",
  "authors": ["evans", "yuan"],
  "year": 2019,
  "keywords": ["learning", "outcomes"],
  "pdf_metadata": {
    "pdf_title": "Learning Outcomes and Years of Schooling",
    "pdf_author": "David Evans, Fei Yuan"
  }
}
```

---

## Utilities

### Database Checks

**`utilities/check_verification_status.py`**
```bash
python utilities/check_verification_status.py
```
Shows verification progress: how many parameters verified, match types distribution.

**`utilities/check_urls_per_parameter.py`**
```bash
python utilities/check_urls_per_parameter.py
```
Shows URL count per parameter, breakdown by source type (original/external).

**`utilities/check_database_structure.py`**
```bash
python utilities/check_database_structure.py
```
Validates database relationships (parameters → sources is 1:N).

### Updates

**`utilities/update_all_sources_from_csv.py`**
```bash
python utilities/update_all_sources_from_csv.py
```
Syncs URLs from `data/param_sources/Parameters sources - Latest.csv` to Supabase.
- Parses both "URL" column and "External Sources" markdown
- Added 206 URLs in latest run

### Exports

**`utilities/export_verification_results.py`**
```bash
python utilities/export_verification_results.py
```
Exports `claim_verification_log` table to `outputs/verification_results.csv`.

---

## Output Format

### `verification_results.csv`

| Column | Description | Example |
|--------|-------------|---------|
| `parameter_name` | Friendly name | "Private School Test Score Gain" |
| `claim_value` | Value being verified | "0.23" |
| `source_document` | Actual filename used | "muralidharan_sundararaman_2015.pdf" |
| `source_url` | URL or local path | "local://muralidharan_sundararaman_2015.pdf" |
| `source_location` | Strategy used | "local" / "supabase_by_url" |
| `source_citation` | Citation text | "Muralidharan & Sundararaman (2015)" |
| `match_type` | Verification result | "exact" / "approximate" / "not_found" / "contradictory" |
| `confidence` | LLM confidence (0-100) | 90 |
| `extracted_snippet` | Evidence (500 chars) | "The treatment effect was 0.23 SD..." |
| `needs_review` | Human review flag | "YES" / "NO" |
| `llm_model` | Model used | "moonshotai/kimi-k2-thinking" |
| `verified_at` | Timestamp | "2026-01-06T10:30:00Z" |

---

## Local-First Strategy

### Why Local-First?

**Performance**:
- Local file read: 0.2-0.5 seconds
- Supabase query + text extraction: 3-5 seconds
- **10x speedup** for parameters with local sources

**Reliability**:
- No network failures
- No URL changes breaking verification
- Documents always available

**Coverage**: 60% of parameters have local sources (48 files covering ~45 parameters)

### Lookup Order

1. **LOCAL exact match** - Check if filename/author/year match citation
2. **Supabase by ID** - If parameter already linked to source_document_id
3. **Supabase by URL** - Direct URL match
4. **LOCAL fuzzy match** - Catalog-powered score-based search
5. **Supabase fuzzy** - Citation/year/keyword matching in database

### Tracking

Every verification result includes:
- `source_url` - Shows if "local://file.pdf" or "https://..."
- `source_location` - Strategy identifier (e.g., "local_fuzzy")
- `source_document` - Actual filename

**Example**:
```csv
parameter_name,source_url,source_location
"Mincer Return",local://plfs_2023_24.pdf,local
"Test Score Gain",https://www.nber.org/papers/w19441,supabase_by_url
```

---

## LLM Verification

### Expert Prompt

Located in `prompts/LLM_Prompt_Expert.md`:
- **Persona**: Economist specializing in India labor markets, education, econometrics
- **Context**: RWF project methodology, PLFS 2023-24 findings
- **Search strategies**: Keyword, conceptual, proxy, structural, cross-validation
- **Output format**: Structured JSON with match_type, confidence, evidence

### Match Types

| Type | Description | Example |
|------|-------------|---------|
| `exact` | Literal value found | Document says "0.23 SD" exactly |
| `approximate` | Close value or derived | Document says "0.2-0.25 SD range" |
| `not_found` | No evidence in document | Claim not mentioned |
| `contradictory` | Document contradicts claim | Document says "0.15 SD" |
| `ambiguous` | Multiple interpretations | Unclear which value applies |

### Confidence Scoring

- **90-100%**: Direct quote, explicit statement
- **70-89%**: Clear implication, derived calculation
- **50-69%**: Reasonable interpretation, proxy measure
- **30-49%**: Weak evidence, multiple steps of inference
- **0-29%**: No clear evidence

**Auto-flag for review**: confidence < 60%

---

## Database Schema

### `claim_verification_log` Table

Primary output table in Supabase:

```sql
CREATE TABLE claim_verification_log (
  id UUID PRIMARY KEY,
  parameter_id UUID REFERENCES parameters(id),
  source_id UUID REFERENCES sources(id),
  source_document_id UUID REFERENCES source_documents(id),

  -- Claim details
  claim_text TEXT,
  claim_value TEXT,

  -- Verification
  verification_method TEXT,  -- 'llm'
  match_type TEXT,           -- 'exact', 'approximate', 'not_found', etc.
  confidence_score FLOAT,    -- 0.0 to 1.0

  -- Evidence
  extracted_snippet TEXT,    -- Up to 500 chars

  -- Source tracking (NEW in Jan 2026)
  source_url TEXT,           -- "local://file.pdf" or "https://..."
  source_document TEXT,      -- Filename
  source_location TEXT,      -- Strategy: 'local', 'supabase_by_url', etc.
  source_citation TEXT,      -- Original citation

  -- LLM details
  llm_model TEXT,
  llm_raw_response JSONB,
  llm_interpretation TEXT,
  llm_confidence_reason TEXT,

  -- Review
  needs_human_review BOOLEAN,

  -- Metadata
  verified_at TIMESTAMP,
  processing_time_ms INTEGER
);
```

---

## Configuration

### Environment Variables

In `../../.env`:
```bash
SUPABASE_URL=https://msytuetfqdchbehzichh.supabase.co
SUPABASE_KEY=your_service_role_key
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=moonshotai/kimi-k2-thinking
SOURCE_DIR=/path/to/sources/
```

### Catalog Settings

Auto-rebuild triggers:
- Catalog file missing
- Any file in `/sources` newer than catalog
- Manual deletion of `outputs/sources_catalog.json`

---

## Troubleshooting

### Catalog not rebuilding

**Symptom**: Old files not appearing in search

**Solution**:
```bash
rm outputs/sources_catalog.json
python build_sources_catalog.py
```

### Verification hanging

**Symptom**: Script stops mid-verification

**Check**:
1. OpenRouter API key valid?
2. Rate limiting (wait 1 minute, resume)
3. Network connection stable?

**Resume**: Use `--resume` flag to skip already-verified parameters

### Source not found

**Symptom**: Parameter shows "no source found"

**Debug**:
```bash
# Check if URL in database
python utilities/check_urls_per_parameter.py

# Check if file in sources/
ls -la ../../sources/ | grep -i "author_year"

# Update URLs from CSV
python utilities/update_all_sources_from_csv.py
```

### Wrong document matched

**Symptom**: LLM analyzing wrong source

**Check** `source_url` and `source_location` in results:
- If `local_fuzzy`, check catalog scoring (may need better filename)
- If `supabase_fuzzy`, check citation matching logic

---

## Recent Updates

### 2026-01-06: Local-First Overhaul
- Reordered strategies to prioritize local files
- Auto-catalog system with metadata extraction
- Source transparency tracking (source_url, source_location)
- 206 URLs added to Supabase
- Snippet size increased (200 → 500 chars)

See `../docs/PROJECT_CHANGELOG.md` for details.

---

## Performance Metrics

**Verification Speed** (per parameter):
- Local exact match: 0.2-0.5s
- Local fuzzy match: 0.3-0.7s
- Supabase lookup: 3-5s
- LLM verification: 8-15s

**Coverage**:
- Parameters with sources: 77/77 (100%)
- Parameters with local files: ~45/77 (60%)
- Verified to date: 13/77 (in progress)

**Accuracy** (from initial 13 verifications):
- Exact matches: 4 (31%)
- Approximate: 0
- Ambiguous: 6 (46%)
- Not found: 3 (23%)
- Needs review: 9 (69%)

---

## Next Steps

### Short-Term
1. Complete verification of remaining 64 parameters
2. Review 9 flagged parameters (low confidence)
3. Download missing source documents

### Long-Term
1. Implement automatic PDF download for URLs
2. Add source quality scoring (citation count, recency)
3. Build verification dashboard

---

## Further Reading

- **[PROJECT_CHANGELOG.md](../docs/PROJECT_CHANGELOG.md)** - Complete pipeline history
- **[LLM Prompt](prompts/LLM_Prompt_Expert.md)** - Expert economist prompt
- **[Project Registry](../docs/current/RWF_Project_Registry_Comprehensive_updated.md)** - Section 22: Source Management

---

**Last Updated**: January 6, 2026
**Status**: ✅ Operational
**Verified Parameters**: 13/77 (in progress)
