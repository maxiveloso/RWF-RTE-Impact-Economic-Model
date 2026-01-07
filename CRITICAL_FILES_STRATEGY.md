# Critical Files Strategy - Path Fix Planning

**Purpose**: Identify the 8 most critical files that MUST be fixed for the project to work, with exact line numbers and strategy for each.

---

## 🎯 Executive Summary

**Bottom line**: Fix these 8 files in order, and 90% of the project will work.

| Priority | File | Lines to Fix | Impact if Broken |
|----------|------|--------------|------------------|
| 🔴 #1 | `model/economic_core_v4.py` | 1431 | Model completely broken |
| 🔴 #2 | `verification/scripts/verify_claims_batch_mode_v2.py` | 80-134, ~30-50, ~60-70 | Verification pipeline broken |
| 🔴 #3 | `verification/scripts/build_sources_catalog.py` | ~20-30, ~40-50 | Catalog won't build |
| 🟡 #4 | `verification/scripts/verify_claims_v1_1.py` | 25-74 | Legacy verification broken |
| 🟡 #5 | `verification/utilities/update_all_sources_from_csv.py` | ~20-40 | Can't sync URLs |
| 🟡 #6 | `verification/utilities/export_verification_results.py` | ~30-50 | Can't export results |
| 🟢 #7 | `scripts/sync_registry.py` | Variable (depends on imports) | Registry sync broken |
| 🟢 #8 | `scripts/test_connection.py` | Likely OK (uses .env) | Can't test DB |

---

## 📂 File-by-File Strategy

---

### 🔴 PRIORITY 1: `model/economic_core_v4.py`

**Why critical**: This is the PRODUCTION economic model. If it breaks, you can't calculate NPV.

**Current location**: `model/economic_core_v4.py`

#### Strategy

**Step 1: Read the file focusing on imports**
```bash
head -50 model/economic_core_v4.py | grep -E "^import|^from"
```

**Step 2: Look for this specific line (around line 1431)**
```python
from parameter_registry_v3 import get_scenario_parameters
```

**Expected issue**: SHOULD work if running from `model/` directory, but may fail if:
- Script uses absolute paths
- Script is called from root directory

**Step 3: Check for file path references**
```bash
grep -n "Path\|path\|\.csv\|\.json" model/economic_core_v4.py | head -20
```

**Look for**:
- Output CSV paths (should write to `model/outputs/`)
- Any references to old `src/key scripts/` location

**Fix pattern**:
```python
# BEFORE (if found)
output_path = 'lnpv_results_v4.csv'

# AFTER
from pathlib import Path
output_path = Path(__file__).parent / 'outputs' / 'lnpv_results_v4.csv'
```

**Test immediately**:
```bash
cd model/
python economic_core_v4.py
# Should create outputs/lnpv_results_v4.csv
```

---

### 🔴 PRIORITY 2: `verification/scripts/verify_claims_batch_mode_v2.py`

**Why critical**: Main verification script. Used for 90% of verification work.

**Current location**: `verification/scripts/verify_claims_batch_mode_v2.py`

#### Strategy

**Step 1: Identify path constants at top of file**
```bash
head -150 verification/scripts/verify_claims_batch_mode_v2.py | grep -E "Path|DIR|CATALOG"
```

**Expected to find (around lines 80-134)**:
```python
SOURCES_CATALOG = None
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
SOURCE_DIR = Path(__file__).parent / 'sources'
```

**Step 2: Map out required fixes**

| Variable | Current (WRONG) | Fixed (CORRECT) | Explanation |
|----------|-----------------|-----------------|-------------|
| `CATALOG_PATH` | `.parent / 'sources_catalog.json'` | `.parent.parent / 'outputs' / 'sources_catalog.json'` | Catalog is in `verification/outputs/` |
| `SOURCE_DIR` | `.parent / 'sources'` | `.parent.parent.parent / 'sources'` | Sources in project root |

**Step 3: Find prompt path reference**
```bash
grep -n "LLM_Prompt_Expert" verification/scripts/verify_claims_batch_mode_v2.py
```

**Expected (around lines 60-70)**:
```python
prompt_path = Path(__file__).parent / 'LLM_Prompt_Expert.md'
```

**Fix**:
```python
prompt_path = Path(__file__).parent.parent / 'prompts' / 'LLM_Prompt_Expert.md'
```

**Step 4: Visual path diagram**
```
verification/scripts/verify_claims_batch_mode_v2.py (YOU ARE HERE)
  ↓ .parent → verification/scripts/
  ↓ .parent → verification/
  ↓ .parent → rwf_model/ (project root)

To reach sources/:
  .parent.parent.parent / 'sources'

To reach verification/outputs/:
  .parent.parent / 'outputs'

To reach verification/prompts/:
  .parent.parent / 'prompts'
```

**Test immediately**:
```bash
cd verification/scripts/
python verify_claims_batch_mode_v2.py --resume
# Should auto-build catalog and start verification
```

---

### 🔴 PRIORITY 3: `verification/scripts/build_sources_catalog.py`

**Why critical**: Without catalog, local-first strategy fails. Verification will be 10x slower.

**Current location**: `verification/scripts/build_sources_catalog.py`

#### Strategy

**Step 1: Find directory constants**
```bash
head -50 verification/scripts/build_sources_catalog.py | grep -E "SOURCES_DIR|OUTPUT|Path"
```

**Expected issues**:
```python
SOURCES_DIR = Path(__file__).parent / 'sources'  # WRONG - sources is in root
output_path = Path(__file__).parent / 'sources_catalog.json'  # WRONG - should be in outputs/
```

**Step 2: Apply fixes**
```python
# FIX 1: Sources directory
SOURCES_DIR = Path(__file__).parent.parent.parent / 'sources'

# FIX 2: Output path
output_path = Path(__file__).parent.parent / 'outputs' / 'sources_catalog.json'
```

**Step 3: Path diagram**
```
verification/scripts/build_sources_catalog.py (YOU ARE HERE)
  ↓ .parent → verification/scripts/
  ↓ .parent → verification/
  ↓ .parent → rwf_model/

To read from: rwf_model/sources/
  .parent.parent.parent / 'sources'

To write to: verification/outputs/
  .parent.parent / 'outputs'
```

**Test immediately**:
```bash
cd verification/scripts/
python build_sources_catalog.py
# Should create ../outputs/sources_catalog.json with 48 files
```

---

### 🟡 PRIORITY 4: `verification/scripts/verify_claims_v1_1.py`

**Why medium priority**: Legacy script. Less used, but should still work.

**Current location**: `verification/scripts/verify_claims_v1_1.py`

#### Strategy

**Same fixes as verify_claims_batch_mode_v2.py** (lines 25-74):
- Update CATALOG_PATH
- Update SOURCE_DIR
- Update prompt path (if exists)

**Shortcut**: Use diff/compare with v2 file to see similarities:
```bash
diff verification/scripts/verify_claims_v1_1.py verification/scripts/verify_claims_batch_mode_v2.py | head -50
```

**Test**:
```bash
cd verification/scripts/
python verify_claims_v1_1.py
```

---

### 🟡 PRIORITY 5: `verification/utilities/update_all_sources_from_csv.py`

**Why medium priority**: Needed when updating source URLs from CSV, but not daily use.

**Current location**: `verification/utilities/update_all_sources_from_csv.py`

#### Strategy

**Step 1: Find CSV path reference**
```bash
grep -n "\.csv\|param_sources\|Parameters sources" verification/utilities/update_all_sources_from_csv.py | head -10
```

**Expected issue**:
```python
csv_path = 'data/param_sources/Parameters sources - Latest.csv'
# or
csv_path = '../data/param_sources/Parameters sources - Latest.csv'
```

**Step 2: Determine current location awareness**

This script is in `verification/utilities/`, so:
```
verification/utilities/update_all_sources_from_csv.py (YOU ARE HERE)
  ↓ .parent → verification/utilities/
  ↓ .parent → verification/
  ↓ .parent → rwf_model/

To reach: rwf_model/data/param_sources/
  .parent.parent.parent / 'data' / 'param_sources'
```

**Fix**:
```python
from pathlib import Path
csv_path = Path(__file__).parent.parent.parent / 'data' / 'param_sources' / 'Parameters sources - Latest.csv'
```

**Test**:
```bash
cd verification/utilities/
python update_all_sources_from_csv.py
# Should report "206 URLs synced" or similar
```

---

### 🟡 PRIORITY 6: `verification/utilities/export_verification_results.py`

**Why medium priority**: Used to export results to CSV, but not blocking.

**Current location**: `verification/utilities/export_verification_results.py`

#### Strategy

**Step 1: Find output path**
```bash
grep -n "output\|csv\|write\|to_csv" verification/utilities/export_verification_results.py | head -10
```

**Expected issue**:
```python
output_path = 'verification_results.csv'  # WRONG - will write to utilities/ folder
```

**Fix**:
```python
from pathlib import Path
output_path = Path(__file__).parent.parent / 'outputs' / 'verification_results.csv'
```

**Path logic**:
```
verification/utilities/export_verification_results.py (YOU ARE HERE)
  ↓ .parent → verification/utilities/
  ↓ .parent → verification/

To write to: verification/outputs/
  .parent.parent / 'outputs'
```

**Test**:
```bash
cd verification/utilities/
python export_verification_results.py
# Should create/update ../outputs/verification_results.csv
```

---

### 🟢 PRIORITY 7: `scripts/sync_registry.py`

**Why lower priority**: Utility script, likely not frequently used.

**Current location**: `scripts/sync_registry.py`

#### Strategy

**Step 1: Check for imports from model**
```bash
grep -n "import.*parameter_registry\|import.*economic_core" scripts/sync_registry.py
```

**Expected issue** (if exists):
```python
from parameter_registry_v3 import ...  # WRONG - not in PATH
```

**Fix** (if needed):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'model'))
from parameter_registry_v3 import ...
```

**Alternative**: May not need imports at all - check file purpose first

**Test**:
```bash
cd scripts/
python sync_registry.py
```

---

### 🟢 PRIORITY 8: `scripts/test_connection.py`

**Why lower priority**: Usually just needs .env, no path issues expected.

**Current location**: `scripts/test_connection.py`

#### Strategy

**Step 1: Check if it uses paths**
```bash
grep -n "Path\|\.csv\|\.json\|import" scripts/test_connection.py | head -20
```

**Expected**: Likely just uses Supabase client (reads from `.env`)

**If paths found**: Apply same `.parent` logic as other files

**Test**:
```bash
cd scripts/
python test_connection.py
# Should show: "Connected! Parameters: 77, Sources: 266"
```

---

## 🎯 Execution Strategy (Step-by-Step)

### Phase 1: Core Model (5 minutes)

1. Read `model/economic_core_v4.py` lines 1-50 and 1420-1440
2. Check import statement and any path references
3. Fix if needed
4. Test: `cd model/ && python economic_core_v4.py`
5. ✅ Verify `outputs/lnpv_results_v4.csv` created

**If this fails, STOP. This is critical.**

---

### Phase 2: Catalog Builder (10 minutes)

1. Read `verification/scripts/build_sources_catalog.py` lines 1-60
2. Find SOURCES_DIR and output_path
3. Apply fixes (use path diagram above)
4. Test: `cd verification/scripts/ && python build_sources_catalog.py`
5. ✅ Verify `../outputs/sources_catalog.json` created with 48 files

**If this fails, verification won't work efficiently.**

---

### Phase 3: Main Verification (15 minutes)

1. Read `verification/scripts/verify_claims_batch_mode_v2.py` lines 1-150
2. Find CATALOG_PATH, SOURCE_DIR, prompt_path
3. Apply all three fixes
4. Test: `cd verification/scripts/ && python verify_claims_batch_mode_v2.py --resume`
5. ✅ Verify it loads catalog and starts processing

**If this works, 80% of project is functional.**

---

### Phase 4: Utilities (15 minutes)

1. Fix `verify_claims_v1_1.py` (copy logic from v2)
2. Fix `update_all_sources_from_csv.py` (CSV path)
3. Fix `export_verification_results.py` (output path)
4. Test each one individually

**These are nice-to-haves but not critical.**

---

### Phase 5: General Scripts (10 minutes)

1. Test `scripts/test_connection.py` (likely works as-is)
2. Check `scripts/sync_registry.py` (may need PATH update)
3. Fix if needed

---

## 🔍 Quick Search Commands

Before starting, run these to identify all files that need attention:

### Find all Python files with hardcoded paths
```bash
cd /Users/maximvf/Library/CloudStorage/GoogleDrive-maxiveloso@gmail.com/Mi\ unidad/Worklife/Applications/RWF/RWF_Lifetime_Economic_Benefits_Estimation/rwf_model/

# Find 'sources/' references (excluding comments)
grep -r "sources/" --include="*.py" --exclude-dir=venv . | grep -v "^#" | grep -v "\.pyc"

# Find catalog references
grep -r "sources_catalog" --include="*.py" --exclude-dir=venv .

# Find LLM prompt references
grep -r "LLM_Prompt_Expert" --include="*.py" --exclude-dir=venv .

# Find CSV references in verification
grep -r "Parameters sources" --include="*.py" --exclude-dir=venv verification/
```

### Count how many files need fixes
```bash
# Files with 'sources_catalog'
grep -r "sources_catalog" --include="*.py" --exclude-dir=venv . | cut -d: -f1 | sort -u | wc -l

# Files with 'sources/' directory
grep -r "sources/" --include="*.py" --exclude-dir=venv . | grep -v "^#" | cut -d: -f1 | sort -u | wc -l
```

---

## 📊 Impact Matrix

| File | Lines to Change | Estimated Time | Impact if Broken |
|------|----------------|----------------|------------------|
| `model/economic_core_v4.py` | ~1-3 | 5 min | CRITICAL - No NPV calculations |
| `verification/scripts/verify_claims_batch_mode_v2.py` | ~5-10 | 10 min | CRITICAL - No verification |
| `verification/scripts/build_sources_catalog.py` | ~2-4 | 5 min | HIGH - Slow verification |
| `verification/scripts/verify_claims_v1_1.py` | ~5-10 | 10 min | MEDIUM - Legacy broken |
| `verification/utilities/update_all_sources_from_csv.py` | ~1-2 | 5 min | MEDIUM - Can't sync URLs |
| `verification/utilities/export_verification_results.py` | ~1-2 | 5 min | LOW - Can't export |
| `scripts/sync_registry.py` | ~0-5 | 5 min | LOW - Utility broken |
| `scripts/test_connection.py` | ~0 | 2 min | LOW - Can't test DB |

**Total estimated time**: 45-60 minutes to fix all paths

---

## ✅ Success Criteria

After fixing these 8 files, you should be able to:

1. ✅ Run economic model: `cd model/ && python economic_core_v4.py`
2. ✅ Build catalog: `cd verification/scripts/ && python build_sources_catalog.py`
3. ✅ Run verification: `cd verification/scripts/ && python verify_claims_batch_mode_v2.py --resume`
4. ✅ Export results: `cd verification/utilities/ && python export_verification_results.py`
5. ✅ Test connection: `cd scripts/ && python test_connection.py`

**If all 5 work**: 🎉 Reorganization fully successful!

---

**Last Updated**: January 7, 2026
**Estimated Total Time**: 1 hour
**Priority**: Start with files #1-3 (red priority)
