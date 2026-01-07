#!/usr/bin/env python3
"""
Associate source URLs to local files by updating the citation field in Supabase.
This script ONLY processes CORE parameters (0-VETTING and 1A-CORE_MODEL).

Process:
1. Read CSV mappings (parameter, URL, local_filename)
2. For each CORE parameter in Supabase:
   - Find matching URLs in CSV
   - Update citation field with local filename
   - Remove duplicate URL entries (keep only one per URL per parameter)

Outputs:
- Updates Supabase sources table
- Generates report of changes made
"""

import os
import sys
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Read CSV
CSV_PATH = 'src/param_sources/Parameters sources - param2URL2sourcename.csv'
df = pd.read_csv(CSV_PATH)

print("="*100)
print("ASSOCIATE SOURCES TO LOCAL FILES - CORE PARAMETERS ONLY")
print("="*100)

print(f"\n📊 CSV Data:")
print(f"   Total mappings: {len(df)}")
print(f"   Unique parameters: {df['parameter'].nunique()}")
print(f"   Unique URLs: {df['url'].nunique()}")
print(f"   Unique local files: {df['/sources'].nunique()}")

# Get CORE parameters from Supabase
print(f"\n🔍 Fetching CORE parameters from Supabase...")
core_params = supabase.table('parameters')\
    .select('id, friendly_name, category')\
    .in_('category', ['0-VETTING', '1A-CORE_MODEL'])\
    .execute()

print(f"   Found {len(core_params.data)} CORE parameters")

# Build URL → local_file mapping from CSV
print(f"\n📋 Building URL → local_file mapping from CSV...")
url_to_file = {}
param_url_to_file = {}  # (param_name, url) → local_file

for idx, row in df.iterrows():
    param_name = row['parameter']
    url = row['url']
    local_file = row.get('/sources', '')

    if local_file and local_file != 'NO_FILE_SPECIFIED':
        url_to_file[url] = local_file
        param_url_to_file[(param_name, url)] = local_file

print(f"   Mapped {len(url_to_file)} URLs to local files")

# Track changes
stats = {
    'params_processed': 0,
    'citations_updated': 0,
    'duplicates_removed': 0,
    'errors': []
}

changes_log = []

print(f"\n{'='*100}")
print("PROCESSING CORE PARAMETERS")
print("="*100)

# Process each core parameter
for param in sorted(core_params.data, key=lambda x: (x.get('category', ''), x.get('friendly_name', ''))):
    param_id = param['id']
    param_name = param['friendly_name']
    category = param.get('category', 'N/A')

    print(f"\n{'─'*100}")
    print(f"📌 {param_name}")
    print(f"   Category: {category}")

    # Get all sources for this parameter
    db_sources = supabase.table('sources').select('*').eq('parameter_id', param_id).execute()

    print(f"   DB sources: {len(db_sources.data)}")

    if not db_sources.data:
        print(f"   ⚠️  No sources in database - skipping")
        continue

    # Group by URL to find duplicates
    url_groups = defaultdict(list)
    for source in db_sources.data:
        url_groups[source['url']].append(source)

    # Find CSV mappings for this parameter
    csv_matches = df[df['parameter'].str.strip() == param_name.strip()]

    print(f"   CSV mappings: {len(csv_matches)}")

    if len(csv_matches) == 0:
        # Try partial match (first 30 chars)
        param_search = param_name[:30]
        csv_matches = df[df['parameter'].str.contains(param_search, case=False, na=False, regex=False)]
        if len(csv_matches) > 0:
            print(f"   ⚠️  Using partial match (found {len(csv_matches)} via '{param_search}')")

    # Process each URL group
    for url, sources_list in url_groups.items():
        url_short = url[:70]

        # Find local file from CSV
        local_file = None

        # Try exact URL match first
        if url in url_to_file:
            local_file = url_to_file[url]
        else:
            # Try finding in CSV matches
            for idx, row in csv_matches.iterrows():
                if row['url'] == url:
                    local_file = row.get('/sources', '')
                    break

        if not local_file or local_file == 'NO_FILE_SPECIFIED':
            print(f"   ⚠️  No CSV mapping for URL: {url_short}...")
            continue

        # Handle duplicates: keep only one, delete the rest
        if len(sources_list) > 1:
            print(f"   🔄 Found {len(sources_list)} duplicates for: {url_short}...")
            print(f"      Local file: {local_file}")

            # Keep the first one, delete others
            to_keep = sources_list[0]
            to_delete = sources_list[1:]

            # Update citation for the one we're keeping
            try:
                update_result = supabase.table('sources')\
                    .update({'citation': local_file})\
                    .eq('id', to_keep['id'])\
                    .execute()

                print(f"      ✅ Updated citation: {local_file}")
                stats['citations_updated'] += 1

                changes_log.append({
                    'parameter': param_name,
                    'url': url,
                    'local_file': local_file,
                    'action': 'UPDATED_CITATION',
                    'source_id': to_keep['id']
                })
            except Exception as e:
                print(f"      ❌ Error updating citation: {e}")
                stats['errors'].append(f"Update citation failed for {param_name}: {e}")

            # Delete duplicates
            for source in to_delete:
                try:
                    delete_result = supabase.table('sources')\
                        .delete()\
                        .eq('id', source['id'])\
                        .execute()

                    stats['duplicates_removed'] += 1

                    changes_log.append({
                        'parameter': param_name,
                        'url': url,
                        'local_file': local_file,
                        'action': 'DELETED_DUPLICATE',
                        'source_id': source['id']
                    })
                except Exception as e:
                    print(f"      ❌ Error deleting duplicate: {e}")
                    stats['errors'].append(f"Delete duplicate failed for {param_name}: {e}")

            print(f"      ✅ Removed {len(to_delete)} duplicates")

        else:
            # Single source - just update citation
            source = sources_list[0]
            current_citation = source.get('citation', '')

            if current_citation != local_file:
                try:
                    update_result = supabase.table('sources')\
                        .update({'citation': local_file})\
                        .eq('id', source['id'])\
                        .execute()

                    print(f"   ✅ Updated: {url_short}...")
                    print(f"      Citation: {local_file}")
                    stats['citations_updated'] += 1

                    changes_log.append({
                        'parameter': param_name,
                        'url': url,
                        'local_file': local_file,
                        'action': 'UPDATED_CITATION',
                        'source_id': source['id']
                    })
                except Exception as e:
                    print(f"   ❌ Error updating: {e}")
                    stats['errors'].append(f"Update failed for {param_name}: {e}")
            else:
                print(f"   ⏭️  Already correct: {url_short}... → {local_file}")

    stats['params_processed'] += 1

# Save changes log
print(f"\n{'='*100}")
print("SUMMARY")
print("="*100)

print(f"\n📊 Statistics:")
print(f"   Parameters processed: {stats['params_processed']}")
print(f"   Citations updated: {stats['citations_updated']}")
print(f"   Duplicates removed: {stats['duplicates_removed']}")
print(f"   Errors: {len(stats['errors'])}")

if stats['errors']:
    print(f"\n❌ Errors encountered:")
    for error in stats['errors'][:10]:
        print(f"   - {error}")

# Save detailed log
log_df = pd.DataFrame(changes_log)
if len(log_df) > 0:
    log_path = 'source_association_changes.csv'
    log_df.to_csv(log_path, index=False)
    print(f"\n📝 Detailed changes log saved to: {log_path}")
    print(f"   Total changes: {len(log_df)}")

print(f"\n{'='*100}")
print("✅ ASSOCIATION COMPLETE")
print("="*100)

print(f"""
NEXT STEPS:
1. Review the changes in 'source_association_changes.csv'
2. Verify fuzzy matching now works correctly
3. Run verification pipeline to test document lookup
4. Check claim_verification_log for improved match rates
""")
