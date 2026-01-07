#!/usr/bin/env python3
"""
Sync Registry - Bidirectional synchronization between Supabase and parameter_registry_v3.py
RWF Economic Impact Model

VERSION: 1.0
CREATED: January 5, 2026

USAGE:
    python sync_registry.py --pull      # Supabase → Python (before running model)
    python sync_registry.py --push      # Python → Supabase (after editing registry)
    python sync_registry.py --sync      # Bidirectional with conflict detection
    python sync_registry.py --diff      # Show differences only (no changes)

REQUIREMENTS:
    pip install supabase python-dotenv

ENVIRONMENT:
    SUPABASE_URL=https://msytuetfqdchbehzichh.supabase.co
    SUPABASE_KEY=<service_role_key>
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Default paths - adjust as needed
DEFAULT_REGISTRY_PATH = Path(__file__).parent / 'parameter_registry_v3.py'
BACKUP_DIR = Path(__file__).parent / 'backups'


# =============================================================================
# PARAMETER EXTRACTION FROM PYTHON FILE
# =============================================================================

def extract_parameters_from_python(filepath: Path) -> Dict[str, Dict]:
    """
    Extract Parameter definitions from parameter_registry_v3.py.
    
    Returns dict mapping parameter name to its attributes.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Registry file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parameters = {}
    
    # Pattern to match Parameter definitions
    # Example: MINCER_RETURN_HS = Parameter(name="...", value=0.058, ...)
    param_pattern = re.compile(
        r'(\w+)\s*=\s*Parameter\s*\(\s*'
        r'name\s*=\s*["\']([^"\']+)["\'].*?'
        r'value\s*=\s*([^,\)]+)',
        re.DOTALL
    )
    
    for match in param_pattern.finditer(content):
        const_name = match.group(1)
        friendly_name = match.group(2)
        value_str = match.group(3).strip()
        
        # Parse value
        try:
            # Handle tuples, floats, ints
            if value_str.startswith('('):
                value = eval(value_str)  # Safe for literals
            else:
                value = float(value_str) if '.' in value_str else int(value_str)
        except:
            value = value_str
        
        parameters[const_name] = {
            'python_const_name': const_name,
            'friendly_name': friendly_name,
            'value': value,
            'raw_match': match.group(0)[:200]  # For debugging
        }
    
    # Also extract BASELINE_WAGES nested structure
    baseline_pattern = re.compile(
        r"'(\w+)':\s*Parameter\s*\(\s*"
        r"name\s*=\s*[\"']([^\"']+)[\"'].*?"
        r"value\s*=\s*(\d+(?:\.\d+)?)",
        re.DOTALL
    )
    
    # Find BASELINE_WAGES block
    wages_match = re.search(r'BASELINE_WAGES\s*=\s*\{(.+?)\n\}', content, re.DOTALL)
    if wages_match:
        wages_block = wages_match.group(1)
        for match in baseline_pattern.finditer(wages_block):
            key = f"BASELINE_WAGE_{match.group(1).upper()}"
            parameters[key] = {
                'python_const_name': key,
                'friendly_name': match.group(2),
                'value': float(match.group(3)),
                'raw_match': match.group(0)[:200]
            }
    
    return parameters


def extract_scenario_configs(filepath: Path) -> Dict[str, Dict]:
    """Extract SCENARIO_CONFIGS from Python file."""
    if not filepath.exists():
        return {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find SCENARIO_CONFIGS block
    match = re.search(r'SCENARIO_CONFIGS\s*=\s*(\{.+?\n\})', content, re.DOTALL)
    if not match:
        return {}
    
    try:
        # Safe eval for dict literal
        return eval(match.group(1))
    except:
        return {}


# =============================================================================
# SUPABASE OPERATIONS
# =============================================================================

def fetch_supabase_parameters() -> Dict[str, Dict]:
    """Fetch all parameters from Supabase."""
    response = supabase.table('parameters')\
        .select('*')\
        .execute()
    
    params = {}
    for row in response.data:
        key = row.get('python_const_name', row.get('friendly_name', str(row['id'])))
        params[key] = row
    
    return params


def update_supabase_parameter(param_id: str, updates: Dict) -> bool:
    """Update a single parameter in Supabase."""
    try:
        supabase.table('parameters')\
            .update(updates)\
            .eq('id', param_id)\
            .execute()
        return True
    except Exception as e:
        print(f"  ✗ Error updating {param_id}: {e}")
        return False


def insert_supabase_parameter(param_data: Dict) -> Optional[str]:
    """Insert a new parameter into Supabase."""
    try:
        response = supabase.table('parameters')\
            .insert(param_data)\
            .execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"  ✗ Error inserting: {e}")
        return None


# =============================================================================
# COMPARISON AND DIFF
# =============================================================================

def compare_values(py_value: Any, db_value: Any) -> bool:
    """Compare values with type tolerance."""
    # Handle None/null
    if py_value is None and db_value is None:
        return True
    if py_value is None or db_value is None:
        return False
    
    # Numeric comparison with tolerance
    if isinstance(py_value, (int, float)) and isinstance(db_value, (int, float)):
        return abs(float(py_value) - float(db_value)) < 1e-9
    
    # String comparison
    if isinstance(py_value, str) and isinstance(db_value, str):
        return py_value.strip() == db_value.strip()
    
    # Tuple/list comparison
    if isinstance(py_value, (tuple, list)) and isinstance(db_value, str):
        # DB might store as JSON string
        try:
            db_parsed = json.loads(db_value)
            return list(py_value) == db_parsed
        except:
            return str(py_value) == db_value
    
    return str(py_value) == str(db_value)


def compute_diff(
    python_params: Dict[str, Dict],
    supabase_params: Dict[str, Dict]
) -> Dict[str, List]:
    """
    Compute differences between Python registry and Supabase.
    
    Returns:
        {
            'only_in_python': [...],
            'only_in_supabase': [...],
            'value_differs': [...],
            'name_differs': [...],
            'identical': [...]
        }
    """
    diff = {
        'only_in_python': [],
        'only_in_supabase': [],
        'value_differs': [],
        'name_differs': [],
        'identical': []
    }
    
    py_keys = set(python_params.keys())
    db_keys = set(supabase_params.keys())
    
    # Only in Python
    for key in py_keys - db_keys:
        diff['only_in_python'].append({
            'key': key,
            'python': python_params[key]
        })
    
    # Only in Supabase
    for key in db_keys - py_keys:
        diff['only_in_supabase'].append({
            'key': key,
            'supabase': supabase_params[key]
        })
    
    # In both - compare values
    for key in py_keys & db_keys:
        py_param = python_params[key]
        db_param = supabase_params[key]
        
        py_value = py_param.get('value')
        db_value = db_param.get('original_value') or db_param.get('value')
        
        py_name = py_param.get('friendly_name', '')
        db_name = db_param.get('friendly_name', '')
        
        if not compare_values(py_value, db_value):
            diff['value_differs'].append({
                'key': key,
                'python_value': py_value,
                'supabase_value': db_value,
                'supabase_id': db_param.get('id')
            })
        elif py_name != db_name:
            diff['name_differs'].append({
                'key': key,
                'python_name': py_name,
                'supabase_name': db_name,
                'supabase_id': db_param.get('id')
            })
        else:
            diff['identical'].append(key)
    
    return diff


def print_diff(diff: Dict[str, List]):
    """Print diff in human-readable format."""
    print(f"\n{'='*80}")
    print("SYNC DIFF REPORT")
    print(f"{'='*80}\n")
    
    # Summary
    print(f"Identical: {len(diff['identical'])}")
    print(f"Only in Python: {len(diff['only_in_python'])}")
    print(f"Only in Supabase: {len(diff['only_in_supabase'])}")
    print(f"Value differs: {len(diff['value_differs'])}")
    print(f"Name differs: {len(diff['name_differs'])}")
    
    # Details
    if diff['only_in_python']:
        print(f"\n--- Only in Python ({len(diff['only_in_python'])}) ---")
        for item in diff['only_in_python'][:10]:
            print(f"  + {item['key']}: {item['python'].get('value')}")
        if len(diff['only_in_python']) > 10:
            print(f"  ... and {len(diff['only_in_python']) - 10} more")
    
    if diff['only_in_supabase']:
        print(f"\n--- Only in Supabase ({len(diff['only_in_supabase'])}) ---")
        for item in diff['only_in_supabase'][:10]:
            print(f"  - {item['key']}")
        if len(diff['only_in_supabase']) > 10:
            print(f"  ... and {len(diff['only_in_supabase']) - 10} more")
    
    if diff['value_differs']:
        print(f"\n--- Value Differs ({len(diff['value_differs'])}) ---")
        for item in diff['value_differs']:
            print(f"  ≠ {item['key']}:")
            print(f"      Python:   {item['python_value']}")
            print(f"      Supabase: {item['supabase_value']}")
    
    if diff['name_differs']:
        print(f"\n--- Name Differs ({len(diff['name_differs'])}) ---")
        for item in diff['name_differs']:
            print(f"  ≈ {item['key']}:")
            print(f"      Python:   {item['python_name']}")
            print(f"      Supabase: {item['supabase_name']}")
    
    print(f"\n{'='*80}\n")


# =============================================================================
# SYNC OPERATIONS
# =============================================================================

def backup_python_file(filepath: Path) -> Path:
    """Create timestamped backup of Python file."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f"parameter_registry_{timestamp}.py"
    
    with open(filepath, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    
    return backup_path


def pull_from_supabase(
    registry_path: Path,
    supabase_params: Dict[str, Dict],
    diff: Dict[str, List],
    dry_run: bool = False
) -> int:
    """
    Pull changes from Supabase to Python file.
    Updates values in Python file where Supabase differs.
    
    Returns number of changes made.
    """
    if not diff['value_differs'] and not diff['name_differs']:
        print("No changes to pull from Supabase.")
        return 0
    
    if dry_run:
        print(f"[DRY RUN] Would update {len(diff['value_differs'])} values in Python")
        return len(diff['value_differs'])
    
    # Backup first
    backup_path = backup_python_file(registry_path)
    print(f"  Backup created: {backup_path}")
    
    with open(registry_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = 0
    for item in diff['value_differs']:
        key = item['key']
        new_value = item['supabase_value']
        
        # Pattern to find and replace value
        pattern = rf'({key}\s*=\s*Parameter\s*\([^)]*value\s*=\s*)([^,\)]+)'
        
        def replacer(match):
            nonlocal changes
            changes += 1
            return f"{match.group(1)}{new_value}"
        
        content, n = re.subn(pattern, replacer, content, flags=re.DOTALL)
        if n > 0:
            print(f"  ✓ Updated {key}: {item['python_value']} → {new_value}")
    
    with open(registry_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return changes


def push_to_supabase(
    python_params: Dict[str, Dict],
    supabase_params: Dict[str, Dict],
    diff: Dict[str, List],
    dry_run: bool = False
) -> int:
    """
    Push changes from Python to Supabase.
    Updates values in Supabase where Python differs.
    
    Returns number of changes made.
    """
    if not diff['value_differs']:
        print("No changes to push to Supabase.")
        return 0
    
    changes = 0
    for item in diff['value_differs']:
        key = item['key']
        new_value = item['python_value']
        param_id = item['supabase_id']
        
        if not param_id:
            print(f"  ⚠ No Supabase ID for {key}, skipping")
            continue
        
        if dry_run:
            print(f"  [DRY RUN] Would update {key}: {item['supabase_value']} → {new_value}")
            changes += 1
            continue
        
        # Determine which field to update
        updates = {'original_value': str(new_value)}
        
        if update_supabase_parameter(param_id, updates):
            print(f"  ✓ Updated {key}: {item['supabase_value']} → {new_value}")
            changes += 1
    
    return changes


def sync_bidirectional(
    registry_path: Path,
    python_params: Dict[str, Dict],
    supabase_params: Dict[str, Dict],
    diff: Dict[str, List],
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Bidirectional sync with conflict detection.
    
    Strategy:
    - If only in Python → push to Supabase
    - If only in Supabase → flag for review (don't auto-create in Python)
    - If value differs → show conflict, require manual resolution
    
    Returns (pulled, pushed) counts.
    """
    pulled, pushed = 0, 0
    
    if diff['value_differs']:
        print("\n⚠ CONFLICTS DETECTED - Manual resolution required:")
        for item in diff['value_differs']:
            print(f"\n  {item['key']}:")
            print(f"    Python:   {item['python_value']}")
            print(f"    Supabase: {item['supabase_value']}")
            
            if not dry_run:
                choice = input("    Keep [p]ython, [s]upabase, or [s]kip? ").lower()
                
                if choice == 'p':
                    # Push Python value to Supabase
                    if update_supabase_parameter(
                        item['supabase_id'],
                        {'original_value': str(item['python_value'])}
                    ):
                        pushed += 1
                        print(f"    ✓ Pushed Python value to Supabase")
                
                elif choice == 's':
                    # Would need to update Python file
                    print(f"    → Run --pull to apply Supabase value")
                
                else:
                    print(f"    → Skipped")
    
    # Push new parameters (only in Python)
    if diff['only_in_python']:
        print(f"\n--- New parameters in Python ({len(diff['only_in_python'])}) ---")
        for item in diff['only_in_python']:
            py_param = item['python']
            print(f"  + {item['key']}: {py_param.get('value')}")
            
            if not dry_run:
                # Insert new parameter
                new_id = insert_supabase_parameter({
                    'python_const_name': item['key'],
                    'friendly_name': py_param.get('friendly_name', item['key']),
                    'original_value': str(py_param.get('value', '')),
                    'verification_status': 'unverified'
                })
                if new_id:
                    pushed += 1
                    print(f"    ✓ Created in Supabase")
    
    return pulled, pushed


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Sync parameter_registry_v3.py with Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_registry.py --diff              # Show differences only
  python sync_registry.py --pull              # Update Python from Supabase
  python sync_registry.py --push              # Update Supabase from Python
  python sync_registry.py --sync              # Bidirectional with conflict resolution
  python sync_registry.py --pull --dry-run    # Preview pull without changes
        """
    )
    
    parser.add_argument('--pull', action='store_true',
                        help='Pull changes from Supabase to Python')
    parser.add_argument('--push', action='store_true',
                        help='Push changes from Python to Supabase')
    parser.add_argument('--sync', action='store_true',
                        help='Bidirectional sync with conflict detection')
    parser.add_argument('--diff', action='store_true',
                        help='Show differences only (no changes)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    parser.add_argument('--registry', type=Path, default=DEFAULT_REGISTRY_PATH,
                        help='Path to parameter_registry_v3.py')
    
    args = parser.parse_args()
    
    # Default to --diff if no action specified
    if not any([args.pull, args.push, args.sync, args.diff]):
        args.diff = True
    
    print(f"\n{'='*80}")
    print("RWF SYNC REGISTRY")
    print(f"{'='*80}")
    print(f"Registry: {args.registry}")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Mode: {'pull' if args.pull else 'push' if args.push else 'sync' if args.sync else 'diff'}")
    print(f"Dry run: {args.dry_run}")
    
    # Load both sources
    print("\nLoading parameters...")
    
    try:
        python_params = extract_parameters_from_python(args.registry)
        print(f"  Python: {len(python_params)} parameters")
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        print(f"    Hint: Set --registry path or create parameter_registry_v3.py")
        return 1
    
    supabase_params = fetch_supabase_parameters()
    print(f"  Supabase: {len(supabase_params)} parameters")
    
    # Compute diff
    diff = compute_diff(python_params, supabase_params)
    print_diff(diff)
    
    # Execute action
    if args.diff:
        return 0
    
    if args.pull:
        changes = pull_from_supabase(
            args.registry, supabase_params, diff, dry_run=args.dry_run
        )
        print(f"\nPulled {changes} changes from Supabase")
    
    elif args.push:
        changes = push_to_supabase(
            python_params, supabase_params, diff, dry_run=args.dry_run
        )
        print(f"\nPushed {changes} changes to Supabase")
    
    elif args.sync:
        pulled, pushed = sync_bidirectional(
            args.registry, python_params, supabase_params, diff, dry_run=args.dry_run
        )
        print(f"\nSync complete: {pulled} pulled, {pushed} pushed")
    
    return 0


if __name__ == '__main__':
    exit(main())
