#!/usr/bin/env python3
"""
Simple example demonstrating PageData structures without requiring OCR tools.

This example creates synthetic OCR data and shows the complete workflow.
"""

import sys
from pathlib import Path

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

import pandas as pd
from page_data import PageData, PageInfoDetected, TextMarker, page_data_list_to_json
from page_analysis import analyze_pages


def create_synthetic_ocr_data():
    """Create synthetic OCR data for demonstration purposes."""
    data = {
        'page_num': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'level': [5, 5, 5, 5, 5, 5, 5, 5, 5],
        'text': [
            'Dear', 'Sir', 'Madam',  # Page 1
            'Thank', 'you', 'letter',  # Page 2
            'Sincerely', 'yours', 'Team'  # Page 3
        ],
        'left': [100, 150, 200, 100, 150, 200, 100, 150, 200],
        'top': [100, 100, 100, 100, 100, 100, 100, 100, 100],
        'width': [50, 50, 50, 50, 50, 50, 50, 50, 50],
        'height': [20, 20, 20, 20, 20, 20, 20, 20, 20]
    }
    return pd.DataFrame(data)


def main():
    """Demonstrate the page data structures and analysis pipeline."""
    print("=" * 70)
    print("PageData Structure and Marker Detection - Simple Example")
    print("=" * 70)
    
    # Create synthetic OCR data
    print("\n1. Creating synthetic OCR data...")
    ocr_df = create_synthetic_ocr_data()
    print(f"   Created DataFrame with {len(ocr_df)} rows, {ocr_df['page_num'].nunique()} pages")
    
    # Analyze pages
    print("\n2. Analyzing pages...")
    pages = analyze_pages(ocr_df)
    print(f"   Generated {len(pages)} PageData instances")
    
    # Display results
    print("\n3. PageData structures created:")
    print("-" * 70)
    for page in pages:
        print(f"\n   Page {page.scan_page_num}:")
        print(f"      - Page info: found={page.page_info.found}, "
              f"current={page.page_info.current}, total={page.page_info.total}")
        print(f"      - Greeting: found={page.greeting.found}")
        print(f"      - Goodbye: found={page.goodbye.found}")
        print(f"      - Betreff: found={page.betreff.found}")
        print(f"      - Address block: found={page.address_block.found}")
    
    # Show JSON serialization
    print("\n4. JSON serialization:")
    print("-" * 70)
    json_output = page_data_list_to_json(pages, indent=2)
    print(json_output)
    
    # Demonstrate manual PageData creation
    print("\n5. Manual PageData creation example:")
    print("-" * 70)
    manual_page = PageData(
        scan_page_num=99,
        page_info=PageInfoDetected(
            found=True,
            current=2,
            total=4,
            raw="Seite 2 von 4"
        ),
        greeting=TextMarker(
            found=True,
            raw="Sehr geehrte Damen und Herren",
            text="Sehr geehrte Damen und Herren"
        ),
        goodbye=TextMarker(found=False),
        betreff=TextMarker(
            found=True,
            raw="Betreff: Test Subject",
            text="Test Subject"
        ),
        address_block=TextMarker(found=False)
    )
    print(f"\n   Created PageData for page {manual_page.scan_page_num}:")
    print(f"      - Page numbering: {manual_page.page_info.current} of {manual_page.page_info.total}")
    print(f"      - Greeting detected: {manual_page.greeting.text}")
    print(f"      - Subject detected: {manual_page.betreff.text}")
    
    # Show JSON for manual page
    print("\n6. JSON for manually created page:")
    print("-" * 70)
    print(manual_page.to_json(indent=2))
    
    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
