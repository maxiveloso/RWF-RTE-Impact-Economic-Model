#!/usr/bin/env python3
"""
Check how many URLs are associated with each parameter in Supabase
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n" + "="*80)
print("URLS PER PARAMETER - FIRST 5 ROWS")
print("="*80 + "\n")

# Get first 5 parameters with their sources
params_response = supabase.table('parameters')\
    .select('id, friendly_name, csv_row_number, sources(*)')\
    .order('csv_row_number')\
    .limit(5)\
    .execute()

local_dir = Path(__file__).parent / 'sources'
local_files = list(local_dir.glob('*.pdf')) + list(local_dir.glob('*.txt'))
local_filenames = {f.name for f in local_files}

print(f"Local files in /sources: {len(local_filenames)}\n")

for idx, param in enumerate(params_response.data, 1):
    param_name = param.get('friendly_name', 'Unknown')
    csv_row = param.get('csv_row_number', '?')
    sources = param.get('sources', [])

    print(f"[{idx}] Row {csv_row}: {param_name}")
    print(f"    Total URLs in Supabase: {len(sources)}")

    if sources:
        # Count by source_type
        original = sum(1 for s in sources if s.get('source_type') == 'original')
        external = sum(1 for s in sources if s.get('source_type') == 'external')

        print(f"      - Original: {original}")
        print(f"      - External: {external}")

        # Show URLs
        for i, src in enumerate(sources[:3], 1):  # Show first 3
            url = src.get('url', 'NO URL')
            citation = src.get('citation') or 'No citation'
            src_type = src.get('source_type', '?')
            print(f"      [{i}] ({src_type}) {url[:70]}")
            if citation != 'No citation':
                print(f"          Citation: {citation[:60]}")

        if len(sources) > 3:
            print(f"      ... and {len(sources) - 3} more")

        # Check if URLs match local files
        matching_local = []
        for src in sources:
            url = src.get('url', '')
            citation = src.get('citation', '')

            # Extract potential filename from citation or URL
            # Simple heuristic: look for author names and years
            if citation:
                import re
                words = re.findall(r'\b[A-Za-z]+\b', citation)
                years = re.findall(r'\b\d{4}\b', citation)

                for local_file in local_filenames:
                    # Check if author names and year appear in filename
                    matches = sum(1 for w in words if w.lower() in local_file.lower())
                    year_matches = sum(1 for y in years if y in local_file)

                    if matches >= 2 and year_matches >= 1:
                        matching_local.append(local_file)
                        break

        if matching_local:
            print(f"      ✓ Found {len(matching_local)} potential local matches:")
            for local in matching_local[:2]:
                print(f"        - {local}")

    print()

print("="*80 + "\n")
