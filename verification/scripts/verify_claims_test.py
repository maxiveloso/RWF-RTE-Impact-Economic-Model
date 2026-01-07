#!/usr/bin/env python3
"""
Test version of verify_claims.py - processes only first 3 parameters
"""

import os
import re
import json
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-r1')

if not all([SUPABASE_URL, SUPABASE_KEY, OPENROUTER_API_KEY]):
    raise ValueError("SUPABASE_URL, SUPABASE_KEY, and OPENROUTER_API_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load LLM prompt
PROMPT_FILE = Path(__file__).parent / 'src' / 'LLM_Prompt_Expert.md'
if not PROMPT_FILE.exists():
    PROMPT_FILE = Path(__file__).parent / 'LLM_Prompt_Expert.md'

if PROMPT_FILE.exists():
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        LLM_SYSTEM_PROMPT = f.read()
else:
    print("Warning: LLM_Prompt_Expert.md not found, using basic prompt")
    LLM_SYSTEM_PROMPT = """You are an expert economist verifying parameters for an economic impact model.
    Analyze the provided document and determine if it supports the claimed parameter value."""


print(f"\n{'='*80}")
print(f"RWF CLAIM VERIFICATION - TEST MODE (First 3 Parameters Only)")
print(f"{'='*80}\n")

# Load parameters with their sources
print("Loading parameters and sources from Supabase...")
try:
    params_response = supabase.table('parameters')\
        .select('*, sources(*)')\
        .execute()

    parameters = params_response.data
    print(f"  ✓ Loaded {len(parameters)} parameters\n")
except Exception as e:
    print(f"  ✗ Error loading data: {str(e)}")
    exit(1)

# Filter to only parameters with 'original' sources that have documents
params_to_verify = []
for param in parameters:
    if param.get('sources'):
        for source in param['sources']:
            if source.get('source_type') == 'original' and source.get('url'):
                # Check if document exists
                try:
                    doc_check = supabase.table('source_documents')\
                        .select('id')\
                        .eq('original_url', source['url'])\
                        .execute()

                    if doc_check.data and len(doc_check.data) > 0:
                        params_to_verify.append({
                            'parameter': param,
                            'source': source
                        })
                        break  # Only verify against one original source per parameter
                except:
                    pass

print(f"Found {len(params_to_verify)} parameters with documents available")
print(f"Testing with first 3 parameters...\n")
print(f"{'='*80}\n")

# Test with first 3
for idx, item in enumerate(params_to_verify[:3], 1):
    param = item['parameter']
    source = item['source']

    param_name = param.get('friendly_name', param.get('python_const_name', 'Unknown'))
    claim_value = param.get('original_value', '')

    print(f"[{idx}/3] Testing: {param_name}")
    print(f"  Claimed value: {claim_value}")

    source_url = source.get('url')
    print(f"  Source URL: {source_url[:60]}...")

    # Get document
    try:
        doc_response = supabase.table('source_documents')\
            .select('id, local_filename, full_text')\
            .eq('original_url', source_url)\
            .execute()

        doc = doc_response.data[0]
        doc_filename = doc['local_filename']
        doc_text = doc['full_text'][:5000]  # Limit for testing

        print(f"  ✓ Document: {doc_filename}")
        print(f"  ✓ Text length: {len(doc_text):,} chars (truncated for test)")
        print(f"  ✓ Ready to send to LLM")
        print()

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        print()

print(f"{'='*80}")
print(f"Test completed successfully!")
print(f"Ready to run full verification with: python verify_claims.py")
print(f"{'='*80}\n")
