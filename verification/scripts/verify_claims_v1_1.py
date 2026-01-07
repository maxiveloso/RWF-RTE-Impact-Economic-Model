#!/usr/bin/env python3
"""
Verify Claims - RWF Claim Verification Pipeline v1.4 - CROSS-DOCUMENT SYNTHESIS
Uses LLM to verify parameter claims against source documents

VERSION: 1.4
UPDATED: January 6, 2026

CHANGES IN v1.4 (CROSS-DOCUMENT EVIDENCE ACCUMULATION):
- NEW: Evidence Memory system tracks findings across multiple sources per parameter
- NEW: Cross-document synthesis - LLM combines partial evidence from multiple papers
- NEW: Automatic synthesis trigger when 2+ sources have PARTIAL but no CONSISTENT >=85%
- NEW: --no-synthesis flag to disable cross-document synthesis
- Example: 3 PARTIAL results (60%, 45%, 55%) -> Synthesized CONSISTENT (82%)
- Database: New columns for synthesis tracking (synthesis_used, synthesis_reasoning, etc.)

CHANGES IN v1.3 (BATCH MODE):
- BATCH PROCESSING: Groups parameters by source document (10-15x SPEEDUP)
- Verifies multiple claims from same document in ONE LLM call

CHANGES IN v1.2:
- LOCAL-FIRST document search (checks sources/ before Supabase)
- FUZZY MATCHING by citation (author+year)
- Multi-strategy document lookup

USAGE:
    python verify_claims_v1_1.py                     # Full mode with synthesis (recommended)
    python verify_claims_v1_1.py --debug             # Verbose debug output
    python verify_claims_v1_1.py --dry-run           # Don't write to database
    python verify_claims_v1_1.py --resume            # Skip already verified
    python verify_claims_v1_1.py --start-from 10    # Start from parameter 10
    python verify_claims_v1_1.py --no-synthesis      # Disable cross-document synthesis
"""

import os
import re
import json
import time
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import httpx
from supabase import create_client
from dotenv import load_dotenv
import sys
import subprocess

# Load environment variables
load_dotenv()

# =============================================================================
# CROSS-DOCUMENT EVIDENCE MEMORY STRUCTURES
# =============================================================================

@dataclass
class SourceEvidence:
    """Evidence found in a single source document."""
    source_name: str
    source_url: str
    source_filename: str
    verification_status: str  # CONSISTENT, PARTIAL, INCONSISTENT, NO_EVIDENCE
    confidence_percent: float
    key_finding: str  # What was found
    limitation: str   # What was missing
    snippet: str      # Exact quote
    derivation_hint: Optional[str] = None  # If data could help derive the claim

@dataclass
class ParameterEvidenceMemory:
    """Accumulated evidence across multiple sources for one parameter."""
    parameter_id: str
    parameter_name: str
    claimed_value: str

    # Evidence from individual sources
    source_evidence: List[SourceEvidence] = field(default_factory=list)

    # Synthesis results (filled after cross-doc analysis)
    synthesis_performed: bool = False
    combined_status: Optional[str] = None
    combined_confidence: Optional[float] = None
    synthesis_reasoning: Optional[str] = None

    def should_synthesize(self) -> bool:
        """Determine if cross-document synthesis should be triggered."""
        if len(self.source_evidence) < 2:
            return False

        # Already have high-confidence result?
        for ev in self.source_evidence:
            if ev.verification_status == 'CONSISTENT' and ev.confidence_percent >= 85:
                return False  # No need to synthesize

        # At least one PARTIAL or better (not all NO_EVIDENCE)?
        has_partial_or_better = any(
            ev.verification_status in ['PARTIAL', 'CONSISTENT']
            for ev in self.source_evidence
        )

        return has_partial_or_better

    def get_best_individual_result(self) -> Optional[SourceEvidence]:
        """Return the best individual result by confidence."""
        if not self.source_evidence:
            return None
        return max(self.source_evidence, key=lambda x: x.confidence_percent)


# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

# Load sources catalog (auto-build if missing or outdated)
SOURCES_CATALOG = None
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
SOURCES_DIR = Path(__file__).parent / 'sources'

# Global flags
DEBUG_MODE = False
SYNTHESIS_ENABLED = True

def debug_print(msg: str):
    """Print only if debug mode is enabled."""
    if DEBUG_MODE:
        print(f"    [DEBUG] {msg}")


def build_catalog_if_needed():
    """Auto-build catalog if missing or outdated"""
    global SOURCES_CATALOG

    rebuild_needed = False

    if not CATALOG_PATH.exists():
        print("Info: Sources catalog not found, building...")
        rebuild_needed = True
    else:
        # Check if catalog is outdated
        if SOURCES_DIR.exists():
            catalog_mtime = CATALOG_PATH.stat().st_mtime
            sources_mtime = max([f.stat().st_mtime for f in SOURCES_DIR.glob('*')] + [0])

            if sources_mtime > catalog_mtime:
                print("Info: Sources catalog outdated, rebuilding...")
                rebuild_needed = True

    if rebuild_needed:
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent / 'build_sources_catalog.py')],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f"Warning: Catalog build failed: {result.stderr}")
                return
        except Exception as e:
            print(f"Warning: Failed to auto-build catalog: {e}")
            return

    # Load catalog
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                SOURCES_CATALOG = json.load(f)
            print(f"Loaded sources catalog: {len(SOURCES_CATALOG)} files indexed")
        except Exception as e:
            print(f"Warning: Failed to load catalog: {e}")

# Build/load catalog at startup
build_catalog_if_needed()

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


# =============================================================================
# PDF/TEXT EXTRACTION
# =============================================================================

# Try importing PyPDF2 for local PDF reading (optional)
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("Warning: PyPDF2 not available. Install with: pip install PyPDF2")

# Try importing OCR processor
try:
    from ocr_processor import extract_text_from_pdf as extract_text_smart
    OCR_PROCESSOR_AVAILABLE = True
except ImportError:
    OCR_PROCESSOR_AVAILABLE = False


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from local PDF file.
    Uses smart OCR processor if available (auto-detects scanned PDFs).
    Falls back to PyPDF2 if OCR not available.
    """
    # Strategy 1: Use OCR processor (smart: PyPDF2 first, OCR fallback)
    if OCR_PROCESSOR_AVAILABLE:
        return extract_text_smart(pdf_path)

    # Strategy 2: Fallback to basic PyPDF2
    if not PYPDF2_AVAILABLE:
        return ""

    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return '\n'.join(text)
    except Exception as e:
        debug_print(f"Error reading PDF {pdf_path}: {e}")
        return ""


def search_local_documents(citation: str, local_dir: Path = None, fallback_url: str = None) -> Optional[Tuple[str, str]]:
    """
    Search for local PDF/TXT files matching the citation.
    IMPROVED v3: Better keyword extraction with stopword filtering and URL fallback.
    Returns (filename, full_text) if found, None otherwise.

    Args:
        citation: The citation text to match
        local_dir: Directory to search (default: sources/)
        fallback_url: URL to try extracting keywords from if citation is empty/unknown
    """
    if local_dir is None:
        local_dir = Path(__file__).parent / 'sources'

    if not local_dir.exists():
        debug_print(f"Local directory not found: {local_dir}")
        return None

    # Stopwords: common words that appear in many citations/filenames but aren't distinctive
    STOPWORDS = {
        'annual', 'report', 'paper', 'study', 'survey', 'data', 'india', 'indian',
        'national', 'economic', 'social', 'development', 'ministry', 'government',
        'analysis', 'review', 'working', 'research', 'policy', 'the', 'and', 'for',
        'bulletin', 'statistics', 'statistical', 'quarterly', 'monthly', 'yearly',
        'www', 'http', 'https', 'com', 'org', 'gov', 'pdf', 'html', 'files', 'uploads'
    }

    # Key acronyms that should have high weight (these are distinctive identifiers)
    KEY_ACRONYMS = {'plfs', 'msde', 'nber', 'ilo', 'niti', 'dgt', 'aser', 'nsso', 'ncaer', 'rbi', 'nsdc', 'nfhs'}

    # If citation is empty/unknown, try to extract from URL
    search_text = citation
    if not citation or citation.lower() in ['unknown', '']:
        if fallback_url:
            search_text = fallback_url
            debug_print(f"Using URL fallback: {fallback_url[:60]}...")
        else:
            debug_print("No citation and no URL fallback")
            return None

    # Extract acronyms (2+ uppercase letters), proper nouns, and years from citation/URL
    raw_words = set(re.findall(r'\b[A-Z]{2,}|\b[A-Z][a-z]+|\b\d{4}\b', search_text))
    # Also extract from lowercase (for URLs)
    raw_words.update(re.findall(r'\b[a-z]{3,}\b', search_text.lower()))
    citation_words = {w.lower() for w in raw_words} - STOPWORDS

    # Also extract 2-digit year patterns like "23-24" or "2023-24"
    year_patterns = re.findall(r'\b(\d{2})-(\d{2})\b|\b(\d{4})-(\d{2})\b', search_text)
    for match in year_patterns:
        for part in match:
            if part and len(part) >= 2:
                citation_words.add(part)

    debug_print(f"Citation keywords (filtered): {citation_words}")

    candidates = []
    for file_path in local_dir.glob('*'):
        if file_path.suffix.lower() not in ['.pdf', '.txt']:
            continue

        # Extract keywords from filename (excluding stopwords)
        filename_words = set()
        for part in file_path.stem.split('_'):
            part_lower = part.lower()
            # Keep years (2 or 4 digits)
            if re.match(r'^\d{2,4}$', part):
                filename_words.add(part_lower)
            # Keep non-stopword parts with 2+ chars
            elif len(part) >= 2 and part_lower not in STOPWORDS:
                filename_words.add(part_lower)

        # Calculate match score
        matched = citation_words & filename_words
        score = len(matched)

        # BONUS: Extra points for matching key acronyms (PLFS, MSDE, etc.)
        acronym_matches = matched & KEY_ACRONYMS
        if acronym_matches:
            score += len(acronym_matches) * 3  # Triple weight for key acronyms

        # PENALTY: If citation has a key acronym but filename has a DIFFERENT key acronym, penalize
        citation_acronyms = citation_words & KEY_ACRONYMS
        filename_acronyms = filename_words & KEY_ACRONYMS
        if citation_acronyms and filename_acronyms:
            mismatched_acronyms = filename_acronyms - citation_acronyms
            if mismatched_acronyms:
                score -= len(mismatched_acronyms) * 5  # Heavy penalty for wrong acronym

        if score > 0:
            candidates.append((file_path, score, matched))

    # Sort by score descending
    candidates.sort(key=lambda x: -x[1])

    if DEBUG_MODE and candidates:
        debug_print(f"Top matches: {[(c[0].name, c[1], c[2]) for c in candidates[:3]]}")

    # Return best match if score >= 2
    if candidates and candidates[0][1] >= 2:
        best_match = candidates[0][0]
        debug_print(f"Selected: {best_match.name} (score={candidates[0][1]})")

        if best_match.suffix.lower() == '.pdf':
            text = extract_text_from_pdf(best_match)
        else:
            try:
                with open(best_match, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                debug_print(f"Error reading TXT {best_match}: {e}")
                return None

        if text:
            return (best_match.name, text)

    debug_print(f"No local document found for citation")
    return None


# =============================================================================
# LLM API CALLS
# =============================================================================

def call_llm_with_retry(prompt: str, document_chunk: str, max_retries: int = 3) -> Optional[Dict]:
    """Call OpenRouter API with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://rightwalkfoundation.org",
                    "X-Title": "RWF Claim Verification"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": document_chunk}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                timeout=120
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"    Rate limited, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"    API error (status {response.status_code}): {response.text}")
                return None

        except httpx.TimeoutException:
            print(f"    Request timed out (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"    Error calling LLM: {str(e)}")
            return None

    return None


def parse_llm_response(raw_response: str) -> Dict:
    """Parse LLM response to extract verification result."""
    result = None

    # Try multiple JSON extraction patterns
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{[^{}]*"verification_status"[^{}]*\})',
        r'(\{.*\})',
    ]

    for pattern in patterns:
        json_match = re.search(pattern, raw_response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                debug_print(f"JSON parsed with pattern: {pattern[:30]}...")
                break
            except json.JSONDecodeError:
                continue

    if result is None:
        try:
            result = json.loads(raw_response.strip())
        except json.JSONDecodeError:
            pass

    if result is None:
        debug_print("JSON parsing failed, using regex fallback")
        result = {
            'verification_status': 'UNKNOWN',
            'confidence_level': 'LOW',
            'confidence_percent': None,
            'evidence_found': {},
            'recommendation': 'FLAG_FOR_REVIEW'
        }

        if re.search(r'\bCONSISTENT\b', raw_response, re.IGNORECASE):
            result['verification_status'] = 'CONSISTENT'
        elif re.search(r'\bPARTIAL\b', raw_response, re.IGNORECASE):
            result['verification_status'] = 'PARTIAL'
        elif re.search(r'\bINCONSISTENT\b', raw_response, re.IGNORECASE):
            result['verification_status'] = 'INCONSISTENT'
        elif re.search(r'NO.?EVIDENCE|NOT.?FOUND', raw_response, re.IGNORECASE):
            result['verification_status'] = 'NO_EVIDENCE'

        conf_match = re.search(r'confidence[:\s]*(\d{1,3})%?', raw_response, re.IGNORECASE)
        if conf_match:
            result['confidence_percent'] = int(conf_match.group(1))

    return result


def extract_key_finding_from_response(parsed: Dict, raw_response: str) -> str:
    """Extract key finding from LLM response for evidence memory."""
    # Try evidence_found.context first
    evidence = parsed.get('evidence_found', {})
    if isinstance(evidence, dict):
        context = evidence.get('context', '')
        if context and len(context) > 10:
            return str(context)[:500]

    # Try derivation_logic
    derivation = parsed.get('derivation_logic', '')
    if derivation and len(derivation) > 10:
        return str(derivation)[:500]

    # Try cross_source_analysis.evidence_chain
    cross_analysis = parsed.get('cross_source_analysis', {})
    if isinstance(cross_analysis, dict):
        chain = cross_analysis.get('evidence_chain', [])
        if chain:
            return '; '.join(chain[:3])[:500]

    # Fallback: extract first substantial sentence
    sentences = re.split(r'[.!?]\s+', raw_response)
    for s in sentences:
        if len(s) > 30 and not s.startswith('{'):
            return s[:500]

    return ''


def extract_limitation_from_response(parsed: Dict) -> str:
    """Extract limitation/missing info from LLM response."""
    # Check discrepancies field
    discrepancies = parsed.get('discrepancies', [])
    if discrepancies and isinstance(discrepancies, list):
        return '; '.join(discrepancies[:2])[:300]

    # Check caveats
    caveats = parsed.get('caveats', [])
    if caveats and isinstance(caveats, list):
        return '; '.join(caveats[:2])[:300]

    # Check recommendation
    rec = parsed.get('recommendation', '')
    if rec == 'FLAG_FOR_REVIEW':
        return 'Requires human review'
    elif rec == 'REJECT':
        return 'Evidence contradicts claim'

    return ''


# =============================================================================
# SINGLE DOCUMENT VERIFICATION
# =============================================================================

def verify_claim_in_document(
    parameter_name: str,
    claim_text: str,
    claim_value: str,
    document_text: str,
    document_name: str,
    max_chars: int = 50000
) -> Dict:
    """
    Verify a specific claim against a document using LLM.
    Handles chunking for large documents.
    """
    # Limit document size
    doc_text = document_text[:max_chars] if len(document_text) > max_chars else document_text

    verification_request = f"""
PARAMETER TO VERIFY:
- Name: {parameter_name}
- Claimed Value: {claim_value}
- Claim Text: {claim_text}

SOURCE DOCUMENT:
- Filename: {document_name}

TASK:
Verify if this claim is supported by the document below. Follow the methodology in your system prompt.
Return your response as a JSON object with these required fields:
- verification_status: "CONSISTENT" | "PARTIAL" | "INCONSISTENT" | "NO_EVIDENCE"
- confidence_level: "HIGH" | "MEDIUM" | "LOW"
- confidence_percent: number from 0-100
- evidence_found: {{ "context": "exact quote from document" }}
- derivation_logic: "explanation if value is derived"
- recommendation: "ACCEPT" | "ACCEPT_WITH_CAVEAT" | "FLAG_FOR_REVIEW" | "REJECT"

DOCUMENT TEXT:
{doc_text}
"""

    start_time = time.time()
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, verification_request)
    processing_time_ms = int((time.time() - start_time) * 1000)

    if not api_response:
        return {
            'match_type': 'error',
            'verification_status': 'UNKNOWN',
            'confidence_score': 0.0,
            'confidence_percent': 0,
            'key_finding': '',
            'limitation': 'LLM API call failed',
            'llm_raw_response': None,
            'processing_time_ms': processing_time_ms,
            'needs_human_review': True
        }

    try:
        llm_content = api_response['choices'][0]['message']['content']
    except (KeyError, IndexError):
        llm_content = str(api_response)

    parsed = parse_llm_response(llm_content)

    # Map verification status to match type
    verification_status = parsed.get('verification_status', 'UNKNOWN')
    match_type_map = {
        'CONSISTENT': 'exact',
        'PARTIAL': 'approximate',
        'INCONSISTENT': 'contradictory',
        'NO_EVIDENCE': 'not_found',
        'UNKNOWN': 'ambiguous'
    }
    match_type = match_type_map.get(verification_status, 'ambiguous')

    # Get confidence
    confidence_percent = parsed.get('confidence_percent')
    confidence_level = parsed.get('confidence_level', 'LOW')

    if confidence_percent is not None and isinstance(confidence_percent, (int, float)):
        confidence_score = float(confidence_percent) / 100.0
    else:
        confidence_map = {'HIGH': 0.9, 'MEDIUM': 0.6, 'LOW': 0.3}
        confidence_score = confidence_map.get(str(confidence_level).upper(), 0.5)
        confidence_percent = confidence_score * 100

    # Extract key finding and limitation for evidence memory
    key_finding = extract_key_finding_from_response(parsed, llm_content)
    limitation = extract_limitation_from_response(parsed)

    # Extract snippet
    evidence = parsed.get('evidence_found', {})
    snippet = ''
    if isinstance(evidence, dict):
        snippet = evidence.get('context', '')[:500]

    needs_review = (
        match_type in ['contradictory', 'ambiguous', 'not_found'] or
        confidence_score < 0.6 or
        parsed.get('recommendation') in ['FLAG_FOR_REVIEW', 'REJECT']
    )

    return {
        'match_type': match_type,
        'verification_status': verification_status,
        'confidence_score': confidence_score,
        'confidence_percent': confidence_percent,
        'key_finding': key_finding,
        'limitation': limitation,
        'extracted_snippet': snippet,
        'llm_raw_response': llm_content,
        'llm_interpretation': parsed.get('derivation_logic', ''),
        'llm_confidence_reason': str(parsed.get('economic_plausibility', '')),
        'processing_time_ms': processing_time_ms,
        'needs_human_review': needs_review,
        'recommendation': parsed.get('recommendation', 'FLAG_FOR_REVIEW')
    }


# =============================================================================
# CROSS-DOCUMENT SYNTHESIS
# =============================================================================

def synthesize_cross_document_evidence(memory: ParameterEvidenceMemory) -> Optional[Dict]:
    """
    Call LLM to synthesize evidence from multiple sources.

    Only called when:
    - 2+ sources verified
    - At least one PARTIAL or CONSISTENT
    - No CONSISTENT with >=85% confidence
    """

    # Build previous evidence summary
    evidence_summary = []
    for ev in memory.source_evidence:
        evidence_summary.append({
            "source": ev.source_name,
            "filename": ev.source_filename,
            "verification_status": ev.verification_status,
            "confidence": ev.confidence_percent,
            "key_finding": ev.key_finding,
            "limitation": ev.limitation
        })

    synthesis_request = f"""
CROSS-DOCUMENT EVIDENCE SYNTHESIS REQUEST

You are in CROSS-DOCUMENT SYNTHESIS MODE. Follow the instructions for this mode in your system prompt.

PARAMETER TO VERIFY:
- Name: {memory.parameter_name}
- Claimed Value: {memory.claimed_value}

EVIDENCE ACCUMULATED FROM {len(memory.source_evidence)} SOURCES:
{json.dumps(evidence_summary, indent=2)}

TASK:
Analyze the COMBINED evidence from all sources above.
Determine if the evidence, when synthesized, supports the claimed value.

Consider:
1. Do the sources complement each other?
2. Can the claim be derived from combining the data?
3. Is there a consistent pattern across sources?
4. Are there contradictions that undermine the synthesis?

IMPORTANT: The combined confidence cannot exceed the maximum individual confidence + 20 points.
Maximum individual confidence was: {max(ev.confidence_percent for ev in memory.source_evidence):.0f}%
So combined confidence max is: {min(100, max(ev.confidence_percent for ev in memory.source_evidence) + 20):.0f}%

Return your synthesis as JSON with:
- synthesis_mode: true
- cross_source_analysis: {{ evidence_chain: [...], complementarity_score: "HIGH/MEDIUM/LOW", derivation_possible: true/false }}
- combined_verdict: {{ verification_status: "CONSISTENT/PARTIAL/INCONSISTENT/NO_EVIDENCE", confidence_level: "HIGH/MEDIUM/LOW", confidence_percent: 0-100, reasoning: "explanation" }}
- caveats: [list of caveats]
- recommendation: "ACCEPT" | "ACCEPT_WITH_CAVEAT" | "FLAG_FOR_REVIEW" | "REJECT"
"""

    print(f"    Calling LLM for cross-document synthesis...")
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, synthesis_request)

    if not api_response:
        print(f"    Warning: Synthesis LLM call failed")
        return None

    try:
        llm_content = api_response['choices'][0]['message']['content']
    except (KeyError, IndexError):
        return None

    # Parse synthesis response
    parsed = parse_synthesis_response(llm_content)

    if parsed:
        debug_print(f"Synthesis parsed successfully")

    return parsed


def parse_synthesis_response(llm_content: str) -> Optional[Dict]:
    """Parse the synthesis LLM response."""
    # Try to extract JSON
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'(\{[^{}]*"synthesis_mode"[^{}]*\})',
        r'(\{[^{}]*"combined_verdict"[^{}]*\})',
        r'(\{.*\})',
    ]

    for pattern in patterns:
        match = re.search(pattern, llm_content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if 'combined_verdict' in parsed or 'synthesis_mode' in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

    # Fallback: extract key information
    result = {
        'synthesis_mode': True,
        'combined_verdict': {
            'verification_status': 'UNKNOWN',
            'confidence_percent': 50,
            'reasoning': 'Could not parse synthesis response'
        },
        'recommendation': 'FLAG_FOR_REVIEW'
    }

    # Try to extract status and confidence from text
    if re.search(r'\bCONSISTENT\b', llm_content, re.IGNORECASE):
        result['combined_verdict']['verification_status'] = 'CONSISTENT'
    elif re.search(r'\bPARTIAL\b', llm_content, re.IGNORECASE):
        result['combined_verdict']['verification_status'] = 'PARTIAL'

    conf_match = re.search(r'confidence[:\s]*(\d{1,3})%?', llm_content, re.IGNORECASE)
    if conf_match:
        result['combined_verdict']['confidence_percent'] = int(conf_match.group(1))

    return result


# =============================================================================
# DOCUMENT RETRIEVAL (Multi-Strategy)
# =============================================================================

def get_document_for_source(source: Dict) -> Optional[Tuple[str, str, str]]:
    """
    Get document text for a source using multiple strategies.
    Returns (filename, text, location_strategy) or None.
    """
    source_url = source.get('url') or ''
    source_citation = source.get('citation') or ''
    source_doc_id = source.get('source_document_id')

    # STRATEGY 0: Local documents FIRST (fastest) - with URL fallback
    local_result = search_local_documents(source_citation, fallback_url=source_url)
    if local_result:
        filename, text = local_result
        debug_print(f"Found local document: {filename}")
        return (filename, text, 'local')

    # STRATEGY 1: Supabase by source_document_id
    if source_doc_id:
        try:
            doc_response = supabase.table('source_documents')\
                .select('local_filename, full_text')\
                .eq('id', source_doc_id)\
                .limit(1)\
                .execute()

            if doc_response.data:
                filename = doc_response.data[0]['local_filename']
                text = doc_response.data[0]['full_text']
                if text and len(text) > 100:
                    debug_print(f"Found by source_document_id: {filename}")
                    return (filename, text, 'supabase_by_id')
        except Exception as e:
            debug_print(f"Supabase ID lookup failed: {e}")

    # STRATEGY 2: Supabase by URL
    if source_url:
        try:
            doc_response = supabase.table('source_documents')\
                .select('local_filename, full_text')\
                .eq('original_url', source_url)\
                .limit(1)\
                .execute()

            if doc_response.data:
                filename = doc_response.data[0]['local_filename']
                text = doc_response.data[0]['full_text']
                if text and len(text) > 100:
                    debug_print(f"Found by URL: {filename}")
                    return (filename, text, 'supabase_by_url')
        except Exception as e:
            debug_print(f"Supabase URL lookup failed: {e}")

    # STRATEGY 3: Fuzzy local match
    if source_citation:
        local_dir = Path(__file__).parent / 'sources'
        if local_dir.exists():
            citation_words = set(re.findall(r'\b[A-Z][a-z]+|\b\d{4}\b', source_citation))
            citation_words = {w.lower() for w in citation_words}

            best_match = None
            best_score = 0

            for file_path in local_dir.glob('*'):
                if file_path.suffix.lower() not in ['.pdf', '.txt']:
                    continue

                filename_words = set()
                parts = file_path.stem.split('_')
                for part in parts:
                    if re.match(r'^\d{4}$', part):
                        filename_words.add(part)
                    elif len(part) >= 3:
                        filename_words.add(part.lower())

                score = len(citation_words & filename_words)
                if score > best_score:
                    best_score = score
                    best_match = file_path

            if best_match and best_score >= 1:
                if best_match.suffix.lower() == '.pdf':
                    text = extract_text_from_pdf(best_match)
                else:
                    try:
                        with open(best_match, 'r', encoding='utf-8') as f:
                            text = f.read()
                    except:
                        text = ''

                if text and len(text) > 100:
                    debug_print(f"Found fuzzy local match: {best_match.name}")
                    return (best_match.name, text, 'local_fuzzy')

    return None


# =============================================================================
# SOURCE DEDUPLICATION
# =============================================================================

def deduplicate_sources(sources: List[Dict]) -> List[Dict]:
    """
    Remove duplicate sources that would resolve to the same document.
    Keeps the first occurrence, removes duplicates based on:
    - Same citation (exact match)
    - Same URL
    - Same source_document_id
    """
    seen_citations = set()
    seen_urls = set()
    seen_doc_ids = set()
    unique_sources = []

    for source in sources:
        citation = (source.get('citation') or '').strip().lower()
        url = (source.get('url') or '').strip().lower()
        doc_id = source.get('source_document_id')

        # Check if we've seen this source before
        is_duplicate = False

        if citation and citation in seen_citations:
            is_duplicate = True
            debug_print(f"Skipping duplicate citation: {citation[:50]}...")
        elif url and url in seen_urls:
            is_duplicate = True
            debug_print(f"Skipping duplicate URL: {url[:50]}...")
        elif doc_id and doc_id in seen_doc_ids:
            is_duplicate = True
            debug_print(f"Skipping duplicate doc_id: {doc_id}")

        if not is_duplicate:
            unique_sources.append(source)
            if citation:
                seen_citations.add(citation)
            if url:
                seen_urls.add(url)
            if doc_id:
                seen_doc_ids.add(doc_id)

    if len(sources) != len(unique_sources):
        debug_print(f"Deduplicated: {len(sources)} -> {len(unique_sources)} sources")

    return unique_sources


# =============================================================================
# MAIN VERIFICATION WITH EVIDENCE MEMORY
# =============================================================================

def verify_parameter_with_memory(
    param: Dict,
    sources: List[Dict],
    dry_run: bool = False
) -> Dict:
    """
    Verify a parameter using evidence accumulation across all its sources.

    Flow:
    1. Deduplicate sources
    2. Create ParameterEvidenceMemory
    3. For each source, verify and store in memory
    4. After all sources, check if synthesis needed
    5. If yes, call synthesis LLM
    6. Return best result (individual or synthesized)
    """
    param_name = param.get('friendly_name', param.get('python_const_name', 'Unknown'))
    claim_value = param.get('original_value', '')

    # Deduplicate sources before verification
    original_count = len(sources)
    sources = deduplicate_sources(sources)
    if len(sources) < original_count:
        print(f"  (Deduplicated: {original_count} -> {len(sources)} unique sources)")

    memory = ParameterEvidenceMemory(
        parameter_id=str(param['id']),
        parameter_name=param_name,
        claimed_value=claim_value
    )

    print(f"\n  Verifying against {len(sources)} source(s)...")

    # Step 1: Verify against each source
    for i, source in enumerate(sources, 1):
        # Handle None values explicitly (dict.get returns None if key exists with None value)
        source_citation = source.get('citation') or 'Unknown'
        source_url = source.get('url') or ''
        citation_display = source_citation[:60] if source_citation else 'Unknown'
        print(f"    [{i}/{len(sources)}] {citation_display}...")

        # Get document
        doc_result = get_document_for_source(source)

        if not doc_result:
            print(f"      - No document found")
            memory.source_evidence.append(SourceEvidence(
                source_name=source_citation,
                source_url=source_url,
                source_filename='NOT_FOUND',
                verification_status='NO_EVIDENCE',
                confidence_percent=0,
                key_finding='',
                limitation='Document not found in local or Supabase',
                snippet=''
            ))
            continue

        filename, doc_text, location = doc_result
        print(f"      - Found: {filename} ({location})")

        # Verify claim
        result = verify_claim_in_document(
            parameter_name=param_name,
            claim_text=param.get('friendly_name', ''),
            claim_value=claim_value,
            document_text=doc_text,
            document_name=filename
        )

        status = result['verification_status']
        conf = result['confidence_percent']
        print(f"      - Result: {status} ({conf:.0f}%)")

        # Store in memory
        memory.source_evidence.append(SourceEvidence(
            source_name=source_citation,
            source_url=source_url,
            source_filename=filename,
            verification_status=status,
            confidence_percent=conf,
            key_finding=result.get('key_finding', ''),
            limitation=result.get('limitation', ''),
            snippet=result.get('extracted_snippet', ''),
            derivation_hint=result.get('llm_interpretation', '')
        ))

        # Early exit if we found strong evidence
        if status == 'CONSISTENT' and conf >= 85:
            print(f"      - Strong evidence found, skipping remaining sources")
            return build_final_result(memory, synthesis_used=False)

    # Step 2: Check if synthesis is warranted
    if SYNTHESIS_ENABLED and memory.should_synthesize():
        print(f"\n  Triggering cross-document synthesis ({len(memory.source_evidence)} sources)...")

        synthesis_result = synthesize_cross_document_evidence(memory)

        if synthesis_result:
            combined = synthesis_result.get('combined_verdict', {})
            memory.synthesis_performed = True
            memory.combined_status = combined.get('verification_status', 'UNKNOWN')
            memory.combined_confidence = combined.get('confidence_percent', 50)
            memory.synthesis_reasoning = combined.get('reasoning', '')

            print(f"    Synthesis result: {memory.combined_status} ({memory.combined_confidence:.0f}%)")

            return build_final_result(memory, synthesis_used=True, synthesis_raw=synthesis_result)

    # Step 3: No synthesis - return best individual result
    return build_final_result(memory, synthesis_used=False)


def build_final_result(memory: ParameterEvidenceMemory, synthesis_used: bool, synthesis_raw: Dict = None) -> Dict:
    """Build the final verification result from memory."""

    if synthesis_used and memory.combined_status:
        final_status = memory.combined_status
        final_confidence = memory.combined_confidence
        reasoning = memory.synthesis_reasoning
    else:
        best = memory.get_best_individual_result()
        if best:
            final_status = best.verification_status
            final_confidence = best.confidence_percent
            reasoning = best.key_finding
        else:
            final_status = 'NO_EVIDENCE'
            final_confidence = 0
            reasoning = 'No sources found'

    # Map to match_type
    match_type_map = {
        'CONSISTENT': 'exact',
        'PARTIAL': 'approximate',
        'INCONSISTENT': 'contradictory',
        'NO_EVIDENCE': 'not_found',
        'UNKNOWN': 'ambiguous'
    }
    match_type = match_type_map.get(final_status, 'ambiguous')

    # Determine needs_human_review
    needs_review = (
        match_type in ['contradictory', 'ambiguous', 'not_found'] or
        final_confidence < 60
    )

    # Build LLM reasoning summary from best evidence or synthesis
    best_ev = memory.get_best_individual_result()
    llm_reasoning = ""
    if synthesis_used and memory.synthesis_reasoning:
        llm_reasoning = f"[SYNTHESIS] {memory.synthesis_reasoning}"
    elif best_ev:
        if best_ev.derivation_hint:
            llm_reasoning = best_ev.derivation_hint
        elif best_ev.key_finding:
            llm_reasoning = best_ev.key_finding

    return {
        'parameter_id': memory.parameter_id,
        'parameter_name': memory.parameter_name,
        'claimed_value': memory.claimed_value,
        'final_status': final_status,
        'final_confidence': final_confidence,
        'match_type': match_type,
        'synthesis_used': synthesis_used,
        'synthesis_reasoning': memory.synthesis_reasoning if synthesis_used else None,
        'llm_reasoning': llm_reasoning,  # NEW: Human-readable reasoning summary
        'evidence_count': len(memory.source_evidence),
        'individual_results': [
            {
                'source': ev.source_name,
                'filename': ev.source_filename,
                'status': ev.verification_status,
                'confidence': ev.confidence_percent,
                'key_finding': ev.key_finding,
                'limitation': ev.limitation,
                'reasoning': ev.derivation_hint or ''  # Include per-source reasoning
            }
            for ev in memory.source_evidence
        ],
        'needs_human_review': needs_review,
        'best_source': best_ev.source_name if best_ev else None
    }


# =============================================================================
# MAIN VERIFICATION FUNCTION
# =============================================================================

def verify_parameters(dry_run: bool = False, resume: bool = False, start_from: int = None):
    """Main verification function with cross-document synthesis."""

    print(f"\n{'='*80}")
    print(f"RWF CLAIM VERIFICATION PIPELINE v1.4 - CROSS-DOCUMENT SYNTHESIS")
    print(f"{'='*80}")
    print(f"Model: {OPENROUTER_MODEL}")
    print(f"Debug mode: {DEBUG_MODE}")
    print(f"Cross-document synthesis: {'ENABLED' if SYNTHESIS_ENABLED else 'DISABLED'}")
    print(f"Dry run: {dry_run}\n")

    # Load parameters with their sources
    print("Loading parameters and sources from Supabase...")
    try:
        params_response = supabase.table('parameters')\
            .select('*, sources(*)')\
            .execute()

        parameters = params_response.data
        print(f"  Loaded {len(parameters)} parameters\n")
    except Exception as e:
        print(f"  Error loading data: {str(e)}")
        return

    # Group sources by parameter
    params_with_sources = []
    for param in parameters:
        sources = param.get('sources', [])
        # Filter to original sources
        original_sources = [s for s in sources if s.get('source_type') == 'original']
        if original_sources:
            params_with_sources.append({
                'parameter': param,
                'sources': original_sources
            })

    print(f"Found {len(params_with_sources)} parameters with 'original' sources")
    total_sources = sum(len(p['sources']) for p in params_with_sources)
    print(f"Total sources to check: {total_sources}\n")

    # Resume mode
    if resume:
        print(f"Resume mode: checking for already verified parameters...")
        try:
            verified_response = supabase.table('claim_verification_log')\
                .select('parameter_id')\
                .execute()

            verified_ids = {row['parameter_id'] for row in verified_response.data if row.get('parameter_id')}
            original_count = len(params_with_sources)
            params_with_sources = [
                p for p in params_with_sources
                if p['parameter']['id'] not in verified_ids
            ]
            print(f"  Skipping {original_count - len(params_with_sources)} already verified\n")
        except Exception as e:
            print(f"  Warning: Could not check verified parameters: {e}\n")

    # Start from index
    if start_from is not None:
        if start_from < 1 or start_from > len(params_with_sources):
            print(f"  Invalid --start-from {start_from}")
            return
        params_with_sources = params_with_sources[start_from - 1:]
        print(f"Starting from parameter {start_from}\n")

    print(f"{'='*80}\n")

    # Results for CSV
    results = []
    synthesis_count = 0

    # Process each parameter
    for idx, item in enumerate(params_with_sources, 1):
        param = item['parameter']
        sources = item['sources']

        param_name = param.get('friendly_name', param.get('python_const_name', 'Unknown'))
        claim_value = param.get('original_value', '')

        print(f"[{idx}/{len(params_with_sources)}] {param_name}")
        print(f"  Claimed value: {claim_value}")
        print(f"  Sources available: {len(sources)}")

        # Verify with evidence memory
        result = verify_parameter_with_memory(param, sources, dry_run)

        # Display final result
        status = result['final_status']
        conf = result['final_confidence']
        synthesis = result['synthesis_used']

        icon_map = {
            'exact': '+', 'approximate': '~', 'contradictory': 'X',
            'not_found': '?', 'ambiguous': '!'
        }
        icon = icon_map.get(result['match_type'], '?')

        print(f"\n  FINAL: [{icon}] {status} ({conf:.0f}%)")
        if synthesis:
            synthesis_count += 1
            print(f"  (Cross-document synthesis used)")

        if result['needs_human_review']:
            print(f"  [!] Flagged for human review")

        # Display LLM reasoning for transparency
        if result.get('llm_reasoning'):
            reasoning_preview = result['llm_reasoning'][:200]
            if len(result['llm_reasoning']) > 200:
                reasoning_preview += "..."
            print(f"  Reasoning: {reasoning_preview}")

        # Save to database
        if not dry_run:
            try:
                log_entry = {
                    'parameter_id': param['id'],
                    'claim_text': param.get('friendly_name', ''),
                    'claim_value': claim_value,
                    'verification_method': 'llm_v1.4',
                    'match_type': result['match_type'],
                    'confidence_score': result['final_confidence'] / 100.0,
                    'llm_model': OPENROUTER_MODEL,
                    'llm_prompt_version': 'v1.4_cross_doc',
                    'verified_at': datetime.utcnow().isoformat(),
                    'needs_human_review': result['needs_human_review'],
                    # New synthesis columns
                    'synthesis_used': result['synthesis_used'],
                    'synthesis_reasoning': result.get('synthesis_reasoning') or result.get('llm_reasoning'),
                    'evidence_source_count': result['evidence_count'],
                    'individual_source_results': json.dumps(result['individual_results'])
                }

                supabase.table('claim_verification_log').insert(log_entry).execute()
                print(f"  Saved to database")
            except Exception as e:
                print(f"  Warning: Failed to save: {e}")
        else:
            print(f"  [DRY RUN] Would save to database")

        # Record for CSV
        results.append({
            'parameter_name': param_name,
            'claimed_value': claim_value,
            'final_status': status,
            'confidence': f"{conf:.0f}%",
            'match_type': result['match_type'],
            'synthesis_used': 'YES' if synthesis else 'NO',
            'evidence_sources': result['evidence_count'],
            'needs_review': 'YES' if result['needs_human_review'] else 'NO',
            'best_source': result.get('best_source', ''),
            'llm_reasoning': (result.get('llm_reasoning') or '')[:500]  # Truncate for CSV
        })

        print()
        time.sleep(0.5)  # Rate limiting

    # Generate report
    print(f"\n{'='*80}")
    print("Generating verification report...")

    csv_path = 'verification_results_v1.4.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'parameter_name', 'claimed_value', 'final_status', 'confidence',
            'match_type', 'synthesis_used', 'evidence_sources', 'needs_review', 'best_source', 'llm_reasoning'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"  Report saved to: {csv_path}\n")

    # Summary
    total = len(results)
    exact = sum(1 for r in results if r['match_type'] == 'exact')
    approximate = sum(1 for r in results if r['match_type'] == 'approximate')
    not_found = sum(1 for r in results if r['match_type'] == 'not_found')
    contradictory = sum(1 for r in results if r['match_type'] == 'contradictory')
    needs_review = sum(1 for r in results if r['needs_review'] == 'YES')
    with_synthesis = sum(1 for r in results if r['synthesis_used'] == 'YES')

    print(f"{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total parameters verified: {total}")
    print(f"  + Exact matches: {exact}")
    print(f"  ~ Approximate matches: {approximate}")
    print(f"  ? Not found: {not_found}")
    print(f"  X Contradictory: {contradictory}")
    print(f"  ! Needs human review: {needs_review}")
    print(f"")
    print(f"Cross-document synthesis:")
    print(f"  Parameters with synthesis: {with_synthesis}")
    print(f"  Synthesis success rate: {(with_synthesis/total*100) if total > 0 else 0:.1f}%")
    print(f"{'='*80}\n")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RWF Claim Verification Pipeline v1.4 - Cross-Document Synthesis')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to database')
    parser.add_argument('--resume', action='store_true', help='Skip already verified parameters')
    parser.add_argument('--start-from', type=int, metavar='N', help='Start from parameter N (1-indexed)')
    parser.add_argument('--no-synthesis', action='store_true', help='Disable cross-document synthesis')
    args = parser.parse_args()

    DEBUG_MODE = args.debug
    SYNTHESIS_ENABLED = not args.no_synthesis

    try:
        verify_parameters(
            dry_run=args.dry_run,
            resume=args.resume,
            start_from=args.start_from
        )
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        raise
