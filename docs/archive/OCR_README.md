# OCR Processor for RWF Project

## Overview

Handles scanned PDFs that can't be processed with standard PyPDF2 extraction.

## Features

✅ **Smart Detection** - Only runs OCR if PyPDF2 fails (checks first 5 pages)
✅ **Parallel Processing** - 4× speedup using multiprocessing (auto-detects CPU cores)
✅ **Intelligent Sampling** - For huge PDFs (>10 MB):
  - First 100 pages fully scanned (covers tables, index)
  - 50 pages sampled evenly from remainder
✅ **Progress Tracking** - Real-time updates every 10 pages

## Installation

### Quick Setup (Recommended)
```bash
cd /path/to/rwf_model
bash setup_ocr.sh
```

### Manual Setup
```bash
# 1. Install Tesseract OCR (macOS)
brew install tesseract tesseract-lang

# 2. Install Python dependencies
source venv/bin/activate
pip install pytesseract pdf2image pillow
```

## Usage

### Standalone Testing
```bash
# Test on a specific PDF
python ocr_processor.py sources/MSDE_annual_report_24_25.pdf
```

### Integrated with verify_claims.py
```python
# Automatic - no code changes needed!
# ocr_processor.py is imported automatically in verify_claims_v1_1.py
python verify_claims_v1_1.py --debug
```

## How It Works

### Decision Tree

```
PDF File
  ↓
PyPDF2 test (first 5 pages)
  ├─ >50 chars/page → Use PyPDF2 (fast)
  │
  └─ <50 chars/page → PDF is scanned
      ↓
      Check PDF size
      ├─ <10 MB → Full OCR parallel (all pages)
      │
      └─ ≥10 MB → Smart sampling
          ├─ First 100 pages (complete)
          └─ 50 pages distributed evenly from rest
```

### Example: MSDE_annual_report_24_25.pdf (47 MB, 572 pages)

**Before OCR processor:**
- PyPDF2 extracts 0 chars
- Script skips file (no verification possible)

**With OCR processor:**
1. Detects no selectable text
2. Size: 47 MB → Smart sampling strategy
3. OCR pages:
   - Pages 1-100 (complete)
   - Pages 150, 200, 250, 300, ... (50 sampled)
   - Total: 150 pages processed
4. Parallel processing with 4 workers
5. **Estimated time: 45-60 min** (vs 4-5 hours for full OCR)

## Performance

| PDF Size | Pages | Strategy | Time (4 cores) |
|----------|-------|----------|----------------|
| <10 MB | <200 | Full OCR | 15-30 min |
| 10-50 MB | 200-500 | Smart sampling (150 pages) | 45-60 min |
| >50 MB | 500+ | Smart sampling (150 pages) | 45-60 min |

## Configuration

Edit `ocr_processor.py` to adjust:

```python
# In extract_text_smart():
size_threshold_mb = 10.0  # Threshold for smart sampling

# In extract_with_ocr_smart_sampling():
first_n = 100       # Pages to OCR from start
sample_rest = 50    # Pages to sample from remainder

# In extract_with_ocr_parallel():
dpi = 300           # Image resolution (higher = slower but more accurate)
```

## Troubleshooting

### "Tesseract not found"
```bash
brew install tesseract
```

### "pdf2image cannot find poppler"
```bash
brew install poppler
```

### OCR is too slow
Reduce parallel workers:
```python
# In ocr_processor.py
workers = 2  # Instead of auto-detect
```

### OCR quality is poor
Increase DPI (slower but more accurate):
```python
dpi = 400  # Default: 300
```

## Integration Points

### verify_claims_v1_1.py
```python
# Lines 59-64: Import OCR processor
from ocr_processor import extract_text_from_pdf as extract_text_smart

# Lines 117-140: extract_text_from_pdf() uses OCR processor
```

### process_local_pdfs.py
Not yet integrated - manual OCR for now.

## Future Improvements

- [ ] Cloud OCR fallback (Google Vision API) for critical documents
- [ ] Caching: Save OCR results to avoid re-processing
- [ ] Page-level chunking metadata for better verification
- [ ] Table detection and structured extraction
