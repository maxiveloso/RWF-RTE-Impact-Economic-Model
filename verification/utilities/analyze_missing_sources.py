#!/usr/bin/env python3
"""
Analyze which parameters have missing or incomplete source information.
"""

import os
import csv
from supabase import create_client
from dotenv import load_dotenv
from collections import defaultdict

# Load environment
load_dotenv()
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

print("Fetching all parameters with sources from Supabase...")

# Get all parameters with their sources
params_response = supabase.table('parameters')\
    .select('id, friendly_name, python_const_name, original_value, sources(*)')\
    .execute()

parameters = params_response.data

print(f"✓ Loaded {len(parameters)} total parameters\n")

# Analyze source completeness
complete_sources = []
incomplete_sources = []
no_sources = []

for param in parameters:
    param_id = param['id']
    param_name = param.get('friendly_name') or param.get('python_const_name', 'Unknown')
    param_value = param.get('original_value', '')

    if not param.get('sources'):
        no_sources.append({
            'param_id': param_id,
            'param_name': param_name,
            'param_value': param_value,
            'issue': 'NO_SOURCES',
            'url': None,
            'citation': None,
            'source_doc_id': None
        })
        continue

    # Check each source
    for source in param['sources']:
        if source.get('source_type') != 'original':
            continue

        url = source.get('url')
        citation = source.get('citation')
        source_doc_id = source.get('source_document_id')

        # Categorize by completeness
        if source_doc_id:
            # Has document ID - should be complete
            complete_sources.append({
                'param_id': param_id,
                'param_name': param_name,
                'param_value': param_value,
                'url': url,
                'citation': citation,
                'source_doc_id': source_doc_id,
                'status': 'COMPLETE'
            })
        elif url and citation:
            # Has URL and citation but no doc_id
            incomplete_sources.append({
                'param_id': param_id,
                'param_name': param_name,
                'param_value': param_value,
                'url': url,
                'citation': citation,
                'source_doc_id': source_doc_id,
                'issue': 'MISSING_DOC_ID'
            })
        elif url or citation:
            # Has only URL or only citation
            incomplete_sources.append({
                'param_id': param_id,
                'param_name': param_name,
                'param_value': param_value,
                'url': url,
                'citation': citation,
                'source_doc_id': source_doc_id,
                'issue': 'PARTIAL_INFO'
            })
        else:
            # Has source entry but no useful info
            incomplete_sources.append({
                'param_id': param_id,
                'param_name': param_name,
                'param_value': param_value,
                'url': url,
                'citation': citation,
                'source_doc_id': source_doc_id,
                'issue': 'EMPTY_SOURCE'
            })

# Print summary
print("="*80)
print("SOURCE COMPLETENESS ANALYSIS")
print("="*80)
print(f"✓ Complete sources (with source_document_id): {len(complete_sources)}")
print(f"⚠ Incomplete sources (missing doc_id): {len(incomplete_sources)}")
print(f"✗ No sources at all: {len(no_sources)}")
print()

# Show incomplete sources in detail
if incomplete_sources:
    print("="*80)
    print("PARAMETERS WITH INCOMPLETE SOURCES")
    print("="*80)

    # Group by issue type
    by_issue = defaultdict(list)
    for item in incomplete_sources:
        by_issue[item['issue']].append(item)

    for issue_type, items in by_issue.items():
        print(f"\n{issue_type}: {len(items)} parameters")
        print("-" * 80)
        for item in items:
            print(f"  • {item['param_name']}")
            print(f"    Value: {item['param_value']}")
            print(f"    URL: {item['url'][:60] if item['url'] else 'None'}...")
            print(f"    Citation: {item['citation'][:60] if item['citation'] else 'None'}...")
            print(f"    ID: {item['param_id'][:8]}...")
            print()

# Save to CSV
if incomplete_sources:
    csv_path = 'parameters_missing_sources.csv'
    with open(csv_path, 'w', newline='') as f:
        fieldnames = ['param_id', 'param_name', 'param_value', 'url', 'citation', 'source_doc_id', 'issue']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(incomplete_sources)
    print(f"\n✓ Saved incomplete sources to: {csv_path}")

# Show which URLs are most common
if incomplete_sources:
    print("\n" + "="*80)
    print("MOST COMMON GENERIC URLs (need specific PDFs)")
    print("="*80)
    url_counts = defaultdict(int)
    for item in incomplete_sources:
        if item['url']:
            url_counts[item['url']] += 1

    for url, count in sorted(url_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{count:2d}× {url}")

print("\n" + "="*80)
