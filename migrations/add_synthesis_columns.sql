-- =============================================================================
-- MIGRATION: Add Cross-Document Synthesis Columns to claim_verification_log
-- =============================================================================
-- Version: 1.4
-- Date: January 6, 2026
-- Description: Adds columns to track cross-document evidence synthesis
-- =============================================================================

-- Add synthesis tracking columns to claim_verification_log table
ALTER TABLE claim_verification_log
ADD COLUMN IF NOT EXISTS synthesis_used BOOLEAN DEFAULT FALSE;

ALTER TABLE claim_verification_log
ADD COLUMN IF NOT EXISTS synthesis_reasoning TEXT;

ALTER TABLE claim_verification_log
ADD COLUMN IF NOT EXISTS evidence_source_count INTEGER DEFAULT 1;

ALTER TABLE claim_verification_log
ADD COLUMN IF NOT EXISTS individual_source_results JSONB;

-- Add index for synthesis queries
CREATE INDEX IF NOT EXISTS idx_claim_verification_synthesis
ON claim_verification_log (synthesis_used)
WHERE synthesis_used = TRUE;

-- Add comment explaining the columns
COMMENT ON COLUMN claim_verification_log.synthesis_used IS
    'TRUE if cross-document synthesis was used to combine evidence from multiple sources';

COMMENT ON COLUMN claim_verification_log.synthesis_reasoning IS
    'LLM reasoning for why combined evidence supports/refutes the claim';

COMMENT ON COLUMN claim_verification_log.evidence_source_count IS
    'Number of source documents checked for this parameter';

COMMENT ON COLUMN claim_verification_log.individual_source_results IS
    'JSON array of individual verification results per source before synthesis';

-- =============================================================================
-- VERIFICATION QUERY: Check columns were added
-- =============================================================================
-- Run this to verify:
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'claim_verification_log'
-- AND column_name IN ('synthesis_used', 'synthesis_reasoning', 'evidence_source_count', 'individual_source_results');
