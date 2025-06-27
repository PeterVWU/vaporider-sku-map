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
    
    print("Verifying mappings...")
    for i, row in enumerate(mapped_data):
        variant_sku = row.get('Variant SKU', '').strip()
        variant_barcode = row.get('Variant Barcode', '').strip()
        handle = row.get('Handle', '').strip()
        title = row.get('Title', '').strip()
        option1 = row.get('Option1 Value', '').strip()
        
        # Count rows with SKU/Barcode data
        if variant_sku:
            rows_with_sku += 1
            used_skus.add(variant_sku)
        if variant_barcode:
            rows_with_barcode += 1
        
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
    
    # Overall assessment
    print("\n=== OVERALL ASSESSMENT ===")
    if incorrect_mappings == 0 and missing_in_sheet1 == 0:
        print("🎉 PERFECT! All mappings are correct.")
    elif incorrect_mappings == 0:
        print("✅ All SKU→Barcode mappings are correct.")
        print(f"⚠️  {missing_in_sheet1} SKUs in output don't exist in Sheet1 (these may be new products).")
    else:
        print(f"⚠️  Found {incorrect_mappings + missing_in_sheet1} issues that need attention.")
    
    accuracy = correct_mappings / max(rows_with_sku, 1) * 100
    print(f"Mapping accuracy: {accuracy:.1f}%")


if __name__ == "__main__":
    sheet1_file = "sheet1.csv"
    mapped_output_file = "mapped_output.csv"
    
    try:
        verify_mapping(sheet1_file, mapped_output_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")