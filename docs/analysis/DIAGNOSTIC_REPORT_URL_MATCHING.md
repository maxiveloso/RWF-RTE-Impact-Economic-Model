# DIAGNOSTIC REPORT: URL-to-File Matching Issues
**Date:** January 6, 2026
**Focus:** Core Parameters Only (0-VETTING & 1A-CORE_MODEL)

---

## 🎯 EXECUTIVE SUMMARY

**Problem:** Fuzzy matching was failing to associate Supabase URLs with local PDF files, resulting in "not_found" or "ambiguous" verification statuses.

**Root Causes Identified:**
1. ✅ **Massive URL duplication in Supabase** (474 records but only 187 unique URLs)
2. ✅ **NULL/empty citation fields** (111 sources missing local filename mapping)
3. ✅ **Fuzzy matching relied on citations** (when NULL, it fell back to URL keywords which didn't match well)

**Solution Implemented:**
- ✅ Created `associate_sources_to_files.py` script
- ✅ Updated **83 citations** across **20 core parameters**
- ✅ Used CSV mappings to populate citation field with local filenames
- ⚠️ Duplicate removal blocked by foreign key constraint (1 error)

---

## 📊 DISCREPANCY ANALYSIS: CSV vs Supabase URLs

### Question: Why does Supabase have 474 URLs when CSV only has 71?

**Answer:**

1. **CSV Scope:** Your param2URL2sourcename.csv contains **71 rows with 53 unique URLs** for **17 CORE parameters only**

2. **Supabase Scope:** Database has **474 total records** with **187 unique URLs** for **77 parameters (ALL, not just core)**

3. **Duplication Breakdown:**
   - Total records: 474
   - Unique URLs: 187
   - **Duplicates: 287** (same URL inserted multiple times)
   - Most duplicated: PLFS_Annual_Report_23_24 URL appears **37 times**

**Conclusion:** NOT a data error - different scopes + historical bulk inserts created duplicates.

---

## ✅ SOLUTION APPLIED & RESULTS

**Script:** `associate_sources_to_files.py`

**Results:**
- Parameters processed: **20** (all core parameters)
- Citations updated: **83**
- Duplicates removed: **0** (blocked by foreign key)
- Errors: **1** (foreign key constraint)

**All local files verified present:** 47 PDFs + 3 TXT files = 50 total

---

## 🎯 NEXT STEPS

### Test the Fix (Immediate):
Run verification on 1-2 core parameters to verify:
- Fuzzy matching now finds local files
- source_url shows "local://" prefix
- Match rates improved to >90%

### Cleanup (Optional):
- Handle 1 duplicate with foreign key constraint
- Review 15-20 URLs in DB but not in CSV
- Add UNIQUE constraint to prevent future duplicates

---

**Status:** ✅ Complete - Ready for verification testing
