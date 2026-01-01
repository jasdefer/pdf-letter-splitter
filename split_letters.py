#!/usr/bin/env python3
"""
pdf-letter-splitter: Automatically split a multi-letter PDF into individual letters.

This script:
1. OCRs the entire input PDF once
2. Detects letter boundaries using heuristics
3. Extracts metadata (date, sender, topic) from each letter
4. Outputs one PDF per letter with appropriate naming
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime
import subprocess
import tempfile


def ocr_pdf(input_pdf_path, output_pdf_path):
    """
    Apply OCR to the entire PDF using ocrmypdf.
    
    Args:
        input_pdf_path: Path to the input PDF
        output_pdf_path: Path where the OCRed PDF will be saved
    """
    print(f"Starting OCR on {input_pdf_path}")
    
    # Run ocrmypdf with German and English language support
    # --skip-text: Skip pages that already have text
    # --deskew: Correct page rotation
    # -l deu+eng: Use German and English language packs
    cmd = [
        "ocrmypdf",
        "--skip-text",
        "--deskew",
        "-l", "deu+eng",
        input_pdf_path,
        output_pdf_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"OCR completed successfully")
        if result.stdout:
            print(f"OCR output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"OCR failed: {e}")
        print(f"stderr: {e.stderr}")
        # If OCR fails, we'll try to work with the original
        return False


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using pdftotext.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of strings, one per page
    """
    print(f"Extracting text from {pdf_path}")
    
    # Use pdftotext to extract text page by page
    pages_text = []
    
    # First, get the number of pages
    cmd = ["pdfinfo", pdf_path]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        num_pages = 0
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                num_pages = int(line.split(':')[1].strip())
                break
        
        print(f"PDF has {num_pages} pages")
        
        # Extract text from each page
        for page_num in range(1, num_pages + 1):
            cmd = ["pdftotext", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            pages_text.append(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"Text extraction failed: {e}")
        return []
    
    return pages_text


def detect_letter_starts(pages_text):
    """
    Detect which pages start a new letter using heuristics.
    
    Args:
        pages_text: List of text strings, one per page
        
    Returns:
        List of page numbers (1-indexed) where letters start
    """
    letter_starts = [1]  # First page always starts a letter
    
    # Heuristics for detecting a new letter:
    # 1. Page contains a date near the top
    # 2. Page contains typical letter headers (company names, addresses)
    # 3. Previous page was mostly empty or had closing phrases
    
    date_patterns = [
        r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b',  # DD.MM.YYYY or DD/MM/YYYY
        r'\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b',     # YYYY-MM-DD
        r'\b\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*\d{4}\b',  # German
        r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',  # English
    ]
    
    closing_phrases = [
        r'Mit freundlichen Grüßen',
        r'Freundliche Grüße',
        r'Beste Grüße',
        r'Hochachtungsvoll',
        r'Sincerely',
        r'Best regards',
        r'Kind regards',
        r'Yours faithfully',
    ]
    
    for i in range(1, len(pages_text)):
        page_text = pages_text[i]
        prev_page_text = pages_text[i-1]
        
        # Check if current page has date pattern in first 500 characters
        top_text = page_text[:500]
        has_date = any(re.search(pattern, top_text, re.IGNORECASE) for pattern in date_patterns)
        
        # Check if previous page has closing phrase
        prev_has_closing = any(re.search(phrase, prev_page_text, re.IGNORECASE) for phrase in closing_phrases)
        
        # If current page has date and previous had closing, likely a new letter
        if has_date and prev_has_closing:
            print(f"Detected new letter starting at page {i+1} (date + previous closing)")
            letter_starts.append(i + 1)
        # Or if page has date and previous page was very short
        elif has_date and len(prev_page_text.strip()) < 200:
            print(f"Detected new letter starting at page {i+1} (date + short previous page)")
            letter_starts.append(i + 1)
    
    return letter_starts


def extract_metadata(page_text):
    """
    Extract date, sender, and topic from the first page of a letter.
    
    Args:
        page_text: Text from the first page of a letter
        
    Returns:
        Dictionary with 'date', 'sender', and 'topic' keys (or None for missing fields)
    """
    metadata = {
        'date': None,
        'sender': None,
        'topic': None
    }
    
    # Extract date
    date_patterns = [
        (r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', 'dmy'),  # DD.MM.YYYY
        (r'\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b', 'ymd'),  # YYYY-MM-DD
        (r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2})\b', 'dmy2'),  # DD.MM.YY
    ]
    
    for pattern, date_format in date_patterns:
        match = re.search(pattern, page_text[:1000])
        if match:
            try:
                if date_format == 'dmy':
                    day, month, year = match.groups()
                    date_obj = datetime(int(year), int(month), int(day))
                elif date_format == 'ymd':
                    year, month, day = match.groups()
                    date_obj = datetime(int(year), int(month), int(day))
                elif date_format == 'dmy2':
                    day, month, year = match.groups()
                    year = int(year)
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                    date_obj = datetime(year, int(month), int(day))
                
                metadata['date'] = date_obj.strftime('%Y-%m-%d')
                print(f"  Extracted date: {metadata['date']}")
                break
            except (ValueError, IndexError):
                continue
    
    # Extract sender (look for company names or organization patterns)
    # This is heuristic - look for capitalized words near the top
    lines = page_text[:800].split('\n')
    for line in lines[:20]:
        line = line.strip()
        # Look for lines with capitalized words (potential company names)
        if len(line) > 5 and len(line) < 50 and line[0].isupper():
            # Check if it looks like a company name (mostly capitals or title case)
            words = line.split()
            if len(words) >= 1 and len(words) <= 5:
                capital_words = sum(1 for w in words if w and w[0].isupper())
                if capital_words >= len(words) * 0.5:
                    # Clean up the sender name for filename use
                    sender = re.sub(r'[^\w\s-]', '', line)
                    sender = re.sub(r'\s+', '-', sender.strip())
                    if sender and len(sender) > 2:
                        metadata['sender'] = sender[:30]  # Limit length
                        print(f"  Extracted sender: {metadata['sender']}")
                        break
    
    # Extract topic (look for "Betreff:", "Re:", "Subject:", etc.)
    topic_patterns = [
        r'Betreff:\s*(.+?)(?:\n|$)',
        r'Re:\s*(.+?)(?:\n|$)',
        r'Subject:\s*(.+?)(?:\n|$)',
        r'Betr\.:\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in topic_patterns:
        match = re.search(pattern, page_text[:1500], re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            # Clean up the topic for filename use
            topic = re.sub(r'[^\w\s-]', '', topic)
            topic = re.sub(r'\s+', '-', topic.strip())
            if topic:
                metadata['topic'] = topic[:30]  # Limit length
                print(f"  Extracted topic: {metadata['topic']}")
                break
    
    return metadata


def split_pdf(input_pdf, output_dir, letter_starts, pages_text):
    """
    Split the PDF into separate files, one per letter.
    
    Args:
        input_pdf: Path to the input PDF
        output_dir: Directory where output PDFs will be written
        letter_starts: List of page numbers where letters start
        pages_text: List of text strings, one per page
    """
    print(f"\nSplitting PDF into {len(letter_starts)} letter(s)")
    
    # Get total number of pages
    cmd = ["pdfinfo", input_pdf]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    num_pages = 0
    for line in result.stdout.split('\n'):
        if line.startswith('Pages:'):
            num_pages = int(line.split(':')[1].strip())
            break
    
    unrecognized_count = 0
    
    for i, start_page in enumerate(letter_starts):
        # Determine end page
        if i + 1 < len(letter_starts):
            end_page = letter_starts[i + 1] - 1
        else:
            end_page = num_pages
        
        print(f"\nProcessing letter {i+1}: pages {start_page}-{end_page}")
        
        # Extract metadata from first page
        first_page_text = pages_text[start_page - 1]
        metadata = extract_metadata(first_page_text)
        
        # Generate filename
        if metadata['date'] and metadata['sender'] and metadata['topic']:
            filename = f"{metadata['date']}-{metadata['sender']}-{metadata['topic']}.pdf"
        else:
            unrecognized_count += 1
            filename = f"XXX-XXX-XXX-{unrecognized_count:02d}.pdf"
        
        output_path = os.path.join(output_dir, filename)
        print(f"  Output: {filename}")
        
        # Extract pages using pdftk or qpdf
        # Try qpdf first, fall back to pdftk
        cmd = [
            "qpdf",
            input_pdf,
            "--pages",
            ".", f"{start_page}-{end_page}",
            "--",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  Successfully created {filename}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try pdftk as fallback
            cmd = [
                "pdftk",
                input_pdf,
                "cat",
                f"{start_page}-{end_page}",
                "output",
                output_path
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"  Successfully created {filename}")
            except subprocess.CalledProcessError as e:
                print(f"  ERROR: Failed to extract pages: {e}")


def main():
    """Main entry point for the pdf-letter-splitter."""
    if len(sys.argv) != 3:
        print("Usage: split_letters.py <input.pdf> <output_directory>")
        print("\nExample:")
        print("  split_letters.py /input/letters.pdf /output")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Validate inputs
    if not os.path.exists(input_pdf):
        print(f"ERROR: Input PDF not found: {input_pdf}")
        sys.exit(1)
    
    if not os.path.isfile(input_pdf):
        print(f"ERROR: Input path is not a file: {input_pdf}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("PDF Letter Splitter")
    print("=" * 60)
    print(f"Input PDF: {input_pdf}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Step 1: OCR the entire PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        ocr_pdf_path = tmp_file.name
    
    try:
        ocr_success = ocr_pdf(input_pdf, ocr_pdf_path)
        
        # Use OCRed version if successful, otherwise use original
        pdf_to_process = ocr_pdf_path if ocr_success and os.path.exists(ocr_pdf_path) else input_pdf
        
        # Step 2: Extract text from all pages
        pages_text = extract_text_from_pdf(pdf_to_process)
        
        if not pages_text:
            print("ERROR: Could not extract text from PDF")
            sys.exit(1)
        
        # Step 3: Detect letter boundaries
        letter_starts = detect_letter_starts(pages_text)
        print(f"\nDetected {len(letter_starts)} letter(s) starting at pages: {letter_starts}")
        
        # Step 4: Split PDF and extract metadata
        split_pdf(pdf_to_process, output_dir, letter_starts, pages_text)
        
        print("\n" + "=" * 60)
        print("Processing complete!")
        print("=" * 60)
        
    finally:
        # Clean up temporary OCR file
        if os.path.exists(ocr_pdf_path):
            os.unlink(ocr_pdf_path)


if __name__ == "__main__":
    main()
