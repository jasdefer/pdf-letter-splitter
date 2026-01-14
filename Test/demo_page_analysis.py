#!/usr/bin/env python3
"""
Demonstration script showing how to use the PageData structure
and marker detection pipeline.

This script shows the typical workflow:
1. Extract OCR data from a PDF
2. Analyze pages to create PageData structures
3. Serialize results to JSON for inspection
"""

import sys
from pathlib import Path

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from process_letters import extract_text
from page_analysis import analyze_pages
from page_data import page_data_list_to_json


def main():
    """Demonstrate the page analysis pipeline."""
    # Example: Using test.pdf
    test_pdf = Path(__file__).parent / 'test.pdf'
    
    if not test_pdf.exists():
        print(f"Error: Test PDF not found at {test_pdf}")
        print("Please provide a valid PDF path.")
        sys.exit(1)
    
    print(f"Processing PDF: {test_pdf}")
    print("-" * 60)
    
    # Step 1: Extract OCR data
    print("\n1. Extracting OCR data from PDF...")
    ocr_df = extract_text(test_pdf)
    print(f"   Extracted {len(ocr_df)} OCR elements from {ocr_df['page_num'].nunique()} pages")
    
    # Step 2: Analyze pages
    print("\n2. Analyzing pages and detecting markers...")
    pages = analyze_pages(ocr_df)
    print(f"   Created {len(pages)} PageData instances")
    
    # Step 3: Display results
    print("\n3. Page analysis results:")
    print("-" * 60)
    for page in pages:
        print(f"\nPage {page.scan_page_num}:")
        print(f"  - Page info found: {page.page_info.found}")
        print(f"  - Greeting found: {page.greeting.found}")
        print(f"  - Goodbye found: {page.goodbye.found}")
        print(f"  - Subject (Betreff) found: {page.betreff.found}")
        print(f"  - Address block found: {page.address_block.found}")
    
    # Step 4: Show JSON serialization
    print("\n4. JSON serialization example:")
    print("-" * 60)
    json_output = page_data_list_to_json(pages, indent=2)
    # Show first 500 characters of JSON
    print(json_output[:500] + "...")
    
    # Optional: Save to file
    output_file = Path('/tmp/page_analysis_output.json')
    output_file.write_text(json_output)
    print(f"\nFull JSON output saved to: {output_file}")


if __name__ == '__main__':
    main()
