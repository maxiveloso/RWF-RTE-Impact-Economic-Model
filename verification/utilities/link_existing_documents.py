#!/usr/bin/env python3
"""
Link existing documents in source_documents to parameters via source_document_id.

This script:
1. Lists all documents in source_documents table
2. For each parameter source that has a URL/citation but no source_document_id
3. Tries to match it to an existing document
4. Updates the source_document_id field
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import re
from urllib.parse import urlparse

# Load environment
load_dotenv()
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

print("="*80)
print("LINKING EXISTING DOCUMENTS TO PARAMETERS")
print("="*80)

# Step 1: Get all documents from source_documents
print("\n1. Fetching all documents from source_documents...")
docs_response = supabase.table('source_documents').select('*').execute()
documents = docs_response.data
print(f"   ✓ Found {len(documents)} documents in source_documents\n")

# Show what we have
print("   Available documents:")
for doc in documents:
    print(f"     - [{doc['id'][:8]}...] {doc.get('local_filename', 'NO_FILENAME')}")
    if doc.get('original_url'):
        print(f"       URL: {doc['original_url'][:70]}...")
    if doc.get('citation'):
        print(f"       Citation: {doc['citation'][:70]}...")
    print()

# Step 2: Get all sources without source_document_id
print("\n2. Fetching sources missing source_document_id...")
sources_response = supabase.table('sources')\
    .select('id, parameter_id, url, citation, source_document_id')\
    .is_('source_document_id', 'null')\
    .eq('source_type', 'original')\
    .execute()

sources_missing = sources_response.data
print(f"   ✓ Found {len(sources_missing)} sources without source_document_id\n")

# Step 3: Match sources to documents
print("\n3. Matching sources to documents...\n")

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url:
        return None
    # Remove protocol and trailing slashes
    parsed = urlparse(url)
    return parsed.netloc + parsed.path.rstrip('/')

def extract_keywords(citation):
    """Extract keywords from citation for fuzzy matching"""
    if not citation:
        return set()
    # Extract words (capitalized) and years
    words = re.findall(r'\b[A-Z][a-z]+|\b\d{4}\b', citation)
    return {w.lower() for w in words}

matches_found = []
no_match = []

for source in sources_missing:
    source_id = source['id']
    source_url = source.get('url')
    source_citation = source.get('citation')

    matched_doc = None
    match_method = None

    # Try URL match first (most reliable)
    if source_url:
        source_url_norm = normalize_url(source_url)
        for doc in documents:
            doc_url_norm = normalize_url(doc.get('original_url'))
            if doc_url_norm and source_url_norm == doc_url_norm:
                matched_doc = doc
                match_method = "EXACT_URL"
                break

    # Try fuzzy URL match (domain + partial path)
    if not matched_doc and source_url:
        source_domain = urlparse(source_url).netloc
        for doc in documents:
            doc_url = doc.get('original_url')
            if doc_url and source_domain in doc_url:
                # Check if paths are similar
                source_path = urlparse(source_url).path
                doc_path = urlparse(doc_url).path
                # Get filename from both
                source_file = source_path.split('/')[-1]
                doc_file = doc_path.split('/')[-1]
                if source_file and doc_file and source_file == doc_file:
                    matched_doc = doc
                    match_method = "FUZZY_URL"
                    break

    # Try citation match
    if not matched_doc and source_citation:
        source_keywords = extract_keywords(source_citation)
        if len(source_keywords) >= 2:  # Need at least 2 keywords
            best_score = 0
            best_doc = None

            for doc in documents:
                doc_citation = doc.get('citation', '')
                doc_keywords = extract_keywords(doc_citation)

                if doc_keywords:
                    score = len(source_keywords & doc_keywords)
                    if score > best_score and score >= 2:  # Need at least 2 matching keywords
                        best_score = score
                        best_doc = doc

            if best_doc:
                matched_doc = best_doc
                match_method = f"CITATION_FUZZY (score={best_score})"

    if matched_doc:
        matches_found.append({
            'source_id': source_id,
            'document_id': matched_doc['id'],
            'document_filename': matched_doc.get('local_filename', 'NO_NAME'),
            'match_method': match_method,
            'source_url': source_url[:60] if source_url else None,
            'source_citation': source_citation[:60] if source_citation else None
        })
        print(f"   ✓ MATCH [{match_method}]")
        print(f"     Source: {source_citation[:60] if source_citation else source_url[:60]}...")
        print(f"     → Doc: {matched_doc.get('local_filename', 'NO_NAME')}")
        print()
    else:
        no_match.append({
            'source_id': source_id,
            'source_url': source_url,
            'source_citation': source_citation
        })

print("\n" + "="*80)
print(f"MATCHING RESULTS")
print("="*80)
print(f"✓ Matched: {len(matches_found)} sources")
print(f"✗ No match: {len(no_match)} sources")
print()

# Step 4: Ask user for confirmation
if matches_found:
    print("="*80)
    print("MATCHES TO BE UPDATED")
    print("="*80)
    for match in matches_found:
        print(f"  {match['match_method']}: {match['document_filename']}")
    print()

    response = input(f"Update {len(matches_found)} sources with matched document IDs? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print("\nUpdating sources...")
        updated_count = 0
        for match in matches_found:
            try:
                supabase.table('sources')\
                    .update({'source_document_id': match['document_id']})\
                    .eq('id', match['source_id'])\
                    .execute()
                updated_count += 1
                print(f"  ✓ Updated source → {match['document_filename']}")
            except Exception as e:
                print(f"  ✗ Failed to update source: {e}")

        print(f"\n✓ Successfully updated {updated_count}/{len(matches_found)} sources")
    else:
        print("\nUpdate cancelled.")

# Step 5: Show what still needs work
if no_match:
    print("\n" + "="*80)
    print("SOURCES THAT STILL NEED DOCUMENTS")
    print("="*80)
    print("These sources couldn't be matched to existing documents.")
    print("You'll need to either:")
    print("  1. Download and process these PDFs")
    print("  2. Manually link them in Supabase\n")

    for item in no_match[:10]:  # Show first 10
        print(f"  Source ID: {item['source_id'][:8]}...")
        if item['source_citation']:
            print(f"    Citation: {item['source_citation'][:70]}...")
        if item['source_url']:
            print(f"    URL: {item['source_url'][:70]}...")
        print()

    if len(no_match) > 10:
        print(f"  ... and {len(no_match) - 10} more")

print("\n" + "="*80)
print("Done!")
print("="*80)
