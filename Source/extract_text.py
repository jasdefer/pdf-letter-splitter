#!/usr/bin/env python3
"""
OCR-based text extractor for PDF documents.

Extracts text from each page of a PDF using Tesseract OCR with German + English language support.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any

try:
    import pdf2image
    import pytesseract
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install pdf2image pytesseract", file=sys.stderr)
    sys.exit(1)


def repair_pdf(input_path: Path) -> Path:
    """
    Attempt to repair a PDF using various tools if the PDF has structural issues.
    
    Args:
        input_path: Path to potentially damaged PDF
        
    Returns:
        Path to repaired PDF (or original if no repair was needed)
    """
    try:
        # Try to convert the PDF directly first
        pdf2image.pdfinfo_from_path(str(input_path), userpw=None, ownerpw=None, strict=False)
        # If successful, return original path
        return input_path
    except Exception:
        # PDF has issues, try to repair it
        pass
    
    # Try mutool clean first (often best for structural repairs)
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        mutool_cmd = [
            'mutool',
            'clean',
            '-gggg',  # Garbage collect with extreme settings
            str(input_path),
            temp_path
        ]
        
        result = subprocess.run(mutool_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Verify the repaired PDF is readable
            try:
                pdf2image.pdfinfo_from_path(str(temp_path), userpw=None, ownerpw=None, strict=False)
                return Path(temp_path)
            except:
                os.unlink(temp_path)
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception:
        pass
    
    # Try qpdf next
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        qpdf_cmd = [
            'qpdf',
            '--linearize',
            str(input_path),
            temp_path
        ]
        
        result = subprocess.run(qpdf_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            try:
                pdf2image.pdfinfo_from_path(str(temp_path), userpw=None, ownerpw=None, strict=False)
                return Path(temp_path)
            except:
                os.unlink(temp_path)
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception:
        pass
    
    # Try ghostscript as last resort
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        gs_cmd = [
            'gs',
            '-o', temp_path,
            '-sDEVICE=pdfwrite',
            '-dPDFSETTINGS=/prepress',
            str(input_path)
        ]
        
        result = subprocess.run(gs_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            try:
                pdf2image.pdfinfo_from_path(str(temp_path), userpw=None, ownerpw=None, strict=False)
                return Path(temp_path)
            except:
                os.unlink(temp_path)
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception:
        pass
    
    # If all repairs fail, return original path and let the error propagate
    return input_path


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
    
    Args:
        input_path: Path to input PDF file
        dpi: Resolution for PDF rendering (default: 300)
        lang: Tesseract language codes (default: 'deu+eng')
        
    Returns:
        Dictionary with page_count and pages list
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        Exception: For any other errors during processing
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")
    
    # Attempt to repair PDF if needed
    pdf_to_use = repair_pdf(input_path)
    temp_pdf_created = (pdf_to_use != input_path)
    
    try:
        # Convert PDF pages to images at specified DPI
        # Use strict=False to allow handling of slightly malformed PDFs
        images = pdf2image.convert_from_path(
            str(pdf_to_use),
            dpi=dpi,
            fmt='png',
            strict=False
        )
    except Exception as e:
        if temp_pdf_created:
            os.unlink(str(pdf_to_use))
        raise RuntimeError(f"Failed to convert PDF to images: {e}")
    
    if not images:
        if temp_pdf_created:
            os.unlink(str(pdf_to_use))
        raise ValueError("No pages found in PDF")
    
    pages = []
    
    for page_num, image in enumerate(images, start=1):
        try:
            # Run OCR on the page image
            text = pytesseract.image_to_string(image, lang=lang)
            
            # Apply whitespace normalization
            normalized_text = normalize_whitespace(text)
            
            pages.append({
                "page_number": page_num,
                "text": normalized_text
            })
            
        except Exception as e:
            if temp_pdf_created:
                os.unlink(str(pdf_to_use))
            raise RuntimeError(f"OCR failed on page {page_num}: {e}")
    
    # Clean up temporary file if created
    if temp_pdf_created:
        os.unlink(str(pdf_to_use))
    
    return {
        "page_count": len(pages),
        "pages": pages
    }


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
