# Post-Reorganization Checklist

**Purpose**: Verify reorganization was successful and fix any path issues.

---

## 🎯 Overview

After reorganizing the project, we need to:
1. **Fix hardcoded paths** in scripts that reference old locations
2. **Test imports** to ensure Python modules can find each other
3. **Clean up duplicates** once everything works

This document identifies **exactly which files** to check and test.

---

## 📋 Critical Files to Check (Priority Order)

### 🔴 PRIORITY 1: Core Model Files (MUST WORK)

These are production code - if they break, the whole model fails.

#### `model/economic_core_v4.py`

**What to check:**
```python
# Line ~1431 - Import statement
from parameter_registry_v3 import get_scenario_parameters
```

**Potential issue**: If this file has any path references to old `src/key scripts/` location

**Test command:**
```bash
cd model/
python economic_core_v4.py
```

**Expected output**: Should run without ImportError and generate `outputs/lnpv_results_v4.csv`

**Common errors:**
- `ModuleNotFoundError: No module named 'parameter_registry_v3'`
  - **Fix**: Ensure you're running from `model/` directory
  - **Alternative**: Add to PYTHONPATH or use relative import

---

#### `model/parameter_registry_v3.py`

**What to check:**
```python
# Look for any imports or file path references
# This file should be self-contained (no external imports except stdlib)
```

**Test command:**
```bash
cd model/
python -c "from parameter_registry_v3 import get_scenario_parameters; print(get_scenario_parameters('moderate'))"
```

**Expected output**: Dictionary with scenario parameters

**Common errors:**
- Usually none (this file is parameter definitions only)

---

### 🔴 PRIORITY 2: Verification Pipeline (MUST WORK)

Main verification scripts that process claims.

#### `verification/scripts/verify_claims_batch_mode_v2.py`

**What to check (line numbers approximate):**

**Lines 80-134** - Catalog path:
```python
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
```
**Issue**: Should be `parent.parent / 'verification/outputs/sources_catalog.json'`
**Fix**: Update to:
```python
CATALOG_PATH = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
```

**Lines ~30-50** - Sources directory:
```python
SOURCE_DIR = Path(__file__).parent / 'sources'
```
**Issue**: `sources/` is in project root, not in `verification/scripts/`
**Fix**: Update to:
```python
SOURCE_DIR = Path(__file__).parent.parent.parent / 'sources'
```

**Lines ~60-70** - LLM Prompt path:
```python
prompt_path = Path(__file__).parent / 'LLM_Prompt_Expert.md'
```
**Issue**: Prompt is now in `verification/prompts/`
**Fix**: Update to:
```python
prompt_path = Path(__file__).parent.parent / 'prompts' / 'LLM_Prompt_Expert.md'
```

**Test command:**
```bash
cd verification/scripts/
python verify_claims_batch_mode_v2.py --resume
```

**Expected behavior**:
1. Auto-builds catalog (or loads if fresh)
2. Queries Supabase
3. Starts verification process

**Common errors:**
- `FileNotFoundError: [Errno 2] No such file or directory: '.../sources_catalog.json'`
  - **Fix**: Update CATALOG_PATH as above
- `FileNotFoundError: [Errno 2] No such file or directory: '.../sources'`
  - **Fix**: Update SOURCE_DIR as above
- `FileNotFoundError: [Errno 2] No such file or directory: '.../LLM_Prompt_Expert.md'`
  - **Fix**: Update prompt_path as above

---

#### `verification/scripts/verify_claims_v1_1.py`

**What to check (similar to v2):**

**Lines 25-74** - Catalog loading:
```python
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
SOURCE_DIR = Path(__file__).parent / 'sources'
```

**Fix**: Same as verify_claims_batch_mode_v2.py above

**Test command:**
```bash
cd verification/scripts/
python verify_claims_v1_1.py
```

---

#### `verification/scripts/build_sources_catalog.py`

**What to check:**

**Lines ~20-30** - Sources directory:
```python
SOURCES_DIR = Path(__file__).parent / 'sources'
```
**Issue**: Should point to project root `sources/`
**Fix**:
```python
SOURCES_DIR = Path(__file__).parent.parent.parent / 'sources'
```

**Lines ~40-50** - Output path:
```python
output_path = Path(__file__).parent / 'sources_catalog.json'
```
**Issue**: Should output to `verification/outputs/`
**Fix**:
```python
output_path = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
```

**Test command:**
```bash
cd verification/scripts/
python build_sources_catalog.py
```

**Expected output**: Creates `verification/outputs/sources_catalog.json`

---

### 🟡 PRIORITY 3: Utilities (Should Work)

Helper scripts that support verification.

#### `verification/utilities/update_all_sources_from_csv.py`

**What to check:**

**CSV path reference** (likely around lines 20-40):
```python
csv_path = 'data/param_sources/Parameters sources - Latest.csv'
# or
csv_path = '../data/param_sources/Parameters sources - Latest.csv'
```

**Issue**: Path might be relative to old location
**Fix**: Use absolute path from script location:
```python
csv_path = Path(__file__).parent.parent.parent / 'data' / 'param_sources' / 'Parameters sources - Latest.csv'
```

**Test command:**
```bash
cd verification/utilities/
python update_all_sources_from_csv.py
```

**Expected output**: "206 URLs added" or "Already synced"

---

#### `verification/utilities/export_verification_results.py`

**What to check:**

**Output CSV path** (likely around lines 30-50):
```python
output_path = 'verification_results.csv'
```

**Issue**: Should output to `verification/outputs/`
**Fix**:
```python
output_path = Path(__file__).parent.parent / 'outputs' / 'verification_results.csv'
```

**Test command:**
```bash
cd verification/utilities/
python export_verification_results.py
```

**Expected output**: Creates/updates `verification/outputs/verification_results.csv`

---

### 🟢 PRIORITY 4: General Scripts (Nice to Have)

#### `scripts/test_connection.py`

**What to check:**
- Supabase connection (uses .env from root)
- No path dependencies

**Test command:**
```bash
cd scripts/
python test_connection.py
```

**Expected output**: "Connected successfully" + parameter/source counts

---

#### `scripts/sync_registry.py`

**What to check:**

**Parameter registry import** (if any):
```python
from parameter_registry_v3 import ...
```
**Issue**: Registry is now in `model/`
**Fix**: Add model/ to path or use absolute import:
```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'model'))
from parameter_registry_v3 import ...
```

**Test command:**
```bash
cd scripts/
python sync_registry.py
```

---

## 🧪 Complete Test Suite

Run these tests in order to verify everything works:

### Test 1: Model Core ⭐ CRITICAL
```bash
cd model/
python economic_core_v4.py
```
**Success criteria**:
- No ImportError
- Creates `outputs/lnpv_results_v4.csv`
- NPV values look reasonable (₹10-50L range)

---

### Test 2: Catalog Build
```bash
cd verification/scripts/
python build_sources_catalog.py
```
**Success criteria**:
- Creates `../outputs/sources_catalog.json`
- Indexes 48 files
- No FileNotFoundError

---

### Test 3: Verification Pipeline ⭐ CRITICAL
```bash
cd verification/scripts/
python verify_claims_batch_mode_v2.py --resume
```
**Success criteria**:
- Loads catalog successfully
- Connects to Supabase
- Processes at least 1 parameter without error
- Creates/updates `../outputs/verification_results.csv`

---

### Test 4: Database Connection
```bash
cd scripts/
python test_connection.py
```
**Success criteria**:
- Connects to Supabase
- Shows parameter count (77)
- Shows source count (266)

---

### Test 5: CSV Export
```bash
cd verification/utilities/
python export_verification_results.py
```
**Success criteria**:
- Exports to `../outputs/verification_results.csv`
- Shows verification count

---

## 🔧 Common Path Patterns to Search For

Use these grep commands to find files that may need path updates:

### Find hardcoded 'src/' references
```bash
grep -r "src/key scripts" . --include="*.py" --exclude-dir=venv
grep -r "src/param_sources" . --include="*.py" --exclude-dir=venv
grep -r "src/artifacts" . --include="*.py" --exclude-dir=venv
```

### Find hardcoded source directory paths
```bash
grep -r "sources/" . --include="*.py" --exclude-dir=venv | grep -v "# "
```

### Find CSV paths that might be broken
```bash
grep -r "\.csv" . --include="*.py" --exclude-dir=venv | grep -v "read_csv\|to_csv"
```

### Find LLM prompt references
```bash
grep -r "LLM_Prompt_Expert.md" . --include="*.py" --exclude-dir=venv
```

### Find catalog references
```bash
grep -r "sources_catalog.json" . --include="*.py" --exclude-dir=venv
```

---

## 📝 Path Update Template

When you find a path that needs updating, use this template:

**OLD (absolute path to old location)**:
```python
path = '/full/path/to/old/src/key scripts/file.py'
```

**NEW (relative from current file)**:
```python
from pathlib import Path
path = Path(__file__).parent.parent / 'model' / 'file.py'
```

**Path navigation guide**:
- `Path(__file__)` = current file
- `.parent` = go up one directory
- `.parent.parent` = go up two directories
- `/ 'folder'` = go into folder

**Examples**:

From `verification/scripts/script.py` → `sources/`:
```python
sources_dir = Path(__file__).parent.parent.parent / 'sources'
```

From `verification/scripts/script.py` → `verification/outputs/`:
```python
output_dir = Path(__file__).parent.parent / 'outputs'
```

From `model/economic_core_v4.py` → `model/parameter_registry_v3.py`:
```python
# Just use direct import (same directory)
from parameter_registry_v3 import get_scenario_parameters
```

---

## 🗑️ Cleanup After Verification

**ONLY do this after ALL tests pass!**

Once you've verified everything works, you can optionally clean up:

```bash
# Remove any remaining duplicates (carefully!)
# NOTE: This is optional - keeping duplicates doesn't hurt

# If you copied files (not moved), originals may still exist
# Check FILE_MIGRATION_MAP.md to see what was copied
```

**Recommendation**: Keep duplicates for now. Disk space is cheap, peace of mind is priceless.

---

## ✅ Success Checklist

- [ ] Model runs successfully (`economic_core_v4.py`)
- [ ] Catalog builds without errors (`build_sources_catalog.py`)
- [ ] Verification pipeline runs (`verify_claims_batch_mode_v2.py`)
- [ ] Database connection works (`test_connection.py`)
- [ ] No FileNotFoundError in any script
- [ ] All imports work (no ModuleNotFoundError)
- [ ] Outputs written to correct locations (`*/outputs/`)

**When all boxes checked**: ✅ Reorganization fully successful!

---

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'parameter_registry_v3'"

**Cause**: Running from wrong directory or path issue

**Fix**:
```bash
# Option 1: Run from correct directory
cd model/
python economic_core_v4.py

# Option 2: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/model"
python model/economic_core_v4.py
```

---

### "FileNotFoundError: sources_catalog.json"

**Cause**: Hardcoded path in script

**Fix**: Update path in script to use relative Path:
```python
CATALOG_PATH = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
```

---

### "FileNotFoundError: sources/ directory"

**Cause**: Script looking for sources in wrong location

**Fix**: Update SOURCE_DIR:
```python
SOURCE_DIR = Path(__file__).parent.parent.parent / 'sources'
```

---

### Import works in terminal but not in script

**Cause**: Different working directory

**Fix**: Use absolute imports with Path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'model'))
from parameter_registry_v3 import ...
```

---

## 📚 Reference

**Key directories**:
- `model/` - Economic core (production)
- `verification/scripts/` - Main verification scripts
- `verification/utilities/` - Helper scripts
- `verification/outputs/` - All generated CSVs/JSONs
- `verification/prompts/` - LLM prompts
- `data/param_sources/` - CSV source mappings
- `sources/` - PDF/TXT documents (unchanged)

**Path relationships**:
```
model/economic_core_v4.py
  → imports from: model/parameter_registry_v3.py
  → outputs to: model/outputs/

verification/scripts/verify_claims_batch_mode_v2.py
  → reads from: verification/prompts/LLM_Prompt_Expert.md
  → reads from: sources/ (project root)
  → reads from: verification/outputs/sources_catalog.json
  → outputs to: verification/outputs/verification_results.csv

verification/scripts/build_sources_catalog.py
  → reads from: sources/ (project root)
  → outputs to: verification/outputs/sources_catalog.json
```

---

**Last Updated**: January 7, 2026
**Status**: Ready for testing
**Next Step**: Run Test 1 (Model Core)
