# Quick Start - Post Reorganization

**TL;DR**: Fix 3 files, run 3 tests, done in 20 minutes.

---

## 🚀 Fastest Path to Working Project

### 1️⃣ Fix Model (5 min)

**File**: `model/economic_core_v4.py`

**Check line 1431**:
```python
from parameter_registry_v3 import get_scenario_parameters
```
Should work as-is if running from `model/` directory.

**Test**:
```bash
cd model/
python economic_core_v4.py
```
✅ Should create `outputs/lnpv_results_v4.csv`

---

### 2️⃣ Fix Catalog Builder (5 min)

**File**: `verification/scripts/build_sources_catalog.py`

**Find these lines (around 20-50)**:
```python
SOURCES_DIR = Path(__file__).parent / 'sources'
output_path = Path(__file__).parent / 'sources_catalog.json'
```

**Replace with**:
```python
SOURCES_DIR = Path(__file__).parent.parent.parent / 'sources'
output_path = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
```

**Test**:
```bash
cd verification/scripts/
python build_sources_catalog.py
```
✅ Should create `../outputs/sources_catalog.json`

---

### 3️⃣ Fix Main Verification (10 min)

**File**: `verification/scripts/verify_claims_batch_mode_v2.py`

**Find these lines (around 80-134)**:
```python
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
SOURCE_DIR = Path(__file__).parent / 'sources'
```

**Replace with**:
```python
CATALOG_PATH = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
SOURCE_DIR = Path(__file__).parent.parent.parent / 'sources'
```

**Find prompt path (around 60-70)**:
```python
prompt_path = Path(__file__).parent / 'LLM_Prompt_Expert.md'
```

**Replace with**:
```python
prompt_path = Path(__file__).parent.parent / 'prompts' / 'LLM_Prompt_Expert.md'
```

**Test**:
```bash
cd verification/scripts/
python verify_claims_batch_mode_v2.py --resume
```
✅ Should load catalog and start verification

---

## ✅ Done!

If all 3 tests pass, your project is 90% functional.

**Optional**: Fix remaining files listed in `CRITICAL_FILES_STRATEGY.md`

---

## 🆘 Quick Troubleshooting

**Error**: `FileNotFoundError: sources_catalog.json`
→ You forgot step 2️⃣ path fix

**Error**: `FileNotFoundError: sources/`
→ Wrong path to sources directory

**Error**: `ModuleNotFoundError: parameter_registry_v3`
→ Run from `model/` directory

---

**For detailed strategy**: See `CRITICAL_FILES_STRATEGY.md`
**For complete checklist**: See `POST_REORGANIZATION_CHECKLIST.md`
