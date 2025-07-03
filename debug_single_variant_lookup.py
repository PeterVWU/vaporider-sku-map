#!/usr/bin/env python3
"""
Debug Single Variant Lookup Script
Traces the exact lookup process for single variant products to identify why they're failing.
"""

import csv
import re
from typing import Dict, List


def load_odoo_variant_export_debug(filename: str) -> dict:
    """Load Odoo variant export with debug info - handles multi-row format."""
    variant_lookup = {}
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        current_variant = None
        
        for i, row in enumerate(reader):
            variant_id = row.get('External ID', '').strip()
            template_name = row.get('Name', '').strip()
            variant_values = row.get('Variant Values', '').strip()
            
            # Check if this is a new variant (has ID and name) or continuation row
            if variant_id and template_name:
                # New variant - save previous if exists
                if current_variant:
                    _save_variant_to_lookup_debug(current_variant, variant_lookup)
                
                # Start new variant
                current_variant = {
                    'id': variant_id,
                    'template_name': template_name,
                    'variant_values': [variant_values] if variant_values else [],
                    'row_number': i + 2
                }
            elif variant_values and current_variant:
                # Continuation row - add attribute to current variant
                current_variant['variant_values'].append(variant_values)
        
        # Don't forget the last variant
        if current_variant:
            _save_variant_to_lookup_debug(current_variant, variant_lookup)
    
    return variant_lookup


def _save_variant_to_lookup_debug(variant_data: dict, variant_lookup: dict):
    """Helper function to save a variant to the lookup dictionary with debug info."""
    template_name = variant_data['template_name']
    variant_values_list = variant_data['variant_values']
    
    # Combine all variant values into a single string
    combined_variant_values = ", ".join(variant_values_list) if variant_values_list else ""
    
    # Create lookup key: template_name + combined variant values
    lookup_key = f"{template_name}|{combined_variant_values}" if combined_variant_values else template_name
    
    variant_lookup[lookup_key] = {
        'id': variant_data['id'],
        'template_name': template_name,
        'variant_values': combined_variant_values,
        'row_number': variant_data['row_number']
    }
    
    # Debug multi-attribute products specifically
    if len(variant_values_list) > 1:
        print(f"Multi-attribute variant found: '{template_name}' with {len(variant_values_list)} attributes")
        print(f"  Combined values: '{combined_variant_values}'")
        print(f"  Lookup key: '{lookup_key}'")
    elif not combined_variant_values:
        print(f"Single variant found: '{template_name}' -> key: '{lookup_key}'")


def find_single_variant_in_mapped_output():
    """Find single variant products in the mapped output to understand their structure."""
    print("=== SEARCHING FOR SINGLE VARIANT PRODUCTS IN MAPPED OUTPUT ===\n")
    
    target_template = "LOOPER HHC- P Live Resin 2G Cartridge"
    
    with open('mapped_output.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            title = row.get('Title', '').strip()
            
            if target_template in title:
                print(f"Found in mapped_output.csv at row {i+2}:")
                print(f"  Title: '{title}'")
                print(f"  Handle: '{row.get('Handle', '').strip()}'")
                print(f"  Option1: '{row.get('Option1 Value', '').strip()}'")
                print(f"  Option2: '{row.get('Option2 Value', '').strip()}'")
                print(f"  Option3: '{row.get('Option3 Value', '').strip()}'")
                print(f"  SKU: '{row.get('Variant SKU', '').strip()}'")
                print()


def simulate_variant_generation():
    """Simulate the variant generation process for the target product."""
    print("=== SIMULATING VARIANT GENERATION PROCESS ===\n")
    
    # Load the export lookup
    print("Loading Odoo variant export...")
    odoo_variant_lookup = load_odoo_variant_export_debug("odoo_variant_export.csv")
    
    # Simulate what happens during variant generation
    target_template = "LOOPER HHC- P Live Resin 2G Cartridge"
    
    # This simulates what would be generated for this product (it has Option1 value)
    template_name = target_template
    # Simulate building variant_values_str from Option1: "Slurricane - Indica"
    variant_values_str = "Flavor: Slurricane - Indica"
    
    print(f"Generated data:")
    print(f"  template_name: '{template_name}'")
    print(f"  variant_values_str: '{variant_values_str}'")
    print(f"  is_single_variant: {not variant_values_str}")
    
    # Test our enhanced lookup logic
    variant_id = None
    
    # Strategy 1: Try full template + variant values lookup
    print(f"\n=== STRATEGY 1: Full template + variant values ===")
    if variant_values_str:
        lookup_key = f"{template_name}|{variant_values_str}"
        print(f"  lookup_key: '{lookup_key}'")
        if lookup_key in odoo_variant_lookup:
            variant_id = odoo_variant_lookup[lookup_key]['id']
            print(f"✅ Strategy 1 SUCCESS! Variant ID: {variant_id}")
        else:
            print(f"❌ Strategy 1 failed.")
    
    # Strategy 2: If no match yet, try template-only (for single-variant exports)
    if not variant_id:
        print(f"\n=== STRATEGY 2: Template-only (single-variant export) ===")
        lookup_key = template_name
        print(f"  lookup_key: '{lookup_key}'")
        if lookup_key in odoo_variant_lookup:
            variant_id = odoo_variant_lookup[lookup_key]['id']
            print(f"✅ Strategy 2 SUCCESS! Variant ID: {variant_id}")
        else:
            print(f"❌ Strategy 2 failed.")
        
        # Check what keys exist that might be similar
        print(f"\nLooking for similar keys in export...")
        matching_templates = []
        for key, variant in odoo_variant_lookup.items():
            if variant['template_name'] == template_name:
                matching_templates.append({
                    'key': key,
                    'template_name': variant['template_name'],
                    'variant_values': variant['variant_values'],
                    'id': variant['id']
                })
        
        if matching_templates:
            print(f"Found {len(matching_templates)} variants with matching template name:")
            for match in matching_templates:
                print(f"  Key: '{match['key']}'")
                print(f"  Template: '{match['template_name']}'")
                print(f"  Values: '{match['variant_values']}'")
                print(f"  ID: '{match['id']}'")
                print()
        else:
            print(f"No variants found with template name: '{template_name}'")
        
        # Try alternative matching
        print(f"Trying alternative matching...")
        for odoo_key, odoo_variant in odoo_variant_lookup.items():
            if odoo_variant['template_name'] == template_name:
                # For single variants, match if both have empty variant values
                if not variant_values_str and not odoo_variant['variant_values']:
                    variant_id = odoo_variant['id']
                    print(f"✅ Alternative match found! Key: '{odoo_key}', ID: {variant_id}")
                    break
    
    if not variant_id:
        print(f"❌ No variant ID found for '{template_name}'")


if __name__ == "__main__":
    try:
        find_single_variant_in_mapped_output()
        simulate_variant_generation()
    except Exception as e:
        print(f"Error: {e}")