# RWF Claim Verification Pipeline - Setup Complete

**Date:** January 4, 2026
**Status:** ✅ Scripts created and tested
**Database:** Connected to Supabase (`msytuetfqdchbehzichh`)

---

## ✅ What Has Been Completed

### 1. Environment Setup
- ✅ Virtual environment created (`venv/`)
- ✅ Dependencies installed: PyPDF2, supabase, python-dotenv, httpx
- ✅ `.env` file configured with credentials
- ✅ Supabase connection tested successfully

### 2. PDF Processing Script (`process_local_pdfs.py`)
- ✅ Successfully processed **47 source files** (44 PDFs + 3 TXTs)
- ✅ Matched **20 files** to URLs in the database
- ✅ Inserted **12 unique documents** into `source_documents` table
- ✅ Generated mapping report: `pdf_mapping.csv`

**Key Documents Inserted:**
1. PLFS 2023-24 Annual Report (referenced by 13 parameters)
2. MSDE Annual Reports (2022-23, 2023-24, 2024-25)
3. Muralidharan & Sundararaman NBER paper (RTE test scores)
4. Chen et al. IZA paper (returns to education)
5. NITI Aayog reports (ITI, annual reports)
6. World Bank reports
7. ILO employment reports

### 3. Claim Verification Script (`verify_claims.py`)
- ✅ Script created with LLM integration (OpenRouter/Kimi K2)
- ✅ Uses expert prompt from `LLM_Prompt_Expert.md`
- ✅ Implements error handling and rate limiting
- ✅ Currently running verification on **37 parameters** with available documents
- ⏳ Verification in progress (background task)

---

## 📊 Processing Results

### PDF Processing Summary
```
Total files processed:    47
  ✓ Successful extraction: 47
  ✗ Failed extraction:      0
  ✓ Matched to URLs:       20
  ⚠  Unmatched:            27 (need manual review)
  ✓ Inserted to database:  12 unique documents
```

### Document Statistics
- Total pages extracted: ~2,700 pages
- Total words extracted: ~1.4 million words
- Largest document: PLFS 2023-24 (572 pages, 287k words)
- Coverage: 12 unique source URLs, supporting 25+ parameters

---

## 📂 Files Created

### Core Scripts
1. **`process_local_pdfs.py`** - PDF text extraction and database insertion
2. **`verify_claims.py`** - LLM-based claim verification
3. **`test_connection.py`** - Supabase connection tester
4. **`check_documents.py`** - View inserted documents
5. **`verify_claims_test.py`** - Test verification setup (first 3 params)

### Output Files
1. **`pdf_mapping.csv`** - Complete mapping of local files to database URLs
2. **`verification_results.csv`** - Verification results (⏳ generating)
3. **`verification_run.log`** - Live verification progress log

---

## 🚀 How to Run

### Step 1: Activate Virtual Environment
```bash
source venv/bin/activate
```

### Step 2: Process PDFs (if needed again)
```bash
python process_local_pdfs.py
```

This will:
- Scan `sources/` directory for PDF/TXT files
- Extract text using PyPDF2
- Match files to `sources` table by citation/URL
- Insert unique documents into `source_documents` table
- Generate `pdf_mapping.csv` report

### Step 3: Verify Claims
```bash
python verify_claims.py
```

This will:
- Load all parameters with 'original' sources
- For each parameter with available document:
  - Retrieve full text from `source_documents`
  - Call LLM API with expert prompt
  - Parse verification result
  - Insert into `claim_verification_log`
  - Generate `verification_results.csv`

**Note:** This process takes ~2-3 minutes per parameter (LLM API calls).
For 37 parameters, expect ~1-2 hours total runtime.

### Step 4: Check Progress
```bash
# View live progress
tail -f verification_run.log

# Check database status
python check_documents.py

# View results (after completion)
cat verification_results.csv
```

---

## 🗄️ Database Schema Reference

### `source_documents` (12 records)
```sql
- id: UUID (PK)
- original_url: TEXT (UNIQUE - one doc per URL)
- local_filename: TEXT
- file_type: 'pdf' | 'txt'
- full_text: TEXT (searchable)
- num_pages: INTEGER
- num_words: INTEGER
- content_hash: TEXT (SHA256)
- extraction_status: 'success' | 'failed'
- processed_at: TIMESTAMPTZ
```

### `claim_verification_log` (⏳ populating)
```sql
- id: UUID (PK)
- parameter_id: UUID (FK)
- source_id: UUID (FK)
- source_document_id: UUID (FK)
- claim_text: TEXT
- claim_value: TEXT
- match_type: 'exact' | 'approximate' | 'not_found' | 'contradictory'
- confidence_score: FLOAT (0-1)
- extracted_snippet: TEXT
- llm_model: TEXT ('moonshotai/kimi-k2-thinking')
- llm_raw_response: TEXT
- needs_human_review: BOOLEAN
- verified_at: TIMESTAMPTZ
```

---

## ⚠️ Important Notes

### 1:N URL Relationship (CRITICAL)
One document can be referenced by MULTIPLE parameters.

Example:
- PLFS 2023-24 → Used by 13 different parameters
- Each has ONE record in `source_documents`
- But 13 records in `claim_verification_log`

**Always filter by URL when retrieving documents:**
```python
doc = supabase.table('source_documents')\
    .select('*')\
    .eq('original_url', source_url)\  # ✅ FILTER BY URL
    .single()\
    .execute()
```

### Unmatched Files (27 files)
These files were extracted successfully but couldn't be automatically matched to database URLs:
- Academic papers not yet in `sources` table
- ISR reports (2022-2026)
- Some ILO, World Bank documents
- Alternative/supplementary sources

**Action needed:** Manual review of `pdf_mapping.csv` to assign URLs or add to database.

### LLM API Configuration
Current setup:
- **Provider:** OpenRouter
- **Model:** `moonshotai/kimi-k2-thinking`
- **Temperature:** 0.1 (factual verification)
- **Rate limiting:** 1-second delay between calls
- **Retry logic:** 3 attempts with exponential backoff

Alternative models (update `.env`):
```bash
OPENROUTER_MODEL=deepseek/deepseek-r1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

---

## 📈 Next Steps

### Immediate (Automated)
1. ⏳ Wait for verification to complete (~1-2 hours)
2. ✅ Review `verification_results.csv`
3. ✅ Check database for records in `claim_verification_log`

### Manual Review Required
1. **High Priority:** Parameters flagged with `needs_human_review=TRUE`
2. **Medium Priority:** Unmatched PDFs (27 files) in `pdf_mapping.csv`
3. **Low Priority:** Parameters with `match_type='approximate'`

### Database Updates
After manual review:
```sql
-- Update parameter verification status
UPDATE parameters
SET verification_status = 'verified'
WHERE id IN (
    SELECT parameter_id
    FROM claim_verification_log
    WHERE match_type = 'exact'
    AND confidence_score > 0.8
);
```

---

## 🐛 Troubleshooting

### Issue: PDF extraction fails
```bash
# Check PyPDF2 installation
pip show PyPDF2

# Try alternative: pdfplumber
pip install pdfplumber
```

### Issue: Supabase connection timeout
```bash
# Test connection
python test_connection.py

# Check credentials in .env
cat .env
```

### Issue: LLM API errors
```bash
# Test OpenRouter API key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check rate limits in verification_run.log
grep "Rate limited" verification_run.log
```

---

## 📝 File Locations

```
rwf_model/
├── .env                          # Credentials (DO NOT COMMIT)
├── venv/                         # Virtual environment
├── sources/                      # Source PDFs/TXTs (47 files)
├── LLM_Prompt_Expert.md          # Expert prompt for verification
│
├── process_local_pdfs.py         # PDF processing script
├── verify_claims.py              # Claim verification script
├── test_connection.py            # Connection tester
├── check_documents.py            # Database viewer
│
├── pdf_mapping.csv               # Processing results
├── verification_results.csv      # Verification results (⏳)
└── verification_run.log          # Live progress log (⏳)
```

---

## ✅ Verification Checklist

Before considering the pipeline complete:

- [x] PDFs processed and extracted
- [x] Documents inserted into database
- [x] Mapping report generated
- [⏳] Claim verification running
- [ ] Verification results reviewed
- [ ] High-confidence claims accepted
- [ ] Low-confidence claims flagged
- [ ] Manual review completed for ambiguous cases
- [ ] `parameters.verification_status` updated

---

## 📞 Support

For issues or questions:
1. Check `verification_run.log` for errors
2. Review `pdf_mapping.csv` for file match issues
3. Inspect database directly via Supabase dashboard
4. Refer to original handoff document for methodology

---

**Pipeline Status:** ✅ Operational
**Last Updated:** January 4, 2026, 5:55 PM
**Next Update:** After verification completes
