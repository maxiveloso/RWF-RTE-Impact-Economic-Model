#!/usr/bin/env python3
"""
Check Supabase database structure and verify parameter-source relationships
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n" + "="*80)
print("CHECKING DATABASE STRUCTURE")
print("="*80)

# 1. Check parameters table
print("\n1. Checking 'parameters' table...")
params_response = supabase.table('parameters').select('*').limit(1).execute()
if params_response.data:
    print(f"   ✓ Parameters table exists")
    print(f"   Columns: {list(params_response.data[0].keys())}")
else:
    print(f"   ✗ No data in parameters table")

# 2. Check sources table
print("\n2. Checking 'sources' table...")
sources_response = supabase.table('sources').select('*').limit(1).execute()
if sources_response.data:
    print(f"   ✓ Sources table exists")
    print(f"   Columns: {list(sources_response.data[0].keys())}")
else:
    print(f"   ✗ No data in sources table")

# 3. Check the 1:N relationship
print("\n3. Checking 1:N relationship (parameters → sources)...")
test_param_response = supabase.table('parameters')\
    .select('id, friendly_name, sources(*)')\
    .limit(5)\
    .execute()

if test_param_response.data:
    for param in test_param_response.data:
        sources_count = len(param.get('sources', []))
        print(f"   Parameter: {param.get('friendly_name', 'Unknown')[:60]}")
        print(f"     → Has {sources_count} sources")
        if sources_count > 0 and param['sources']:
            for src in param['sources'][:3]:  # Show first 3
                print(f"       - {src.get('url', 'No URL')[:80]}")

# 4. Check specific parameter: "Test Score to Years of Schooling Conversion"
print("\n4. Checking 'Test Score to Years of Schooling Conversion' parameter...")
test_score_response = supabase.table('parameters')\
    .select('id, friendly_name, python_const_name, sources(*)')\
    .ilike('friendly_name', '%Test Score%Years%Schooling%')\
    .execute()

if not test_score_response.data:
    # Try with python_const_name
    test_score_response = supabase.table('parameters')\
        .select('id, friendly_name, python_const_name, sources(*)')\
        .ilike('python_const_name', '%TEST_SCORE%YEARS%')\
        .execute()

if test_score_response.data:
    param = test_score_response.data[0]
    print(f"   ✓ Found parameter: {param.get('friendly_name')}")
    print(f"   Python constant: {param.get('python_const_name')}")
    print(f"   Parameter ID: {param.get('id')}")

    sources = param.get('sources', [])
    print(f"\n   Has {len(sources)} sources:")

    expected_urls = [
        "https://documents1.worldbank.org/curated/en/123371550594320297/txt/WPS8752.txt",
        "https://documents1.worldbank.org/curated/en/801901603314530125/pdf/How-to-Improve-Education-Outcomes-Most-Efficiently-A-Comparison-of-150-Interventions-Using-the-New-Learning-Adjusted-Years-of-Schooling-Metric.pdf",
        "https://openknowledge.worldbank.org/server/api/core/bitstreams/ee996c03-1232-54eb-89cd-7f6fe71e13a4/content",
        "https://www.nature.com/articles/s41586-021-03323-7",
        "https://eproceedings.epublishing.ekt.gr/index.php/inoek/article/view/7034/6697"
    ]

    actual_urls = [src.get('url') for src in sources if src.get('url')]

    for i, src in enumerate(sources, 1):
        url = src.get('url', 'NO URL')
        citation = src.get('citation') or 'NO CITATION'
        source_type = src.get('source_type', 'NO TYPE')
        print(f"   [{i}] URL: {url}")
        print(f"       Citation: {citation[:80] if citation != 'NO CITATION' else citation}")
        print(f"       Type: {source_type}")

    print(f"\n   Expected {len(expected_urls)} URLs:")
    for i, url in enumerate(expected_urls, 1):
        status = "✓" if url in actual_urls else "✗ MISSING"
        print(f"   [{i}] {status} {url[:80]}")

    missing = set(expected_urls) - set(actual_urls)
    extra = set(actual_urls) - set(expected_urls)

    if missing:
        print(f"\n   ⚠ MISSING URLs ({len(missing)}):")
        for url in missing:
            print(f"     - {url}")

    if extra:
        print(f"\n   ⚠ EXTRA URLs not in expected list ({len(extra)}):")
        for url in extra:
            print(f"     - {url}")

    if not missing and not extra:
        print(f"\n   ✓ ALL EXPECTED URLs ARE PRESENT!")
else:
    print(f"   ✗ Parameter 'Test Score to Years of Schooling Conversion' NOT FOUND")
    print(f"   Searching for similar names...")
    similar = supabase.table('parameters')\
        .select('friendly_name, python_const_name')\
        .ilike('friendly_name', '%test%')\
        .execute()

    if similar.data:
        print(f"   Found {len(similar.data)} parameters with 'test' in name:")
        for p in similar.data[:10]:
            print(f"     - {p.get('friendly_name', p.get('python_const_name'))}")

print("\n" + "="*80)
print("STRUCTURE CHECK COMPLETE")
print("="*80 + "\n")
