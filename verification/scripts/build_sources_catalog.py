#!/usr/bin/env python3
"""
Build a catalog/index of all files in /sources for faster lookup
Extracts metadata: filename, potential authors, year, keywords
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List
import PyPDF2

def extract_metadata_from_filename(filename: str) -> Dict:
    """Extract metadata from filename convention: author_year_title.pdf"""
    metadata = {
        'filename': filename,
        'authors': [],
        'year': None,
        'keywords': [],
        'file_size_kb': 0
    }

    stem = Path(filename).stem
    parts = stem.split('_')

    # Extract year (4-digit number)
    years = [p for p in parts if re.match(r'^\d{4}$', p)]
    if years:
        metadata['year'] = int(years[0])

    # Extract potential author names (capitalized words at start)
    for part in parts[:3]:  # First 3 parts are usually authors
        if part and not part.isdigit() and len(part) >= 3:
            # Clean up
            part_clean = re.sub(r'[^a-zA-Z]', '', part)
            if part_clean and part_clean[0].isupper():
                metadata['authors'].append(part_clean.lower())

    # Extract keywords (all parts with 4+ chars, lowercase)
    for part in parts:
        if len(part) >= 4 and not part.isdigit():
            keyword = re.sub(r'[^a-zA-Z]', '', part).lower()
            if keyword and keyword not in metadata['authors']:
                metadata['keywords'].append(keyword)

    return metadata


def extract_metadata_from_pdf(file_path: Path) -> Dict:
    """Extract metadata from PDF file itself (first page, PDF info)"""
    metadata = {
        'pdf_title': None,
        'pdf_author': None,
        'pdf_subject': None,
        'first_page_text': ''
    }

    try:
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)

            # PDF metadata
            if pdf.metadata:
                metadata['pdf_title'] = pdf.metadata.get('/Title', '')
                metadata['pdf_author'] = pdf.metadata.get('/Author', '')
                metadata['pdf_subject'] = pdf.metadata.get('/Subject', '')

            # Extract first page text (first 500 chars for title/author detection)
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                metadata['first_page_text'] = text[:500] if text else ''

    except Exception as e:
        print(f"    ⚠️ Error reading PDF metadata: {e}")

    return metadata


def build_catalog(sources_dir: Path) -> List[Dict]:
    """Build complete catalog of all files in sources/"""
    catalog = []

    print("\n" + "="*80)
    print("BUILDING SOURCES CATALOG")
    print("="*80 + "\n")

    files = list(sources_dir.glob('*.pdf')) + list(sources_dir.glob('*.txt'))
    print(f"Found {len(files)} files in {sources_dir}\n")

    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file_path.name}")

        entry = {
            'filename': file_path.name,
            'file_path': str(file_path),
            'file_size_kb': file_path.stat().st_size / 1024,
            'file_type': file_path.suffix.lower()
        }

        # Extract from filename
        filename_meta = extract_metadata_from_filename(file_path.name)
        entry.update(filename_meta)

        # Extract from PDF content (if PDF)
        if file_path.suffix.lower() == '.pdf':
            pdf_meta = extract_metadata_from_pdf(file_path)
            entry['pdf_metadata'] = pdf_meta

        catalog.append(entry)

    print(f"\n✓ Catalog built: {len(catalog)} entries\n")
    print("="*80 + "\n")

    return catalog


def save_catalog(catalog: List[Dict], output_path: Path):
    """Save catalog to JSON file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"✓ Catalog saved to: {output_path}")
    print(f"  Total entries: {len(catalog)}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB\n")


def search_catalog(catalog: List[Dict], query: str, threshold: int = 1) -> List[Dict]:
    """
    Search catalog for files matching query
    Returns list of matches sorted by relevance score
    """
    query_words = set(re.findall(r'\b[A-Za-z]+\b', query.lower()))
    query_years = set(re.findall(r'\b\d{4}\b', query))

    results = []

    for entry in catalog:
        score = 0

        # Match authors
        for author in entry.get('authors', []):
            if author in query_words:
                score += 3  # Authors are important

        # Match year
        if entry.get('year') and str(entry['year']) in query_years:
            score += 2

        # Match keywords
        for keyword in entry.get('keywords', []):
            if keyword in query_words:
                score += 1

        # Match filename
        filename_lower = entry['filename'].lower()
        for word in query_words:
            if word in filename_lower:
                score += 0.5

        if score >= threshold:
            results.append({
                'entry': entry,
                'score': score
            })

    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


if __name__ == '__main__':
    sources_dir = Path(__file__).parent / 'sources'
    output_path = Path(__file__).parent / 'sources_catalog.json'

    if not sources_dir.exists():
        print(f"❌ Sources directory not found: {sources_dir}")
        exit(1)

    # Build catalog
    catalog = build_catalog(sources_dir)

    # Save to JSON
    save_catalog(catalog, output_path)

    # Example search
    print("\n" + "="*80)
    print("EXAMPLE SEARCH: 'Evans Yuan 2019'")
    print("="*80 + "\n")

    results = search_catalog(catalog, "Evans Yuan 2019")

    print(f"Found {len(results)} matches:\n")
    for i, result in enumerate(results[:3], 1):
        entry = result['entry']
        print(f"[{i}] Score: {result['score']}")
        print(f"    File: {entry['filename']}")
        print(f"    Authors: {', '.join(entry.get('authors', []))}")
        print(f"    Year: {entry.get('year')}")
        print()
