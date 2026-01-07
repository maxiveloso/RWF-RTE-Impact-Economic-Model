#!/usr/bin/env python3
"""
OCR Processor for Scanned PDFs - RWF Project
Extracts text using Tesseract OCR when PyPDF2 fails

VERSION: 2.1
UPDATED: January 5, 2026

FEATURES:
- Hybrid extraction: PyPDF2 first per page, OCR fallback for empty pages
- Smart detection: Only runs OCR if PyPDF2 fails
- Parallel processing: 4x speedup using multiprocessing
- Smart sampling: For huge PDFs, scans first 100 pages + distributed sample
- Progress tracking: Real-time progress bars

CHANGES IN v2.1:
- Added extract_text_hybrid() for mixed PDFs (some pages scanned, some not)
- Per-page decision: PyPDF2 first, OCR only if <50 chars extracted
- Handles mixed PDFs like MSDE (pages 1-2 scanned, rest has text)
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple
from multiprocessing import Pool, cpu_count
import PyPDF2

try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR dependencies not installed.")
    print("Install with: brew install tesseract && pip install pytesseract pdf2image pillow")


def pdf_has_selectable_text(pdf_path: Path, sample_pages: int = 5) -> bool:
    """
    Check if PDF has selectable text by sampling first N pages.

    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to check (default: 5)

    Returns:
        True if text is extractable, False if scanned/image-only
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            pages_to_check = min(sample_pages, total_pages)

            total_chars = 0
            for i in range(pages_to_check):
                page_text = reader.pages[i].extract_text()
                total_chars += len(page_text.strip())

            # If we got >50 chars per page on average, it has selectable text
            avg_chars = total_chars / pages_to_check
            return avg_chars > 50

    except Exception as e:
        print(f"    Error checking PDF text: {e}")
        return False


def get_pdf_size_mb(pdf_path: Path) -> float:
    """Get PDF file size in MB"""
    return pdf_path.stat().st_size / (1024 * 1024)


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get total page count of PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except:
        return 0


def ocr_single_page(args: Tuple[Path, int, int]) -> Tuple[int, str]:
    """
    OCR a single page (for parallel processing).

    Args:
        args: (pdf_path, page_num, dpi)

    Returns:
        (page_num, extracted_text)
    """
    pdf_path, page_num, dpi = args

    try:
        # Convert single page to image
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num,
            last_page=page_num
        )

        if images:
            # OCR the image
            text = pytesseract.image_to_string(images[0], lang='eng')
            return (page_num, f"--- PAGE {page_num} ---\n{text}")
        else:
            return (page_num, f"--- PAGE {page_num} ---\n[IMAGE CONVERSION FAILED]\n")

    except Exception as e:
        return (page_num, f"--- PAGE {page_num} ---\n[OCR ERROR: {str(e)}]\n")


def extract_with_ocr_parallel(
    pdf_path: Path,
    pages: List[int] = None,
    dpi: int = 300,
    workers: int = None
) -> str:
    """
    Extract text from PDF using parallel OCR.

    Args:
        pdf_path: Path to PDF file
        pages: List of page numbers to OCR (None = all pages)
        dpi: Resolution for image conversion (300 recommended)
        workers: Number of parallel workers (None = auto-detect)

    Returns:
        Extracted text with page markers
    """
    if not OCR_AVAILABLE:
        return ""

    # Auto-detect worker count (use 75% of CPU cores)
    if workers is None:
        workers = max(1, int(cpu_count() * 0.75))

    # Get total pages if not specified
    if pages is None:
        total_pages = get_pdf_page_count(pdf_path)
        pages = list(range(1, total_pages + 1))

    print(f"    OCR processing {len(pages)} pages with {workers} workers...")

    # Prepare arguments for parallel processing
    ocr_args = [(pdf_path, page_num, dpi) for page_num in pages]

    # Process pages in parallel
    with Pool(processes=workers) as pool:
        results = []
        # Use imap for progress tracking
        for i, result in enumerate(pool.imap(ocr_single_page, ocr_args), 1):
            results.append(result)
            # Print progress every 10 pages
            if i % 10 == 0 or i == len(pages):
                print(f"      Progress: {i}/{len(pages)} pages")

    # Sort by page number and join
    results.sort(key=lambda x: x[0])
    text_pages = [text for _, text in results]

    print(f"    ✓ OCR completed: {len(text_pages)} pages processed")
    return '\n\n'.join(text_pages)


def extract_with_ocr_smart_sampling(
    pdf_path: Path,
    first_n: int = 100,
    sample_rest: int = 50,
    dpi: int = 300
) -> str:
    """
    Smart sampling for huge PDFs.

    Strategy:
    1. OCR first N pages (covers tables, index, early sections)
    2. Sample remaining pages evenly distributed

    Args:
        pdf_path: Path to PDF
        first_n: Number of initial pages to OCR completely
        sample_rest: Number of pages to sample from remainder
        dpi: Image resolution

    Returns:
        Extracted text from sampled pages
    """
    total_pages = get_pdf_page_count(pdf_path)

    # Pages to process
    pages_to_ocr = []

    # 1. First N pages
    pages_to_ocr.extend(range(1, min(first_n + 1, total_pages + 1)))

    # 2. Distributed sample from rest
    if total_pages > first_n:
        remaining_pages = total_pages - first_n
        if remaining_pages > sample_rest:
            # Sample evenly distributed
            step = remaining_pages // sample_rest
            sampled = [first_n + 1 + (i * step) for i in range(sample_rest)]
            pages_to_ocr.extend(sampled)
        else:
            # Take all remaining
            pages_to_ocr.extend(range(first_n + 1, total_pages + 1))

    print(f"    Smart sampling: {len(pages_to_ocr)} pages from {total_pages} total")
    print(f"      First {min(first_n, total_pages)} pages + {len(pages_to_ocr) - min(first_n, total_pages)} sampled")

    return extract_with_ocr_parallel(pdf_path, pages=pages_to_ocr, dpi=dpi)


def extract_text_hybrid(
    pdf_path: Path,
    char_threshold: int = 50,
    dpi: int = 300,
    workers: int = None
) -> str:
    """
    Hybrid extraction: PyPDF2 per page, OCR fallback for empty pages.

    Handles mixed PDFs where some pages are scanned and others have selectable text.
    Example: MSDE report with pages 1-2 scanned (0 chars) but rest with text.

    Strategy:
    1. For each page, try PyPDF2 first
    2. If page has <char_threshold chars, use OCR for that page only
    3. Combine all pages into single document

    Args:
        pdf_path: Path to PDF file
        char_threshold: Min chars to consider page has text (default: 50)
        dpi: Resolution for OCR image conversion (default: 300)
        workers: Parallel workers for OCR (default: auto-detect)

    Returns:
        Combined text from all pages (PyPDF2 + OCR as needed)
    """
    if not OCR_AVAILABLE:
        print(f"    ⚠ OCR not available, falling back to PyPDF2 only")
        return extract_text_pypdf2_only(pdf_path)

    print(f"  Processing (hybrid): {pdf_path.name}")

    # Get page count
    total_pages = get_pdf_page_count(pdf_path)
    if total_pages == 0:
        return ""

    # Track which pages need OCR
    pages_needing_ocr = []
    pypdf2_texts = {}

    # Step 1: Try PyPDF2 for all pages
    print(f"    Scanning {total_pages} pages with PyPDF2...")
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num in range(total_pages):
                page_text = reader.pages[page_num].extract_text()
                if len(page_text.strip()) < char_threshold:
                    pages_needing_ocr.append(page_num + 1)  # 1-indexed for OCR
                else:
                    pypdf2_texts[page_num + 1] = page_text
    except Exception as e:
        print(f"    ⚠ PyPDF2 error: {e}, falling back to full OCR")
        return extract_with_ocr_parallel(pdf_path, dpi=dpi, workers=workers)

    # Step 2: OCR pages that failed PyPDF2
    if pages_needing_ocr:
        print(f"    {len(pages_needing_ocr)} pages need OCR (empty/scanned)")
        print(f"    Running OCR on pages: {pages_needing_ocr[:10]}{'...' if len(pages_needing_ocr) > 10 else ''}")

        ocr_text = extract_with_ocr_parallel(
            pdf_path,
            pages=pages_needing_ocr,
            dpi=dpi,
            workers=workers
        )

        # Parse OCR results (format: "--- PAGE N ---\ntext\n\n")
        ocr_by_page = {}
        for block in ocr_text.split('--- PAGE ')[1:]:  # Skip first empty split
            parts = block.split(' ---\n', 1)
            if len(parts) == 2:
                page_num = int(parts[0])
                page_text = parts[1]
                ocr_by_page[page_num] = page_text
    else:
        print(f"    ✓ All pages have selectable text, no OCR needed")
        ocr_by_page = {}

    # Step 3: Combine results in page order
    combined_text = []
    for page_num in range(1, total_pages + 1):
        if page_num in pypdf2_texts:
            combined_text.append(f"--- PAGE {page_num} (PyPDF2) ---\n{pypdf2_texts[page_num]}")
        elif page_num in ocr_by_page:
            combined_text.append(f"--- PAGE {page_num} (OCR) ---\n{ocr_by_page[page_num]}")
        else:
            combined_text.append(f"--- PAGE {page_num} ---\n[EXTRACTION FAILED]\n")

    print(f"    ✓ Hybrid extraction complete: {len(pypdf2_texts)} PyPDF2 + {len(ocr_by_page)} OCR pages")
    return '\n\n'.join(combined_text)


def extract_text_pypdf2_only(pdf_path: Path) -> str:
    """Fallback: Extract with PyPDF2 only (no OCR)"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return '\n'.join(text)
    except Exception as e:
        print(f"    Error reading PDF: {e}")
        return ""


def extract_text_smart(
    pdf_path: Path,
    use_ocr: bool = True,
    size_threshold_mb: float = 10.0,
    hybrid_mode: bool = True
) -> str:
    """
    Smart text extraction with hybrid support.

    Decision tree:
    1. Check if PDF has selectable text (sample first 5 pages)
    2. If mostly text AND hybrid_mode=True:
       - Use hybrid extraction (PyPDF2 per page + OCR fallback)
    3. If no text detected:
       - PDFs < 10 MB: Full OCR parallel
       - PDFs >= 10 MB: Smart sampling (first 100 + distributed sample)

    Args:
        pdf_path: Path to PDF file
        use_ocr: Enable OCR fallback (default: True)
        size_threshold_mb: Size threshold for smart sampling (default: 10 MB)
        hybrid_mode: Use per-page hybrid extraction (default: True)

    Returns:
        Extracted text
    """
    print(f"  Processing: {pdf_path.name}")

    # Step 1: Check if PDF has selectable text
    has_text = pdf_has_selectable_text(pdf_path)

    # Step 2: If has some text, use hybrid mode
    if has_text and hybrid_mode and use_ocr and OCR_AVAILABLE:
        print(f"    PDF has some selectable text, using hybrid extraction")
        return extract_text_hybrid(pdf_path)

    # Step 3: If has text but hybrid disabled, use PyPDF2 only
    if has_text:
        print(f"    ✓ PDF has selectable text, using PyPDF2")
        return extract_text_pypdf2_only(pdf_path)

    # Step 4: No text detected, use OCR
    if not use_ocr or not OCR_AVAILABLE:
        print(f"    ⚠ No selectable text and OCR not available")
        return ""

    print(f"    PDF is scanned/image-only, using OCR...")

    # Step 5: Choose OCR strategy based on size
    pdf_size = get_pdf_size_mb(pdf_path)
    total_pages = get_pdf_page_count(pdf_path)

    print(f"    PDF size: {pdf_size:.1f} MB, {total_pages} pages")

    if pdf_size < size_threshold_mb:
        # Small/medium PDF: Full OCR
        print(f"    Strategy: Full OCR (all {total_pages} pages)")
        return extract_with_ocr_parallel(pdf_path)
    else:
        # Large PDF: Smart sampling
        print(f"    Strategy: Smart sampling (PDF > {size_threshold_mb} MB)")
        return extract_with_ocr_smart_sampling(pdf_path, first_n=100, sample_rest=50)


# Backward compatibility with verify_claims_v1_1.py
def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Backward compatible wrapper for verify_claims.
    Tries PyPDF2, falls back to OCR if needed.
    """
    return extract_text_smart(pdf_path, use_ocr=True)


if __name__ == '__main__':
    """Test OCR processor on a sample PDF"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_processor.py <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"OCR PROCESSOR TEST")
    print(f"{'='*80}\n")

    # Check if PDF has selectable text
    has_text = pdf_has_selectable_text(pdf_path)
    print(f"Has selectable text: {has_text}")
    print(f"File size: {get_pdf_size_mb(pdf_path):.1f} MB")
    print(f"Page count: {get_pdf_page_count(pdf_path)}\n")

    # Extract text
    text = extract_text_smart(pdf_path)

    print(f"\n{'='*80}")
    print(f"EXTRACTION RESULTS")
    print(f"{'='*80}")
    print(f"Total characters: {len(text):,}")
    print(f"First 500 characters:\n")
    print(text[:500])
    print("...")
