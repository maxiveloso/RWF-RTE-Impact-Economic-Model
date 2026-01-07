#!/usr/bin/env python3
"""
Check document matching for 0-VETTING and 1A-CORE_MODEL parameters.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SOURCES_DIR = Path(__file__).parent / 'sources'

# Stopwords and key acronyms from the verification script
STOPWORDS = {
    'annual', 'report', 'paper', 'study', 'survey', 'data', 'india', 'indian',
    'national', 'economic', 'social', 'development', 'ministry', 'government',
    'analysis', 'review', 'working', 'research', 'policy', 'the', 'and', 'for',
    'bulletin', 'statistics', 'statistical', 'quarterly', 'monthly', 'yearly',
    'www', 'http', 'https', 'com', 'org', 'gov', 'pdf', 'html', 'files', 'uploads'
}
KEY_ACRONYMS = {'plfs', 'msde', 'nber', 'ilo', 'niti', 'dgt', 'aser', 'nsso', 'ncaer', 'rbi', 'nsdc', 'nfhs'}

def get_local_files():
    """Get all local PDF/TXT files."""
    files = {}
    for f in SOURCES_DIR.glob('*'):
        if f.suffix.lower() in ['.pdf', '.txt']:
            # Extract keywords from filename
            words = set()
            for part in f.stem.split('_'):
                part_lower = part.lower()
                if re.match(r'^\d{2,4}$', part):
                    words.add(part_lower)
                elif len(part) >= 2 and part_lower not in STOPWORDS:
                    words.add(part_lower)
            files[f.name] = words
    return files

def extract_keywords(text):
    """Extract keywords from citation/URL."""
    if not text:
        return set()
    raw_words = set(re.findall(r'\b[A-Z]{2,}|\b[A-Z][a-z]+|\b\d{4}\b', text))
    raw_words.update(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    words = {w.lower() for w in raw_words} - STOPWORDS
    # Year patterns
    for match in re.findall(r'\b(\d{2})-(\d{2})\b|\b(\d{4})-(\d{2})\b', text):
        for part in match:
            if part and len(part) >= 2:
                words.add(part)
    return words

def find_best_match(search_text, local_files):
    """Find best matching local file."""
    if not search_text:
        return None, 0, set()

    search_words = extract_keywords(search_text)

    candidates = []
    for filename, file_words in local_files.items():
        matched = search_words & file_words
        score = len(matched)

        # Bonus for key acronyms
        acronym_matches = matched & KEY_ACRONYMS
        if acronym_matches:
            score += len(acronym_matches) * 3

        # Penalty for mismatched acronyms
        search_acronyms = search_words & KEY_ACRONYMS
        file_acronyms = file_words & KEY_ACRONYMS
        if search_acronyms and file_acronyms:
            mismatched = file_acronyms - search_acronyms
            if mismatched:
                score -= len(mismatched) * 5

        if score > 0:
            candidates.append((filename, score, matched))

    candidates.sort(key=lambda x: -x[1])

    if candidates and candidates[0][1] >= 2:
        return candidates[0]
    return None, 0, set()

print("=" * 100)
print("DOCUMENT MATCHING ANALYSIS FOR CORE PARAMETERS")
print("=" * 100)

local_files = get_local_files()
print(f"\nLocal files indexed: {len(local_files)}")

core_categories = ['0-VETTING', '1A-CORE_MODEL']

for category in core_categories:
    print(f"\n{'='*100}")
    print(f"CATEGORY: {category}")
    print("=" * 100)

    # Get parameters with sources
    params = supabase.table("parameters").select("id, friendly_name, python_const_name, sources(*)").eq("category", category).execute()

    for p in params.data:
        param_name = p.get('friendly_name') or p.get('python_const_name') or 'Unknown'
        sources = [s for s in p.get('sources', []) if s.get('source_type') == 'original']

        print(f"\n  PARAM: {param_name}")
        print(f"  Sources: {len(sources)}")

        if not sources:
            print(f"    ⚠️ NO SOURCES LINKED")
            continue

        for i, src in enumerate(sources, 1):
            citation = src.get('citation') or ''
            url = src.get('url') or ''

            # Try citation first, then URL
            search_text = citation if citation else url

            match, score, matched_words = find_best_match(search_text, local_files)

            citation_preview = (citation[:50] + '...') if len(citation) > 50 else (citation or '(empty)')
            url_preview = (url[:60] + '...') if len(url) > 60 else (url or '(empty)')

            print(f"\n    Source {i}:")
            print(f"      Citation: {citation_preview}")
            print(f"      URL: {url_preview}")

            if match:
                print(f"      ✓ MATCH: {match} (score={score})")
                print(f"        Keywords matched: {matched_words}")
            else:
                # Show what keywords were extracted
                kw = extract_keywords(search_text)
                print(f"      ✗ NO MATCH (score={score})")
                print(f"        Extracted keywords: {kw}")
                # Show top 3 potential matches even if score < 2
                all_candidates = []
                for filename, file_words in local_files.items():
                    matched = kw & file_words
                    s = len(matched)
                    if s > 0:
                        all_candidates.append((filename, s, matched))
                all_candidates.sort(key=lambda x: -x[1])
                if all_candidates:
                    print(f"        Closest (but below threshold):")
                    for fn, sc, mw in all_candidates[:3]:
                        print(f"          - {fn} (score={sc}, matched={mw})")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
