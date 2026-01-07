#!/usr/bin/env python3
"""
Export all verification results from claim_verification_log to CSV.
"""

import os
import csv
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

print("="*80)
print("EXPORTING VERIFICATION RESULTS FROM SUPABASE")
print("="*80)

# Get all verification logs
print("\n1. Fetching verification logs...")
logs_response = supabase.table('claim_verification_log').select('*').execute()
logs = logs_response.data
print(f"   ✓ Found {len(logs)} records\n")

if not logs:
    print("No records found.")
    exit(0)

# Get parameters
print("2. Fetching parameters...")
params_response = supabase.table('parameters').select('id, friendly_name, python_const_name, original_value').execute()
params_dict = {p['id']: p for p in params_response.data}
print(f"   ✓ Loaded {len(params_dict)} parameters\n")

# Get sources
print("3. Fetching sources...")
sources_response = supabase.table('sources').select('id, url, citation').execute()
sources_dict = {s['id']: s for s in sources_response.data}
print(f"   ✓ Loaded {len(sources_dict)} sources\n")

# Enrich logs
print("4. Processing...")
enriched = []
for log in logs:
    param = params_dict.get(log.get('parameter_id'), {})
    source = sources_dict.get(log.get('source_id'), {})
    enriched.append({
        'parameter_name': param.get('friendly_name', param.get('python_const_name', 'Unknown')),
        'claim_value': param.get('original_value', ''),
        'source_document': log.get('source_document', ''),
        'source_url': (source.get('url', '') or '')[:100],
        'verification_status': log.get('verification_status', ''),
        'confidence_score': log.get('confidence_score', 0),
        'confidence_level': log.get('confidence_level', ''),
        'match_type': log.get('match_type', ''),
        'extracted_snippet': (log.get('extracted_snippet', '') or '')[:200],
        'needs_review': log.get('needs_human_review', False),
        'verified_at': log.get('verified_at', '')
    })

# Save CSV
csv_path = 'verification_results_complete.csv'
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=enriched[0].keys())
    writer.writeheader()
    writer.writerows(enriched)

print(f"✓ Saved {len(enriched)} records to {csv_path}\n")

# Summary
status_counts = {}
for item in enriched:
    status = item['verification_status'] or 'UNKNOWN'
    status_counts[status] = status_counts.get(status, 0) + 1

print("SUMMARY:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

avg_conf = sum(item['confidence_score'] for item in enriched) / len(enriched) if enriched else 0
print(f"\nAverage Confidence: {avg_conf:.1f}%")
print(f"Needs Review: {sum(1 for i in enriched if i['needs_review'])}")
