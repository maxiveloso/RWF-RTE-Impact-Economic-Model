#!/usr/bin/env python3
"""
Update MOSPI PLFS URLs to DGE version (same document, different URL).

This fixes the issue where sources couldn't be deleted due to FK constraints.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

mospi_url = "https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf"
dge_url = "https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf"

print("="*80)
print("UPDATING PLFS MOSPI URLs TO DGE VERSION")
print("="*80)
print(f"\nFrom: {mospi_url}")
print(f"To:   {dge_url}\n")

# Get sources with MOSPI URL
sources_response = supabase.table('sources')\
    .select('id, parameter_id, url')\
    .eq('url', mospi_url)\
    .execute()

sources = sources_response.data
print(f"Found {len(sources)} sources with MOSPI URL\n")

if sources:
    print("Updating URLs...")
    for source in sources:
        try:
            supabase.table('sources')\
                .update({'url': dge_url})\
                .eq('id', source['id'])\
                .execute()
            print(f"  ✓ Updated source {source['id'][:8]}...")
        except Exception as e:
            print(f"  ✗ Failed to update {source['id'][:8]}...: {e}")

    print(f"\n✓ Successfully updated {len(sources)} sources")
else:
    print("No sources to update (may have been updated already)")

print("\n" + "="*80)
