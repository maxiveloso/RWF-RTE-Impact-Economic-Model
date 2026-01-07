#!/usr/bin/env python3
"""
Analyze the discrepancy between CSV URLs and Supabase URLs
and identify which core parameters lack proper file associations
"""

import os
import re
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from collections import Counter

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

# Read the updated CSV
csv_path = 'src/param_sources/Parameters sources - param2URL2sourcename.csv'
df = pd.read_csv(csv_path)

print("="*100)
print("URL DISCREPANCY ANALYSIS: 71 CSV URLs vs 474 Supabase Records")
print("="*100)

# 1. Analyze Supabase duplication
all_sources = supabase.table('sources').select('*').execute()
url_counts = Counter([s['url'] for s in all_sources.data if s.get('url')])

print(f"\n📊 SUPABASE STATISTICS:")
print(f"   Total source records: {len(all_sources.data)}")
print(f"   Unique URLs: {len(url_counts)}")
print(f"   Total duplicates: {sum([count - 1 for count in url_counts.values() if count > 1])}")
print(f"   Source types: {Counter([s.get('source_type', 'NULL') for s in all_sources.data])}")

print(f"\n📊 CSV STATISTICS:")
print(f"   Total rows: {len(df)}")
print(f"   Unique URLs: {df['url'].nunique()}")
print(f"   Unique parameters: {df['parameter'].nunique()}")

print(f"\n🔍 MOST DUPLICATED URLs IN SUPABASE (Top 10):")
for url_str, count in url_counts.most_common(10):
    print(f"   {count:2d}x: {url_str[:90]}")

# 2. Get core parameters
core_params = supabase.table('parameters')\
    .select('id, friendly_name, category, csv_row_number')\
    .in_('category', ['0-VETTING', '1A-CORE_MODEL'])\
    .execute()

print(f"\n\n{'='*100}")
print(f"CORE PARAMETERS ANALYSIS ({len(core_params.data)} parameters)")
print("="*100)

# Get local files
local_files = set(os.listdir('sources')) if os.path.exists('sources') else set()
local_pdfs = [f for f in local_files if f.endswith('.pdf')]

print(f"\n📁 LOCAL FILES: {len(local_pdfs)} PDFs in /sources folder")

# Analyze each core parameter
issues = []

for param in sorted(core_params.data, key=lambda x: (x.get('category', ''), x.get('friendly_name', ''))):
    param_name = param['friendly_name']
    param_id = param['id']

    # Escape special regex characters
    param_search = re.escape(param_name[:30])

    # Find in CSV (exact match or substring)
    csv_matches = df[df['parameter'] == param_name]
    if len(csv_matches) == 0:
        # Try partial match
        csv_matches = df[df['parameter'].str.contains(param_search[:20], case=False, na=False, regex=False)]

    # Find in DB
    db_sources = supabase.table('sources').select('*').eq('parameter_id', param_id).execute()

    # Count citations
    null_citations = [s for s in db_sources.data if not s.get('citation')]

    print(f"\n{'─'*100}")
    print(f"📌 {param_name}")
    print(f"   Category: {param.get('category', 'N/A')}")
    print(f"   CSV URLs: {len(csv_matches)} | DB Sources: {len(db_sources.data)} | NULL citations: {len(null_citations)}")

    # Show CSV local files
    if len(csv_matches) > 0:
        print(f"\n   📋 CSV Expected Local Files:")
        for idx, row in csv_matches.iterrows():
            local_file = row.get('/sources', 'NO_FILE_SPECIFIED')
            url_short = row['url'][:70]

            # Check if file exists locally
            if local_file and local_file != 'NO_FILE_SPECIFIED':
                exists = f"{local_file}.pdf" in local_pdfs or local_file in local_pdfs
                status = "✅" if exists else "❌ MISSING"
                print(f"      {status} {local_file}")
                print(f"         URL: {url_short}...")

                if not exists:
                    issues.append({
                        'parameter': param_name,
                        'category': param.get('category'),
                        'local_file': local_file,
                        'url': row['url'],
                        'issue': 'FILE_NOT_DOWNLOADED'
                    })
            else:
                print(f"      ⚠️  NO LOCAL FILE SPECIFIED")
                print(f"         URL: {url_short}...")
                issues.append({
                    'parameter': param_name,
                    'category': param.get('category'),
                    'local_file': 'NONE',
                    'url': row['url'],
                    'issue': 'NO_LOCAL_FILE_IN_CSV'
                })
    else:
        print(f"\n   ⚠️  NO CSV ENTRIES FOUND FOR THIS PARAMETER")
        issues.append({
            'parameter': param_name,
            'category': param.get('category'),
            'local_file': 'NONE',
            'url': 'NONE',
            'issue': 'NOT_IN_CSV'
        })

    # Show DB sources with NULL citations
    if null_citations:
        print(f"\n   ⚠️  DB Sources with NULL Citations ({len(null_citations)}):")
        for s in null_citations[:3]:
            print(f"      - {s['url'][:80]}...")

print("\n\n" + "="*100)
print("SUMMARY OF ISSUES")
print("="*100)

issue_summary = Counter([i['issue'] for i in issues])
print(f"\n📊 Issue Breakdown:")
for issue_type, count in issue_summary.most_common():
    print(f"   {issue_type}: {count}")

print(f"\n❌ Parameters with Missing Local Files:")
missing_files = [i for i in issues if i['issue'] == 'FILE_NOT_DOWNLOADED']
for issue in missing_files[:10]:
    print(f"   - {issue['parameter'][:60]}")
    print(f"     Missing: {issue['local_file']}")

print("\n\n" + "="*100)
print("CONCLUSION")
print("="*100)

print(f"""
The discrepancy (71 CSV URLs vs 474 Supabase records) is caused by:

1. ❌ MASSIVE DUPLICATION in Supabase
   - Same URLs inserted multiple times for same parameters
   - Example: PLFS_Annual_Report appears 37 times in DB
   - This happened during bulk inserts from previous scripts

2. ⚠️  CITATION MATCHING ISSUE
   - {len([s for s in all_sources.data if not s.get('citation')])} sources have NULL citations
   - Fuzzy matching can't work without citations
   - Need to populate 'citation' field with local filenames

3. 📁 MISSING LOCAL FILES
   - {len([i for i in issues if i['issue'] == 'FILE_NOT_DOWNLOADED'])} files specified in CSV but not downloaded
   - These URLs point to external sources that need downloading

NEXT STEPS:
1. Clean duplicate URLs in Supabase
2. Populate 'citation' field with local filenames from CSV
3. Download missing PDFs
4. Re-run fuzzy matching
""")
