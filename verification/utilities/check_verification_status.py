#!/usr/bin/env python3
"""Check verification status in database"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n=== Claim Verification Status ===\n")

# Get verification logs
logs = supabase.table('claim_verification_log')\
    .select('parameter_id, claim_text, match_type, confidence_score, needs_human_review, verified_at')\
    .order('verified_at')\
    .execute()

print(f"Total verifications in database: {len(logs.data)}\n")

# Summary by match type
from collections import Counter
match_types = Counter(log['match_type'] for log in logs.data)

print("Results by Match Type:")
for match_type, count in match_types.items():
    print(f"  {match_type.upper()}: {count}")

# Count needing review
needs_review = sum(1 for log in logs.data if log.get('needs_human_review'))
print(f"\nNeeds human review: {needs_review}")

print("\n=== Recent Verifications ===\n")
for log in logs.data[-5:]:
    print(f"• {log.get('claim_text', 'Unknown')[:60]}...")
    print(f"  Match: {log['match_type'].upper()}, Confidence: {log.get('confidence_score', 0):.1%}")
    print(f"  Verified: {log.get('verified_at', 'Unknown')[:19]}")
    print()
