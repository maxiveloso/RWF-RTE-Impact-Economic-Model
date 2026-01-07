#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get one document to see schema
result = supabase.table('source_documents').select('*').limit(1).execute()

if result.data:
    print("source_documents table fields:")
    for key in result.data[0].keys():
        print(f"  - {key}")
else:
    print("No documents in table")
