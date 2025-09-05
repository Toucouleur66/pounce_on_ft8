#!/usr/bin/env python3
"""
Extract callsigns and grids from ADIF file format.
"""

import re
import os

def load_existing_data(output_file_path):
    """
    Load existing callsign/grid data from output file if it exists.
    
    Args:
        output_file_path: Path to the output text file
        
    Returns:
        dict: Dictionary of existing callsign -> grid mappings
    """
    callsign_grid_dict = {}
    
    if os.path.exists(output_file_path):
        try:
            with open(output_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if ',' in line:
                        callsign, grid = line.split(',', 1)
                        callsign_grid_dict[callsign] = grid
            print(f"Loaded {len(callsign_grid_dict)} existing entries from {output_file_path}")
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
    
    return callsign_grid_dict

def extract_callsigns_and_grids(adif_file_paths, output_file_path):
    """
    Extract callsigns and grids from ADIF file(s) and merge with existing data.
    Only includes callsigns that have gridsquare data.
    Duplicate callsigns are overridden with the last occurrence.
    
    Args:
        adif_file_paths: List of paths to ADIF files or single path string
        output_file_path: Path to the output text file
    """
    
    # Load existing data first
    callsign_grid_dict = load_existing_data(output_file_path)
    initial_count = len(callsign_grid_dict)
    
    # Handle single file path or list of file paths
    if isinstance(adif_file_paths, str):
        adif_file_paths = [adif_file_paths]
    
    # Process each ADIF file
    for adif_file_path in adif_file_paths:
        if not os.path.exists(adif_file_path):
            print(f"Warning: File {adif_file_path} not found, skipping...")
            continue
            
        print(f"Processing {adif_file_path}...")
        
        try:
            with open(adif_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(adif_file_path, 'r', encoding='latin-1') as file:
                content = file.read()
        
        # Split records by <EOR> (End of Record)
        records = content.split('<EOR>')
        file_count = 0
        
        for record in records:
            if not record.strip():
                continue
                
            # Extract callsign using regex (case insensitive)
            call_match = re.search(r'<call:\d+>([^<]+)', record, re.IGNORECASE)
            if not call_match:
                continue
                
            callsign = call_match.group(1).strip()
            
            # Extract gridsquare using regex (case insensitive)
            grid_match = re.search(r'<gridsquare:\d+>([^<]+)', record, re.IGNORECASE)
            
            # Only process if we have both callsign and grid
            if callsign and grid_match:
                grid = grid_match.group(1).strip()
                if grid:  # Make sure grid is not empty
                    callsign_grid_dict[callsign] = grid  # This will override duplicates
                    file_count += 1
        
        print(f"  Added {file_count} callsign/grid pairs from {os.path.basename(adif_file_path)}")
    
    # Convert dict to list of formatted strings
    callsign_grid_pairs = [f"{callsign},{grid}" for callsign, grid in callsign_grid_dict.items()]
    
    # Write to output file
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for pair in callsign_grid_pairs:
            output_file.write(pair + '\n')
    
    final_count = len(callsign_grid_pairs)
    new_entries = final_count - initial_count
    
    print(f"\nSummary:")
    print(f"  Initial entries: {initial_count}")
    print(f"  New entries added: {new_entries}")
    print(f"  Total unique entries: {final_count}")
    print(f"  Saved to: {output_file_path}")
    
    # Show first few entries as preview
    if callsign_grid_pairs:
        print("\nFirst few entries:")
        for pair in callsign_grid_pairs[:5]:
            print(f"  {pair}")
        if len(callsign_grid_pairs) > 5:
            print(f"  ... and {len(callsign_grid_pairs) - 5} more entries")

if __name__ == "__main__":
    import sys
    
    # Default files
    default_files = [
    ]
    output_file = "callsigns_grids.txt"
    
    # Use command line arguments if provided, otherwise use defaults
    if len(sys.argv) > 1:
        adif_files = sys.argv[1:]
    else:
        adif_files = default_files
    
    if adif_files:
        extract_callsigns_and_grids(adif_files, output_file)
    else:
        print("Usage: python3 extract_callsigns_grids.py <adif_file1> [adif_file2] ...")
        print("Example: python3 extract_callsigns_grids.py /path/to/file.adi")
        print("This will add new callsign/grid pairs to callsigns_grids.txt")