#!/usr/bin/env python3
"""
Analyze Shopify Extra Rows Script
Identifies what extra rows are in shopify update CSV that aren't in mapped_output.csv.
"""

import csv
from typing import Set, Dict, List
from collections import defaultdict


def load_mapped_output_handles(filename: str) -> Set[str]:
    """Load all handle+variant combinations from mapped_output.csv."""
    mapped_keys = set()
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            handle = row.get('Handle', '').strip()
            option1 = row.get('Option1 Value', '').strip()
            option2 = row.get('Option2 Value', '').strip()
            option3 = row.get('Option3 Value', '').strip()
            
            # Create unique key for this variant
            key = f"{handle}|{option1}|{option2}|{option3}"
            mapped_keys.add(key)
    
    return mapped_keys


def load_shopify_update_details(filename: str) -> Dict[str, List[Dict]]:
    """Load all rows from shopify update CSV with full details."""
    shopify_rows = defaultdict(list)
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            handle = row.get('Handle', '').strip()
            title = row.get('Title', '').strip()
            option1 = row.get('Option1 Value', '').strip()
            option2 = row.get('Option2 Value', '').strip()
            option3 = row.get('Option3 Value', '').strip()
            variant_sku = row.get('Variant SKU', '').strip()
            
            # Create unique key for this variant
            key = f"{handle}|{option1}|{option2}|{option3}"
            shopify_rows[key].append({
                'row_number': i + 2,  # +2 for header and 0-indexing
                'handle': handle,
                'title': title,
                'option1': option1,
                'option2': option2,
                'option3': option3,
                'variant_sku': variant_sku
            })
    
    return shopify_rows


def analyze_shopify_extra_rows(mapped_output_file: str, shopify_update_file: str):
    """Analyze extra rows in shopify update CSV."""
    print("=== ANALYZING SHOPIFY UPDATE CSV EXTRA ROWS ===\n")
    
    # Load data
    print("Loading mapped_output.csv rows...")
    mapped_keys = load_mapped_output_handles(mapped_output_file)
    print(f"Found {len(mapped_keys)} unique rows in mapped_output.csv")
    
    print("Loading shopify update CSV rows...")
    shopify_rows = load_shopify_update_details(shopify_update_file)
    total_shopify_rows = sum(len(rows) for rows in shopify_rows.values())
    print(f"Found {len(shopify_rows)} unique variants in shopify update CSV")
    print(f"Total rows in shopify update CSV: {total_shopify_rows}")
    
    # Find extra rows
    extra_keys = set(shopify_rows.keys()) - mapped_keys
    print(f"\nExtra unique variants in shopify update: {len(extra_keys)}")
    
    # Find duplicates within shopify update
    duplicate_keys = []
    total_duplicates = 0
    for key, rows in shopify_rows.items():
        if len(rows) > 1:
            duplicate_keys.append(key)
            total_duplicates += len(rows) - 1  # Count extra copies
    
    print(f"Duplicate variants in shopify update: {len(duplicate_keys)}")
    print(f"Total duplicate rows: {total_duplicates}")
    
    # Calculate the difference
    expected_total = len(mapped_keys)
    actual_total = total_shopify_rows
    difference = actual_total - expected_total
    
    print(f"\nRow count analysis:")
    print(f"Expected (mapped_output.csv): {expected_total}")
    print(f"Actual (shopify update CSV): {actual_total}")
    print(f"Difference: +{difference}")
    print(f"Extra unique variants: {len(extra_keys)}")
    print(f"Duplicate rows: {total_duplicates}")
    
    # Show sample extra rows
    if extra_keys:
        print(f"\n=== SAMPLE EXTRA ROWS (NOT IN MAPPED OUTPUT) ===")
        for i, key in enumerate(list(extra_keys)[:5]):
            row_data = shopify_rows[key][0]  # Take first occurrence
            print(f"{i+1}. Row {row_data['row_number']}: {row_data['handle']}")
            print(f"   Title: {row_data['title']}")
            print(f"   Options: {row_data['option1']} | {row_data['option2']} | {row_data['option3']}")
            print(f"   SKU: {row_data['variant_sku']}")
            print()
    
    # Show sample duplicates
    if duplicate_keys:
        print(f"\n=== SAMPLE DUPLICATE ROWS ===")
        for i, key in enumerate(duplicate_keys[:5]):
            rows = shopify_rows[key]
            print(f"{i+1}. Variant appears {len(rows)} times:")
            print(f"   Handle: {rows[0]['handle']}")
            print(f"   Title: {rows[0]['title']}")
            print(f"   Options: {rows[0]['option1']} | {rows[0]['option2']} | {rows[0]['option3']}")
            print(f"   Rows: {', '.join(str(r['row_number']) for r in rows)}")
            print()
    
    # Write reports
    if extra_keys:
        print(f"Writing {len(extra_keys)} extra rows to 'shopify_extra_rows.csv'...")
        with open('shopify_extra_rows.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Row_Number', 'Handle', 'Title', 'Option1', 'Option2', 'Option3', 'Variant_SKU'])
            for key in extra_keys:
                row_data = shopify_rows[key][0]  # Take first occurrence
                writer.writerow([
                    row_data['row_number'],
                    row_data['handle'],
                    row_data['title'],
                    row_data['option1'],
                    row_data['option2'],
                    row_data['option3'],
                    row_data['variant_sku']
                ])
    
    if duplicate_keys:
        print(f"Writing {total_duplicates} duplicate rows to 'shopify_duplicate_rows.csv'...")
        with open('shopify_duplicate_rows.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Row_Number', 'Handle', 'Title', 'Option1', 'Option2', 'Option3', 'Variant_SKU', 'Duplicate_Count'])
            for key in duplicate_keys:
                rows = shopify_rows[key]
                for row_data in rows:
                    writer.writerow([
                        row_data['row_number'],
                        row_data['handle'],
                        row_data['title'],
                        row_data['option1'],
                        row_data['option2'],
                        row_data['option3'],
                        row_data['variant_sku'],
                        len(rows)
                    ])
    
    print("✅ Analysis complete!")


if __name__ == "__main__":
    mapped_output_file = "mapped_output.csv"
    shopify_update_file = "mapped_output_shopify_update.csv"
    
    try:
        analyze_shopify_extra_rows(mapped_output_file, shopify_update_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")