#!/usr/bin/env python3
"""
Compare Missing SKU Lists Script
Compares the differences between missing_skus.csv and missing_shopify_update_skus.csv.
"""

import csv
from typing import Set, Dict, List


def load_missing_skus_from_csv(filename: str) -> Set[str]:
    """Load SKUs from a missing SKUs CSV file."""
    skus = set()
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sku = row.get('SKU', '').strip()
                if sku:
                    skus.add(sku)
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
        return set()
    
    return skus


def load_missing_skus_with_details(filename: str) -> Dict[str, Dict[str, str]]:
    """Load SKUs with details from a missing SKUs CSV file."""
    skus = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sku = row.get('SKU', '').strip()
                if sku:
                    skus[sku] = {
                        'name': row.get('Product_Name', '').strip(),
                        'barcode': row.get('Barcode', '').strip()
                    }
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
        return {}
    
    return skus


def compare_missing_sku_lists():
    """Compare the two missing SKU lists and analyze differences."""
    print("=== COMPARING MISSING SKU LISTS ===\n")
    
    # Load both missing SKU lists
    print("Loading missing_skus.csv...")
    missing_skus_1 = load_missing_skus_from_csv('missing_skus.csv')
    print(f"Found {len(missing_skus_1)} SKUs in missing_skus.csv")
    
    print("Loading missing_shopify_update_skus.csv...")
    missing_skus_2 = load_missing_skus_from_csv('missing_shopify_update_skus.csv')
    print(f"Found {len(missing_skus_2)} SKUs in missing_shopify_update_skus.csv")
    
    if not missing_skus_1 or not missing_skus_2:
        print("Error: Could not load one or both files")
        return
    
    # Find differences
    only_in_first = missing_skus_1 - missing_skus_2  # In missing_skus.csv but not in shopify
    only_in_second = missing_skus_2 - missing_skus_1  # In shopify but not in missing_skus.csv
    common_skus = missing_skus_1 & missing_skus_2  # In both lists
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"SKUs in both lists: {len(common_skus)}")
    print(f"SKUs only in missing_skus.csv: {len(only_in_first)}")
    print(f"SKUs only in missing_shopify_update_skus.csv: {len(only_in_second)}")
    print(f"Total unique missing SKUs: {len(missing_skus_1 | missing_skus_2)}")
    
    # Load details for analysis
    details_1 = load_missing_skus_with_details('missing_skus.csv')
    details_2 = load_missing_skus_with_details('missing_shopify_update_skus.csv')
    
    # Show samples of differences
    if only_in_first:
        print(f"\n=== SAMPLE SKUs ONLY IN missing_skus.csv (not in Shopify update) ===")
        print("These SKUs are missing from product_variants.csv but present in Shopify update:")
        for i, sku in enumerate(list(only_in_first)[:10]):
            if sku in details_1:
                print(f"{i+1:2d}. {sku} - {details_1[sku]['name']}")
        
        if len(only_in_first) > 10:
            print(f"... and {len(only_in_first) - 10} more")
    
    if only_in_second:
        print(f"\n=== SAMPLE SKUs ONLY IN missing_shopify_update_skus.csv (not in product variants) ===")
        print("These SKUs are missing from Shopify update but present in product_variants.csv:")
        for i, sku in enumerate(list(only_in_second)[:10]):
            if sku in details_2:
                print(f"{i+1:2d}. {sku} - {details_2[sku]['name']}")
        
        if len(only_in_second) > 10:
            print(f"... and {len(only_in_second) - 10} more")
    
    # Write detailed comparison reports
    if only_in_first:
        print(f"\nWriting {len(only_in_first)} SKUs to 'skus_only_missing_from_product_variants.csv'...")
        with open('skus_only_missing_from_product_variants.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Product_Name', 'Barcode', 'Status'])
            for sku in sorted(only_in_first):
                if sku in details_1:
                    writer.writerow([sku, details_1[sku]['name'], details_1[sku]['barcode'], 
                                   'Missing from product_variants.csv but present in Shopify update'])
    
    if only_in_second:
        print(f"Writing {len(only_in_second)} SKUs to 'skus_only_missing_from_shopify_update.csv'...")
        with open('skus_only_missing_from_shopify_update.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Product_Name', 'Barcode', 'Status'])
            for sku in sorted(only_in_second):
                if sku in details_2:
                    writer.writerow([sku, details_2[sku]['name'], details_2[sku]['barcode'], 
                                   'Missing from Shopify update but present in product_variants.csv'])
    
    if common_skus:
        print(f"Writing {len(common_skus)} common SKUs to 'skus_missing_from_both.csv'...")
        with open('skus_missing_from_both.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Product_Name', 'Barcode', 'Status'])
            for sku in sorted(common_skus):
                if sku in details_1:
                    writer.writerow([sku, details_1[sku]['name'], details_1[sku]['barcode'], 
                                   'Missing from both product_variants.csv and Shopify update'])
    
    print("✅ Comparison complete!")
    
    # Summary explanation
    print(f"\n=== SUMMARY EXPLANATION ===")
    print("missing_skus.csv: SKUs from Sheet1 not found in product_variants.csv (Odoo format)")
    print("missing_shopify_update_skus.csv: SKUs from Sheet1 not found in Shopify update CSV")
    print()
    print("The difference suggests:")
    if len(only_in_first) > 0:
        print(f"• {len(only_in_first)} SKUs are in Shopify update but not in product_variants.csv")
    if len(only_in_second) > 0:
        print(f"• {len(only_in_second)} SKUs are in product_variants.csv but not in Shopify update")
    if len(common_skus) > 0:
        print(f"• {len(common_skus)} SKUs are missing from both outputs")


if __name__ == "__main__":
    try:
        compare_missing_sku_lists()
    except Exception as e:
        print(f"Error: {e}")