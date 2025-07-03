#!/usr/bin/env python3
"""
Find Missing Shopify Rows Script
Identifies rows from mapped_output.csv that are not present in mapped_output_shopify_update.csv.
"""

import csv
from typing import Set, Dict, List


def load_mapped_output_handles(filename: str) -> Dict[str, Dict[str, str]]:
    """Load all handle+variant combinations from mapped_output.csv."""
    mapped_rows = {}
    
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
            mapped_rows[key] = {
                'row_number': i + 2,  # +2 for header and 0-indexing
                'handle': handle,
                'title': title,
                'option1': option1,
                'option2': option2,
                'option3': option3,
                'variant_sku': variant_sku
            }
    
    return mapped_rows


def load_shopify_update_handles(filename: str) -> Set[str]:
    """Load all handle+variant combinations from shopify update CSV."""
    shopify_keys = set()
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            handle = row.get('Handle', '').strip()
            option1 = row.get('Option1 Value', '').strip()
            option2 = row.get('Option2 Value', '').strip()
            option3 = row.get('Option3 Value', '').strip()
            
            # Create unique key for this variant
            key = f"{handle}|{option1}|{option2}|{option3}"
            shopify_keys.add(key)
    
    return shopify_keys


def find_missing_shopify_rows(mapped_output_file: str, shopify_update_file: str):
    """Find rows that are in mapped_output.csv but missing from shopify update CSV."""
    print("=== FINDING MISSING SHOPIFY UPDATE ROWS ===\n")
    
    # Load data
    print("Loading mapped_output.csv rows...")
    mapped_rows = load_mapped_output_handles(mapped_output_file)
    print(f"Found {len(mapped_rows)} rows in mapped_output.csv")
    
    print("Loading shopify update CSV rows...")
    shopify_keys = load_shopify_update_handles(shopify_update_file)
    print(f"Found {len(shopify_keys)} rows in shopify update CSV")
    
    # Find missing rows
    missing_keys = set(mapped_rows.keys()) - shopify_keys
    print(f"\nMissing rows: {len(missing_keys)}")
    print(f"Coverage: {len(shopify_keys)}/{len(mapped_rows)} ({len(shopify_keys)/len(mapped_rows)*100:.1f}%)")
    
    if missing_keys:
        print(f"\n=== MISSING SHOPIFY UPDATE ROWS ANALYSIS ===")
        
        # Create detailed report
        missing_details = []
        for key in missing_keys:
            if key in mapped_rows:
                row_data = mapped_rows[key]
                missing_details.append({
                    'row_number': row_data['row_number'],
                    'handle': row_data['handle'],
                    'title': row_data['title'],
                    'option1': row_data['option1'],
                    'option2': row_data['option2'],
                    'option3': row_data['option3'],
                    'variant_sku': row_data['variant_sku']
                })
        
        # Sort by row number for consistent output
        missing_details.sort(key=lambda x: x['row_number'])
        
        # Show first 10 missing rows
        print("First 10 missing rows:")
        for i, detail in enumerate(missing_details[:10]):
            print(f"{i+1:2d}. Row {detail['row_number']}: {detail['handle']}")
            print(f"    Title: {detail['title']}")
            print(f"    Options: {detail['option1']} | {detail['option2']} | {detail['option3']}")
            print(f"    SKU: {detail['variant_sku']}")
            print()
        
        if len(missing_details) > 10:
            print(f"... and {len(missing_details) - 10} more")
        
        # Analyze patterns in missing rows
        print("\n=== MISSING ROWS PATTERNS ===")
        
        # Count by handle
        handle_counts = {}
        sku_counts = {'with_sku': 0, 'without_sku': 0}
        
        for detail in missing_details:
            handle = detail['handle']
            handle_counts[handle] = handle_counts.get(handle, 0) + 1
            
            if detail['variant_sku']:
                sku_counts['with_sku'] += 1
            else:
                sku_counts['without_sku'] += 1
        
        print(f"Rows with SKU: {sku_counts['with_sku']}")
        print(f"Rows without SKU: {sku_counts['without_sku']}")
        
        # Top handles with missing rows
        sorted_handles = sorted(handle_counts.items(), key=lambda x: x[1], reverse=True)
        print(f"\nTop 10 handles with missing rows:")
        for i, (handle, count) in enumerate(sorted_handles[:10]):
            print(f"{i+1:2d}. {handle}: {count} missing rows")
        
        # Write detailed report to CSV
        print(f"\nWriting {len(missing_details)} missing rows to 'missing_shopify_rows.csv'...")
        with open('missing_shopify_rows.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Row_Number', 'Handle', 'Title', 'Option1', 'Option2', 'Option3', 'Variant_SKU'])
            for detail in missing_details:
                writer.writerow([
                    detail['row_number'],
                    detail['handle'],
                    detail['title'],
                    detail['option1'],
                    detail['option2'],
                    detail['option3'],
                    detail['variant_sku']
                ])
        
        print("✅ Report saved to 'missing_shopify_rows.csv'")
    else:
        print("\n🎉 No missing rows found! All mapped_output.csv rows are present in shopify update CSV")


if __name__ == "__main__":
    mapped_output_file = "mapped_output.csv"
    shopify_update_file = "mapped_output_shopify_update.csv"
    
    try:
        find_missing_shopify_rows(mapped_output_file, shopify_update_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")