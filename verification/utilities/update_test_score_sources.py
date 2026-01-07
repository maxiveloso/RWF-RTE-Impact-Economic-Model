#!/usr/bin/env python3
"""
Update sources table for 'Test Score to Years of Schooling Conversion' parameter
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n" + "="*80)
print("UPDATING SOURCES FOR 'Test Score to Years of Schooling Conversion'")
print("="*80 + "\n")

# Get the parameter
param_response = supabase.table('parameters')\
    .select('id, friendly_name')\
    .ilike('friendly_name', '%Test Score%Years%Schooling%Conversion%')\
    .execute()

if not param_response.data:
    print("ERROR: Parameter not found!")
    exit(1)

param_id = param_response.data[0]['id']
param_name = param_response.data[0]['friendly_name']

print(f"Parameter found: {param_name}")
print(f"Parameter ID: {param_id}\n")

# Get current sources
current_sources = supabase.table('sources')\
    .select('*')\
    .eq('parameter_id', param_id)\
    .execute()

print(f"Current sources: {len(current_sources.data)}")
for src in current_sources.data:
    print(f"  - {src['url']}")
    print(f"    Type: {src['source_type']}, Citation: {src.get('citation', 'None')}")

# Define all 5 expected URLs with their metadata
expected_sources = [
    {
        'url': 'https://documents1.worldbank.org/curated/en/123371550594320297/txt/WPS8752.txt',
        'citation': 'World Bank WPS8752 - Evans & Yuan (2019)',
        'year': '2019',
        'source_type': 'original',
        'local_filename': 'evans_yuan_2019_equivalent_years_schooling_learning_gains.txt'
    },
    {
        'url': 'https://documents1.worldbank.org/curated/en/801901603314530125/pdf/How-to-Improve-Education-Outcomes-Most-Efficiently-A-Comparison-of-150-Interventions-Using-the-New-Learning-Adjusted-Years-of-Schooling-Metric.pdf',
        'citation': 'World Bank - Angrist & Evans (2020)',
        'year': '2020',
        'source_type': 'original',
        'local_filename': 'angrist_evans_2020_improve_education_outcomes_efficiently.pdf'
    },
    {
        'url': 'https://openknowledge.worldbank.org/server/api/core/bitstreams/ee996c03-1232-54eb-89cd-7f6fe71e13a4/content',
        'citation': 'World Bank - Angrist et al. (2021) - Measuring Human Capital',
        'year': '2021',
        'source_type': 'original',
        'local_filename': 'angrist_etal_2021_measuring_human_capital_learning_data.pdf'
    },
    {
        'url': 'https://www.nature.com/articles/s41586-021-03323-7',
        'citation': 'Nature - Angrist et al. (2021)',
        'year': '2021',
        'source_type': 'external'
    },
    {
        'url': 'https://eproceedings.epublishing.ekt.gr/index.php/inoek/article/view/7034/6697',
        'citation': 'IZA Discussion Paper - Patrinos (2024)',
        'year': '2024',
        'source_type': 'original',
        'local_filename': 'patrinos_2024_returns_to_education.pdf'
    }
]

# Check which URLs are missing
current_urls = {src['url'] for src in current_sources.data}
missing_sources = [src for src in expected_sources if src['url'] not in current_urls]

if not missing_sources:
    print("\n✓ All expected sources are already in database!")
else:
    print(f"\n⚠ Found {len(missing_sources)} missing sources:")
    for src in missing_sources:
        print(f"  - {src['url'][:80]}")
        print(f"    Citation: {src['citation']}")

    # Add missing sources
    print("\nAdding sources...")

    for src in missing_sources:
        try:
            insert_data = {
                'parameter_id': param_id,
                'url': src['url'],
                'citation': src['citation'],
                'year': src['year'],
                'source_type': src['source_type']
            }

            result = supabase.table('sources').insert(insert_data).execute()
            print(f"  ✓ Added: {src['citation']}")

        except Exception as e:
            print(f"  ✗ Error adding {src['citation']}: {e}")

    print("\n✓ Update complete!")

    # Verify final count
    final_sources = supabase.table('sources')\
        .select('*')\
        .eq('parameter_id', param_id)\
        .execute()

    print(f"\nFinal source count: {len(final_sources.data)}")

print("\n" + "="*80 + "\n")
