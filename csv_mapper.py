#!/usr/bin/env python3
"""
CSV Mapper Script
Maps SKU and Barcode data from Sheet1 to Sheet2 based on name matching.
"""

import csv
import re
from typing import Dict, List, Optional


def normalize_string(text: str) -> str:
    """Remove spaces, dashes, commas and convert to lowercase for comparison."""
    if not text:
        return ""
    # Remove spaces, dashes, commas, dots, quotes, parentheses, and special chars
    normalized = re.sub(r'[\s\-–,\.\"\(\)!&:+]', '', text.lower())
    # Remove specific filler words/phrases that might be inconsistent
    normalized = re.sub(r'poweredby[a-zA-Z]*vape[a-zA-Z]*co\.?', '', normalized)  # Remove "powered by X vape co"
    normalized = re.sub(r'disposabledevice', 'disposable', normalized)  # Normalize device vs no device
    normalized = re.sub(r'ecigdevice', 'ecig', normalized)  # Normalize ecig device vs ecig
    normalized = re.sub(r'(\d+)puffs?', r'\1', normalized)  # Remove "puff/puffs" only after numbers
    normalized = re.sub(r'\d+pack', '', normalized)  # Remove pack quantities
    normalized = re.sub(r'kit|pod', '', normalized)  # Remove KIT/POD variations
    return normalized


def build_option_suffix(row: Dict[str, str]) -> str:
    """Build suffix from option values if they exist."""
    options = []
    for i in range(1, 4):  # Option1, Option2, Option3
        option_key = f'Option{i} Value'
        if option_key in row and row[option_key].strip():
            options.append(row[option_key].strip())
    
    return f"-{'-'.join(options)}" if options else ""


def load_sheet1(filename: str) -> Dict[str, Dict[str, str]]:
    """Load Sheet1 data and create lookup dictionaries."""
    sheet1_data = {}
    sheet1_normalized = {}
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row.get('Name', '').strip()
            if name:
                # Store by exact name
                sheet1_data[name] = {
                    'internal_reference': row.get('Internal Reference', ''),
                    'barcode': row.get('Barcode', '')
                }
                
                # Store by normalized name
                normalized_name = normalize_string(name)
                sheet1_normalized[normalized_name] = sheet1_data[name]
    
    return sheet1_data, sheet1_normalized


def fill_missing_titles(sheet2_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Fill empty titles with the first title from the same handle group."""
    handle_titles = {}
    
    # First pass: collect first title for each handle
    for row in sheet2_data:
        handle = row.get('Handle', '').strip()
        title = row.get('Title', '').strip()
        
        if handle and title and handle not in handle_titles:
            handle_titles[handle] = title
    
    # Second pass: fill missing titles
    for row in sheet2_data:
        handle = row.get('Handle', '').strip()
        if handle and not row.get('Title', '').strip():
            if handle in handle_titles:
                row['Title'] = handle_titles[handle]
    
    return sheet2_data


def find_match(row: Dict[str, str], sheet1_data: Dict[str, Dict[str, str]], 
               sheet1_normalized: Dict[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Find matching record from Sheet1 using both strategies."""
    
    # Strategy 1: Direct title + options match
    title = row.get('Title', '').strip()
    if title:
        option_suffix = build_option_suffix(row)
        direct_match_name = f"{title}{option_suffix}"
        
        if direct_match_name in sheet1_data:
            return sheet1_data[direct_match_name]
    
    # Strategy 2: Normalized handle + options match
    handle = row.get('Handle', '').strip()
    if handle:
        option_suffix = build_option_suffix(row)
        handle_with_spaces = handle.replace('-', ' ')
        handle_match_name = f"{handle_with_spaces}{option_suffix}"
        normalized_handle_name = normalize_string(handle_match_name)
        
        if normalized_handle_name in sheet1_normalized:
            return sheet1_normalized[normalized_handle_name]
    
    return None


def process_csv_mapping(sheet1_file: str, sheet2_file: str, output_file: str):
    """Main processing function."""
    print("Loading Sheet1 data...")
    sheet1_data, sheet1_normalized = load_sheet1(sheet1_file)
    print(f"Loaded {len(sheet1_data)} records from Sheet1")
    
    print("Loading Sheet2 data...")
    sheet2_data = []
    with open(sheet2_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            sheet2_data.append(row)
    
    print(f"Loaded {len(sheet2_data)} records from Sheet2")
    
    print("Filling missing titles...")
    sheet2_data = fill_missing_titles(sheet2_data)
    
    print("Processing matches and updating data...")
    matches_found = 0
    matched_rows = []
    
    for row in sheet2_data:
        match_data = find_match(row, sheet1_data, sheet1_normalized)
        
        if match_data:
            matches_found += 1
            row['Variant SKU'] = match_data['internal_reference']
            row['Variant Barcode'] = match_data['barcode']
            matched_rows.append(row)
            print(f"Match found: {row.get('Title', row.get('Handle', ''))} -> SKU: {match_data['internal_reference']}")
    
    print(f"Found {matches_found} matches out of {len(sheet2_data)} records")
    print(f"Output will contain {len(matched_rows)} rows (only matched products)")
    
    print(f"Writing output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_rows)
    
    print("Processing complete!")


if __name__ == "__main__":
    sheet1_file = "sheet1.csv"
    sheet2_file = "sheet2.csv"
    output_file = "mapped_output.csv"
    
    try:
        process_csv_mapping(sheet1_file, sheet2_file, output_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")