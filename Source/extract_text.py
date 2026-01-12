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

# Lazy import - check for pypdf only when needed
pypdf = None
try:
    import pypdf
except ImportError:
    pass  # Will be handled when extract_text_from_pdf is called


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


def extract_text_from_pdf(input_path: Path, lang: str = 'deu+eng', 
                          rotate: bool = True, deskew: bool = True, 
                          jobs: int = 0) -> Dict[str, Any]:
    """
    Extract text from all pages of a PDF using OCR.
    
    Uses ocrmypdf to create a searchable PDF, then extracts text from each page.
    
    Args:
        input_path: Path to input PDF file
        lang: Tesseract language codes (default: 'deu+eng')
        rotate: Enable automatic page rotation correction (default: True)
        deskew: Enable deskewing of pages (default: True)
        jobs: Number of parallel jobs (0 = use all CPU cores, default: 0)
        
    Returns:
        Dictionary with page_count and pages list
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: For OCR processing errors
        ValueError: For invalid PDF files
        ImportError: If pypdf package is not installed
    """
    # Check for required pypdf package
    if pypdf is None:
        raise ImportError("pypdf package is required. Install with: pip install pypdf")
    
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
            '--force-ocr',  # Always use OCR, never rely on embedded text
            '--output-type', 'pdf',
            '--pdf-renderer', 'sandwich',
            '--jobs', str(jobs),  # Enable parallel processing
        ]
        
        # Add optional rotation correction
        if rotate:
            ocrmypdf_cmd.append('--rotate-pages')
        
        # Add optional deskewing
        if deskew:
            ocrmypdf_cmd.append('--deskew')
        
        # Add input and output paths
        ocrmypdf_cmd.extend([str(input_path), temp_ocr_pdf])
        
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
                
                # Handle cases where extract_text() returns None
                if text is None:
                    text = ""
                
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
