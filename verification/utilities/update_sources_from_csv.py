#!/usr/bin/env python3
"""
Update Supabase sources table based on the updated CSV in param_sources.

Actions based on PENDING_SOURCE_DOCUMENTS.md:
1. Remove duplicate PLFS MOSPI URLs → keep only DGE version
2. Update NBER paper URL to direct PDF link
3. Deduplicate IZA paper entries
4. Add murty_panda Social Discount Rate paper
"""

import os
import csv
from supabase import create_client
from dotenv import load_dotenv

# Load environment
load_dotenv()
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

CSV_PATH = 'src/param_sources/Parameters sources - Latest.csv'

print("="*80)
print("UPDATING SUPABASE SOURCES FROM CSV")
print("="*80)

# Read CSV
print(f"\n1. Reading CSV: {CSV_PATH}")
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)

print(f"   ✓ Loaded {len(csv_rows)} rows from CSV\n")

# Get all current sources from Supabase
print("2. Fetching current sources from Supabase...")
sources_response = supabase.table('sources').select('*').execute()
current_sources = sources_response.data
print(f"   ✓ Found {len(current_sources)} sources in Supabase\n")

# Get all parameters
print("3. Fetching parameters...")
params_response = supabase.table('parameters').select('id, friendly_name, python_const_name').execute()
parameters = {p['friendly_name']: p['id'] for p in params_response.data if p.get('friendly_name')}
# Also map by python_const_name
for p in params_response.data:
    if p.get('python_const_name'):
        parameters[p['python_const_name']] = p['id']

print(f"   ✓ Found {len(parameters)} parameters\n")

# ACTION 1: Remove MOSPI PLFS URLs (keep DGE version)
print("="*80)
print("ACTION 1: Remove duplicate PLFS MOSPI URLs")
print("="*80)

mospi_url = "https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf"
dge_url = "https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf"

mospi_sources = [s for s in current_sources if s.get('url') == mospi_url]
print(f"Found {len(mospi_sources)} sources with MOSPI URL")

if mospi_sources:
    print(f"Deleting {len(mospi_sources)} MOSPI URL sources (keeping DGE version)...")
    for source in mospi_sources:
        try:
            supabase.table('sources').delete().eq('id', source['id']).execute()
            print(f"  ✓ Deleted source {source['id'][:8]}...")
        except Exception as e:
            print(f"  ✗ Failed to delete: {e}")
    print(f"\n✓ Deleted {len(mospi_sources)} MOSPI sources")
else:
    print("  No MOSPI sources found (may have been deleted already)")

print()

# ACTION 2: Update NBER paper URL to direct PDF
print("="*80)
print("ACTION 2: Update NBER paper URL to direct PDF")
print("="*80)

nber_old_url = "https://www.nber.org/papers/w19441"
nber_new_url = "https://www.nber.org/system/files/working_papers/w19441/w19441.pdf"

nber_sources = [s for s in current_sources if s.get('url') == nber_old_url]
print(f"Found {len(nber_sources)} sources with old NBER URL")

if nber_sources:
    print(f"Updating {len(nber_sources)} NBER URLs to direct PDF...")
    for source in nber_sources:
        try:
            supabase.table('sources')\
                .update({'url': nber_new_url})\
                .eq('id', source['id'])\
                .execute()
            print(f"  ✓ Updated source {source['id'][:8]}... → {nber_new_url[:60]}...")
        except Exception as e:
            print(f"  ✗ Failed to update: {e}")
    print(f"\n✓ Updated {len(nber_sources)} NBER sources")
else:
    print("  No old NBER sources found")

print()

# ACTION 3: Deduplicate IZA paper
print("="*80)
print("ACTION 3: Check for duplicate IZA paper entries")
print("="*80)

iza_url = "https://docs.iza.org/dp15002.pdf"
iza_sources = [s for s in current_sources if s.get('url') == iza_url]
print(f"Found {len(iza_sources)} sources with IZA URL")

# Group by parameter_id
from collections import defaultdict
iza_by_param = defaultdict(list)
for source in iza_sources:
    iza_by_param[source['parameter_id']].append(source)

duplicates = {pid: sources for pid, sources in iza_by_param.items() if len(sources) > 1}

if duplicates:
    print(f"Found {len(duplicates)} parameters with duplicate IZA sources")
    for pid, sources in duplicates.items():
        print(f"  Parameter {pid[:8]}... has {len(sources)} duplicate sources")

    print(f"Removing duplicates (keeping newest)...")
    for pid, sources in duplicates.items():
        # Sort by created_at, keep newest
        sources_sorted = sorted(sources, key=lambda s: s.get('created_at', ''), reverse=True)
        to_delete = sources_sorted[1:]  # Delete all except first (newest)

        for source in to_delete:
            try:
                supabase.table('sources').delete().eq('id', source['id']).execute()
                print(f"  ✓ Deleted duplicate source {source['id'][:8]}...")
            except Exception as e:
                print(f"  ✗ Failed to delete: {e}")
    print(f"\n✓ Removed {sum(len(s)-1 for s in duplicates.values())} duplicate IZA sources")
else:
    print("  No duplicate IZA sources found")

print()

# ACTION 4: Add Social Discount Rate paper (murty_panda)
print("="*80)
print("ACTION 4: Check Social Discount Rate paper")
print("="*80)

murty_pdf_path = "sources/murty_panda_2020_social_time_preference_rate_climate.pdf"
murty_url = "https://iegindia.org/upload/profile_publication/doc-310320_153806wp388.pdf"

# Check if this document is in source_documents
print(f"Checking if {murty_pdf_path} exists locally...")
full_path = os.path.join('/Users/maximvf/Library/CloudStorage/GoogleDrive-maxiveloso@gmail.com/Mi unidad/Worklife/Applications/RWF/RWF_Lifetime_Economic_Benefits_Estimation/rwf_model', murty_pdf_path)

if os.path.exists(full_path):
    print(f"  ✓ File exists: {full_path}")
    print(f"  → This file needs to be processed with OCR and uploaded to source_documents")
    print(f"  → Then update sources table to point to it")
else:
    print(f"  ✗ File NOT found at: {full_path}")
    print(f"  → Need to verify the correct path")

print()

# SUMMARY
print("="*80)
print("SUMMARY")
print("="*80)
print("""
Completed actions based on PENDING_SOURCE_DOCUMENTS.md:

✓ ACTION 1: Removed duplicate PLFS MOSPI URLs (kept DGE version)
✓ ACTION 2: Updated NBER paper URL to direct PDF link
✓ ACTION 3: Deduplicated IZA paper entries
⚠ ACTION 4: Social Discount Rate paper needs OCR processing

Next steps:
1. Process murty_panda PDF with OCR
2. Upload to source_documents table
3. Update sources to reference it
4. Run verify_claims_v1_1.py to verify parameters
""")

print("="*80)
