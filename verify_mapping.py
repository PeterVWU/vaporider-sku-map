#!/usr/bin/env python3
"""
Verification Script for CSV Mapping
Checks if the mapped_output.csv has correct SKU and Barcode mappings from Sheet1.
"""

import csv
from typing import Dict, Set
from collections import defaultdict


def load_sheet1_data(filename: str) -> Dict[str, Dict[str, str]]:
    """Load Sheet1 data for verification."""
    sheet1_data = {}
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sku = row.get('Internal Reference', '').strip()
            if sku:
                sheet1_data[sku] = {
                    'name': row.get('Name', '').strip(),
                    'barcode': row.get('Barcode', '').strip()
                }
    
    return sheet1_data


def verify_mapping(sheet1_file: str, mapped_output_file: str):
    """Verify the mapping results."""
    print("=== CSV MAPPING VERIFICATION ===\n")
    
    # Load Sheet1 data
    print("Loading Sheet1 data...")
    sheet1_data = load_sheet1_data(sheet1_file)
    print(f"Loaded {len(sheet1_data)} SKUs from Sheet1\n")
    
    # Load mapped output
    print("Loading mapped output...")
    mapped_data = []
    with open(mapped_output_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            mapped_data.append(row)
    
    print(f"Loaded {len(mapped_data)} rows from mapped output\n")
    
    # Verification statistics
    total_rows = len(mapped_data)
    rows_with_sku = 0
    rows_with_barcode = 0
    correct_mappings = 0
    incorrect_mappings = 0
    missing_in_sheet1 = 0
    sku_mismatches = []
    barcode_mismatches = []
    
    # Track which SKUs from Sheet1 were used
    used_skus = set()
    
    # Track duplicates
    sku_tracker = defaultdict(list)  # SKU -> [row_info, ...]
    barcode_tracker = defaultdict(list)  # Barcode -> [row_info, ...]
    duplicate_skus = []
    duplicate_barcodes = []
    
    print("Verifying mappings...")
    for i, row in enumerate(mapped_data):
        variant_sku = row.get('Variant SKU', '').strip()
        variant_barcode = row.get('Variant Barcode', '').strip()
        handle = row.get('Handle', '').strip()
        title = row.get('Title', '').strip()
        option1 = row.get('Option1 Value', '').strip()
        
        # Count rows with SKU/Barcode data and track duplicates
        row_info = {
            'row': i + 2,  # +2 for header and 0-indexing
            'handle': handle,
            'title': title,
            'option1': option1,
            'sku': variant_sku,
            'barcode': variant_barcode
        }
        
        if variant_sku:
            rows_with_sku += 1
            used_skus.add(variant_sku)
            sku_tracker[variant_sku].append(row_info)
            
        if variant_barcode:
            rows_with_barcode += 1
            barcode_tracker[variant_barcode].append(row_info)
        
        # If this row has a SKU, verify it against Sheet1
        if variant_sku:
            if variant_sku in sheet1_data:
                sheet1_record = sheet1_data[variant_sku]
                expected_barcode = sheet1_record['barcode']
                
                # Check if barcode matches
                if variant_barcode == expected_barcode:
                    correct_mappings += 1
                else:
                    incorrect_mappings += 1
                    barcode_mismatches.append({
                        'row': i + 2,  # +2 for header and 0-indexing
                        'sku': variant_sku,
                        'handle': handle,
                        'title': title,
                        'option1': option1,
                        'expected_barcode': expected_barcode,
                        'actual_barcode': variant_barcode
                    })
            else:
                missing_in_sheet1 += 1
                sku_mismatches.append({
                    'row': i + 2,
                    'sku': variant_sku,
                    'handle': handle,
                    'title': title,
                    'option1': option1
                })
    
    # Calculate unused SKUs from Sheet1
    all_sheet1_skus = set(sheet1_data.keys())
    unused_skus = all_sheet1_skus - used_skus
    
    # Find duplicates
    print("Checking for duplicates...")
    for sku, row_list in sku_tracker.items():
        if len(row_list) > 1:
            for row_info in row_list:
                duplicate_skus.append({
                    'sku': sku,
                    'row': row_info['row'],
                    'handle': row_info['handle'],
                    'title': row_info['title'],
                    'option1': row_info['option1'],
                    'total_occurrences': len(row_list)
                })
    
    for barcode, row_list in barcode_tracker.items():
        if len(row_list) > 1:
            for row_info in row_list:
                duplicate_barcodes.append({
                    'barcode': barcode,
                    'row': row_info['row'],
                    'handle': row_info['handle'],
                    'title': row_info['title'],
                    'option1': row_info['option1'],
                    'sku': row_info['sku'],
                    'total_occurrences': len(row_list)
                })
    
    # Print verification results
    print("=== VERIFICATION RESULTS ===")
    print(f"Total rows in mapped output: {total_rows:,}")
    print(f"Rows with SKU data: {rows_with_sku:,} ({rows_with_sku/total_rows*100:.1f}%)")
    print(f"Rows with Barcode data: {rows_with_barcode:,} ({rows_with_barcode/total_rows*100:.1f}%)")
    print()
    print(f"✅ Correct mappings: {correct_mappings:,}")
    print(f"❌ Incorrect barcode mappings: {incorrect_mappings:,}")
    print(f"⚠️  SKUs not found in Sheet1: {missing_in_sheet1:,}")
    print()
    print(f"🔄 Duplicate SKUs found: {len(duplicate_skus):,}")
    print(f"🔄 Duplicate barcodes found: {len(duplicate_barcodes):,}")
    print()
    print(f"Sheet1 SKUs used: {len(used_skus):,} / {len(all_sheet1_skus):,} ({len(used_skus)/len(all_sheet1_skus)*100:.1f}%)")
    print(f"Sheet1 SKUs unused: {len(unused_skus):,}")
    print()
    
    # Show sample errors if any
    if barcode_mismatches:
        print("=== SAMPLE BARCODE MISMATCHES ===")
        for i, mismatch in enumerate(barcode_mismatches[:5]):
            print(f"{i+1}. Row {mismatch['row']}: SKU {mismatch['sku']}")
            print(f"   Product: {mismatch['title']} - {mismatch['option1']}")
            print(f"   Expected Barcode: {mismatch['expected_barcode']}")
            print(f"   Actual Barcode: {mismatch['actual_barcode']}")
            print()
    
    if sku_mismatches:
        print("=== SAMPLE SKUS NOT FOUND IN SHEET1 ===")
        for i, mismatch in enumerate(sku_mismatches[:5]):
            print(f"{i+1}. Row {mismatch['row']}: SKU {mismatch['sku']}")
            print(f"   Product: {mismatch['title']} - {mismatch['option1']}")
            print()
    
    if duplicate_skus:
        print("=== SAMPLE DUPLICATE SKUS ===")
        # Group duplicates by SKU for better display
        sku_groups = defaultdict(list)
        for dup in duplicate_skus:
            sku_groups[dup['sku']].append(dup)
        
        for i, (sku, dup_list) in enumerate(list(sku_groups.items())[:5]):
            print(f"{i+1}. SKU '{sku}' appears {len(dup_list)} times:")
            for dup in dup_list[:3]:  # Show first 3 occurrences
                print(f"   Row {dup['row']}: {dup['title']} - {dup['option1']}")
            if len(dup_list) > 3:
                print(f"   ... and {len(dup_list) - 3} more")
            print()
    
    if duplicate_barcodes:
        print("=== SAMPLE DUPLICATE BARCODES ===")
        # Group duplicates by barcode for better display
        barcode_groups = defaultdict(list)
        for dup in duplicate_barcodes:
            barcode_groups[dup['barcode']].append(dup)
        
        for i, (barcode, dup_list) in enumerate(list(barcode_groups.items())[:5]):
            print(f"{i+1}. Barcode '{barcode}' appears {len(dup_list)} times:")
            for dup in dup_list[:3]:  # Show first 3 occurrences
                print(f"   Row {dup['row']}: SKU {dup['sku']} - {dup['title']} - {dup['option1']}")
            if len(dup_list) > 3:
                print(f"   ... and {len(dup_list) - 3} more")
            print()
    
    # Write detailed error reports
    if barcode_mismatches:
        print(f"Writing {len(barcode_mismatches)} barcode mismatches to 'barcode_mismatches.csv'...")
        with open('barcode_mismatches.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Row', 'SKU', 'Handle', 'Title', 'Option1', 'Expected_Barcode', 'Actual_Barcode'])
            for m in barcode_mismatches:
                writer.writerow([m['row'], m['sku'], m['handle'], m['title'], m['option1'], 
                               m['expected_barcode'], m['actual_barcode']])
    
    if sku_mismatches:
        print(f"Writing {len(sku_mismatches)} SKU mismatches to 'sku_mismatches.csv'...")
        with open('sku_mismatches.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Row', 'SKU', 'Handle', 'Title', 'Option1'])
            for m in sku_mismatches:
                writer.writerow([m['row'], m['sku'], m['handle'], m['title'], m['option1']])
    
    if unused_skus:
        print(f"Writing {len(unused_skus)} unused SKUs to 'unused_skus.csv'...")
        with open('unused_skus.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Product_Name', 'Barcode'])
            for sku in sorted(unused_skus):
                if sku in sheet1_data:
                    writer.writerow([sku, sheet1_data[sku]['name'], sheet1_data[sku]['barcode']])
    
    if duplicate_skus:
        print(f"Writing {len(duplicate_skus)} duplicate SKUs to 'duplicate_skus_detailed.csv'...")
        with open('duplicate_skus_detailed.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Row', 'Handle', 'Title', 'Option1', 'Total_Occurrences'])
            for dup in duplicate_skus:
                writer.writerow([dup['sku'], dup['row'], dup['handle'], dup['title'], 
                               dup['option1'], dup['total_occurrences']])
    
    if duplicate_barcodes:
        print(f"Writing {len(duplicate_barcodes)} duplicate barcodes to 'duplicate_barcodes_detailed.csv'...")
        with open('duplicate_barcodes_detailed.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Barcode', 'SKU', 'Row', 'Handle', 'Title', 'Option1', 'Total_Occurrences'])
            for dup in duplicate_barcodes:
                writer.writerow([dup['barcode'], dup['sku'], dup['row'], dup['handle'], 
                               dup['title'], dup['option1'], dup['total_occurrences']])
    
    # Overall assessment
    print("\n=== OVERALL ASSESSMENT ===")
    total_issues = incorrect_mappings + missing_in_sheet1
    total_duplicates = len(duplicate_skus) + len(duplicate_barcodes)
    
    if total_issues == 0 and total_duplicates == 0:
        print("🎉 PERFECT! All mappings are correct and no duplicates found.")
    elif total_issues == 0:
        print("✅ All SKU→Barcode mappings are correct.")
        if total_duplicates > 0:
            print(f"⚠️  Found {len(duplicate_skus)} duplicate SKUs and {len(duplicate_barcodes)} duplicate barcodes.")
    else:
        print(f"⚠️  Found {total_issues} mapping issues that need attention.")
        if total_duplicates > 0:
            print(f"🔄 Additionally found {len(duplicate_skus)} duplicate SKUs and {len(duplicate_barcodes)} duplicate barcodes.")
    
    accuracy = correct_mappings / max(rows_with_sku, 1) * 100
    print(f"Mapping accuracy: {accuracy:.1f}%")
    
    if total_duplicates > 0:
        print(f"⚠️  Duplicate data may cause issues in Odoo import - review detailed reports.")


if __name__ == "__main__":
    sheet1_file = "sheet1.csv"
    mapped_output_file = "mapped_output.csv"
    
    try:
        verify_mapping(sheet1_file, mapped_output_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")