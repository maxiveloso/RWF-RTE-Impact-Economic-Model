#!/usr/bin/env python3
"""Quick test to verify Supabase connection"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

print("Testing Supabase connection...")
print(f"URL: {SUPABASE_URL}")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Test query
    response = supabase.table('parameters').select('id').limit(1).execute()
    print(f"✓ Connection successful!")
    print(f"✓ Can access 'parameters' table")

    # Count tables
    params_count = supabase.table('parameters').select('id', count='exact').execute()
    sources_count = supabase.table('sources').select('id', count='exact').execute()

    print(f"✓ Parameters count: {params_count.count}")
    print(f"✓ Sources count: {sources_count.count}")

except Exception as e:
    print(f"✗ Connection failed: {str(e)}")
