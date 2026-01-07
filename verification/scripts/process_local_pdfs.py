#!/usr/bin/env python3
"""
Process Local PDFs - RWF Claim Verification Pipeline
Extracts text from PDF/TXT files and matches them to Supabase sources table
"""

import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import csv

from PyPDF2 import PdfReader
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SOURCE_DIR = os.getenv('SOURCE_DIR', './sources')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_filename(filename: str) -> Dict[str, any]:
    """
    Parse filename following convention: [autor1]_[autor2]_[año]_[keywords].pdf

    Returns:
        dict: {authors: list, year: int, keywords: list, base_name: str}
    """
    # Remove extension
    base_name = Path(filename).stem

    # Split by underscore
    parts = base_name.split('_')

    parsed = {
        'authors': [],
        'year': None,
        'keywords': [],
        'base_name': base_name
    }

    for i, part in enumerate(parts):
        # Check if it's a year (4 digits)
        if re.match(r'^\d{4}$', part):
            parsed['year'] = int(part)
            # Everything before is authors, after is keywords
            parsed['authors'] = parts[:i]
            parsed['keywords'] = parts[i+1:]
            break

    # If no year found, treat all as keywords
    if parsed['year'] is None:
        parsed['keywords'] = parts

    return parsed


def extract_pdf_text(filepath: str) -> Tuple[str, int, Optional[str]]:
    """
    Extract text from PDF file.

    Returns:
        tuple: (full_text, num_pages, error_message)
    """
    try:
        reader = PdfReader(filepath)
        num_pages = len(reader.pages)

        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                print(f"  Warning: Error extracting page {page_num}: {str(e)}")

        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            return "", num_pages, "No text could be extracted from PDF"

        return full_text, num_pages, None

    except Exception as e:
        return "", 0, f"PDF extraction failed: {str(e)}"


def extract_txt_content(filepath: str) -> Tuple[str, Optional[str]]:
    """
    Read plain text file.

    Returns:
        tuple: (content, error_message)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, None
    except UnicodeDecodeError:
        try:
            # Try latin-1 encoding
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
            return content, None
        except Exception as e:
            return "", f"Text extraction failed: {str(e)}"
    except Exception as e:
        return "", f"Text extraction failed: {str(e)}"


def calculate_hash(text: str) -> str:
    """Calculate SHA256 hash of text content."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def find_matching_url(parsed: Dict, sources: List[Dict]) -> Optional[str]:
    """
    Find the URL this file corresponds to based on citation/URL matching.

    Args:
        parsed: Parsed filename info
        sources: List of source records from database

    Returns:
        str: Matched URL or None
    """
    best_match = None
    best_score = 0

    for source in sources:
        score = 0

        # Check citation field
        if source.get('citation'):
            citation_lower = source['citation'].lower()

            # Author match (worth 2 points each)
            for author in parsed['authors']:
                if author.lower() in citation_lower:
                    score += 2

            # Year match (worth 2 points)
            if parsed['year'] and str(parsed['year']) in citation_lower:
                score += 2

        # Check URL for keywords (worth 1 point each)
        if source.get('url'):
            url_lower = source['url'].lower()

            # Check for author names in URL
            for author in parsed['authors']:
                if author.lower() in url_lower:
                    score += 1

            # Check for year in URL
            if parsed['year'] and str(parsed['year']) in url_lower:
                score += 1

            # Check for keywords in URL
            for keyword in parsed['keywords']:
                if keyword.lower() in url_lower:
                    score += 1

        # Update best match if this score is higher
        if score > best_score:
            best_score = score
            best_match = source.get('url')

    # Return match only if score is >= 3
    return best_match if best_score >= 3 else None


def insert_source_document(doc_data: Dict) -> Optional[str]:
    """
    Insert document into source_documents table.

    Returns:
        str: document_id if successful, None otherwise
    """
    try:
        response = supabase.table('source_documents').insert(doc_data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"  Error inserting document: {str(e)}")
        return None


def process_directory(source_dir: str):
    """
    Main processing function.
    """
    print(f"\n{'='*80}")
    print(f"RWF CLAIM VERIFICATION PIPELINE - PDF PROCESSING")
    print(f"{'='*80}\n")

    source_path = Path(source_dir)
    if not source_path.exists():
        raise ValueError(f"Source directory does not exist: {source_dir}")

    # Load all sources from Supabase
    print("Loading sources from Supabase...")
    try:
        sources_response = supabase.table('sources').select('id, url, citation, year, source_type').execute()
        sources = sources_response.data
        print(f"  ✓ Loaded {len(sources)} source records\n")
    except Exception as e:
        print(f"  ✗ Error loading sources: {str(e)}")
        return

    # Find all PDF and TXT files
    pdf_files = list(source_path.glob('*.pdf'))
    txt_files = list(source_path.glob('*.txt'))
    all_files = pdf_files + txt_files

    print(f"Found {len(pdf_files)} PDF files and {len(txt_files)} TXT files\n")
    print(f"{'='*80}\n")

    # Results for CSV export
    results = []

    # Process each file
    for idx, filepath in enumerate(all_files, 1):
        filename = filepath.name
        file_type = 'pdf' if filepath.suffix.lower() == '.pdf' else 'txt'

        print(f"[{idx}/{len(all_files)}] Processing: {filename}")

        # Parse filename
        parsed = parse_filename(filename)
        print(f"  Parsed: authors={parsed['authors']}, year={parsed['year']}, keywords={parsed['keywords'][:3]}...")

        # Extract text
        if file_type == 'pdf':
            full_text, num_pages, error = extract_pdf_text(str(filepath))
            num_words = count_words(full_text) if full_text else 0
        else:
            full_text, error = extract_txt_content(str(filepath))
            num_pages = 0
            num_words = count_words(full_text) if full_text else 0

        # Check extraction status
        if error:
            print(f"  ✗ Extraction error: {error}")
            extraction_status = 'failed'
        elif not full_text.strip():
            print(f"  ✗ No text extracted")
            extraction_status = 'failed'
        else:
            print(f"  ✓ Extracted {num_words:,} words" + (f" from {num_pages} pages" if num_pages > 0 else ""))
            extraction_status = 'success'

        # Calculate hash
        content_hash = calculate_hash(full_text) if full_text else None

        # Find matching URL
        matched_url = find_matching_url(parsed, sources)

        if matched_url:
            print(f"  ✓ Matched to URL: {matched_url[:60]}...")
            match_confidence = "high"
        else:
            print(f"  ⚠ No URL match found (will need manual review)")
            match_confidence = "none"

        # Check if document already exists by URL
        doc_exists = False
        if matched_url:
            try:
                existing = supabase.table('source_documents')\
                    .select('id')\
                    .eq('original_url', matched_url)\
                    .execute()

                if existing.data and len(existing.data) > 0:
                    doc_exists = True
                    print(f"  ℹ Document already exists in database (skipping)")
            except Exception as e:
                print(f"  Warning: Error checking existing document: {str(e)}")

        # Count how many sources reference this URL
        num_sources_linked = 0
        if matched_url:
            num_sources_linked = sum(1 for s in sources if s.get('url') == matched_url)
            if num_sources_linked > 1:
                print(f"  ℹ This document is referenced by {num_sources_linked} parameters")

        # Insert document if it doesn't exist and extraction was successful
        doc_id = None
        if not doc_exists and extraction_status == 'success' and matched_url:
            doc_data = {
                'original_url': matched_url,
                'local_filename': filename,
                'file_type': file_type,
                'file_size_bytes': filepath.stat().st_size,
                'parsed_authors': parsed['authors'],
                'parsed_year': parsed['year'],
                'parsed_title_keywords': parsed['keywords'],
                'full_text': full_text,
                'num_pages': num_pages if num_pages > 0 else None,
                'num_words': num_words,
                'content_hash': content_hash,
                'extraction_status': extraction_status,
                'extraction_error': error,
                'processed_at': datetime.utcnow().isoformat()
            }

            doc_id = insert_source_document(doc_data)
            if doc_id:
                print(f"  ✓ Inserted into database (ID: {doc_id[:8]}...)")
            else:
                print(f"  ✗ Failed to insert into database")

        # Record result
        results.append({
            'local_filename': filename,
            'matched_url': matched_url or '',
            'match_confidence': match_confidence,
            'extraction_status': extraction_status,
            'num_sources_linked': num_sources_linked,
            'num_pages': num_pages,
            'num_words': num_words,
            'document_id': doc_id or '',
            'error': error or ''
        })

        print()  # Blank line between files

    # Generate mapping report
    print(f"{'='*80}\n")
    print("Generating mapping report...")

    csv_path = 'pdf_mapping.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'local_filename', 'matched_url', 'match_confidence', 'extraction_status',
            'num_sources_linked', 'num_pages', 'num_words', 'document_id', 'error'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"  ✓ Report saved to: {csv_path}\n")

    # Summary statistics
    total = len(results)
    successful = sum(1 for r in results if r['extraction_status'] == 'success')
    failed = sum(1 for r in results if r['extraction_status'] == 'failed')
    matched = sum(1 for r in results if r['matched_url'])
    unmatched = total - matched

    print(f"{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total files processed: {total}")
    print(f"  ✓ Successful extractions: {successful}")
    print(f"  ✗ Failed extractions: {failed}")
    print(f"  ✓ Matched to URLs: {matched}")
    print(f"  ⚠ Unmatched (need review): {unmatched}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    try:
        process_directory(SOURCE_DIR)
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        raise
