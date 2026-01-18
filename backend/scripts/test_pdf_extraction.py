#!/usr/bin/env python3
"""
Test script to extract and display all fields from the PDF file.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.adk_agents.document_agent import ADKDocumentAgent
import json


async def main():
    """Extract and display fields from the PDF."""
    # Find the PDF file
    backend_dir = Path(__file__).parent.parent
    uploads_dir = backend_dir / "uploads"
    pdf_name = "202200420453_VROV4-digitCare_15942315559823643_SCHEDULE.pdf"
    
    pdf_path = None
    for subdir in uploads_dir.iterdir():
        if subdir.is_dir():
            candidate = subdir / pdf_name
            if candidate.exists():
                pdf_path = str(candidate)
                break
    
    if not pdf_path:
        print(f"❌ PDF file {pdf_name} not found in uploads directory")
        return
    
    print(f"📄 Analyzing PDF: {pdf_path}\n")
    
    # Initialize agent
    agent = ADKDocumentAgent()
    
    # Extract data
    print("🔄 Extracting data from PDF...\n")
    result = await agent.analyze(
        "test-extraction",
        [{"file_path": pdf_path}]
    )
    
    # Display results
    print("=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    
    extracted_data = result.get("extracted_data", {})
    
    # Document Classification
    print("\n📋 DOCUMENT CLASSIFICATION:")
    print("-" * 80)
    classification = extracted_data.get("document_classification", {})
    for key, value in classification.items():
        print(f"  {key}: {value}")
    
    # Extracted Fields
    print("\n📝 EXTRACTED FIELDS:")
    print("-" * 80)
    extracted_fields = extracted_data.get("extracted_fields", {})
    
    if not extracted_fields:
        print("  ⚠️  No fields extracted")
    else:
        # Group fields by category for better readability
        categories = {
            "Document Info": ["document_type", "policy_number", "claim_number", "vro_date", "printed_date"],
            "Vehicle Info": ["owner_name", "registration_number", "date_of_registration", "vehicle_make_and_model", "engine_number", "vehicle_age_years"],
            "Contact Info": ["vendor_name", "workshop_name", "workshop_gst_number", "surveyor_name", "claim_coordinator", "contact_number", "email", "toll_free_number"],
            "Financial Info": ["total_liability", "compulsory_deductible", "voluntary_deductible", "salvage_deductions", "non_standard_amount", "towing_amount", "customer_liability", "digit_liability"],
            "Tax Breakdown": ["sub_total", "total_tax", "grand_total", "remove_and_refitting_taxable_amount", "repair_taxable_amount", "paint_material_taxable_amount", "paint_labour_taxable_amount"],
            "Tax Amounts": ["remove_and_refitting_tax_amount", "repair_tax_amount", "paint_material_tax_amount", "paint_labour_tax_amount"],
            "Total Amounts": ["remove_and_refitting_total_amount", "repair_total_amount", "paint_labour_total_amount", "final_total"],
            "Other": ["date_of_accident", "payment_to"]
        }
        
        # Display categorized fields
        for category, field_names in categories.items():
            category_fields = {k: v for k, v in extracted_fields.items() if k in field_names}
            if category_fields:
                print(f"\n  {category}:")
                for key, value in category_fields.items():
                    print(f"    • {key}: {value}")
        
        # Display any remaining fields not in categories
        categorized_keys = set()
        for field_list in categories.values():
            categorized_keys.update(field_list)
        
        remaining_fields = {k: v for k, v in extracted_fields.items() if k not in categorized_keys}
        if remaining_fields:
            print(f"\n  Other Fields:")
            for key, value in remaining_fields.items():
                print(f"    • {key}: {value}")
    
    # Line Items
    print("\n📊 LINE ITEMS:")
    print("-" * 80)
    line_items = extracted_data.get("line_items", [])
    if line_items:
        print(f"  Found {len(line_items)} line item(s):")
        for i, item in enumerate(line_items[:5], 1):  # Show first 5
            print(f"    {i}. {json.dumps(item, indent=6)}")
        if len(line_items) > 5:
            print(f"    ... and {len(line_items) - 5} more")
    else:
        print("  No line items found")
    
    # Tables
    print("\n📋 TABLES:")
    print("-" * 80)
    tables = extracted_data.get("tables", [])
    if tables:
        print(f"  Found {len(tables)} table(s):")
        for i, table in enumerate(tables[:3], 1):  # Show first 3
            print(f"    Table {i}:")
            print(f"      Headers: {table.get('headers', [])}")
            print(f"      Rows: {len(table.get('rows', []))} row(s)")
            if table.get('summary'):
                print(f"      Summary: {table.get('summary')}")
    else:
        print("  No tables found")
    
    # Metadata
    print("\n📈 METADATA:")
    print("-" * 80)
    metadata = extracted_data.get("metadata", {})
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    # Validity
    print("\n✅ VALIDITY:")
    print("-" * 80)
    print(f"  Valid: {extracted_data.get('valid', False)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total Fields Extracted: {len(extracted_fields)}")
    print(f"  Line Items: {len(line_items)}")
    print(f"  Tables: {len(tables)}")
    print(f"  Confidence: {metadata.get('confidence', 0.0):.2%}")
    print(f"  Valid: {extracted_data.get('valid', False)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
