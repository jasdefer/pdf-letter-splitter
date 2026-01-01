#!/usr/bin/env python3
"""
PDF Letter Splitter - Automatic multi-letter PDF processing

Accepts a single scanned multi-page PDF and:
1. OCR the full PDF (German and English)
2. Extract per-page text
3. Detect letter boundaries using heuristics
4. Split into one PDF per letter
5. Extract metadata (date, sender, topic) from first page using local LLM
6. Name outputs accordingly
"""

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import requests
import ocrmypdf
from pypdf import PdfReader, PdfWriter


# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# LLM Configuration - loaded from environment variables
LLAMA_BASE_URL = os.getenv('LLAMA_BASE_URL', 'http://localhost:8080')
MODEL_FIELDS_LANGUAGE_HINT = os.getenv('MODEL_FIELDS_LANGUAGE_HINT', 'deu+eng')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.1'))
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '256'))
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '30'))


class Letter:
    """Represents a detected letter with its page range and metadata."""
    
    def __init__(self, start_page: int, end_page: int):
        self.start_page = start_page
        self.end_page = end_page
        self.date: Optional[str] = None
        self.sender: Optional[str] = None
        self.topic: Optional[str] = None
    
    def __repr__(self):
        return f"Letter(pages {self.start_page}-{self.end_page}, date={self.date}, sender={self.sender}, topic={self.topic})"


def ocr_pdf(input_pdf: Path, output_pdf: Path) -> None:
    """
    OCR the input PDF with German and English language support.
    
    Args:
        input_pdf: Path to input PDF
        output_pdf: Path to output OCRed PDF
    """
    logger.info(f"Starting OCR on {input_pdf}")
    logger.info("Languages: German (deu) and English (eng)")
    
    try:
        ocrmypdf.ocr(
            input_pdf,
            output_pdf,
            language='deu+eng',  # German and English
            skip_text=False,     # OCR even if text exists
            force_ocr=True,      # Force OCR on all pages
            output_type='pdf',
            progress_bar=False
        )
        logger.info(f"OCR completed successfully: {output_pdf}")
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise


def extract_page_text(pdf_path: Path) -> List[str]:
    """
    Extract text from each page of the PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of text strings, one per page
    """
    logger.info(f"Extracting text from {pdf_path}")
    reader = PdfReader(pdf_path)
    page_texts = []
    
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        page_texts.append(text)
        logger.debug(f"Page {page_num}: {len(text)} characters extracted")
    
    logger.info(f"Extracted text from {len(page_texts)} pages")
    return page_texts


def detect_letter_start(page_text: str, page_num: int) -> Tuple[bool, str]:
    """
    Detect if a page is the start of a new letter using heuristics.
    
    Heuristics:
    1. Contains a date pattern (e.g., DD.MM.YYYY or similar)
    2. Contains common German/English letter salutations
    3. Contains sender address patterns
    4. Has typical letter header structure
    
    Args:
        page_text: Text content of the page
        page_num: Page number (1-indexed)
        
    Returns:
        Tuple of (is_letter_start, reason)
    """
    # Heuristic 1: Date patterns (various formats)
    date_patterns = [
        r'\b\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\b',  # DD.MM.YYYY or D.M.YYYY
        r'\b\d{1,2}\.\s*\d{1,2}\.\s*\d{2}\b',   # DD.MM.YY
        r'\b\d{4}-\d{2}-\d{2}\b',               # YYYY-MM-DD
        r'\b\d{1,2}\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}\b',  # German month
        r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',  # English month
    ]
    
    has_date = any(re.search(pattern, page_text, re.IGNORECASE) for pattern in date_patterns)
    
    # Heuristic 2: Common salutations
    salutations = [
        r'\bSehr\s+geehrte[rn]?\b',  # German: Sehr geehrte/r
        r'\bLiebe[rn]?\b',            # German: Liebe/r
        r'\bDear\b',                   # English: Dear
        r'\bGuten\s+Tag\b',           # German: Guten Tag
    ]
    
    has_salutation = any(re.search(pattern, page_text, re.IGNORECASE) for pattern in salutations)
    
    # Heuristic 3: Sender/address patterns
    address_patterns = [
        r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+\b',  # German postal code + city
        r'\b[A-ZÄÖÜ][a-zäöüß]+straße\s+\d+\b',  # Street name
        r'\b[A-ZÄÖÜ][a-zäöüß]+str\.\s+\d+\b',   # Abbreviated street
    ]
    
    has_address = any(re.search(pattern, page_text) for pattern in address_patterns)
    
    # Heuristic 4: Letter reference numbers
    reference_patterns = [
        r'\b(?:Zeichen|Az|Ref|Reference)[\s:]+[\w\-/]+\b',
        r'\b(?:Datum|Date)[\s:]+\d{1,2}\.\d{1,2}\.\d{2,4}\b',
    ]
    
    has_reference = any(re.search(pattern, page_text, re.IGNORECASE) for pattern in reference_patterns)
    
    # Decision logic: If it's page 1, it's always a letter start
    if page_num == 1:
        return True, "First page of document"
    
    # Strong indicators: date + salutation or date + address
    if has_date and (has_salutation or has_address):
        reasons = []
        if has_date:
            reasons.append("date pattern")
        if has_salutation:
            reasons.append("salutation")
        if has_address:
            reasons.append("address pattern")
        return True, f"Letter start detected: {', '.join(reasons)}"
    
    # Moderate indicator: date + reference
    if has_date and has_reference:
        return True, "Letter start detected: date pattern, reference number"
    
    return False, ""


def detect_letter_boundaries(page_texts: List[str]) -> List[Letter]:
    """
    Detect letter boundaries in the document using heuristics.
    
    Args:
        page_texts: List of text strings, one per page
        
    Returns:
        List of Letter objects with page ranges
    """
    logger.info("Starting letter boundary detection")
    letters = []
    current_letter_start = 0
    
    for page_num, page_text in enumerate(page_texts):
        is_start, reason = detect_letter_start(page_text, page_num + 1)
        
        if is_start and page_num > 0:
            # Close previous letter
            letter = Letter(current_letter_start, page_num - 1)
            letters.append(letter)
            logger.info(f"Letter detected: pages {current_letter_start + 1}-{page_num}")
            logger.info(f"  Next letter starts at page {page_num + 1} | Reason: {reason}")
            current_letter_start = page_num
    
    # Add the last letter
    if current_letter_start < len(page_texts):
        letter = Letter(current_letter_start, len(page_texts) - 1)
        letters.append(letter)
        logger.info(f"Letter detected: pages {current_letter_start + 1}-{len(page_texts)}")
    
    logger.info(f"Total letters detected: {len(letters)}")
    return letters


def call_llm_for_metadata(first_page_text: str, retry: bool = False) -> Dict[str, str]:
    """
    Call local LLM to extract metadata from first page text.
    
    Args:
        first_page_text: Text content of the first page
        retry: If True, use a stricter prompt for retry
        
    Returns:
        Dictionary with keys: date, sender, topic (values may be "XXX" for unrecognized)
    """
    # Truncate text to focus on header region (first ~4000 characters or ~40 lines)
    lines = first_page_text.split('\n')
    truncated_text = '\n'.join(lines[:40])
    if len(truncated_text) > 4000:
        truncated_text = truncated_text[:4000]
    
    # Build prompt based on whether this is a retry
    if retry:
        # Stricter prompt for retry
        prompt = f"""You must respond with ONLY valid JSON. No other text.

Extract these three fields from this letter text:
- date: in YYYY-MM-DD format, or "XXX" if not found
- sender: short sender name (no address), or "XXX" if not found  
- topic: short topic/subject (no full sentences), or "XXX" if not found

Letter languages: {MODEL_FIELDS_LANGUAGE_HINT}

Letter text:
{truncated_text}

Response (JSON only):"""
    else:
        # Normal prompt
        prompt = f"""Extract metadata from this letter. Return JSON only with these exact keys:
- "date": normalize to YYYY-MM-DD format, or "XXX" if date not found or invalid
- "sender": short sender name (company/person, no full address), or "XXX" if not found
- "topic": short topic/subject (no address, no full sentence if avoidable), or "XXX" if not found

The letter may be in German or English ({MODEL_FIELDS_LANGUAGE_HINT}).

Letter text (first page):
{truncated_text}

Return ONLY a JSON object with the three keys. No other text."""

    # Prepare request payload for llama.cpp /completion endpoint
    payload = {
        "prompt": prompt,
        "temperature": LLM_TEMPERATURE,
        "n_predict": LLM_MAX_TOKENS,
        "stop": ["\n\n\n", "###"],  # Stop sequences
    }
    
    try:
        logger.info(f"Calling LLM at {LLAMA_BASE_URL}/completion")
        response = requests.post(
            f"{LLAMA_BASE_URL}/completion",
            json=payload,
            timeout=LLM_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the generated text from response
        # llama.cpp returns {"content": "...", ...}
        generated_text = result.get('content', '')
        
        logger.debug(f"LLM raw response: {generated_text}")
        
        # Try multiple strategies to extract and parse JSON from the response
        metadata = None
        
        # Strategy 1: Try to parse the entire response as JSON
        try:
            metadata = json.loads(generated_text.strip())
            if all(key in metadata for key in ['date', 'sender', 'topic']):
                logger.info(f"Successfully extracted metadata via LLM (direct parse)")
                return metadata
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Strategy 2: Remove markdown code blocks and try again
        cleaned_text = re.sub(r'```(?:json)?\s*', '', generated_text)
        cleaned_text = re.sub(r'```\s*', '', cleaned_text)
        try:
            metadata = json.loads(cleaned_text.strip())
            if all(key in metadata for key in ['date', 'sender', 'topic']):
                logger.info(f"Successfully extracted metadata via LLM (cleaned parse)")
                return metadata
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Strategy 3: Find first '{' and last '}', extract and parse
        first_brace = generated_text.find('{')
        last_brace = generated_text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                json_str = generated_text[first_brace:last_brace + 1]
                metadata = json.loads(json_str)
                if all(key in metadata for key in ['date', 'sender', 'topic']):
                    logger.info(f"Successfully extracted metadata via LLM (brace extraction)")
                    return metadata
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Strategy 4: Use regex as last resort (original approach)
        json_match = re.search(r'\{[^{}]*"date"[^{}]*"sender"[^{}]*"topic"[^{}]*\}', generated_text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                metadata = json.loads(json_str)
                
                # Validate keys exist
                if all(key in metadata for key in ['date', 'sender', 'topic']):
                    logger.info(f"Successfully extracted metadata via LLM (regex extraction)")
                    return metadata
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If we reach here, all JSON parsing strategies failed
        logger.warning(f"Failed to parse JSON from LLM response: {generated_text[:200]}")
        raise ValueError("Invalid JSON response from LLM")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request to LLM failed: {e}")
        raise
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise


def extract_metadata_with_llm(letter: Letter, page_texts: List[str]) -> None:
    """
    Extract metadata from the first page of a letter using LLM.
    
    Args:
        letter: Letter object to populate with metadata
        page_texts: List of all page texts
    """
    first_page_text = page_texts[letter.start_page]
    
    try:
        # Try to get metadata from LLM
        metadata = call_llm_for_metadata(first_page_text)
        
        letter.date = metadata.get('date', 'XXX')
        letter.sender = metadata.get('sender', 'XXX')
        letter.topic = metadata.get('topic', 'XXX')
        
    except Exception as e:
        logger.warning(f"First LLM attempt failed: {e}")
        logger.info("Retrying with stricter prompt...")
        
        try:
            # Retry with stricter prompt
            metadata = call_llm_for_metadata(first_page_text, retry=True)
            
            letter.date = metadata.get('date', 'XXX')
            letter.sender = metadata.get('sender', 'XXX')
            letter.topic = metadata.get('topic', 'XXX')
            
        except Exception as retry_error:
            logger.error(f"LLM retry also failed: {retry_error}")
            logger.warning("Falling back to XXX for all fields")
            
            # Fallback to XXX for all fields
            letter.date = 'XXX'
            letter.sender = 'XXX'
            letter.topic = 'XXX'
    
    # Sanitize extracted values (remove newlines, excess whitespace)
    if letter.date != 'XXX':
        letter.date = letter.date.strip().replace('\n', '')[:50]
    if letter.sender != 'XXX':
        letter.sender = letter.sender.strip().replace('\n', '')[:50]
    if letter.topic != 'XXX':
        letter.topic = letter.topic.strip().replace('\n', '')[:50]
    
    logger.info(f"Metadata extracted for pages {letter.start_page + 1}-{letter.end_page + 1}:")
    logger.info(f"  Date: {letter.date}")
    logger.info(f"  Sender: {letter.sender}")
    logger.info(f"  Topic: {letter.topic}")


def extract_metadata(letter: Letter, page_texts: List[str]) -> None:
    """
    Extract metadata from the first page of a letter.
    This function now uses LLM-based extraction.
    
    Args:
        letter: Letter object to populate with metadata
        page_texts: List of all page texts
    """
    extract_metadata_with_llm(letter, page_texts)


def sanitize_filename_component(component: str) -> str:
    """
    Sanitize a filename component to be filesystem-safe.
    
    Args:
        component: String to sanitize
        
    Returns:
        Sanitized string
    """
    # Remove or replace unsafe characters
    component = re.sub(r'[<>:"/\\|?*]', '', component)
    # Replace multiple spaces/dashes with single dash
    component = re.sub(r'[\s\-]+', '-', component)
    # Remove leading/trailing dashes
    component = component.strip('-')
    return component


def generate_output_filename(letter: Letter, unrecognized_counter: int) -> str:
    """
    Generate output filename based on metadata.
    
    Args:
        letter: Letter object with metadata
        unrecognized_counter: Counter for unrecognized files
        
    Returns:
        Filename without extension
    """
    # Check if any field is XXX (unrecognized)
    if letter.date == "XXX" or letter.sender == "XXX" or letter.topic == "XXX":
        # Unrecognized format: XXX-XXX-XXX-01.pdf
        filename = f"XXX-XXX-XXX-{unrecognized_counter:02d}"
    else:
        # Recognized format: YYYY-MM-DD-Sender-Topic.pdf
        date = sanitize_filename_component(letter.date)
        sender = sanitize_filename_component(letter.sender)
        topic = sanitize_filename_component(letter.topic)
        filename = f"{date}-{sender}-{topic}"
    
    return filename


def split_pdf(input_pdf: Path, output_dir: Path, letters: List[Letter]) -> None:
    """
    Split PDF into separate files based on letter boundaries.
    
    Args:
        input_pdf: Path to input OCRed PDF
        output_dir: Directory for output files
        letters: List of Letter objects with metadata
    """
    logger.info(f"Splitting PDF into {len(letters)} letters")
    
    reader = PdfReader(input_pdf)
    unrecognized_counter = 1
    
    for letter in letters:
        # Generate filename
        is_recognized = (letter.date != "XXX" and letter.sender != "XXX" and letter.topic != "XXX")
        if is_recognized:
            filename = generate_output_filename(letter, 0)
        else:
            filename = generate_output_filename(letter, unrecognized_counter)
            unrecognized_counter += 1
        
        output_path = output_dir / f"{filename}.pdf"
        
        # Create PDF writer and add pages
        writer = PdfWriter()
        for page_num in range(letter.start_page, letter.end_page + 1):
            writer.add_page(reader.pages[page_num])
        
        # Write output file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        logger.info(f"Created output file: {output_path.name} (pages {letter.start_page + 1}-{letter.end_page + 1})")


def process_pdf(input_pdf: Path, output_dir: Path) -> None:
    """
    Main processing function: OCR, detect boundaries, extract metadata, split PDF.
    
    Args:
        input_pdf: Path to input PDF file
        output_dir: Path to output directory
    """
    logger.info("=" * 80)
    logger.info("PDF Letter Splitter - Starting processing")
    logger.info("=" * 80)
    logger.info(f"Input PDF: {input_pdf}")
    logger.info(f"Output directory: {output_dir}")
    
    # Validate input
    if not input_pdf.exists():
        logger.error(f"Input PDF not found: {input_pdf}")
        sys.exit(1)
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: OCR the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_ocr:
        temp_ocr_path = Path(temp_ocr.name)
    
    try:
        ocr_pdf(input_pdf, temp_ocr_path)
        
        # Step 2: Extract text from each page
        page_texts = extract_page_text(temp_ocr_path)
        
        # Step 3: Detect letter boundaries
        letters = detect_letter_boundaries(page_texts)
        
        # Step 4: Extract metadata for each letter
        for letter in letters:
            extract_metadata(letter, page_texts)
        
        # Step 5: Split PDF into separate files
        split_pdf(temp_ocr_path, output_dir, letters)
        
        logger.info("=" * 80)
        logger.info("Processing completed successfully")
        logger.info("=" * 80)
        
    finally:
        # Clean up temporary OCR file
        if temp_ocr_path.exists():
            temp_ocr_path.unlink()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='PDF Letter Splitter - Automatic multi-letter PDF processing',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input_pdf',
        type=str,
        nargs='?',
        default=None,
        help='Path to input PDF file (or set INPUT_PDF env var)'
    )
    parser.add_argument(
        'output_dir',
        type=str,
        nargs='?',
        default=None,
        help='Path to output directory (or set OUTPUT_DIR env var)'
    )
    
    args = parser.parse_args()
    
    # Get input_pdf from args or environment
    input_pdf_str = args.input_pdf or os.getenv('INPUT_PDF')
    if not input_pdf_str:
        logger.error("No input PDF specified. Provide as argument or set INPUT_PDF environment variable.")
        sys.exit(1)
    
    # Get output_dir from args or environment
    output_dir_str = args.output_dir or os.getenv('OUTPUT_DIR')
    if not output_dir_str:
        logger.error("No output directory specified. Provide as argument or set OUTPUT_DIR environment variable.")
        sys.exit(1)
    
    input_pdf = Path(input_pdf_str)
    output_dir = Path(output_dir_str)
    
    try:
        process_pdf(input_pdf, output_dir)
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
