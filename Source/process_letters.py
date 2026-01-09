#!/usr/bin/env python3
"""
Main entry point for PDF letter processing pipeline.

This script orchestrates the complete workflow:
1. Extract text from PDF using OCR (extract_text.py)
2. Segment pages into individual letters (analyze_letters.py)
3. Output structured results with metadata for each letter

Usage:
    python process_letters.py -i input.pdf -o output.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from extract_text import extract_text_from_pdf
    from analyze_letters import analyze_documents
except ImportError as e:
    print(f"Error: Required module not found: {e}", file=sys.stderr)
    print("Make sure extract_text.py and analyze_letters.py are in the same directory", file=sys.stderr)
    sys.exit(1)


def process_pdf_letters(
    input_path: Path,
    rotate: bool = True,
    deskew: bool = True,
    jobs: int = 0
) -> Dict[str, Any]:
    """
    Complete pipeline to process a PDF containing multiple letters.
    
    Extracts OCR text from the PDF and segments it into individual letters
    with metadata extraction.
    
    Args:
        input_path: Path to input PDF file
        rotate: Enable automatic page rotation correction (default: True)
        deskew: Enable deskewing of pages (default: True)
        jobs: Number of parallel OCR jobs (0 = use all CPU cores, default: 0)
        
    Returns:
        Dictionary with:
            - input_file: str (input PDF path)
            - total_pages: int (total pages in PDF)
            - letters_found: int (number of letters detected)
            - letters: list[dict] (letter metadata and page info)
            
    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: For OCR processing errors
        ValueError: For invalid PDF files
    """
    # Step 1: Extract text from PDF using OCR
    ocr_result = extract_text_from_pdf(
        input_path,
        rotate=rotate,
        deskew=deskew,
        jobs=jobs
    )
    
    # Step 2: Extract page text for analysis
    ocr_pages = [page['text'] for page in ocr_result['pages']]
    
    # Step 3: Analyze and segment letters
    letters = analyze_documents(ocr_pages)
    
    # Step 4: Prepare output structure
    result = {
        'input_file': str(input_path),
        'total_pages': ocr_result['page_count'],
        'letters_found': len(letters),
        'letters': letters
    }
    
    return result


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Process PDF containing multiple letters: extract text via OCR and segment into individual letters with metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python process_letters.py -i letters.pdf -o results.json
  
  # Disable rotation and deskew
  python process_letters.py -i letters.pdf -o results.json --no-rotate --no-deskew
  
  # Use specific number of parallel jobs
  python process_letters.py -i letters.pdf -o results.json --jobs 4
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='Input PDF file path'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.json',
        help='Output JSON file path (default: output.json)'
    )
    parser.add_argument(
        '--no-rotate',
        action='store_true',
        help='Disable automatic page rotation correction'
    )
    parser.add_argument(
        '--no-deskew',
        action='store_true',
        help='Disable deskewing of pages'
    )
    parser.add_argument(
        '--jobs',
        type=int,
        default=0,
        help='Number of parallel OCR jobs (0 = use all CPU cores, default: 0)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    try:
        # Process the PDF
        if args.verbose:
            print(f"Processing: {input_path}", file=sys.stderr)
            print("Step 1: Extracting text via OCR...", file=sys.stderr)
        
        result = process_pdf_letters(
            input_path,
            rotate=not args.no_rotate,
            deskew=not args.no_deskew,
            jobs=args.jobs
        )
        
        if args.verbose:
            print(f"Step 2: Analyzing and segmenting letters...", file=sys.stderr)
            print(f"Found {result['letters_found']} letter(s) in {result['total_pages']} pages", file=sys.stderr)
        
        # Write results to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"Successfully processed {result['total_pages']} pages")
        print(f"Detected {result['letters_found']} letter(s)")
        print(f"Results written to: {output_path}")
        
        # Print detailed summary if verbose
        if args.verbose:
            print("\nLetter summary:", file=sys.stderr)
            for i, letter in enumerate(result['letters'], 1):
                print(f"\nLetter {i}:", file=sys.stderr)
                print(f"  Start page: {letter['start_page']}", file=sys.stderr)
                print(f"  Page count: {letter['page_count']}", file=sys.stderr)
                print(f"  Date: {letter['date'] or 'Not found'}", file=sys.stderr)
                print(f"  Sender: {letter['sender'] or 'Not found'}", file=sys.stderr)
                print(f"  Topic: {letter['topic'] or 'Not found'}", file=sys.stderr)
        
    except FileNotFoundError as e:
        print(f"Error: Input file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
