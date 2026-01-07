#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get one source to see its structure
result = supabase.table('sources').select('*').limit(1).execute()

if result.data:
    print("Sources table fields:")
    for key in result.data[0].keys():
        print(f"  - {key}: {result.data[0][key]}")
