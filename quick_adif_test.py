"""
Quick ADIF Test Helper - Easy to import in Python terminal
Usage:
    >>> from quick_adif_test import *
    >>> entity_from("F5UKW")
    >>> "F" in adif_data.get('entity', {}).get("2026", {}).get("80m", {})
"""

import json
import os
from collections import defaultdict
from utils import parse_adif_incremental
from callsign_lookup import CallsignLookup

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'params.json')
with open(config_path, 'r') as f:
    config = json.load(f)

adif_file_paths = config.get('adif_file_paths', [])

print("Initializing CallsignLookup...")
lookup = CallsignLookup()
print("✓ CallsignLookup initialized")

print("\nLoading ADIF files...")
merged_data = {
    'wkb4': defaultdict(lambda: defaultdict(set)),
    'entity': defaultdict(lambda: defaultdict(set)),
    'grid': defaultdict(lambda: defaultdict(list)),
}

for file_path in adif_file_paths:
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        continue

    print(f"📂 Processing: {os.path.basename(file_path)}")

    try:
        processing_time, file_data = parse_adif_incremental(
            file_path, 0, lookup, max_lines=None
        )

        # Merge data
        if 'wkb4' in file_data:
            for year, bands in file_data['wkb4'].items():
                for band, calls in bands.items():
                    merged_data['wkb4'][year][band].update(calls)

        if 'entity' in file_data:
            for year, bands in file_data['entity'].items():
                for band, entities in bands.items():
                    merged_data['entity'][year][band].update(entities)

        if 'grid' in file_data:
            for band, grids in file_data['grid'].items():
                for grid, qso_data in grids.items():
                    merged_data['grid'][band][grid].extend(qso_data)

        print(f"   ✓ Loaded ({processing_time:.2f}s)")
    except Exception as e:
        print(f"   ✗ Error: {e}")

adif_data = merged_data

def entity_from(callsign):
    """Get entity information from a callsign

    Returns entity_code (ADIF number), entity_name, and prefix
    """
    try:
        callsign_info = lookup.lookup_callsign(callsign)
        if callsign_info:
            entity_code = callsign_info.get('entity_code')  # This is ADIF number (int)
            entity_name = callsign_info.get('entity_name') or callsign_info.get('entity')
            prefix = callsign_info.get('prefix', '')  # The actual prefix string

            return {
                'entity_code': entity_code,  # ADIF entity number (e.g., 291 for USA)
                'entity_name': entity_name,
                'prefix': prefix,  # Prefix string (e.g., "K" for USA)
                'full_info': callsign_info
            }
        else:
            return f"No information found for {callsign}"
    except Exception as e:
        return f"Error: {e}"

print("\n" + "="*60)
print("Ready! Available variables:")
print("  - adif_data: The merged ADIF data")
print("  - lookup: CallsignLookup instance")
print("  - entity_from(callsign): Quick entity lookup function")
print("\nExamples:")
print('  >>> entity_from("K5USD")')
print('  >>> entity_from("K5USD")["entity_code"]  # Returns ADIF number (e.g., 291)')
print('  >>> entity_from("K5USD")["entity_code"] in adif_data.get("entity", {}).get("2026", {}).get("80m", {})')
print('  >>> adif_data.get("entity", {}).get("2026", {}).get("80m", {})  # Shows ADIF numbers')
print("="*60 + "\n")
