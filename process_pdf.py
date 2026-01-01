#!/usr/bin/env python3
"""
PDF Letter Splitter - Automatic multi-letter PDF processing

Accepts a single scanned multi-page PDF and:
1. OCR the full PDF (German and English)
2. Extract per-page text
3. Detect letter boundaries using heuristics
4. Split into one PDF per letter
5. Extract metadata (date, sender, topic) from first page
6. Name outputs accordingly
"""

import argparse
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import ocrmypdf
import requests
from pypdf import PdfReader, PdfWriter


# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# LLM Configuration
LLAMA_SERVER_URL = os.getenv('LLAMA_SERVER_URL', 'http://localhost:8080')
LLAMA_ENABLED = os.getenv('LLAMA_ENABLED', 'false').lower() in ('true', '1', 'yes')
LLAMA_TIMEOUT = 30  # seconds
LLAMA_ENDPOINT = '/completion'  # llama.cpp completion endpoint

# Text limits for LLM processing
SENDER_TEXT_LIMIT = 1000  # characters - focus on header for sender
TOPIC_TEXT_LIMIT = 2000   # characters - more context for topic

# Character filtering pattern for German filenames
ALLOWED_CHARS_PATTERN = r'[^a-zA-ZäöüßÄÖÜ\s\-]'


def call_llm(prompt: str, max_tokens: int = 50) -> Optional[str]:
    """
    Call the llama.cpp server with a prompt and return the response.
    
    Args:
        prompt: The prompt to send to the LLM
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        The LLM response text or None if:
        - LLAMA_ENABLED is False
        - Network/connection errors occur
        - HTTP request fails (non-2xx status)
        - Response format is unexpected
        - Timeout occurs (after LLAMA_TIMEOUT seconds)
    """
    if not LLAMA_ENABLED:
        logger.debug("LLM is disabled, skipping call")
        return None
    
    try:
        url = f"{LLAMA_SERVER_URL}{LLAMA_ENDPOINT}"
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.1,  # Low temperature for consistent outputs
            "stop": ["\n", "\n\n"],  # Stop at newlines
            "stream": False
        }
        
        response = requests.post(url, json=payload, timeout=LLAMA_TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        if 'content' in result:
            return result['content'].strip()
        
        logger.warning(f"Unexpected LLM response format: {result}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"LLM call failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error calling LLM: {e}")
        return None


def normalize_sender_with_llm(ocr_text: str, fallback_sender: str) -> str:
    """
    Use LLM to normalize sender name to max 3 words, no addresses/numbers.
    
    Args:
        ocr_text: OCR text from the first page of the letter
        fallback_sender: Heuristic-extracted sender name as fallback
        
    Returns:
        Normalized sender name (max 3 words)
    """
    if not LLAMA_ENABLED:
        return fallback_sender
    
    # Limit input text to first N characters to focus on header
    text_excerpt = ocr_text[:SENDER_TEXT_LIMIT] if len(ocr_text) > SENDER_TEXT_LIMIT else ocr_text
    
    prompt = f"""Extract the sender name from this letter text. Return ONLY the organization or person name.
Rules:
- Maximum 3 words
- No addresses, no numbers, no special characters
- Example: "Deutsche Bank" or "Finanzamt München" or "Max Müller"

Letter text:
{text_excerpt}

Sender name:"""
    
    result = call_llm(prompt, max_tokens=20)
    
    if result:
        # Clean and validate result
        result = result.strip()
        # Remove quotes if present
        result = result.strip('"\'')
        # Check word count
        words = result.split()
        if 1 <= len(words) <= 3:
            # Remove numbers and special characters
            cleaned = re.sub(ALLOWED_CHARS_PATTERN, '', result)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned and len(cleaned) > 2:
                logger.info(f"LLM normalized sender: '{fallback_sender}' -> '{cleaned}'")
                return cleaned.replace(' ', '-')
    
    logger.debug(f"LLM sender normalization failed, using fallback: {fallback_sender}")
    return fallback_sender


def normalize_topic_with_llm(ocr_text: str, fallback_topic: str) -> str:
    """
    Use LLM to normalize topic to max 4 words, human-readable label.
    
    Args:
        ocr_text: OCR text from the full letter
        fallback_topic: Heuristic-extracted topic as fallback
        
    Returns:
        Normalized topic (max 4 words)
    """
    if not LLAMA_ENABLED:
        return fallback_topic
    
    # Limit input text to first N characters for topic extraction
    text_excerpt = ocr_text[:TOPIC_TEXT_LIMIT] if len(ocr_text) > TOPIC_TEXT_LIMIT else ocr_text
    
    prompt = f"""What is the main topic or purpose of this letter? Provide a short descriptive label.
Rules:
- Maximum 4 words
- No dates, no reference numbers
- Human-readable, like: "Rechnung", "Vertragsänderung", "Zahlungserinnerung", "Jahresabrechnung"
- German preferred for German letters

Letter text:
{text_excerpt}

Topic:"""
    
    result = call_llm(prompt, max_tokens=30)
    
    if result:
        # Clean and validate result
        result = result.strip()
        # Remove quotes if present
        result = result.strip('"\'')
        # Check word count
        words = result.split()
        if 1 <= len(words) <= 4:
            # Remove numbers and special characters (but keep German letters)
            cleaned = re.sub(ALLOWED_CHARS_PATTERN, '', result)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned and len(cleaned) > 2:
                logger.info(f"LLM normalized topic: '{fallback_topic}' -> '{cleaned}'")
                return cleaned.replace(' ', '-')
    
    logger.debug(f"LLM topic normalization failed, using fallback: {fallback_topic}")
    return fallback_topic


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


def extract_date(text: str) -> Optional[str]:
    """
    Extract date from text and normalize to YYYY-MM-DD format.
    
    Args:
        text: Text to search for dates
        
    Returns:
        Date in YYYY-MM-DD format or None
    """
    # Pattern 1: DD.MM.YYYY
    match = re.search(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', text)
    if match:
        day, month, year = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Pattern 2: DD.MM.YY (assume 20XX for YY < 50, else 19XX)
    match = re.search(r'\b(\d{1,2})\.(\d{1,2})\.(\d{2})\b', text)
    if match:
        day, month, year = match.groups()
        try:
            year_int = int(year)
            # Use sliding window: 00-49 -> 2000-2049, 50-99 -> 1950-1999
            year_full = 2000 + year_int if year_int < 50 else 1900 + year_int
            date_obj = datetime(year_full, int(month), int(day))
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Pattern 3: YYYY-MM-DD
    match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if match:
        year, month, day = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Pattern 4: German month names
    german_months = {
        'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6,
        'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12
    }
    for month_name, month_num in german_months.items():
        pattern = rf'\b(\d{{1,2}})\.\s*{month_name}\s+(\d{{4}})\b'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day, year = match.groups()
            try:
                date_obj = datetime(int(year), month_num, int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    return None


def extract_sender(text: str) -> Optional[str]:
    """
    Extract sender from text (company or person name).
    
    Args:
        text: Text to search for sender
        
    Returns:
        Sender name or None
    """
    # Look for common sender patterns in the first portion of the text
    first_lines = text.split('\n')[:20]  # Check first 20 lines
    
    # Pattern 1: Line with GmbH, AG, e.V., etc.
    for line in first_lines:
        if re.search(r'\b(?:GmbH|AG|KG|OHG|e\.V\.|eV)\b', line):
            # Clean and extract company name
            line = line.strip()
            if len(line) > 3 and len(line) < 100:
                # Remove special characters, keep alphanumeric and spaces
                sender = re.sub(r'[^\w\s\-äöüßÄÖÜ]', '', line)
                sender = re.sub(r'\s+', '-', sender.strip())
                if sender:
                    return sender[:50]  # Limit length
    
    # Pattern 2: Look for lines with common government/institution keywords
    institution_keywords = ['Finanzamt', 'Versicherung', 'Bank', 'Kasse', 'Amt', 'Behörde', 'Gericht']
    for line in first_lines:
        for keyword in institution_keywords:
            if keyword.lower() in line.lower():
                line = line.strip()
                if len(line) > 3 and len(line) < 100:
                    sender = re.sub(r'[^\w\s\-äöüßÄÖÜ]', '', line)
                    sender = re.sub(r'\s+', '-', sender.strip())
                    if sender:
                        return sender[:50]
    
    # Pattern 3: Capitalized words that might be names (2-3 words)
    for line in first_lines:
        # Look for 2-3 consecutive capitalized words
        match = re.search(r'\b([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,2})\b', line)
        if match:
            sender = match.group(1)
            sender = re.sub(r'\s+', '-', sender.strip())
            if len(sender) > 3:
                return sender[:50]
    
    return None


def extract_topic(text: str) -> Optional[str]:
    """
    Extract topic/subject from text.
    
    Args:
        text: Text to search for topic
        
    Returns:
        Topic or None
    """
    # Pattern 1: Explicit subject line (Betreff, Subject, Re:)
    subject_patterns = [
        r'(?:Betreff|Betr\.|Subject|Re)[\s:]+(.+?)(?:\n|$)',
        r'(?:Thema|Topic)[\s:]+(.+?)(?:\n|$)',
    ]
    
    for pattern in subject_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            # Clean up
            topic = re.sub(r'[^\w\s\-äöüßÄÖÜ]', '', topic)
            topic = re.sub(r'\s+', '-', topic.strip())
            if topic and len(topic) > 2:
                return topic[:50]
    
    # Pattern 2: Look for lines with keywords that suggest topic
    topic_keywords = ['Mahnung', 'Rechnung', 'Angebot', 'Kündigung', 'Vertrag', 
                      'Bescheid', 'Mitteilung', 'Einladung', 'Bestätigung']
    
    lines = text.split('\n')
    for line in lines[:30]:  # Check first 30 lines
        for keyword in topic_keywords:
            if keyword.lower() in line.lower():
                # Extract the line containing the keyword
                line = line.strip()
                if len(line) > 3 and len(line) < 100:
                    topic = re.sub(r'[^\w\s\-äöüßÄÖÜ]', '', line)
                    topic = re.sub(r'\s+', '-', topic.strip())
                    if topic:
                        return topic[:50]
    
    return None


def extract_metadata(letter: Letter, page_texts: List[str]) -> None:
    """
    Extract metadata from the first page of a letter.
    
    Args:
        letter: Letter object to populate with metadata
        page_texts: List of all page texts
    """
    first_page_text = page_texts[letter.start_page]
    
    # Get text for all pages of this letter (for topic extraction)
    letter_full_text = '\n'.join(page_texts[letter.start_page:letter.end_page + 1])
    
    # Extract date (not normalized by LLM)
    letter.date = extract_date(first_page_text)
    if not letter.date:
        letter.date = "XXX"
    
    # Extract sender using heuristics
    heuristic_sender = extract_sender(first_page_text)
    if not heuristic_sender:
        heuristic_sender = "XXX"
    
    # Normalize sender with LLM (with heuristic as fallback)
    if heuristic_sender != "XXX":
        letter.sender = normalize_sender_with_llm(first_page_text, heuristic_sender)
    else:
        letter.sender = "XXX"
    
    # Extract topic using heuristics
    heuristic_topic = extract_topic(first_page_text)
    if not heuristic_topic:
        heuristic_topic = "XXX"
    
    # Normalize topic with LLM (with heuristic as fallback)
    if heuristic_topic != "XXX":
        letter.topic = normalize_topic_with_llm(letter_full_text, heuristic_topic)
    else:
        letter.topic = "XXX"
    
    logger.info(f"Metadata extracted for pages {letter.start_page + 1}-{letter.end_page + 1}:")
    logger.info(f"  Date: {letter.date}")
    logger.info(f"  Sender: {letter.sender}")
    logger.info(f"  Topic: {letter.topic}")


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
        help='Path to input PDF file'
    )
    parser.add_argument(
        'output_dir',
        type=str,
        help='Path to output directory'
    )
    
    args = parser.parse_args()
    
    input_pdf = Path(args.input_pdf)
    output_dir = Path(args.output_dir)
    
    try:
        process_pdf(input_pdf, output_dir)
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
