#!/usr/bin/env python3
"""
Run this script after adding DATABASE_URL to .env
DATABASE_URL format: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    print("Get it from Supabase Dashboard > Project Settings > Database > Connection string")
    exit(1)

print("Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Running migration...")

statements = [
    "ALTER TABLE claim_verification_log ADD COLUMN IF NOT EXISTS synthesis_used BOOLEAN DEFAULT FALSE",
    "ALTER TABLE claim_verification_log ADD COLUMN IF NOT EXISTS synthesis_reasoning TEXT",
    "ALTER TABLE claim_verification_log ADD COLUMN IF NOT EXISTS evidence_source_count INTEGER DEFAULT 1",
    "ALTER TABLE claim_verification_log ADD COLUMN IF NOT EXISTS individual_source_results JSONB",
    "CREATE INDEX IF NOT EXISTS idx_claim_verification_synthesis ON claim_verification_log (synthesis_used) WHERE synthesis_used = TRUE"
]

for stmt in statements:
    print(f"  Executing: {stmt[:50]}...")
    cur.execute(stmt)

conn.commit()
print("Migration completed!")

# Verify
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'claim_verification_log' 
    AND column_name IN ('synthesis_used', 'synthesis_reasoning', 'evidence_source_count', 'individual_source_results')
""")

print("\nNew columns:")
for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

cur.close()
conn.close()
