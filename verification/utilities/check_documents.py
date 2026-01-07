#!/usr/bin/env python3
"""Quick check of inserted documents"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n=== Source Documents in Database ===\n")

docs = supabase.table('source_documents').select('id, local_filename, num_pages, num_words, original_url').execute()

print(f"Total documents: {len(docs.data)}\n")

for idx, doc in enumerate(docs.data, 1):
    print(f"{idx}. {doc['local_filename']}")
    print(f"   Pages: {doc.get('num_pages', 'N/A')}, Words: {doc.get('num_words', 0):,}")
    print(f"   URL: {doc['original_url'][:80]}...")
    print()
