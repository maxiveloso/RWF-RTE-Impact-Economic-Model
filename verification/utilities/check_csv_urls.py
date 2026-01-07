#!/usr/bin/env python3
"""
Check URLs in the Parameters sources CSV for 'Test Score to Years of Schooling Conversion'
"""

import csv
import os

csv_path = 'src/param_sources/Parameters sources - Latest.csv'

print("\n" + "="*80)
print("CHECKING CSV FOR 'Test Score to Years of Schooling Conversion'")
print("="*80 + "\n")

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        param_name = row.get('Parameter/Variable Name', '')

        if 'Test Score' in param_name and 'Years' in param_name and 'Schooling' in param_name and 'Conversion' in param_name:
            print(f"Found parameter: {param_name}\n")

            # Get URLs
            url_field = row.get('URL', '')
            print(f"URL field content:")
            print(f"{url_field}\n")

            # Split by semicolon or comma
            urls = []
            if ';' in url_field:
                urls = [u.strip() for u in url_field.split(';') if u.strip()]
            elif ',' in url_field:
                urls = [u.strip() for u in url_field.split(',') if u.strip()]
            else:
                urls = [url_field.strip()] if url_field.strip() else []

            print(f"Parsed {len(urls)} URLs:")
            for i, url in enumerate(urls, 1):
                print(f"  [{i}] {url}")

            # Check external sources
            ext_sources = row.get('External Sources', '')
            if ext_sources:
                print(f"\nExternal Sources field:")
                print(ext_sources[:500])

            break
    else:
        print("Parameter 'Test Score to Years of Schooling Conversion' NOT FOUND in CSV")

print("\n" + "="*80 + "\n")
