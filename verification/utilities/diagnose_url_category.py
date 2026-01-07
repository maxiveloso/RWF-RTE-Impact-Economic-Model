#!/usr/bin/env python3
"""
Diagnostic script to investigate:
1. Why URL fallback isn't finding documents
2. If category column exists in parameters table
3. Count of 0-VETTING and 1A-CORE_MODEL parameters
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("DIAGNOSTIC: URL and Category Analysis")
print("=" * 80)

# 1. Check if sources have URLs
print("\n1. SOURCES TABLE - URL STATUS")
print("-" * 40)

# Get total sources
total_sources = supabase.table("sources").select("id", count="exact").execute()
print(f"Total sources: {total_sources.count}")

# Get sources with non-null URLs
sources_with_url = supabase.table("sources").select("id, url, citation").not_.is_("url", "null").execute()
print(f"Sources with URL (not null): {len(sources_with_url.data)}")

# Check how many have EMPTY string URLs vs actual URLs
actual_urls = [s for s in sources_with_url.data if s.get('url') and len(s.get('url', '')) > 10]
print(f"Sources with actual URLs (len > 10): {len(actual_urls)}")

# Get sources with empty URLs
sources_empty_url = supabase.table("sources").select("id, url, citation").eq("url", "").execute()
print(f"Sources with empty URL (''): {len(sources_empty_url.data)}")

# Sample some sources to see URL content
print("\n   Sample of sources with URLs:")
sample_with_url = supabase.table("sources").select("id, citation, url").not_.is_("url", "null").limit(5).execute()
for s in sample_with_url.data:
    url_preview = (s.get('url') or '')[:60]
    citation_preview = (s.get('citation') or 'None')[:40]
    print(f"   ID {s['id'][:8]}: citation='{citation_preview}' url='{url_preview}...'")

print("\n   Sample of sources WITHOUT URLs (NULL):")
sample_no_url = supabase.table("sources").select("id, citation, url").is_("url", "null").limit(5).execute()
if sample_no_url.data:
    for s in sample_no_url.data:
        citation_preview = (s.get('citation') or 'None')[:60]
        print(f"   ID {s['id'][:8]}: citation='{citation_preview}' url=NULL")
else:
    print("   (none - all sources have URLs)")

# 2. Check parameters table schema
print("\n" + "=" * 80)
print("2. PARAMETERS TABLE - COLUMN CHECK")
print("-" * 40)

# Get one parameter to see all columns
sample_param = supabase.table("parameters").select("*").limit(1).execute()
if sample_param.data:
    columns = list(sample_param.data[0].keys())
    print(f"Available columns in parameters table:")
    for col in sorted(columns):
        print(f"   - {col}")

    # Check if category exists
    if 'category' in columns:
        print("\n   ✓ 'category' column EXISTS!")
    else:
        print("\n   ✗ 'category' column NOT FOUND")
        # Check for similar column names
        similar = [c for c in columns if 'cat' in c.lower() or 'type' in c.lower() or 'group' in c.lower()]
        if similar:
            print(f"   Similar columns found: {similar}")

# 3. Check category values if exists
print("\n" + "=" * 80)
print("3. PARAMETERS CATEGORY ANALYSIS")
print("-" * 40)

# Try to get category values - use friendly_name instead of parameter_name
try:
    params_with_category = supabase.table("parameters").select("id, friendly_name, python_const_name, category").execute()
    if params_with_category.data and 'category' in params_with_category.data[0]:
        # Count by category
        categories = {}
        for p in params_with_category.data:
            cat = p.get('category') or 'NULL'
            categories[cat] = categories.get(cat, 0) + 1

        print("Parameters by category:")
        for cat, count in sorted(categories.items()):
            print(f"   {cat}: {count}")

        # Specifically check for 0-VETTING and 1A-CORE_MODEL
        vetting = supabase.table("parameters").select("id, friendly_name, python_const_name").eq("category", "0-VETTING").execute()
        core_model = supabase.table("parameters").select("id, friendly_name, python_const_name").eq("category", "1A-CORE_MODEL").execute()

        print(f"\n   0-VETTING parameters: {len(vetting.data)}")
        print(f"   1A-CORE_MODEL parameters: {len(core_model.data)}")

        if vetting.data:
            print("\n   0-VETTING parameter names (first 10):")
            for p in vetting.data[:10]:
                name = p.get('friendly_name') or p.get('python_const_name') or 'Unknown'
                print(f"      - {name}")

        if core_model.data:
            print("\n   1A-CORE_MODEL parameter names (first 10):")
            for p in core_model.data[:10]:
                name = p.get('friendly_name') or p.get('python_const_name') or 'Unknown'
                print(f"      - {name}")
    else:
        print("   Category column not in query results")
except Exception as e:
    print(f"   Error querying categories: {e}")

# 4. Check source_documents table
print("\n" + "=" * 80)
print("4. SOURCE_DOCUMENTS TABLE STATUS")
print("-" * 40)

try:
    total_docs = supabase.table("source_documents").select("id", count="exact").execute()
    print(f"Total source_documents: {total_docs.count}")

    # First check what columns exist
    sample_doc = supabase.table("source_documents").select("*").limit(1).execute()
    if sample_doc.data:
        print(f"\n   Columns in source_documents: {list(sample_doc.data[0].keys())}")

        # Sample using actual columns
        for d in sample_doc.data:
            print(f"   Sample doc: {d}")
except Exception as e:
    print(f"   Error: {e}")

# 5. Check claim_verification_log to see what's being processed
print("\n" + "=" * 80)
print("5. CLAIM VERIFICATION LOG - RECENT ENTRIES")
print("-" * 40)

try:
    recent_logs = supabase.table("claim_verification_log").select("*").order("verified_at", desc=True).limit(5).execute()
    print(f"Recent verification entries:")
    for log in recent_logs.data:
        param_id = log.get('parameter_id', 'N/A')[:8] if log.get('parameter_id') else 'N/A'
        status = log.get('verification_status', 'N/A')
        method = log.get('verification_method', 'N/A')
        print(f"   Param {param_id}: status={status}, method={method}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
