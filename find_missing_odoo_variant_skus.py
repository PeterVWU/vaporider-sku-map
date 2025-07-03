#!/usr/bin/env python3
"""
Find Missing Odoo Variant SKUs Script
Identifies SKUs from Sheet1 that are not present in mapped_output_odoo_variant_update.csv.
"""

import csv
from typing import Set, Dict, List


def load_sheet1_skus(filename: str) -> Dict[str, Dict[str, str]]:
    """Load all SKUs from Sheet1 with their product details."""
    sheet1_skus = {}
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sku = row.get('Internal Reference', '').strip()
            if sku:
                sheet1_skus[sku] = {
                    'name': row.get('Name', '').strip(),
                    'barcode': row.get('Barcode', '').strip()
                }
    
    return sheet1_skus


def load_odoo_variant_skus(filename: str) -> Set[str]:
    """Load all SKUs from odoo variant update CSV."""
    variant_skus = set()
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Try different possible column names for SKUs
            sku = row.get('default_code', '').strip() or row.get('Variant SKU', '').strip()
            if sku:
                variant_skus.add(sku)
    
    return variant_skus


def find_missing_odoo_variant_skus(sheet1_file: str, odoo_variant_file: str):
    """Find SKUs that are in Sheet1 but missing from shopify update CSV."""
    print("=== FINDING MISSING SHOPIFY UPDATE SKUs ===\n")
    
    # Load data
    print("Loading Sheet1 SKUs...")
    sheet1_skus = load_sheet1_skus(sheet1_file)
    print(f"Found {len(sheet1_skus)} SKUs in Sheet1")
    
    print("Loading shopify update CSV SKUs...")
    variant_skus = load_odoo_variant_skus(odoo_variant_file)
    print(f"Found {len(variant_skus)} SKUs in shopify update CSV")
    
    # Find missing SKUs
    missing_skus = set(sheet1_skus.keys()) - variant_skus
    print(f"\nMissing SKUs: {len(missing_skus)}")
    print(f"Coverage: {len(variant_skus)}/{len(sheet1_skus)} ({len(variant_skus)/len(sheet1_skus)*100:.1f}%)")
    
    if missing_skus:
        print(f"\n=== MISSING SHOPIFY UPDATE SKUs ANALYSIS ===")
        
        # Create detailed report
        missing_details = []
        for sku in missing_skus:
            if sku in sheet1_skus:
                missing_details.append({
                    'sku': sku,
                    'name': sheet1_skus[sku]['name'],
                    'barcode': sheet1_skus[sku]['barcode']
                })
        
        # Sort by SKU for consistent output
        missing_details.sort(key=lambda x: x['sku'])
        
        # Show first 10 missing SKUs
        print("First 10 missing SKUs:")
        for i, detail in enumerate(missing_details[:10]):
            print(f"{i+1:2d}. {detail['sku']} - {detail['name']}")
        
        if len(missing_details) > 10:
            print(f"... and {len(missing_details) - 10} more")
        
        # Write detailed report to CSV
        print(f"\nWriting {len(missing_details)} missing SKUs to 'missing_shopify_update_skus.csv'...")
        with open('missing_shopify_update_skus.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU', 'Product_Name', 'Barcode'])
            for detail in missing_details:
                writer.writerow([detail['sku'], detail['name'], detail['barcode']])
        
        print("✅ Report saved to 'missing_shopify_update_skus.csv'")
    else:
        print("\n🎉 No missing SKUs found! All Sheet1 SKUs are present in shopify update CSV")


if __name__ == "__main__":
    sheet1_file = "sheet1.csv"
    odoo_variant_file = "mapped_output_shopify_update.csv"
    
    try:
        find_missing_odoo_variant_skus(sheet1_file, odoo_variant_file)
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error: {e}")