#!/usr/bin/env python3
"""
Rule-based PDF letter segmentation and metadata extraction.

This module processes OCR text output from extract_text.py to identify letter boundaries
and extract metadata (date, sender, topic) from formal correspondence.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def find_date(page_text: str) -> Optional[str]:
    """
    Extract date from the top section of a page using prioritized regex patterns.
    
    Searches for common date formats in the header area (top 15% of text).
    Prioritizes ISO format, then European format, then US format.
    
    Args:
        page_text: OCR text from a single page
        
    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    if not page_text:
        return None
    
    # Extract top portion (approximately first 15% of lines)
    lines = page_text.split('\n')
    top_lines_count = max(5, len(lines) // 7)  # At least 5 lines, or ~15%
    top_section = '\n'.join(lines[:top_lines_count])
    
    # Date patterns in priority order
    date_patterns = [
        # ISO format: YYYY-MM-DD or YYYY/MM/DD
        (r'\b(20\d{2})[/-](0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])\b', 
         lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
        
        # European format: DD.MM.YYYY or DD/MM/YYYY
        (r'\b(0[1-9]|[12]\d|3[01])[./](0[1-9]|1[0-2])[./](20\d{2})\b',
         lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),
        
        # US format: MM/DD/YYYY or MM-DD-YYYY
        (r'\b(0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])[/-](20\d{2})\b',
         lambda m: f"{m.group(3)}-{m.group(1)}-{m.group(2)}"),
        
        # German format with month name: DD. Month YYYY (e.g., "15. Januar 2026")
        (r'\b(0?[1-9]|[12]\d|3[01])\.\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(20\d{2})\b',
         lambda m: _convert_german_month_date(m.group(1), m.group(2), m.group(3))),
        
        # English format with month name: Month DD, YYYY (e.g., "January 15, 2026")
        (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(0?[1-9]|[12]\d|3[01]),?\s+(20\d{2})\b',
         lambda m: _convert_english_month_date(m.group(2), m.group(1), m.group(3))),
    ]
    
    for pattern, converter in date_patterns:
        match = re.search(pattern, top_section, re.IGNORECASE)
        if match:
            try:
                date_str = converter(match)
                # Validate the date is actually valid
                if _is_valid_date(date_str):
                    return date_str
            except (ValueError, IndexError):
                continue
    
    return None


def _is_valid_date(date_str: str) -> bool:
    """
    Validate that a date string in YYYY-MM-DD format represents a real date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        True if the date is valid, False otherwise
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _convert_german_month_date(day: str, month_name: str, year: str) -> str:
    """Convert German month name to numeric format."""
    months = {
        'januar': '01', 'februar': '02', 'märz': '03', 'april': '04',
        'mai': '05', 'juni': '06', 'juli': '07', 'august': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'dezember': '12'
    }
    month_num = months.get(month_name.lower())
    if month_num:
        return f"{year}-{month_num}-{int(day):02d}"
    raise ValueError("Invalid German month name")


def _convert_english_month_date(day: str, month_name: str, year: str) -> str:
    """Convert English month name to numeric format."""
    months = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    month_num = months.get(month_name.lower())
    if month_num:
        return f"{year}-{month_num}-{int(day):02d}"
    raise ValueError("Invalid English month name")


def find_sender(page_text: str) -> Optional[str]:
    """
    Identify sender from the top section of a page.
    
    Examines the first 5-10 lines to find names or organizations,
    skipping common noise patterns.
    
    Args:
        page_text: OCR text from a single page
        
    Returns:
        Sender name/organization, or None if not found
    """
    if not page_text:
        return None
    
    lines = page_text.split('\n')
    # Examine first 5-10 non-empty lines
    candidates = []
    
    for line in lines[:15]:  # Check up to first 15 lines
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip noise patterns
        if _is_noise_line(line):
            continue
        
        # Look for organization indicators
        if _has_organization_marker(line):
            # Clean and return the organization name
            sender = _clean_sender_name(line)
            if sender and len(sender) > 2:
                return sender
        
        # Collect potential name lines (capitalized words)
        if _looks_like_name(line):
            candidates.append(line)
        
        # Stop after collecting enough candidates
        if len(candidates) >= 3:
            break
    
    # Return first candidate if found
    if candidates:
        sender = _clean_sender_name(candidates[0])
        if sender and len(sender) > 2:
            return sender
    
    return None


def _is_noise_line(line: str) -> bool:
    """Check if line is noise (page numbers, common headers, etc.)."""
    noise_patterns = [
        r'^page\s+\d+',
        r'^\d+\s+of\s+\d+',
        r'^seite\s+\d+',
        r'^\d+\s+von\s+\d+',
        r'^[|/\\-]+$',  # Lines with only separators
        r'^\d{1,3}$',  # Just a number
    ]
    
    for pattern in noise_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    return False


def _has_organization_marker(line: str) -> bool:
    """Check if line contains organization/company markers."""
    markers = [
        r'\bGmbH\b', r'\bAG\b', r'\bKG\b', r'\bOHG\b',  # German
        r'\bInc\b', r'\bLLC\b', r'\bLtd\b', r'\bCorp\b', r'\bLimited\b',  # English
        r'\be\.V\.\b', r'\bVerein\b',  # Associations
        r'\bFinanzamt\b', r'\bBehörde\b', r'\bAmt\b',  # Government
    ]
    
    for marker in markers:
        if re.search(marker, line, re.IGNORECASE):
            return True
    
    return False


def _looks_like_name(line: str) -> bool:
    """Check if line looks like a person or organization name."""
    # Skip very short or very long lines
    if len(line) < 3 or len(line) > 100:
        return False
    
    # Should have mostly letters and spaces
    alpha_count = sum(1 for c in line if c.isalpha() or c.isspace())
    if alpha_count < len(line) * 0.7:
        return False
    
    # Should start with capital letter
    if not line[0].isupper():
        return False
    
    return True


def _clean_sender_name(name: str) -> str:
    """Clean and normalize sender name."""
    # Remove excessive whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Remove common prefixes
    name = re.sub(r'^(From:|Von:|An:|To:)\s*', '', name, flags=re.IGNORECASE)
    
    return name


def find_topic(page_text: str) -> Optional[str]:
    """
    Extract topic/subject from a page.
    
    Searches for lines starting with Subject:, RE:, Regarding:, Betreff:, etc.
    Falls back to finding first prominent line before salutation.
    
    Args:
        page_text: OCR text from a single page
        
    Returns:
        Topic/subject string, or None if not found
    """
    if not page_text:
        return None
    
    lines = page_text.split('\n')
    
    # Look for explicit subject markers
    subject_patterns = [
        r'^(Subject|Betreff|RE|Regarding|Topic|Thema|Betrifft)\s*:\s*(.+)$',
    ]
    
    for line in lines[:30]:  # Check first 30 lines
        line = line.strip()
        for pattern in subject_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                topic = match.group(2).strip()
                if topic and len(topic) > 2:
                    return _clean_topic(topic)
    
    # Fallback: Look for bolded/capitalized line before salutation
    # We need to be smart about skipping sender info while still catching topics
    lines_checked = 0
    sender_lines_skipped = 0
    
    for i, line in enumerate(lines[:30]):
        line = line.strip()
        
        # Check if this is a salutation (stop searching)
        if _is_salutation(line):
            break
        
        # Skip short lines and noise
        if len(line) < 5 or _is_noise_line(line):
            continue
        
        # Skip lines that look like sender/organization, but only the first 2
        if sender_lines_skipped < 2 and _has_organization_marker(line):
            sender_lines_skipped += 1
            continue
        
        # Skip lines that look like addresses, but only the first 2
        if sender_lines_skipped < 2 and re.search(r'\b\d{5}\b|\bstraße\b', line, re.IGNORECASE):
            sender_lines_skipped += 1
            continue
        
        # Skip likely sender name lines (but only first couple)
        if sender_lines_skipped < 2 and i < 2 and _looks_like_name(line) and not line.isupper():
            sender_lines_skipped += 1
            continue
        
        lines_checked += 1
        
        # Look for ALL CAPS lines (likely headings)
        if line.isupper() and len(line) > 5:
            return _clean_topic(line)
        
        # Look for lines with multiple capital words (likely headings)
        words = line.split()
        if len(words) >= 2:  # Just need multiple words
            capital_words = sum(1 for w in words if w and w[0].isupper())
            if capital_words >= len(words) * 0.7:  # 70% capitalized
                return _clean_topic(line)
    
    return None


def _is_salutation(line: str) -> bool:
    """Check if line is a formal salutation."""
    salutations = [
        r'^(Dear|Sehr geehrte|Sehr geehrter|Liebe|Lieber|Hello|Hallo)',
        r'^(To whom it may concern|An wen es betrifft)',
    ]
    
    for pattern in salutations:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    return False


def _clean_topic(topic: str) -> str:
    """Clean and normalize topic string."""
    # Remove excessive whitespace
    topic = re.sub(r'\s+', ' ', topic).strip()
    
    # Remove trailing punctuation
    topic = topic.rstrip('.:,;')
    
    return topic


def _calculate_header_score(page_text: str) -> int:
    """
    Calculate a "header score" to determine if a page is the start of a new letter.
    
    Higher scores indicate stronger evidence of being a letter's first page.
    
    Args:
        page_text: OCR text from a single page
        
    Returns:
        Integer score (0-100+)
    """
    if not page_text:
        return 0
    
    score = 0
    lines = page_text.split('\n')
    top_section = '\n'.join(lines[:max(5, len(lines) // 7)])
    
    # Date in top section: +30 points
    if find_date(page_text):
        score += 30
    
    # Sender/organization found: +20 points
    if find_sender(page_text):
        score += 20
    
    # Subject line found: +15 points
    if find_topic(page_text):
        score += 15
    
    # Salutation found: +15 points
    for line in lines[:20]:
        if _is_salutation(line):
            score += 15
            break
    
    # "Page 1" or "1 of X" marker: +25 points
    page_one_patterns = [
        r'\bpage\s+1\b',
        r'\b1\s+of\s+\d+\b',
        r'\bseite\s+1\b',
        r'\b1\s+von\s+\d+\b',
    ]
    for pattern in page_one_patterns:
        if re.search(pattern, top_section, re.IGNORECASE):
            score += 25
            break
    
    # Address block structure: +10 points
    # Look for lines with postal codes, street patterns
    address_patterns = [
        r'\b\d{5}\b',  # Postal code (5 digits)
        r'\b\d{1,5}\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Straße|Str)\b',
    ]
    for pattern in address_patterns:
        if re.search(pattern, top_section, re.IGNORECASE):
            score += 10
            break
    
    return score


def analyze_documents(ocr_pages: List[str]) -> List[Dict[str, Any]]:
    """
    Main orchestrator function to segment and analyze letters from OCR pages.
    
    Iterates through pages, detects letter boundaries using header scoring,
    and extracts metadata for each identified letter.
    
    Args:
        ocr_pages: List of OCR text strings, one per page in sequential order
        
    Returns:
        List of dictionaries, each containing:
            - date: string or None
            - sender: string or None
            - topic: string or None
            - page_count: integer
            - start_page: integer (1-indexed page number where letter starts)
    """
    if not ocr_pages:
        return []
    
    letters = []
    current_letter = None
    header_threshold = 40  # Minimum score to trigger new letter
    
    for page_num, page_text in enumerate(ocr_pages, start=1):
        score = _calculate_header_score(page_text)
        
        # Check if this looks like the start of a new letter
        is_new_letter = score >= header_threshold
        
        # Special case: First page should always start a letter (unless completely empty)
        if page_num == 1 and page_text.strip():
            is_new_letter = True
        
        if is_new_letter:
            # Save previous letter if exists
            if current_letter is not None:
                letters.append(current_letter)
            
            # Start new letter
            current_letter = {
                'date': find_date(page_text),
                'sender': find_sender(page_text),
                'topic': find_topic(page_text),
                'page_count': 1,
                'start_page': page_num
            }
        else:
            # Continue current letter
            if current_letter is not None:
                current_letter['page_count'] += 1
            else:
                # Edge case: No letter started yet, start one now
                current_letter = {
                    'date': None,
                    'sender': None,
                    'topic': None,
                    'page_count': 1,
                    'start_page': page_num
                }
    
    # Don't forget the last letter
    if current_letter is not None:
        letters.append(current_letter)
    
    return letters
