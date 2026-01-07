#!/usr/bin/env python3
"""
Update ALL sources in Supabase from the Parameters sources CSV
Parses both URL column and External Sources column to get all URLs
"""

import os
import csv
import re
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = 'src/param_sources/Parameters sources - Latest.csv'

print("\n" + "="*80)
print("UPDATING ALL SOURCES FROM CSV TO SUPABASE")
print("="*80 + "\n")


def extract_urls_from_text(text):
    """Extract all URLs from markdown/text content"""
    if not text:
        return []

    # Pattern for URLs in markdown links: [text](url) or just bare URLs
    urls = []

    # Markdown links
    markdown_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    for match in re.finditer(markdown_pattern, text):
        urls.append(match.group(2))

    # Bare URLs (https://...)
    bare_url_pattern = r'(?<!\()(https?://[^\s<>\)\]]+)'
    for match in re.finditer(bare_url_pattern, text):
        url = match.group(1)
        # Avoid duplicates from markdown links
        if url not in urls:
            urls.append(url)

    return urls


def parse_citation_from_external_sources(external_sources, url):
    """Try to extract citation for a specific URL from External Sources markdown"""
    if not external_sources or not url:
        return None

    # Find the section containing this URL
    lines = external_sources.split('\n')
    citation = None

    for i, line in enumerate(lines):
        if url in line:
            # Look backwards for the citation (usually in ** ** format)
            for j in range(i, max(0, i-5), -1):
                match = re.search(r'\*\*([^*]+)\*\*', lines[j])
                if match:
                    citation = match.group(1).strip()
                    # Clean up citation
                    citation = re.sub(r'\s+', ' ', citation)
                    return citation

    return None


def extract_year_from_citation(citation):
    """Extract year from citation text"""
    if not citation:
        return None

    match = re.search(r'\((\d{4})\)|\b(\d{4})\b', citation)
    if match:
        return match.group(1) or match.group(2)

    return None


# Load CSV
print(f"Loading CSV from: {CSV_PATH}")

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"  ✓ Loaded {len(rows)} parameters from CSV\n")

# Get all parameters from Supabase
print("Loading parameters from Supabase...")
params_response = supabase.table('parameters').select('id, friendly_name, python_const_name, csv_row_number').execute()

# Create lookup by csv_row_number (most reliable)
params_by_row = {}
params_by_name = {}

for p in params_response.data:
    # Index by csv_row_number (most reliable)
    if p.get('csv_row_number'):
        params_by_row[p['csv_row_number']] = p
    # Index by friendly_name as fallback
    if p.get('friendly_name'):
        params_by_name[p['friendly_name']] = p

print(f"  ✓ Loaded {len(params_response.data)} parameters from Supabase")
print(f"    - {len(params_by_row)} have csv_row_number\n")

# Statistics
total_urls_found = 0
total_urls_added = 0
total_urls_skipped = 0
params_updated = 0

# Process each row in CSV
for csv_row_idx, row in enumerate(rows, 1):
    param_name = row.get('Parameter/Variable Name', '').strip()

    if not param_name:
        continue

    # STRATEGY 1: Match by csv_row_number (idx + 1 to match Excel/CSV 1-indexed row numbers, +1 for header)
    csv_row_number = csv_row_idx + 1  # +1 for header row
    param = params_by_row.get(csv_row_number)

    # STRATEGY 2: Fallback to name matching
    if not param:
        param = params_by_name.get(param_name)

    if not param:
        print(f"[{csv_row_idx}/{len(rows)}] ⚠ Parameter not found (row {csv_row_number}): {param_name[:60]}")
        continue

    param_id = param['id']

    # Extract URLs from URL column
    url_field = row.get('URL', '')
    urls_from_url_column = []

    if url_field:
        # Split by semicolon or newline
        if ';' in url_field:
            urls_from_url_column = [u.strip() for u in url_field.split(';') if u.strip()]
        else:
            urls_from_url_column = [url_field.strip()]

    # Extract URLs from External Sources column
    external_sources = row.get('External Sources', '')
    urls_from_external = extract_urls_from_text(external_sources)

    # Combine all URLs (deduplicate)
    all_urls = list(dict.fromkeys(urls_from_url_column + urls_from_external))

    if not all_urls:
        continue

    total_urls_found += len(all_urls)

    # Get existing sources for this parameter
    existing_sources = supabase.table('sources')\
        .select('url')\
        .eq('parameter_id', param_id)\
        .execute()

    existing_urls = {src['url'] for src in existing_sources.data}

    # Find missing URLs
    missing_urls = [url for url in all_urls if url not in existing_urls]

    if not missing_urls:
        continue

    print(f"[{csv_row_idx}/{len(rows)}] {param_name[:60]}")
    print(f"  Found {len(all_urls)} total URLs, {len(missing_urls)} missing")

    params_updated += 1

    # Add missing URLs
    for url in missing_urls:
        # Try to extract citation
        citation = parse_citation_from_external_sources(external_sources, url)

        # Extract year
        year = extract_year_from_citation(citation)

        # Determine source type (original if from URL column, external otherwise)
        source_type = 'original' if url in urls_from_url_column else 'external'

        try:
            insert_data = {
                'parameter_id': param_id,
                'url': url,
                'citation': citation,
                'year': year,
                'source_type': source_type
            }

            result = supabase.table('sources').insert(insert_data).execute()
            total_urls_added += 1

            print(f"    ✓ Added: {url[:70]}")
            if citation:
                print(f"      Citation: {citation[:60]}")

        except Exception as e:
            print(f"    ✗ Error adding {url[:60]}: {e}")
            total_urls_skipped += 1

print("\n" + "="*80)
print("UPDATE COMPLETE")
print("="*80)
print(f"Parameters updated: {params_updated}")
print(f"Total URLs found in CSV: {total_urls_found}")
print(f"URLs added to Supabase: {total_urls_added}")
print(f"URLs skipped (errors): {total_urls_skipped}")
print("="*80 + "\n")
