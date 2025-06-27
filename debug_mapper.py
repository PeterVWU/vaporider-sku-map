#!/usr/bin/env python3
"""
Debug CSV Mapper Script
Analyzes why there are unmatched rows between Sheet1 and Sheet2.
"""

import csv
import re
from typing import Dict, List, Optional
from collections import defaultdict


def normalize_string(text: str) -> str:
    """Remove spaces, dashes, commas and convert to lowercase for comparison."""
    if not text:
        return ""
    # Remove spaces, dashes, commas, dots, quotes, parentheses, and special chars
    normalized = re.sub(r'[\s\-–,\.\"\(\)!&:]', '', text.lower())
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


def load_sheet1_debug(filename: str) -> Dict[str, Dict[str, str]]:
    """Load Sheet1 data and return mapping with debug info."""
    sheet1_data = {}
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            name = row.get('Name', '').strip()
            if name:
                sheet1_data[name] = {
                    'internal_reference': row.get('Internal Reference', ''),
                    'barcode': row.get('Barcode', ''),
                    'row_number': i + 2  # +2 for header and 0-indexing
                }
    
    return sheet1_data


def load_sheet2_debug(filename: str) -> List[Dict[str, str]]:
    """Load Sheet2 data and fill missing titles."""
    sheet2_data = []
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            row['row_number'] = i + 2  # +2 for header and 0-indexing
            sheet2_data.append(row)
    
    # Fill missing titles
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


def generate_sheet2_lookup_names(sheet2_data: List[Dict[str, str]]) -> Dict[str, List[Dict]]:
    """Generate all possible lookup names from Sheet2 data."""
    lookup_names = defaultdict(list)
    
    for row in sheet2_data:
        # Strategy 1: Direct title + options match
        title = row.get('Title', '').strip()
        if title:
            option_suffix = build_option_suffix(row)
            direct_match_name = f"{title}{option_suffix}"
            lookup_names[direct_match_name].append({
                'type': 'direct_title',
                'name': direct_match_name,
                'row': row
            })
        
        # Strategy 2: Handle + options match (with spaces)
        handle = row.get('Handle', '').strip()
        if handle:
            option_suffix = build_option_suffix(row)
            handle_with_spaces = handle.replace('-', ' ')
            handle_match_name = f"{handle_with_spaces}{option_suffix}"
            lookup_names[handle_match_name].append({
                'type': 'handle_spaces',
                'name': handle_match_name,
                'row': row
            })
            
            # Strategy 3: Normalized comparison
            normalized_handle_name = normalize_string(handle_match_name)
            lookup_names[normalized_handle_name].append({
                'type': 'normalized_handle',
                'name': normalized_handle_name,
                'original': handle_match_name,
                'row': row
            })
    
    return lookup_names


def debug_matching():
    """Debug the matching process."""
    print("=== CSV MAPPING DEBUG ANALYSIS ===\n")
    
    # Load data
    print("Loading data...")
    sheet1_data = load_sheet1_debug('sheet1.csv')
    sheet2_data = load_sheet2_debug('sheet2.csv')
    
    print(f"Sheet1: {len(sheet1_data)} unique products")
    print(f"Sheet2: {len(sheet2_data)} rows\n")
    
    # Generate all possible lookup names from Sheet2
    print("Generating Sheet2 lookup names...")
    sheet2_lookup = generate_sheet2_lookup_names(sheet2_data)
    print(f"Generated {len(sheet2_lookup)} unique lookup names from Sheet2\n")
    
    # Find matches and unmatched items
    matched_sheet1 = set()
    unmatched_sheet1 = []
    
    for name in sheet1_data:
        found_match = False
        
        # Direct match
        if name in sheet2_lookup:
            matched_sheet1.add(name)
            found_match = True
        
        # Normalized match
        if not found_match:
            normalized_name = normalize_string(name)
            if normalized_name in sheet2_lookup:
                matched_sheet1.add(name)
                found_match = True
        
        if not found_match:
            unmatched_sheet1.append({
                'name': name,
                'normalized': normalize_string(name),
                'sku': sheet1_data[name]['internal_reference'],
                'row': sheet1_data[name]['row_number']
            })
    
    print(f"MATCHING RESULTS:")
    print(f"Matched: {len(matched_sheet1)} / {len(sheet1_data)} ({len(matched_sheet1)/len(sheet1_data)*100:.1f}%)")
    print(f"Unmatched: {len(unmatched_sheet1)} / {len(sheet1_data)} ({len(unmatched_sheet1)/len(sheet1_data)*100:.1f}%)\n")
    
    # Write all unmatched items to a file
    print("Writing unmatched items to 'unmatched_items.csv'...")
    with open('unmatched_items.csv', 'w', encoding='utf-8', newline='') as file:
        import csv
        writer = csv.writer(file)
        writer.writerow(['Row', 'Name', 'SKU', 'Normalized'])
        
        for item in unmatched_sheet1:
            writer.writerow([item['row'], item['name'], item['sku'], item['normalized']])
    
    print(f"Exported {len(unmatched_sheet1)} unmatched items to unmatched_items.csv\n")
    
    # Show sample unmatched items
    print("=== SAMPLE UNMATCHED SHEET1 ITEMS ===")
    for i, item in enumerate(unmatched_sheet1[:10]):
        print(f"{i+1}. Row {item['row']}: {item['name']}")
        print(f"   SKU: {item['sku']}")
        print(f"   Normalized: {item['normalized']}")
        
        # Try to find close matches in Sheet2
        close_matches = []
        for lookup_name in sheet2_lookup:
            if len(lookup_name) > 10:  # Only check reasonable length names
                # Check if normalized versions have significant overlap
                norm_item = item['normalized']
                norm_lookup = normalize_string(lookup_name) if lookup_name != normalize_string(lookup_name) else lookup_name
                
                # Simple similarity check - common substring
                if len(norm_item) > 5 and norm_item[:15] in norm_lookup:
                    close_matches.append(lookup_name)
                elif len(norm_lookup) > 5 and norm_lookup[:15] in norm_item:
                    close_matches.append(lookup_name)
        
        if close_matches:
            print(f"   Possible matches in Sheet2:")
            for match in close_matches[:3]:  # Show top 3
                print(f"     - {match}")
        else:
            print(f"   No obvious matches found in Sheet2")
        print()
    
    # Show some Sheet2 sample names for comparison
    print("=== SAMPLE SHEET2 LOOKUP NAMES ===")
    sample_sheet2 = list(sheet2_lookup.keys())[:15]
    for i, name in enumerate(sample_sheet2):
        entries = sheet2_lookup[name]
        print(f"{i+1}. {name}")
        print(f"   Type: {entries[0]['type']}")
        if 'original' in entries[0]:
            print(f"   Original: {entries[0]['original']}")
        print(f"   Row: {entries[0]['row']['row_number']}")
        print()


if __name__ == "__main__":
    debug_matching()