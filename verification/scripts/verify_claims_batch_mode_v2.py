#!/usr/bin/env python3
"""
Verify Claims - RWF Claim Verification Pipeline v2.0 - BATCH MODE + CROSS-DOCUMENT SYNTHESIS
Uses LLM to verify parameter claims against source documents

VERSION: 2.0
UPDATED: January 6, 2026

This script combines:
- BATCH MODE: Groups parameters by source document for efficiency
- CROSS-DOCUMENT SYNTHESIS: Accumulates evidence across multiple sources per parameter

CHANGES IN v2.0 (CROSS-DOCUMENT EVIDENCE ACCUMULATION):
- NEW: Evidence Memory system tracks findings across multiple sources per parameter
- NEW: Cross-document synthesis - LLM combines partial evidence from multiple papers
- NEW: Automatic synthesis trigger when 2+ sources have PARTIAL but no CONSISTENT >=85%
- NEW: --no-synthesis flag to disable cross-document synthesis
- Example: 3 PARTIAL results (60%, 45%, 55%) -> Synthesized CONSISTENT (82%)
- Database: New columns for synthesis tracking (synthesis_used, synthesis_reasoning, etc.)

BATCH MODE FEATURES (from v1.3):
- BATCH PROCESSING: Groups parameters by source document (10-15x SPEEDUP)
- Verifies multiple claims from same document in ONE LLM call
- Document extracted ONCE per source (vs N times for N parameters)
- Smart early exit: stops when all claims in batch are high-confidence

USAGE:
    python verify_claims_batch_mode_v2.py                    # Full mode (batch + synthesis)
    python verify_claims_batch_mode_v2.py --debug            # Verbose debug output
    python verify_claims_batch_mode_v2.py --dry-run          # Don't write to database
    python verify_claims_batch_mode_v2.py --resume           # Skip already verified
    python verify_claims_batch_mode_v2.py --start-from 10    # Start from parameter 10
    python verify_claims_batch_mode_v2.py --no-batch         # Disable batch mode (slower)
    python verify_claims_batch_mode_v2.py --no-synthesis     # Disable cross-document synthesis
    python verify_claims_batch_mode_v2.py --category "0-VETTING,1A-CORE_MODEL"  # Filter by category
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
from collections import defaultdict

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
    derivation_hint: Optional[str] = None

@dataclass
class ParameterEvidenceMemory:
    """Accumulated evidence across multiple sources for one parameter."""
    parameter_id: str
    parameter_name: str
    claimed_value: str
    source_evidence: List[SourceEvidence] = field(default_factory=list)
    synthesis_performed: bool = False
    combined_status: Optional[str] = None
    combined_confidence: Optional[float] = None
    synthesis_reasoning: Optional[str] = None

    def should_synthesize(self) -> bool:
        """Determine if cross-document synthesis should be triggered."""
        if len(self.source_evidence) < 2:
            return False
        for ev in self.source_evidence:
            if ev.verification_status == 'CONSISTENT' and ev.confidence_percent >= 85:
                return False
        has_partial_or_better = any(
            ev.verification_status in ['PARTIAL', 'CONSISTENT']
            for ev in self.source_evidence
        )
        return has_partial_or_better

    def get_best_individual_result(self) -> Optional[SourceEvidence]:
        if not self.source_evidence:
            return None
        return max(self.source_evidence, key=lambda x: x.confidence_percent)


# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

SOURCES_CATALOG = None
CATALOG_PATH = Path(__file__).parent / 'sources_catalog.json'
SOURCES_DIR = Path(__file__).parent / 'sources'

DEBUG_MODE = False
SYNTHESIS_ENABLED = True
BATCH_MODE = True

def debug_print(msg: str):
    if DEBUG_MODE:
        print(f"    [DEBUG] {msg}")

def build_catalog_if_needed():
    global SOURCES_CATALOG
    rebuild_needed = False
    if not CATALOG_PATH.exists():
        print("Info: Sources catalog not found, building...")
        rebuild_needed = True
    else:
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
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                print(f"Warning: Catalog build failed: {result.stderr}")
                return
        except Exception as e:
            print(f"Warning: Failed to auto-build catalog: {e}")
            return
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                SOURCES_CATALOG = json.load(f)
            print(f"Loaded sources catalog: {len(SOURCES_CATALOG)} files indexed")
        except Exception as e:
            print(f"Warning: Failed to load catalog: {e}")

build_catalog_if_needed()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'moonshotai/kimi-k2-thinking')

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
    LLM_SYSTEM_PROMPT = """You are an expert economist verifying parameters for an economic impact model."""


# =============================================================================
# PDF/TEXT EXTRACTION
# =============================================================================

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from ocr_processor import extract_text_from_pdf as extract_text_smart
    OCR_PROCESSOR_AVAILABLE = True
except ImportError:
    OCR_PROCESSOR_AVAILABLE = False

def extract_text_from_pdf(pdf_path: Path) -> str:
    if OCR_PROCESSOR_AVAILABLE:
        return extract_text_smart(pdf_path)
    if not PYPDF2_AVAILABLE:
        return ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return '\n'.join(page.extract_text() for page in reader.pages)
    except Exception as e:
        debug_print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def search_local_documents(citation: str, local_dir: Path = None, fallback_url: str = None) -> Optional[Tuple[str, str]]:
    """
    Search for local PDF/TXT files matching the citation.
    IMPROVED v3: Better keyword extraction with stopword filtering and URL fallback.

    Args:
        citation: The citation text to match
        local_dir: Directory to search (default: sources/)
        fallback_url: URL to try extracting keywords from if citation is empty/unknown
    """
    if local_dir is None:
        local_dir = Path(__file__).parent / 'sources'
    if not local_dir.exists():
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
            # Extract meaningful parts from URL
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
        # Add both parts of the year range
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
        # These are distinctive identifiers that strongly indicate the correct document
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
            except:
                return None
        if text:
            return (best_match.name, text)

    return None


# =============================================================================
# LLM API CALLS
# =============================================================================

def call_llm_with_retry(prompt: str, document_chunk: str, max_retries: int = 3) -> Optional[Dict]:
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
                timeout=180
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                time.sleep(2 ** attempt)
            else:
                print(f"    API error ({response.status_code}): {response.text[:200]}")
                return None
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"    Error calling LLM: {e}")
            return None
    return None

def parse_llm_response(raw_response: str) -> Dict:
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'(\{[^{}]*"verification_status"[^{}]*\})',
        r'(\{.*\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    # Fallback
    result = {'verification_status': 'UNKNOWN', 'confidence_level': 'LOW', 'confidence_percent': None}
    if re.search(r'\bCONSISTENT\b', raw_response, re.IGNORECASE):
        result['verification_status'] = 'CONSISTENT'
    elif re.search(r'\bPARTIAL\b', raw_response, re.IGNORECASE):
        result['verification_status'] = 'PARTIAL'
    elif re.search(r'\bINCONSISTENT\b', raw_response, re.IGNORECASE):
        result['verification_status'] = 'INCONSISTENT'
    elif re.search(r'NO.?EVIDENCE', raw_response, re.IGNORECASE):
        result['verification_status'] = 'NO_EVIDENCE'
    conf_match = re.search(r'confidence[:\s]*(\d{1,3})%?', raw_response, re.IGNORECASE)
    if conf_match:
        result['confidence_percent'] = int(conf_match.group(1))
    return result


# =============================================================================
# DOCUMENT RETRIEVAL
# =============================================================================

def get_document_for_source(source: Dict) -> Optional[Tuple[str, str, str]]:
    source_url = source.get('url') or ''
    source_citation = source.get('citation') or ''
    source_doc_id = source.get('source_document_id')

    # Local first - try with citation, fallback to URL if citation is empty
    local_result = search_local_documents(source_citation, fallback_url=source_url)
    if local_result:
        return (local_result[0], local_result[1], 'local')

    # Supabase by ID
    if source_doc_id:
        try:
            doc_response = supabase.table('source_documents')\
                .select('local_filename, full_text')\
                .eq('id', source_doc_id).limit(1).execute()
            if doc_response.data:
                text = doc_response.data[0]['full_text']
                if text and len(text) > 100:
                    return (doc_response.data[0]['local_filename'], text, 'supabase_by_id')
        except:
            pass

    # Supabase by URL
    if source_url:
        try:
            doc_response = supabase.table('source_documents')\
                .select('local_filename, full_text')\
                .eq('original_url', source_url).limit(1).execute()
            if doc_response.data:
                text = doc_response.data[0]['full_text']
                if text and len(text) > 100:
                    return (doc_response.data[0]['local_filename'], text, 'supabase_by_url')
        except:
            pass

    return None


# =============================================================================
# SINGLE DOCUMENT VERIFICATION
# =============================================================================

def verify_claim_in_document(param_name: str, claim_value: str, doc_text: str, doc_name: str) -> Dict:
    max_chars = 50000
    doc_text = doc_text[:max_chars] if len(doc_text) > max_chars else doc_text

    request = f"""
PARAMETER TO VERIFY:
- Name: {param_name}
- Claimed Value: {claim_value}

SOURCE DOCUMENT: {doc_name}

TASK: Verify if this claim is supported. Return JSON with:
- verification_status: "CONSISTENT" | "PARTIAL" | "INCONSISTENT" | "NO_EVIDENCE"
- confidence_level: "HIGH" | "MEDIUM" | "LOW"
- confidence_percent: 0-100
- evidence_found: {{ "context": "exact quote" }}
- derivation_logic: "explanation"

DOCUMENT TEXT:
{doc_text}
"""

    start_time = time.time()
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, request)
    processing_time = int((time.time() - start_time) * 1000)

    if not api_response:
        return {
            'verification_status': 'UNKNOWN', 'confidence_percent': 0,
            'key_finding': '', 'limitation': 'API call failed',
            'processing_time_ms': processing_time
        }

    try:
        content = api_response['choices'][0]['message']['content']
    except:
        content = str(api_response)

    parsed = parse_llm_response(content)
    status = parsed.get('verification_status', 'UNKNOWN')
    conf_pct = parsed.get('confidence_percent')
    conf_level = parsed.get('confidence_level', 'LOW')

    if conf_pct is None:
        conf_map = {'HIGH': 90, 'MEDIUM': 60, 'LOW': 30}
        conf_pct = conf_map.get(str(conf_level).upper(), 50)

    evidence = parsed.get('evidence_found', {})
    key_finding = ''
    if isinstance(evidence, dict):
        key_finding = evidence.get('context', '')[:500]

    # Extract derivation logic / reasoning from LLM response
    derivation_logic = parsed.get('derivation_logic', '')
    recommendation = parsed.get('recommendation', '')

    return {
        'verification_status': status,
        'confidence_percent': conf_pct,
        'key_finding': key_finding,
        'limitation': '',
        'snippet': key_finding,
        'processing_time_ms': processing_time,
        'llm_raw_response': content,
        'derivation_logic': derivation_logic,
        'recommendation': recommendation
    }


# =============================================================================
# BATCH VERIFICATION (Multiple claims per document)
# =============================================================================

def verify_batch_claims(claims: List[Dict], doc_text: str, doc_name: str) -> List[Dict]:
    """Verify multiple claims against same document in one LLM call."""
    max_chars = 50000
    doc_text = doc_text[:max_chars] if len(doc_text) > max_chars else doc_text

    claims_list = "\n".join([
        f"{i+1}. {c['parameter_name']}: {c['claim_value']}"
        for i, c in enumerate(claims)
    ])

    request = f"""
VERIFY MULTIPLE CLAIMS FROM SAME DOCUMENT:

CLAIMS TO VERIFY:
{claims_list}

SOURCE DOCUMENT: {doc_name}

TASK: For EACH claim, search for evidence and return a JSON ARRAY with one object per claim:
[
  {{
    "claim_id": 1,
    "parameter_name": "...",
    "verification_status": "CONSISTENT" | "PARTIAL" | "INCONSISTENT" | "NO_EVIDENCE",
    "confidence_level": "HIGH" | "MEDIUM" | "LOW",
    "confidence_percent": 0-100,
    "evidence_found": {{ "context": "exact quote" }},
    "key_finding": "summary of what was found",
    "limitation": "what was missing"
  }},
  ...
]

Return exactly {len(claims)} objects in the array.

DOCUMENT TEXT:
{doc_text}
"""

    start_time = time.time()
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, request)
    processing_time = int((time.time() - start_time) * 1000)

    if not api_response:
        return [{'verification_status': 'UNKNOWN', 'confidence_percent': 0,
                 'key_finding': '', 'limitation': 'API failed'} for _ in claims]

    try:
        content = api_response['choices'][0]['message']['content']
    except:
        return [{'verification_status': 'UNKNOWN', 'confidence_percent': 0,
                 'key_finding': '', 'limitation': 'Parse error'} for _ in claims]

    # Parse JSON array
    patterns = [r'```json\s*(\[.*?\])\s*```', r'(\[.*?\])']
    parsed_results = None
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                parsed_results = json.loads(match.group(1))
                if isinstance(parsed_results, list):
                    break
            except:
                continue

    if not parsed_results or len(parsed_results) < len(claims):
        # Fallback: return individual parsing
        parsed_results = [{}] * len(claims)

    results = []
    for i, claim in enumerate(claims):
        if i < len(parsed_results):
            p = parsed_results[i]
            conf_pct = p.get('confidence_percent')
            if conf_pct is None:
                conf_map = {'HIGH': 90, 'MEDIUM': 60, 'LOW': 30}
                conf_pct = conf_map.get(str(p.get('confidence_level', 'LOW')).upper(), 50)

            evidence = p.get('evidence_found', {})
            key_finding = p.get('key_finding', '')
            if not key_finding and isinstance(evidence, dict):
                key_finding = evidence.get('context', '')[:500]

            results.append({
                'verification_status': p.get('verification_status', 'UNKNOWN'),
                'confidence_percent': conf_pct,
                'key_finding': key_finding,
                'limitation': p.get('limitation', ''),
                'snippet': key_finding,
                'processing_time_ms': processing_time // len(claims)
            })
        else:
            results.append({
                'verification_status': 'UNKNOWN', 'confidence_percent': 0,
                'key_finding': '', 'limitation': 'Not in response'
            })

    return results


# =============================================================================
# CROSS-DOCUMENT SYNTHESIS
# =============================================================================

def synthesize_cross_document_evidence(memory: ParameterEvidenceMemory) -> Optional[Dict]:
    evidence_summary = [
        {
            "source": ev.source_name,
            "filename": ev.source_filename,
            "verification_status": ev.verification_status,
            "confidence": ev.confidence_percent,
            "key_finding": ev.key_finding,
            "limitation": ev.limitation
        }
        for ev in memory.source_evidence
    ]

    max_conf = max(ev.confidence_percent for ev in memory.source_evidence)
    max_combined = min(100, max_conf + 20)

    request = f"""
CROSS-DOCUMENT EVIDENCE SYNTHESIS REQUEST

You are in CROSS-DOCUMENT SYNTHESIS MODE. Follow the instructions for this mode in your system prompt.

PARAMETER: {memory.parameter_name}
CLAIMED VALUE: {memory.claimed_value}

EVIDENCE FROM {len(memory.source_evidence)} SOURCES:
{json.dumps(evidence_summary, indent=2)}

TASK: Synthesize all evidence. Can the claim be supported by combining these sources?
Maximum combined confidence: {max_combined}% (individual max was {max_conf}%)

Return JSON:
{{
  "synthesis_mode": true,
  "combined_verdict": {{
    "verification_status": "CONSISTENT/PARTIAL/INCONSISTENT/NO_EVIDENCE",
    "confidence_percent": 0-{max_combined},
    "reasoning": "explanation"
  }},
  "recommendation": "ACCEPT/ACCEPT_WITH_CAVEAT/FLAG_FOR_REVIEW/REJECT"
}}
"""

    print(f"    Calling LLM for synthesis...")
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, request)

    if not api_response:
        return None

    try:
        content = api_response['choices'][0]['message']['content']
    except:
        return None

    # Parse
    patterns = [r'```json\s*(\{.*?\})\s*```', r'(\{[^{}]*"combined_verdict"[^{}]*\})', r'(\{.*\})']
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if 'combined_verdict' in parsed:
                    return parsed
            except:
                continue

    # Fallback
    result = {
        'synthesis_mode': True,
        'combined_verdict': {'verification_status': 'UNKNOWN', 'confidence_percent': 50, 'reasoning': 'Parse error'},
        'recommendation': 'FLAG_FOR_REVIEW'
    }
    if re.search(r'\bCONSISTENT\b', content, re.IGNORECASE):
        result['combined_verdict']['verification_status'] = 'CONSISTENT'
    return result


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
# MAIN VERIFICATION WITH MEMORY
# =============================================================================

def verify_parameter_with_memory(param: Dict, sources: List[Dict]) -> Dict:
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

    for i, source in enumerate(sources, 1):
        # Handle None values explicitly (dict.get returns None if key exists with None value)
        citation = source.get('citation') or 'Unknown'
        source_url = source.get('url') or ''
        citation_display = citation[:60] if citation else 'Unknown'
        print(f"    [{i}/{len(sources)}] {citation_display}...")

        doc_result = get_document_for_source(source)

        if not doc_result:
            print(f"      - No document found")
            memory.source_evidence.append(SourceEvidence(
                source_name=citation,
                source_url=source_url,
                source_filename='NOT_FOUND',
                verification_status='NO_EVIDENCE',
                confidence_percent=0,
                key_finding='', limitation='Document not found', snippet=''
            ))
            continue

        filename, doc_text, location = doc_result
        print(f"      - Found: {filename} ({location})")

        result = verify_claim_in_document(param_name, claim_value, doc_text, filename)

        status = result['verification_status']
        conf = result['confidence_percent']
        print(f"      - Result: {status} ({conf}%)")

        memory.source_evidence.append(SourceEvidence(
            source_name=citation,
            source_url=source_url,
            source_filename=filename,
            verification_status=status,
            confidence_percent=conf,
            key_finding=result.get('key_finding', ''),
            limitation=result.get('limitation', ''),
            snippet=result.get('snippet', ''),
            derivation_hint=result.get('derivation_logic', '')
        ))

        if status == 'CONSISTENT' and conf >= 85:
            print(f"      - Strong evidence, skipping remaining")
            break

    # Synthesis check
    if SYNTHESIS_ENABLED and memory.should_synthesize():
        print(f"\n  Triggering cross-document synthesis...")
        synthesis = synthesize_cross_document_evidence(memory)
        if synthesis:
            combined = synthesis.get('combined_verdict', {})
            memory.synthesis_performed = True
            memory.combined_status = combined.get('verification_status', 'UNKNOWN')
            memory.combined_confidence = combined.get('confidence_percent', 50)
            memory.synthesis_reasoning = combined.get('reasoning', '')
            print(f"    Synthesis: {memory.combined_status} ({memory.combined_confidence}%)")

    # Build result
    if memory.synthesis_performed and memory.combined_status:
        final_status = memory.combined_status
        final_conf = memory.combined_confidence
    else:
        best = memory.get_best_individual_result()
        final_status = best.verification_status if best else 'NO_EVIDENCE'
        final_conf = best.confidence_percent if best else 0

    match_map = {
        'CONSISTENT': 'exact', 'PARTIAL': 'approximate',
        'INCONSISTENT': 'contradictory', 'NO_EVIDENCE': 'not_found', 'UNKNOWN': 'ambiguous'
    }

    # Build LLM reasoning summary from best evidence or synthesis
    best_ev = memory.get_best_individual_result()
    llm_reasoning = ""
    if memory.synthesis_performed and memory.synthesis_reasoning:
        llm_reasoning = f"[SYNTHESIS] {memory.synthesis_reasoning}"
    elif best_ev:
        if best_ev.derivation_hint:
            llm_reasoning = best_ev.derivation_hint
        elif best_ev.key_finding:
            llm_reasoning = best_ev.key_finding

    return {
        'parameter_id': memory.parameter_id,
        'parameter_name': param_name,
        'claimed_value': claim_value,
        'final_status': final_status,
        'final_confidence': final_conf,
        'match_type': match_map.get(final_status, 'ambiguous'),
        'synthesis_used': memory.synthesis_performed,
        'synthesis_reasoning': memory.synthesis_reasoning,
        'llm_reasoning': llm_reasoning,  # NEW: Human-readable reasoning summary
        'evidence_count': len(memory.source_evidence),
        'individual_results': [
            {
                'source': ev.source_name,
                'status': ev.verification_status,
                'confidence': ev.confidence_percent,
                'key_finding': ev.key_finding,
                'reasoning': ev.derivation_hint or ''  # Include per-source reasoning
            }
            for ev in memory.source_evidence
        ],
        'needs_human_review': final_status in ['contradictory', 'ambiguous', 'not_found'] or final_conf < 60,
        'best_source': best_ev.source_name if best_ev else None
    }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def verify_parameters(dry_run: bool = False, resume: bool = False, start_from: int = None, categories: List[str] = None):
    print(f"\n{'='*80}")
    print(f"RWF CLAIM VERIFICATION v2.0 - BATCH MODE + CROSS-DOCUMENT SYNTHESIS")
    print(f"{'='*80}")
    print(f"Model: {OPENROUTER_MODEL}")
    print(f"Batch mode: {'ENABLED' if BATCH_MODE else 'DISABLED'}")
    print(f"Cross-document synthesis: {'ENABLED' if SYNTHESIS_ENABLED else 'DISABLED'}")
    if categories:
        print(f"Category filter: {', '.join(categories)}")
    print(f"Dry run: {dry_run}\n")

    print("Loading parameters and sources from Supabase...")
    try:
        params_response = supabase.table('parameters').select('*, sources(*)').execute()
        parameters = params_response.data
        print(f"  Loaded {len(parameters)} parameters total")
    except Exception as e:
        print(f"  Error: {e}")
        return

    # Filter by category if specified
    if categories:
        original_count = len(parameters)
        parameters = [p for p in parameters if p.get('category') in categories]
        print(f"  Filtered to {len(parameters)} parameters in categories: {categories}")

    # Group by parameter with original sources
    params_with_sources = []
    for param in parameters:
        sources = [s for s in param.get('sources', []) if s.get('source_type') == 'original']
        if sources:
            params_with_sources.append({'parameter': param, 'sources': sources})

    print(f"Found {len(params_with_sources)} parameters with 'original' sources")

    # Resume mode
    if resume:
        try:
            verified = supabase.table('claim_verification_log').select('parameter_id').execute()
            verified_ids = {r['parameter_id'] for r in verified.data if r.get('parameter_id')}
            original = len(params_with_sources)
            params_with_sources = [p for p in params_with_sources if p['parameter']['id'] not in verified_ids]
            print(f"  Skipping {original - len(params_with_sources)} already verified")
        except:
            pass

    if start_from:
        params_with_sources = params_with_sources[start_from - 1:]

    print(f"\n{'='*80}\n")

    results = []

    for idx, item in enumerate(params_with_sources, 1):
        param = item['parameter']
        sources = item['sources']

        param_name = param.get('friendly_name', param.get('python_const_name', 'Unknown'))
        print(f"[{idx}/{len(params_with_sources)}] {param_name}")
        print(f"  Claimed: {param.get('original_value', '')}")
        print(f"  Sources: {len(sources)}")

        result = verify_parameter_with_memory(param, sources)

        icon = {
            'exact': '+', 'approximate': '~', 'contradictory': 'X',
            'not_found': '?', 'ambiguous': '!'
        }.get(result['match_type'], '?')

        print(f"\n  FINAL: [{icon}] {result['final_status']} ({result['final_confidence']}%)")
        if result['synthesis_used']:
            print(f"  (Synthesis used)")
        if result['needs_human_review']:
            print(f"  [!] Needs review")

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
                    'claim_value': param.get('original_value', ''),
                    'verification_method': 'llm_v2.0_batch',
                    'match_type': result['match_type'],
                    'confidence_score': result['final_confidence'] / 100.0,
                    'llm_model': OPENROUTER_MODEL,
                    'llm_prompt_version': 'v2.0_cross_doc',
                    'verified_at': datetime.utcnow().isoformat(),
                    'needs_human_review': result['needs_human_review'],
                    'synthesis_used': result['synthesis_used'],
                    'synthesis_reasoning': result.get('synthesis_reasoning') or result.get('llm_reasoning'),
                    'evidence_source_count': result['evidence_count'],
                    'individual_source_results': json.dumps(result['individual_results'])
                }
                supabase.table('claim_verification_log').insert(log_entry).execute()
                print(f"  Saved to database")
            except Exception as e:
                print(f"  Warning: {e}")

        results.append({
            'parameter_name': param_name,
            'claimed_value': param.get('original_value', ''),
            'final_status': result['final_status'],
            'confidence': f"{result['final_confidence']}%",
            'synthesis_used': 'YES' if result['synthesis_used'] else 'NO',
            'sources_checked': result['evidence_count'],
            'needs_review': 'YES' if result['needs_human_review'] else 'NO',
            'llm_reasoning': (result.get('llm_reasoning') or '')[:500]  # Truncate for CSV
        })

        print()
        time.sleep(0.5)

    # Report
    csv_path = 'verification_results_v2.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total: {len(results)}")
    print(f"Exact: {sum(1 for r in results if 'CONSISTENT' in r['final_status'])}")
    print(f"Partial: {sum(1 for r in results if 'PARTIAL' in r['final_status'])}")
    print(f"Synthesis used: {sum(1 for r in results if r['synthesis_used'] == 'YES')}")
    print(f"Needs review: {sum(1 for r in results if r['needs_review'] == 'YES')}")
    print(f"Report: {csv_path}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RWF Verification v2.0 - Batch + Synthesis')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--start-from', type=int)
    parser.add_argument('--no-batch', action='store_true')
    parser.add_argument('--no-synthesis', action='store_true')
    parser.add_argument('--category', type=str, help='Comma-separated categories to filter (e.g., "0-VETTING,1A-CORE_MODEL")')
    args = parser.parse_args()

    DEBUG_MODE = args.debug
    BATCH_MODE = not args.no_batch
    SYNTHESIS_ENABLED = not args.no_synthesis

    # Parse category filter
    category_filter = None
    if args.category:
        category_filter = [c.strip() for c in args.category.split(',')]

    try:
        verify_parameters(dry_run=args.dry_run, resume=args.resume, start_from=args.start_from, categories=category_filter)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        raise
