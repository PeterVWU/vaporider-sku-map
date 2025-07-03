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
    normalized = re.sub(r'(\d+)puffs?', r'\1', normalized)  # Remove "puff/puffs" only after numbers
    return normalized


def normalize_attribute_name(attr_name: str) -> str:
    """Normalize attribute names to clean up duplicates and variations."""
    # Attribute mapping dictionary to consolidate similar attributes
    attribute_mapping = {
        # === FLAVOR VARIANTS ===
        "Flavor": "Flavor",
        "Flavor 1": "Flavor", 
        "Flavor 2": "Flavor",
        "Flavors": "Flavor",
        "flavor": "Flavor",
        
        # === COIL TYPE VARIANTS ===
        "Coil Type": "Coil Type",
        "Coil-type": "Coil Type",
        
        # === COMPOUND COIL + COLOR ===
        "Coil Type | Color": "Coil Type | Color",
        "Color & Coil Type": "Coil Type | Color",
        
        # === COMPOUND FLAVOR + NICOTINE ===
        "Flavor | Nicotine Level": "Flavor | Nicotine Level",
        "Flavor | Nicotine  Level": "Flavor | Nicotine Level",  # Extra space
        "Flavor | Nicotine level": "Flavor | Nicotine Level",   # Case
        "Flavor | Strength": "Flavor | Nicotine Level",
        
        # === NICOTINE VARIANTS ===
        "Nicotine Level": "Nicotine Level",
        "Nicotine Strength": "Nicotine Level",
        "Strength": "Nicotine Level",
        
        # === TYPE VARIANTS ===
        "Type": "Type",
        "type": "Type",
        
        # === SINGLE ATTRIBUTES (no changes) ===
        "Addon Options": "Addon Options",
        "Amount": "Amount", 
        "Color": "Color",
        "Device Options": "Device Options",
        "Edition": "Edition",
        "Option": "Option",
        "Quantity": "Quantity", 
        "Resistance": "Resistance",
        "Size": "Size",
        "Strain": "Strain",
        "Text Color": "Text Color"
    }
    
    return attribute_mapping.get(attr_name, attr_name)  # Return normalized name or original if not found


def load_odoo_attribute_mappings(filename: str) -> tuple:
    """Load Odoo attribute export and create name-to-ID mappings."""
    attribute_name_to_id = {}
    attribute_value_name_to_id = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            current_attribute_name = None
            current_attribute_id = None
            
            for row in reader:
                attr_id = row.get('id', '').strip()
                attr_name = row.get('name', '').strip()
                value_id = row.get('value_ids/id', '').strip()
                value_name = row.get('value_ids/name', '').strip()
                
                # New attribute (has ID and name)
                if attr_id and attr_name:
                    current_attribute_name = attr_name
                    current_attribute_id = attr_id
                    attribute_name_to_id[attr_name] = attr_id
                
                # Attribute value (has value ID and name)
                if value_id and value_name and current_attribute_name:
                    # Store value with attribute context to handle duplicates
                    key = f"{current_attribute_name}:{value_name}"
                    attribute_value_name_to_id[key] = value_id
                    
        print(f"Loaded {len(attribute_name_to_id)} attributes and {len(attribute_value_name_to_id)} attribute values from Odoo export")
        return attribute_name_to_id, attribute_value_name_to_id
        
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using name-based format instead of IDs.")
        return {}, {}


def load_odoo_variant_export(filename: str) -> dict:
    """Load Odoo variant export and create lookup by template name + variant values.
    Handles multi-row format where additional attributes appear in subsequent rows.
    """
    variant_lookup = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            current_variant = None
            
            for row in reader:
                variant_id = row.get('External ID', '').strip()
                template_name = row.get('Name', '').strip()
                variant_values = row.get('Variant Values', '').strip()
                
                # Check if this is a new variant (has ID and name) or continuation row
                if variant_id and template_name:
                    # New variant - save previous if exists
                    if current_variant:
                        _save_variant_to_lookup(current_variant, variant_lookup)
                    
                    # Start new variant
                    current_variant = {
                        'id': variant_id,
                        'template_name': template_name,
                        'variant_values': [variant_values] if variant_values else []
                    }
                elif variant_values and current_variant:
                    # Continuation row - add attribute to current variant
                    current_variant['variant_values'].append(variant_values)
            
            # Don't forget the last variant
            if current_variant:
                _save_variant_to_lookup(current_variant, variant_lookup)
                    
        print(f"Loaded {len(variant_lookup)} variant records from Odoo export")
        return variant_lookup
        
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Will use template reference format instead of variant IDs.")
        return {}


def _save_variant_to_lookup(variant_data: dict, variant_lookup: dict):
    """Helper function to save a variant to the lookup dictionary."""
    template_name = variant_data['template_name']
    variant_values_list = variant_data['variant_values']
    
    # Combine all variant values into a single string
    combined_variant_values = ", ".join(variant_values_list) if variant_values_list else ""
    
    # Create lookup key: template_name + combined variant values
    lookup_key = f"{template_name}|{combined_variant_values}" if combined_variant_values else template_name
    
    variant_lookup[lookup_key] = {
        'id': variant_data['id'],
        'template_name': template_name,
        'variant_values': combined_variant_values
    }


def build_option_suffix(row: Dict[str, str]) -> str:
    """Build suffix from option values if they exist."""
    options = []
    for i in range(1, 4):  # Option1, Option2, Option3
        option_name_key = f'Option{i} Name'
        option_value_key = f'Option{i} Value'
        
        if option_value_key in row and row[option_value_key].strip():
            option_name = row.get(option_name_key, '').strip()
            option_value = row[option_value_key].strip()
            
            # Skip "Default Title" when Option Name is "Title"
            if option_name == 'Title' and option_value == 'Default Title':
                continue
                
            options.append(option_value)
    
    return f"-{'-'.join(options)}" if options else ""


def load_sheet1(filename: str) -> tuple:
    """Load Sheet1 data and create lookup dictionaries."""
    sheet1_data = {}
    sheet1_normalized = {}
    sheet1_full_data = {}  # Store complete row data
    sku_tracker = {}  # Track SKUs for duplicate detection
    duplicate_skus = []  # Store duplicate SKU information
    
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
            name = row.get('Name', '').strip()
            sku = row.get('Internal Reference', '').strip()
            
            if name:
                # Track SKU duplicates
                if sku:
                    if sku in sku_tracker:
                        # Mark both original and current as duplicates
                        duplicate_skus.append({
                            'sku': sku,
                            'name': sku_tracker[sku]['name'],
                            'row': sku_tracker[sku]['row'],
                            'duplicate_of': 'First occurrence'
                        })
                        duplicate_skus.append({
                            'sku': sku,
                            'name': name,
                            'row': row_num,
                            'duplicate_of': f"Duplicate of row {sku_tracker[sku]['row']}"
                        })
                    else:
                        sku_tracker[sku] = {'name': name, 'row': row_num}
                
                # Store by exact name
                sheet1_data[name] = {
                    'internal_reference': sku,
                    'barcode': row.get('Barcode', '')
                }
                
                # Store complete row data for output
                sheet1_full_data[name] = row
                
                # Store by normalized name
                normalized_name = normalize_string(name)
                sheet1_normalized[normalized_name] = sheet1_data[name]
    
    return sheet1_data, sheet1_normalized, sheet1_full_data, duplicate_skus


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
               sheet1_normalized: Dict[str, Dict[str, str]]) -> Optional[tuple]:
    """Find matching record from Sheet1 using both strategies."""
    
    # Strategy 1: Direct title + options match
    title = row.get('Title', '').strip()
    if title:
        option_suffix = build_option_suffix(row)
        
        # Try format 1: "Product-Option" (dash without spaces)
        direct_match_name = f"{title}{option_suffix}"
        if direct_match_name in sheet1_data:
            return sheet1_data[direct_match_name], direct_match_name
        
        # Try format 2: "Product - Option" (space-dash-space)
        if option_suffix:
            spaced_option_suffix = option_suffix.replace('-', ' - ')
            direct_match_name_spaced = f"{title}{spaced_option_suffix}"
            if direct_match_name_spaced in sheet1_data:
                return sheet1_data[direct_match_name_spaced], direct_match_name_spaced
        
        # Try format 3: "Puffs-aware" matching - remove " Puffs" from title and normalize dashes
        if option_suffix and " Puffs" in title:
            title_without_puffs = title.replace(" Puffs", "")
            # Normalize en-dash (–) to regular dash (-) for better matching
            title_without_puffs = title_without_puffs.replace("–", "-")
            
            # Try without puffs: "Product-Option"
            puffs_match_name = f"{title_without_puffs}{option_suffix}"
            if puffs_match_name in sheet1_data:
                return sheet1_data[puffs_match_name], puffs_match_name
            
            # Try without puffs: "Product - Option"
            spaced_option_suffix = option_suffix.replace('-', ' - ')
            puffs_match_name_spaced = f"{title_without_puffs}{spaced_option_suffix}"
            if puffs_match_name_spaced in sheet1_data:
                return sheet1_data[puffs_match_name_spaced], puffs_match_name_spaced
    
    # Strategy 2: Normalized handle + options match
    handle = row.get('Handle', '').strip()
    if handle:
        option_suffix = build_option_suffix(row)
        handle_with_spaces = handle.replace('-', ' ')
        handle_match_name = f"{handle_with_spaces}{option_suffix}"
        normalized_handle_name = normalize_string(handle_match_name)
        
        if normalized_handle_name in sheet1_normalized:
            # Find the original name that matches this normalized version
            for original_name, data in sheet1_data.items():
                if normalize_string(original_name) == normalized_handle_name:
                    return sheet1_normalized[normalized_handle_name], original_name
    
    return None


def process_csv_mapping(sheet1_file: str, sheet2_file: str, output_file: str):
    """Main processing function."""
    print("Loading Sheet1 data...")
    sheet1_data, sheet1_normalized, sheet1_full_data, duplicate_skus = load_sheet1(sheet1_file)
    print(f"Loaded {len(sheet1_data)} records from Sheet1")
    
    # Load Odoo attribute mappings if available
    print("Loading Odoo attribute ID mappings...")
    attribute_name_to_id, attribute_value_name_to_id = load_odoo_attribute_mappings("odoo_attribute_export.csv")
    
    # Load Odoo variant export for variant update CSV
    print("Loading Odoo variant export...")
    odoo_variant_lookup = load_odoo_variant_export("odoo_variant_export.csv")
    
    # Report duplicate SKUs
    if duplicate_skus:
        print(f"⚠️  Found {len(duplicate_skus)} duplicate SKU entries in Sheet1")
    else:
        print("✅ No duplicate SKUs found in Sheet1")
    
    print("Loading Sheet2 data...")
    sheet2_data = []
    with open(sheet2_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        sheet2_fieldnames = reader.fieldnames
        for row in reader:
            sheet2_data.append(row)
    
    print(f"Loaded {len(sheet2_data)} records from Sheet2")
    
    print("Filling missing titles...")
    sheet2_data = fill_missing_titles(sheet2_data)
    
    print("Processing matches and updating data...")
    matches_found = 0
    matched_sheet2_rows = []
    matched_sheet1_names = set()  # Track which Sheet1 products were matched
    
    for row in sheet2_data:
        match_result = find_match(row, sheet1_data, sheet1_normalized)
        
        if match_result:
            match_data, matched_name = match_result
            matches_found += 1
            row['Variant SKU'] = match_data['internal_reference']
            row['Variant Barcode'] = match_data['barcode']
            matched_sheet2_rows.append(row)
            matched_sheet1_names.add(matched_name)
            # print(f"Match found: {row.get('Title', row.get('Handle', ''))} -> SKU: {match_data['internal_reference']}")
    
    print(f"Found {matches_found} matches out of {len(sheet2_data)} records")
    print(f"Sheet2 output will contain {len(matched_sheet2_rows)} rows (only matched products)")
    
    # Write Sheet2 format output (existing functionality)
    print(f"Writing Sheet2 format output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=sheet2_fieldnames)
        writer.writeheader()
        writer.writerows(matched_sheet2_rows)
    
    # Write Odoo files in proper import sequence (4 separate files)
    odoo_base_name = output_file.replace('.csv', '_odoo')
    print(f"Writing Odoo import files in sequence...")
    
    # Collect all attributes and values from matched products
    all_attributes = {}  # {attr_name: set_of_values}
    all_templates = {}   # {handle: template_info}
    all_variants = []    # List of variant info
    
    # Analyze all matched products to collect attributes, values, templates, and variants
    matched_lookup = {}
    for row in matched_sheet2_rows:
        handle = row.get('Handle', '').strip()
        option1 = row.get('Option1 Value', '').strip()
        option2 = row.get('Option2 Value', '').strip()
        option3 = row.get('Option3 Value', '').strip()
        key = f"{handle}|{option1}|{option2}|{option3}"
        
        # Enhanced row data with Sheet1 data
        enhanced_row = row.copy()
        variant_sku = row.get('Variant SKU', '').strip()
        if variant_sku:
            for sheet1_name, sheet1_row in sheet1_full_data.items():
                if sheet1_row.get('Internal Reference', '').strip() == variant_sku:
                    enhanced_row['Sheet1_Data'] = sheet1_row
                    break
        
        matched_lookup[key] = enhanced_row
    
    # Find all handles that have at least one match
    matched_handles = set()
    for row in matched_sheet2_rows:
        handle = row.get('Handle', '').strip()
        if handle:
            matched_handles.add(handle)
    
    # Group by handle using ALL Sheet2 data
    templates = {}
    for row in sheet2_data:
        handle = row.get('Handle', '').strip()
        if handle in matched_handles:
            if handle not in templates:
                templates[handle] = []
            templates[handle].append(row)
    
    # Process each template to collect data for the 4 CSV files
    for handle, variants in templates.items():
        # Get template name from first variant with a title
        template_name = ''
        for variant in variants:
            title = variant.get('Title', '').strip()
            if title:
                template_name = title
                break
        
        if not template_name:
            continue
        
        # Find Sheet1 data for this template
        template_sheet1_data = None
        for variant in variants:
            option1 = variant.get('Option1 Value', '').strip()
            option2 = variant.get('Option2 Value', '').strip()
            option3 = variant.get('Option3 Value', '').strip()
            key = f"{handle}|{option1}|{option2}|{option3}"
            
            if key in matched_lookup and 'Sheet1_Data' in matched_lookup[key]:
                template_sheet1_data = matched_lookup[key]['Sheet1_Data']
                break
        
        # Determine attributes used by this product
        attributes_used = set()
        option_positions = {}
        for variant in variants:
            for i in range(1, 4):
                attr_name = variant.get(f'Option{i} Name', '').strip()
                if attr_name and attr_name != 'Title':
                    normalized_attr_name = normalize_attribute_name(attr_name)
                    attributes_used.add(normalized_attr_name)
                    option_positions[normalized_attr_name] = i
        
        # Collect attribute values for this product
        template_attr_values = set()
        for variant in variants:
            option1 = variant.get('Option1 Value', '').strip()
            option2 = variant.get('Option2 Value', '').strip()
            option3 = variant.get('Option3 Value', '').strip()
            key = f"{handle}|{option1}|{option2}|{option3}"
            
            if key in matched_lookup:
                for normalized_attr_name in sorted(attributes_used):
                    option_position = option_positions.get(normalized_attr_name)
                    if option_position:
                        option_value = variant.get(f'Option{option_position} Value', '').strip()
                        if option_value:
                            template_attr_values.add((normalized_attr_name, option_value))
        
        # Store attribute data globally
        for attr_name in attributes_used:
            if attr_name not in all_attributes:
                all_attributes[attr_name] = set()
        
        for attr_name, attr_value in template_attr_values:
            all_attributes[attr_name].add(attr_value)
        
        # Store template data
        all_templates[handle] = {
            'name': template_name,
            'categ_id/name': template_sheet1_data.get('Product Category', '') if template_sheet1_data else '',
            'purchase': template_sheet1_data.get('Purchase', 'TRUE') if template_sheet1_data else 'TRUE',
            'sale_ok': template_sheet1_data.get('Sales', 'TRUE') if template_sheet1_data else 'TRUE',
            'type': 'goods',
            'attributes_used': sorted(attributes_used),
            'attribute_values': sorted(list(template_attr_values))
        }
        
        # Store variant data
        for variant in variants:
            option1 = variant.get('Option1 Value', '').strip()
            option2 = variant.get('Option2 Value', '').strip()
            option3 = variant.get('Option3 Value', '').strip()
            key = f"{handle}|{option1}|{option2}|{option3}"
            
            if key in matched_lookup:
                matched_data = matched_lookup[key]
                variant_sheet1_data = matched_data.get('Sheet1_Data')
                
                # Build variant attribute values
                variant_attributes = []
                for normalized_attr_name in sorted(attributes_used):
                    option_position = option_positions.get(normalized_attr_name)
                    if option_position:
                        option_value = variant.get(f'Option{option_position} Value', '').strip()
                        variant_attributes.append((normalized_attr_name, option_value))
                
                all_variants.append({
                    'template_name': template_name,
                    'name': f"{template_name} ({', '.join([val for attr, val in variant_attributes if val])})" if any(val for attr, val in variant_attributes) else template_name,
                    'default_code': matched_data.get('Variant SKU', ''),
                    'barcode': matched_data.get('Variant Barcode', ''),
                    'standard_price': variant_sheet1_data.get('Cost', '') if variant_sheet1_data else '',
                    'list_price': variant_sheet1_data.get('Sales Price', '') if variant_sheet1_data else '',
                    'weight': variant_sheet1_data.get('Weight (lb)', '') if variant_sheet1_data else '',
                    'attribute_values': variant_attributes
                })
    
    # 1. COMBINED ATTRIBUTES & VALUES CSV
    attributes_file = f"{odoo_base_name}_1_attributes_values.csv"
    print(f"Writing Odoo attributes and values to {attributes_file}...")
    with open(attributes_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['value/value', 'attribute', 'display_type', 'create_variant'])
        writer.writeheader()
        
        for attr_name in sorted(all_attributes.keys()):
            attr_values = sorted(all_attributes[attr_name])
            if attr_values:  # Only process attributes that have values
                # First row: attribute definition with first value
                writer.writerow({
                    'value/value': attr_values[0],
                    'attribute': attr_name,
                    'display_type': 'radio',
                    'create_variant': 'instantly'
                })
                
                # Subsequent rows: just the values
                for attr_value in attr_values[1:]:
                    writer.writerow({
                        'value/value': attr_value,
                        'attribute': '',
                        'display_type': '',
                        'create_variant': ''
                    })
    
    total_values = sum(len(values) for values in all_attributes.values())
    print(f"Combined attributes file contains {len(all_attributes)} attributes and {total_values} values")
    
    # 2. PRODUCT TEMPLATES CSV
    templates_file = f"{odoo_base_name}_2_product_templates.csv"
    print(f"Writing Odoo product templates to {templates_file}...")
    
    # Determine fieldnames based on whether we have Odoo ID mappings
    if attribute_name_to_id and attribute_value_name_to_id:
        fieldnames = [
            'name', 'product_category', 'purchase', 'sale_ok', 'type',
            'attribute_line_ids/attribute_id/id', 'attribute_line_ids/value_ids/id'
        ]
        print("Using external ID format for attribute references")
    else:
        fieldnames = [
            'name', 'product_category', 'purchase', 'sale_ok', 'type',
            'product_attributes/attribute', 'product_attributes/values'
        ]
        print("Using name-based format for attribute references")
    
    with open(templates_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for handle, template_data in all_templates.items():
            # Build attribute line data
            if template_data['attributes_used']:
                if attribute_name_to_id and attribute_value_name_to_id:
                    # Use external IDs - multi-row format
                    
                    # Group values by attribute
                    attr_value_groups = {}
                    for attr_name, attr_value in template_data['attribute_values']:
                        if attr_name not in attr_value_groups:
                            attr_value_groups[attr_name] = []
                        attr_value_groups[attr_name].append(attr_value)
                    
                    # Write one row per attribute
                    for attr_index, attr_name in enumerate(sorted(template_data['attributes_used'])):
                        # Get attribute ID
                        attr_id = attribute_name_to_id.get(attr_name, '')
                        if attr_id:
                            # Get value IDs for this attribute
                            value_ids = []
                            if attr_name in attr_value_groups:
                                for attr_value in sorted(attr_value_groups[attr_name]):
                                    value_key = f"{attr_name}:{attr_value}"
                                    value_id = attribute_value_name_to_id.get(value_key, '')
                                    if value_id:
                                        value_ids.append(value_id)
                            
                            value_data = ','.join(value_ids) if value_ids else ''
                            
                            if attr_index == 0:
                                # First row: include all template data + first attribute
                                row_data = {
                                    'name': template_data['name'],
                                    'product_category': template_data['categ_id/name'],
                                    'purchase': template_data['purchase'],
                                    'sale_ok': template_data['sale_ok'],
                                    'type': 'goods',
                                    'attribute_line_ids/attribute_id/id': attr_id,
                                    'attribute_line_ids/value_ids/id': value_data
                                }
                            else:
                                # Subsequent rows: only attribute data, other columns empty
                                row_data = {
                                    'name': '',
                                    'product_category': '',
                                    'purchase': '',
                                    'sale_ok': '',
                                    'type': '',
                                    'attribute_line_ids/attribute_id/id': attr_id,
                                    'attribute_line_ids/value_ids/id': value_data
                                }
                            
                            writer.writerow(row_data)
                else:
                    # Use name-based format (fallback) - single row
                    attr_names = ';'.join(template_data['attributes_used'])
                    # Group values by attribute
                    attr_value_groups = {}
                    for attr_name, attr_value in template_data['attribute_values']:
                        if attr_name not in attr_value_groups:
                            attr_value_groups[attr_name] = []
                        attr_value_groups[attr_name].append(attr_value)
                    
                    # Build value string in same order as attributes
                    value_groups = []
                    for attr_name in template_data['attributes_used']:
                        if attr_name in attr_value_groups:
                            value_groups.append(','.join(sorted(attr_value_groups[attr_name])))
                        else:
                            value_groups.append('')
                    attr_values = ';'.join(value_groups)
                    
                    row_data = {
                        'name': template_data['name'],
                        'product_category': template_data['categ_id/name'],
                        'purchase': template_data['purchase'],
                        'sale_ok': template_data['sale_ok'],
                        'type': 'goods',
                        'product_attributes/attribute': attr_names,
                        'product_attributes/values': attr_values
                    }
                    writer.writerow(row_data)
            else:
                # No attributes - single row
                if attribute_name_to_id and attribute_value_name_to_id:
                    row_data = {
                        'name': template_data['name'],
                        'product_category': template_data['categ_id/name'],
                        'purchase': template_data['purchase'],
                        'sale_ok': template_data['sale_ok'],
                        'type': 'goods',
                        'attribute_line_ids/attribute_id/id': '',
                        'attribute_line_ids/value_ids/id': ''
                    }
                else:
                    row_data = {
                        'name': template_data['name'],
                        'product_category': template_data['categ_id/name'],
                        'purchase': template_data['purchase'],
                        'sale_ok': template_data['sale_ok'],
                        'type': 'goods',
                        'product_attributes/attribute': '',
                        'product_attributes/values': ''
                    }
                writer.writerow(row_data)
    
    print(f"Product templates file contains {len(all_templates)} templates")
    
    # 3. PRODUCT VARIANTS CSV
    variants_file = f"{odoo_base_name}_3_product_variants.csv"
    print(f"Writing Odoo product variants to {variants_file}...")
    
    # Determine fieldnames based on priority: variant IDs > external IDs > names
    if odoo_variant_lookup:
        variants_fieldnames = ['id', 'default_code', 'barcode', 'standard_price', 'list_price', 'weight']
        print("Using variant external ID format for updating existing variants")
    elif attribute_name_to_id and attribute_value_name_to_id:
        variants_fieldnames = [
            'name', 'product_tmpl_id', 'default_code', 'barcode', 'standard_price',
            'attribute_value_ids/id'
        ]
        print("Using external ID format for variant attribute values")
    else:
        variants_fieldnames = [
            'name', 'product_tmpl_id', 'default_code', 'barcode', 'standard_price',
            'attribute_value_ids/name'
        ]
        print("Using name-based format for variant attribute values")
    
    with open(variants_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=variants_fieldnames)
        writer.writeheader()
        for variant_data in all_variants:
            if odoo_variant_lookup:
                # Use variant IDs - match by template name + attribute values
                template_name = variant_data['template_name']
                
                # Build variant values string in Odoo format "Attribute: Value"
                variant_values_parts = []
                for attr_name, attr_value in variant_data['attribute_values']:
                    if attr_value:  # Only include non-empty values
                        variant_values_parts.append(f"{attr_name}: {attr_value}")
                variant_values_str = ", ".join(variant_values_parts) if variant_values_parts else ""
                
                # Try to find matching Odoo variant
                variant_id = None
                
                # Strategy 1: Try full template + variant values lookup
                if variant_values_str:
                    # Multi-variant - match by template name + variant values
                    lookup_key = f"{template_name}|{variant_values_str}"
                    if lookup_key in odoo_variant_lookup:
                        variant_id = odoo_variant_lookup[lookup_key]['id']
                
                # Strategy 2: If no match yet, try template-only (for single-variant exports)
                if not variant_id:
                    lookup_key = template_name
                    if lookup_key in odoo_variant_lookup:
                        variant_id = odoo_variant_lookup[lookup_key]['id']
                
                # Strategy 3: If still no match, try alternative matching with normalization
                if not variant_id:
                    for odoo_key, odoo_variant in odoo_variant_lookup.items():
                        if odoo_variant['template_name'] == template_name:
                            # For products with variant values, try normalized matching
                            if variant_values_str and odoo_variant['variant_values']:
                                odoo_values_normalized = re.sub(r'[,\s]+', '', odoo_variant['variant_values'].lower())
                                our_values_normalized = re.sub(r'[,\s]+', '', variant_values_str.lower())
                                
                                if odoo_values_normalized == our_values_normalized:
                                    variant_id = odoo_variant['id']
                                    break
                            # For template-only matching, check if export has empty variant values
                            elif not odoo_variant['variant_values']:
                                variant_id = odoo_variant['id']
                                break
                    
                    # Strategy 4: Try "Puffs-aware" matching if still no match found
                    if not variant_id and " Puffs" in template_name:
                        # Remove " Puffs" and normalize dashes for better matching
                        puffs_template_name = template_name.replace(" Puffs", "").replace("–", "-")
                        
                        # Strategy 4a: Try full puffs template + variant values lookup
                        if variant_values_str:
                            puffs_lookup_key = f"{puffs_template_name}|{variant_values_str}"
                            if puffs_lookup_key in odoo_variant_lookup:
                                variant_id = odoo_variant_lookup[puffs_lookup_key]['id']
                        
                        # Strategy 4b: If no match yet, try puffs template-only (for single-variant exports)
                        if not variant_id:
                            puffs_lookup_key = puffs_template_name
                            if puffs_lookup_key in odoo_variant_lookup:
                                variant_id = odoo_variant_lookup[puffs_lookup_key]['id']
                        
                        # Strategy 4c: Try alternative matching with puffs-normalized name
                        if not variant_id:
                            for odoo_key, odoo_variant in odoo_variant_lookup.items():
                                if odoo_variant['template_name'] == puffs_template_name:
                                    # For products with variant values, try normalized matching
                                    if variant_values_str and odoo_variant['variant_values']:
                                        odoo_values_normalized = re.sub(r'[,\s]+', '', odoo_variant['variant_values'].lower())
                                        our_values_normalized = re.sub(r'[,\s]+', '', variant_values_str.lower())
                                        
                                        if odoo_values_normalized == our_values_normalized:
                                            variant_id = odoo_variant['id']
                                            break
                                    # For template-only matching, check if export has empty variant values
                                    elif not odoo_variant['variant_values']:
                                        variant_id = odoo_variant['id']
                                        break
                
                if variant_id:
                    row_data = {
                        'id': variant_id,
                        'default_code': variant_data['default_code'],
                        'barcode': variant_data['barcode'],
                        'standard_price': variant_data['standard_price'],
                        'list_price': variant_data['list_price'],
                        'weight': variant_data['weight']
                    }
                    writer.writerow(row_data)
                else:
                    print(f"Warning: No Odoo variant ID found for {template_name} with values: {variant_values_str}")
                    
            elif attribute_name_to_id and attribute_value_name_to_id:
                # Use external IDs for attribute values
                attr_value_ids = []
                for attr_name, attr_value in variant_data['attribute_values']:
                    if attr_value:  # Only process non-empty values
                        value_key = f"{attr_name}:{attr_value}"
                        value_id = attribute_value_name_to_id.get(value_key, '')
                        if value_id:
                            attr_value_ids.append(value_id)
                attr_values_str = ','.join(attr_value_ids) if attr_value_ids else ''
                
                row_data = {
                    'name': variant_data['name'],
                    'product_tmpl_id': variant_data['template_name'],
                    'default_code': variant_data['default_code'],
                    'barcode': variant_data['barcode'],
                    'standard_price': variant_data['standard_price'],
                    'attribute_value_ids/id': attr_values_str
                }
                writer.writerow(row_data)
            else:
                # Use name-based format (fallback)
                attr_values = [val for attr, val in variant_data['attribute_values'] if val]
                attr_values_str = ','.join(attr_values) if attr_values else ''
                
                row_data = {
                    'name': variant_data['name'],
                    'product_tmpl_id': variant_data['template_name'],
                    'default_code': variant_data['default_code'],
                    'barcode': variant_data['barcode'],
                    'standard_price': variant_data['standard_price'],
                    'attribute_value_ids/name': attr_values_str
                }
                writer.writerow(row_data)
    
    print(f"Product variants file contains {len(all_variants)} variants")
    print(f"Odoo import sequence: 1→Attributes & Values, 2→Templates, 3→Variants")
    
    # Write unmapped Sheet1 rows
    unmapped_sheet1_rows = []
    if sheet1_full_data:
        for product_name, row_data in sheet1_full_data.items():
            if product_name not in matched_sheet1_names:
                unmapped_sheet1_rows.append(row_data)
        
        unmapped_output_file = output_file.replace('.csv', '_unmapped_sheet1.csv')
        print(f"Writing unmapped Sheet1 rows to {unmapped_output_file}...")
        sheet1_fieldnames = list(next(iter(sheet1_full_data.values())).keys())
        with open(unmapped_output_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=sheet1_fieldnames)
            writer.writeheader()
            writer.writerows(unmapped_sheet1_rows)
        
        print(f"Unmapped Sheet1 output contains {len(unmapped_sheet1_rows)} rows")
        
        # Write Shopify-optimized export (minimal columns for updates)
        shopify_output_file = output_file.replace('.csv', '_shopify_update.csv')
        print(f"Writing Shopify-optimized export to {shopify_output_file}...")
        
        # Create Shopify-optimized rows - include ALL Sheet2 rows
        shopify_rows = []
        shopify_fieldnames = [
            'Handle', 'Title',
            'Option1 Name', 'Option1 Value',
            'Option2 Name', 'Option2 Value', 
            'Option3 Name', 'Option3 Value',
            'Variant SKU', 'Variant Barcode', 'Variant Cost'
        ]
        
        # Create a lookup of matched rows for quick access
        matched_lookup = {}
        for row in matched_sheet2_rows:
            handle = row.get('Handle', '').strip()
            option1 = row.get('Option1 Value', '').strip()
            option2 = row.get('Option2 Value', '').strip()
            option3 = row.get('Option3 Value', '').strip()
            key = f"{handle}|{option1}|{option2}|{option3}"
            
            # Enhanced row data with cost from Sheet1
            enhanced_row = row.copy()
            # Find the Sheet1 cost data for this matched row
            variant_sku = row.get('Variant SKU', '').strip()
            if variant_sku:
                # Find the Sheet1 product that matches this SKU
                for sheet1_name, sheet1_row in sheet1_full_data.items():
                    if sheet1_row.get('Internal Reference', '').strip() == variant_sku:
                        enhanced_row['Sheet1_Cost'] = sheet1_row.get('Cost', '')
                        break
            
            matched_lookup[key] = enhanced_row
        
        # Process ALL Sheet2 data - both matched and unmatched products
        for row in sheet2_data:
            handle = row.get('Handle', '').strip()
            option1 = row.get('Option1 Value', '').strip()
            option2 = row.get('Option2 Value', '').strip()
            option3 = row.get('Option3 Value', '').strip()
            key = f"{handle}|{option1}|{option2}|{option3}"
            
            shopify_row = {}
            for field in shopify_fieldnames:
                if field == 'Variant SKU':
                    # Only include SKU if we have a match from Sheet1, otherwise leave blank
                    if key in matched_lookup:
                        shopify_row[field] = matched_lookup[key].get(field, '')
                    else:
                        shopify_row[field] = ''  # Leave blank to remove duplicate SKUs
                elif field == 'Variant Barcode':
                    # Use matched barcode if available, otherwise keep original Sheet2 barcode
                    if key in matched_lookup:
                        shopify_row[field] = matched_lookup[key].get(field, '')
                    else:
                        shopify_row[field] = row.get(field, '')  # Keep original barcode
                elif field == 'Variant Cost':
                    # Use Sheet1 cost if matched, otherwise keep original Sheet2 cost
                    if key in matched_lookup:
                        shopify_row[field] = matched_lookup[key].get('Sheet1_Cost', '')
                    else:
                        shopify_row[field] = row.get('Variant Cost', '')  # Keep original Sheet2 cost
                else:
                    shopify_row[field] = row.get(field, '')
            
            shopify_rows.append(shopify_row)
        
        with open(shopify_output_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=shopify_fieldnames)
            writer.writeheader()
            writer.writerows(shopify_rows)
        
        matched_variants = len([r for r in shopify_rows if r.get('Variant SKU', '')])
        total_variants = len(shopify_rows)
        print(f"Shopify export contains {total_variants} total variants ({matched_variants} with SKU/barcode updates)")
        
        # Write duplicate SKUs report
        if duplicate_skus:
            duplicate_output_file = output_file.replace('.csv', '_duplicate_skus.csv')
            print(f"Writing duplicate SKUs report to {duplicate_output_file}...")
            with open(duplicate_output_file, 'w', encoding='utf-8', newline='') as file:
                fieldnames = ['SKU', 'Product_Name', 'Row_Number', 'Duplicate_Status']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                
                for dup in duplicate_skus:
                    writer.writerow({
                        'SKU': dup['sku'],
                        'Product_Name': dup['name'],
                        'Row_Number': dup['row'],
                        'Duplicate_Status': dup['duplicate_of']
                    })
            
            print(f"Duplicate SKUs report contains {len(duplicate_skus)} entries")
        
        # Write Odoo categories export
        odoo_categories_file = output_file.replace('.csv', '_odoo_categories.csv')
        print(f"Writing Odoo categories export to {odoo_categories_file}...")
        
        # Extract unique categories from matched Sheet1 products
        categories = set()
        for product_name in matched_sheet1_names:
            if product_name in sheet1_full_data:
                category = sheet1_full_data[product_name].get('Product Category', '').strip()
                if category:
                    categories.add(category)
        
        # Write categories to CSV
        with open(odoo_categories_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['category_name'])  # Header
            for category in sorted(categories):  # Sort alphabetically
                writer.writerow([category])
        
        print(f"Odoo categories export contains {len(categories)} unique categories")
    
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