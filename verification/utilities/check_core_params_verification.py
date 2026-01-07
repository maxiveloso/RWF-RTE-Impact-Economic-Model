#!/usr/bin/env python3
"""
Check which 0-VETTING and 1A-CORE_MODEL parameters have been verified.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("CORE PARAMETERS VERIFICATION STATUS")
print("=" * 80)

# Get all core parameters
core_categories = ['0-VETTING', '1A-CORE_MODEL']

for category in core_categories:
    print(f"\n{category}")
    print("-" * 40)

    # Get parameters in this category
    params = supabase.table("parameters").select("id, friendly_name, python_const_name, original_value").eq("category", category).execute()

    for p in params.data:
        param_id = p['id']
        name = p.get('friendly_name') or p.get('python_const_name') or 'Unknown'
        value = (p.get('original_value') or '')[:30]

        # Check if verified
        verification = supabase.table("claim_verification_log").select("*").eq("parameter_id", param_id).order("verified_at", desc=True).limit(1).execute()

        if verification.data:
            v = verification.data[0]
            status = v.get('match_type', 'N/A')
            conf = v.get('confidence_score')
            conf_str = f"{int(conf*100)}%" if conf else 'N/A'
            verified_at = v.get('verified_at', '')[:10]
            print(f"  ✓ {name[:40]}")
            print(f"      Value: {value}... | Status: {status} | Conf: {conf_str} | Date: {verified_at}")
        else:
            print(f"  ✗ {name[:40]}")
            print(f"      Value: {value}... | NOT VERIFIED")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("-" * 40)

total_core = 0
verified_core = 0

for category in core_categories:
    params = supabase.table("parameters").select("id").eq("category", category).execute()
    cat_total = len(params.data)

    verified_count = 0
    for p in params.data:
        verification = supabase.table("claim_verification_log").select("id").eq("parameter_id", p['id']).limit(1).execute()
        if verification.data:
            verified_count += 1

    total_core += cat_total
    verified_core += verified_count
    print(f"  {category}: {verified_count}/{cat_total} verified")

print(f"\n  TOTAL CORE: {verified_core}/{total_core} verified")
print("=" * 80)
