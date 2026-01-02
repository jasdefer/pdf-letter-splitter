#!/usr/bin/env python3
"""
OCR-based text extractor for PDF documents.

Extracts text from each page of a PDF using OCRmyPDF with German + English language support.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

try:
    import pypdf
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install pypdf", file=sys.stderr)
    sys.exit(1)


def normalize_whitespace(text: str) -> str:
    """
    Apply minimal whitespace normalization to extracted text.
    
    - Trim trailing spaces per line
    - Collapse multiple spaces/tabs into a single space within lines
    - Collapse excessive blank lines
    - Trim leading/trailing whitespace per page
    
    Args:
        text: Raw OCR text
        
    Returns:
        Normalized text
    """
    # Split into lines
    lines = text.split('\n')
    
    # Process each line
    normalized_lines = []
    for line in lines:
        # Trim trailing spaces
        line = line.rstrip()
        # Collapse multiple spaces/tabs into single space
        line = re.sub(r'[ \t]+', ' ', line)
        normalized_lines.append(line)
    
    # Join lines back together
    result = '\n'.join(normalized_lines)
    
    # Collapse excessive blank lines (more than 2 consecutive newlines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Trim leading/trailing whitespace
    result = result.strip()
    
    return result


def extract_text_from_pdf(input_path: Path, dpi: int = 300, lang: str = 'deu+eng') -> Dict[str, Any]:
    """
    Extract text from all pages of a PDF using OCR.
    
    Uses ocrmypdf to create a searchable PDF, then extracts text from each page.
    
    Args:
        input_path: Path to input PDF file
        dpi: Resolution for PDF rendering (default: 300)
        lang: Tesseract language codes (default: 'deu+eng')
        
    Returns:
        Dictionary with page_count and pages list
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: For OCR processing errors
        ValueError: For invalid PDF files
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")
    
    # Create a temporary file for the OCR'd PDF
    temp_fd, temp_ocr_pdf = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        # Run ocrmypdf to create a searchable PDF
        ocrmypdf_cmd = [
            'ocrmypdf',
            '--language', lang,
            '--deskew',
            '--output-type', 'pdf',
            '--pdf-renderer', 'sandwich',
            str(input_path),
            temp_ocr_pdf
        ]
        
        result = subprocess.run(ocrmypdf_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # ocrmypdf returns 0 for success, 1 for bad input, etc.
            # Try to provide a helpful error message
            error_msg = result.stderr if result.stderr else result.stdout
            raise RuntimeError(f"OCR processing failed: {error_msg}")
        
        # Extract text from the searchable PDF
        try:
            reader = pypdf.PdfReader(temp_ocr_pdf)
        except Exception as e:
            raise RuntimeError(f"Failed to read OCR'd PDF: {e}")
        
        if len(reader.pages) == 0:
            raise ValueError("No pages found in PDF")
        
        pages = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                # Extract text from the page
                text = page.extract_text()
                
                # Apply whitespace normalization
                normalized_text = normalize_whitespace(text)
                
                pages.append({
                    "page_number": page_num,
                    "text": normalized_text
                })
                
            except Exception as e:
                raise RuntimeError(f"Text extraction failed on page {page_num}: {e}")
        
        return {
            "page_count": len(pages),
            "pages": pages
        }
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_ocr_pdf):
            os.unlink(temp_ocr_pdf)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Extract text from PDF using OCR (German + English)'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='input.pdf',
        help='Input PDF file path (default: input.pdf)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output.json',
        help='Output JSON file path (default: output.json)'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    try:
        # Extract text from PDF
        result = extract_text_from_pdf(input_path)
        
        # Write results to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully extracted text from {result['page_count']} pages")
        print(f"Output written to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
