#!/usr/bin/env python3
"""
Verify Claims - RWF Claim Verification Pipeline
Uses LLM to verify parameter claims against source documents
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


def chunk_text(text: str, max_tokens: int = 4000) -> List[str]:
    """
    Split text into chunks that fit within token limits.
    Rough estimate: 1 token ≈ 4 characters
    """
    max_chars = max_tokens * 4
    chunks = []

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if current_size + para_size > max_chars and current_chunk:
            # Save current chunk and start new one
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def call_llm_with_retry(prompt: str, document_chunk: str, max_retries: int = 3) -> Optional[Dict]:
    """
    Call OpenRouter API with exponential backoff retry logic.

    Returns:
        dict: API response or None if all retries failed
    """
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
                    "temperature": 0.1,  # Low temperature for factual verification
                    "max_tokens": 2000
                },
                timeout=120
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
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
    """
    Parse LLM response to extract verification result.
    Expects JSON format from the LLM.
    """
    try:
        # Try to extract JSON from response
        # Look for JSON block between ```json and ```
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to parse entire response as JSON
        return json.loads(raw_response)

    except json.JSONDecodeError:
        # Fallback: extract key information using regex
        result = {
            'verification_status': 'UNKNOWN',
            'confidence_level': 'LOW',
            'evidence_found': {},
            'recommendation': 'FLAG_FOR_REVIEW'
        }

        # Try to extract verification status
        if re.search(r'CONSISTENT|consistent', raw_response, re.IGNORECASE):
            result['verification_status'] = 'CONSISTENT'
        elif re.search(r'PARTIAL|partial', raw_response, re.IGNORECASE):
            result['verification_status'] = 'PARTIAL'
        elif re.search(r'INCONSISTENT|inconsistent', raw_response, re.IGNORECASE):
            result['verification_status'] = 'INCONSISTENT'
        elif re.search(r'NO.?EVIDENCE|not found', raw_response, re.IGNORECASE):
            result['verification_status'] = 'NO_EVIDENCE'

        return result


def verify_claim_in_document(
    parameter_name: str,
    claim_text: str,
    claim_value: str,
    document_text: str,
    document_name: str
) -> Dict:
    """
    Verify a specific claim against a document using LLM.

    Returns:
        dict: Verification result
    """
    # Build verification prompt
    verification_request = f"""
PARAMETER TO VERIFY:
- Name: {parameter_name}
- Claimed Value: {claim_value}
- Claim Text: {claim_text}

SOURCE DOCUMENT:
- Filename: {document_name}

TASK:
Verify if this claim is supported by the document below. Follow the methodology in your system prompt.
Return your response as a JSON object matching the format specified in the prompt.

DOCUMENT TEXT:
{document_text[:8000]}  # Limit to avoid token overflow
"""

    start_time = time.time()

    # Call LLM
    api_response = call_llm_with_retry(LLM_SYSTEM_PROMPT, verification_request)

    processing_time_ms = int((time.time() - start_time) * 1000)

    if not api_response:
        return {
            'match_type': 'error',
            'confidence_score': 0.0,
            'llm_raw_response': None,
            'processing_time_ms': processing_time_ms,
            'needs_human_review': True
        }

    # Extract content from API response
    try:
        llm_content = api_response['choices'][0]['message']['content']
    except (KeyError, IndexError):
        llm_content = str(api_response)

    # Parse LLM response
    parsed = parse_llm_response(llm_content)

    # Map to database schema
    verification_status = parsed.get('verification_status', 'UNKNOWN')

    match_type_map = {
        'CONSISTENT': 'exact',
        'PARTIAL': 'approximate',
        'INCONSISTENT': 'contradictory',
        'NO_EVIDENCE': 'not_found',
        'UNKNOWN': 'ambiguous'
    }

    confidence_map = {
        'HIGH': 0.9,
        'MEDIUM': 0.6,
        'LOW': 0.3
    }

    match_type = match_type_map.get(verification_status, 'ambiguous')
    confidence_level = parsed.get('confidence_level', 'LOW')
    confidence_score = confidence_map.get(confidence_level, 0.5)

    # Extract evidence
    evidence = parsed.get('evidence_found', {})
    extracted_snippet = ''
    if evidence and isinstance(evidence, dict):
        context = evidence.get('context', '')
        if context:
            extracted_snippet = str(context)[:500]  # Limit to 500 chars

    # Determine if human review needed
    needs_review = (
        match_type in ['contradictory', 'ambiguous', 'not_found'] or
        confidence_score < 0.6 or
        parsed.get('recommendation') in ['FLAG_FOR_REVIEW', 'REJECT']
    )

    return {
        'match_type': match_type,
        'confidence_score': confidence_score,
        'extracted_snippet': extracted_snippet,
        'llm_raw_response': llm_content,
        'llm_interpretation': parsed.get('derivation_logic', ''),
        'llm_confidence_reason': str(parsed.get('economic_plausibility', '')),
        'processing_time_ms': processing_time_ms,
        'needs_human_review': needs_review
    }


def verify_parameters():
    """
    Main verification function.
    """
    print(f"\n{'='*80}")
    print(f"RWF CLAIM VERIFICATION PIPELINE - CLAIM VERIFICATION")
    print(f"{'='*80}\n")

    # Load parameters with their sources
    print("Loading parameters and sources from Supabase...")
    try:
        # Get parameters with sources joined
        params_response = supabase.table('parameters')\
            .select('*, sources(*)')\
            .execute()

        parameters = params_response.data
        print(f"  ✓ Loaded {len(parameters)} parameters\n")
    except Exception as e:
        print(f"  ✗ Error loading data: {str(e)}")
        return

    # Filter to only parameters with 'original' sources
    params_to_verify = []
    for param in parameters:
        if param.get('sources'):
            for source in param['sources']:
                if source.get('source_type') == 'original':
                    params_to_verify.append({
                        'parameter': param,
                        'source': source
                    })
                    break  # Only verify against one original source per parameter

    print(f"Found {len(params_to_verify)} parameters with 'original' sources to verify\n")
    print(f"{'='*80}\n")

    # Results for CSV export
    results = []

    # Process each parameter
    for idx, item in enumerate(params_to_verify, 1):
        param = item['parameter']
        source = item['source']

        param_name = param.get('friendly_name', param.get('python_const_name', 'Unknown'))
        claim_value = param.get('original_value', '')

        print(f"[{idx}/{len(params_to_verify)}] Verifying: {param_name}")
        print(f"  Claimed value: {claim_value}")

        # Get source URL
        source_url = source.get('url')
        if not source_url:
            print(f"  ⚠ No URL for source, skipping")
            print()
            continue

        print(f"  Source URL: {source_url[:60]}...")

        # Get source document by URL - CRITICAL: Filter by URL to avoid cross-contamination
        try:
            doc_response = supabase.table('source_documents')\
                .select('id, local_filename, full_text')\
                .eq('original_url', source_url)\
                .execute()

            if not doc_response.data or len(doc_response.data) == 0:
                print(f"  ⚠ No document found for this URL")
                print()
                continue

            doc = doc_response.data[0]
            doc_id = doc['id']
            doc_filename = doc['local_filename']
            doc_text = doc['full_text']

            print(f"  ✓ Found document: {doc_filename}")

        except Exception as e:
            print(f"  ✗ Error fetching document: {str(e)}")
            print()
            continue

        # Verify claim
        print(f"  Verifying with LLM...")

        verification_result = verify_claim_in_document(
            parameter_name=param_name,
            claim_text=param.get('friendly_name', ''),
            claim_value=claim_value,
            document_text=doc_text,
            document_name=doc_filename
        )

        # Display result
        match_type = verification_result['match_type']
        confidence = verification_result['confidence_score']

        match_icons = {
            'exact': '✓',
            'approximate': '≈',
            'contradictory': '✗',
            'not_found': '?',
            'ambiguous': '⚠',
            'error': '⚠'
        }

        icon = match_icons.get(match_type, '?')
        print(f"  {icon} Result: {match_type.upper()} (confidence: {confidence:.1%})")

        if verification_result.get('extracted_snippet'):
            snippet = verification_result['extracted_snippet'][:100]
            print(f"  Evidence: \"{snippet}...\"")

        if verification_result.get('needs_human_review'):
            print(f"  ⚠ Flagged for human review")

        # Insert into claim_verification_log
        try:
            log_entry = {
                'parameter_id': param['id'],
                'source_id': source['id'],
                'source_document_id': doc_id,
                'claim_text': param.get('friendly_name', ''),
                'claim_value': claim_value,
                'verification_method': 'llm',
                'match_type': verification_result['match_type'],
                'confidence_score': verification_result['confidence_score'],
                'extracted_snippet': verification_result.get('extracted_snippet'),
                'llm_model': OPENROUTER_MODEL,
                'llm_prompt_version': 'v1_expert',
                'llm_raw_response': verification_result.get('llm_raw_response'),
                'llm_interpretation': verification_result.get('llm_interpretation'),
                'llm_confidence_reason': verification_result.get('llm_confidence_reason'),
                'verified_at': datetime.utcnow().isoformat(),
                'processing_time_ms': verification_result.get('processing_time_ms'),
                'needs_human_review': verification_result.get('needs_human_review', False)
            }

            supabase.table('claim_verification_log').insert(log_entry).execute()
            print(f"  ✓ Logged to database")

        except Exception as e:
            print(f"  ✗ Error logging result: {str(e)}")

        # Record for CSV
        results.append({
            'parameter_id': param['id'],
            'friendly_name': param_name,
            'claim_text': param.get('friendly_name', ''),
            'claim_value': claim_value,
            'source_url': source_url[:100],
            'document': doc_filename,
            'match_type': match_type,
            'confidence': f"{confidence:.1%}",
            'snippet': verification_result.get('extracted_snippet', '')[:200],
            'needs_review': 'YES' if verification_result.get('needs_human_review') else 'NO'
        })

        print()

        # Rate limiting: small delay between API calls
        time.sleep(1)

    # Generate verification report
    print(f"{'='*80}\n")
    print("Generating verification report...")

    csv_path = 'verification_results.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'parameter_id', 'friendly_name', 'claim_text', 'claim_value',
            'source_url', 'document', 'match_type', 'confidence', 'snippet', 'needs_review'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"  ✓ Report saved to: {csv_path}\n")

    # Summary statistics
    total = len(results)
    exact = sum(1 for r in results if r['match_type'] == 'exact')
    approximate = sum(1 for r in results if r['match_type'] == 'approximate')
    not_found = sum(1 for r in results if r['match_type'] == 'not_found')
    contradictory = sum(1 for r in results if r['match_type'] == 'contradictory')
    needs_review = sum(1 for r in results if r['needs_review'] == 'YES')

    print(f"{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total parameters verified: {total}")
    print(f"  ✓ Exact matches: {exact}")
    print(f"  ≈ Approximate matches: {approximate}")
    print(f"  ? Not found: {not_found}")
    print(f"  ✗ Contradictory: {contradictory}")
    print(f"  ⚠ Needs human review: {needs_review}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    try:
        verify_parameters()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        raise
