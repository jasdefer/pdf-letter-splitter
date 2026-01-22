#!/usr/bin/env python3
"""
PDF processing module for splitting multi-letter PDFs into individual files.

This module provides functionality to:
- Split a PDF into individual files based on Letter groupings
- Name files according to extracted metadata (Date-Sender-Topic)
- Handle filename sanitization and collision avoidance
- Create output directories as needed
"""

import logging
import re
from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    raise ImportError("pypdf is required. Install with: pip install pypdf")

from splitter import Letter

# Configure module logger
logger = logging.getLogger(__name__)

# Maximum filename length (conservative limit for cross-platform compatibility)
MAX_FILENAME_LENGTH = 200

# Common stop words to filter from topics (English and German)
STOP_WORDS = {
    'the', 'a', 'an', 'in', 'for', 'and', 'or', 'of', 'to', 'at', 'by', 'with',
    'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines',
    'und', 'oder', 'für', 'von', 'zu', 'mit', 'bei', 'im', 'am'
}


class PDFProcessor:
    """
    Handles PDF splitting and file naming based on extracted metadata.
    
    Attributes:
        output_dir: Directory where split PDFs will be written
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize the PDF processor.
        
        Args:
            output_dir: Path to output directory (will be created if it doesn't exist)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF processor initialized with output directory: {self.output_dir}")
    
    def process_letters(self, input_pdf_path: Path, letters: list[Letter]) -> list[Path]:
        """
        Split a PDF into individual files based on Letter groupings.
        
        Args:
            input_pdf_path: Path to the input PDF file
            letters: List of Letter objects defining page groupings
            
        Returns:
            List of paths to created PDF files
            
        Raises:
            FileNotFoundError: If input PDF doesn't exist
            RuntimeError: If PDF processing fails
        """
        if not input_pdf_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")
        
        logger.info(f"Processing {len(letters)} letters from {input_pdf_path}")
        
        # Load the input PDF
        try:
            reader = PdfReader(str(input_pdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF: {e}")
        
        created_files = []
        
        for i, letter in enumerate(letters, start=1):
            output_path = self._split_letter(reader, letter, i)
            created_files.append(output_path)
        
        logger.info(f"Successfully created {len(created_files)} PDF files")
        return created_files
    
    def _split_letter(self, reader: PdfReader, letter: Letter, letter_num: int) -> Path:
        """
        Extract pages for a single letter and write to a new PDF.
        
        Args:
            reader: PdfReader for the input PDF
            letter: Letter object with page information
            letter_num: Sequential letter number (for logging)
            
        Returns:
            Path to the created PDF file
        """
        if not letter.pages:
            raise ValueError(f"Letter {letter_num} has no pages")
        
        # Construct filename from metadata
        filename = self._construct_filename(letter)
        
        # Handle collision
        output_path = self._get_unique_filepath(filename)
        
        # Create PDF writer and add pages
        writer = PdfWriter()
        
        # Get page range (convert 1-indexed scan_page_num to 0-indexed pypdf indices)
        page_nums = [page.scan_page_num for page in letter.pages]
        pages_added = 0
        
        for scan_page_num in page_nums:
            # Convert to 0-indexed for pypdf
            pypdf_index = scan_page_num - 1
            
            if pypdf_index < 0 or pypdf_index >= len(reader.pages):
                logger.warning(
                    f"Page {scan_page_num} out of range (PDF has {len(reader.pages)} pages). Skipping."
                )
                continue
            
            writer.add_page(reader.pages[pypdf_index])
            pages_added += 1
        
        # Validate that at least one page was added
        if pages_added == 0:
            raise RuntimeError(
                f"Letter {letter_num}: No valid pages could be added. "
                f"Requested pages {page_nums} but PDF has {len(reader.pages)} pages."
            )
        
        # Write to file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        # Log the creation
        page_range = f"{min(page_nums)}-{max(page_nums)}" if len(page_nums) > 1 else str(page_nums[0])
        logger.info(f"Created {output_path.name} (Pages: {page_range})")
        
        return output_path
    
    def _construct_filename(self, letter: Letter) -> str:
        """
        Construct a filename from letter metadata.
        
        Format: YYYYMMDD-Sender-Topic.pdf
        If any part is missing: 0_Incomplete_YYYYMMDD-Sender-Topic.pdf
        
        Args:
            letter: Letter object with metadata
            
        Returns:
            Sanitized filename (without extension)
        """
        # Extract metadata
        date_str = self._extract_date(letter)
        sender_str = self._extract_sender(letter)
        topic_str = self._extract_topic(letter)
        
        # Check if any part is missing
        is_incomplete = not date_str or not sender_str or not topic_str
        
        # Use empty string for missing parts
        date_part = date_str or ''
        sender_part = sender_str or ''
        topic_part = topic_str or ''
        
        # Construct filename
        filename_parts = [date_part, sender_part, topic_part]
        filename_core = '-'.join(filter(None, filename_parts))
        
        # Handle empty filename
        if not filename_core:
            filename_core = 'Unknown'
        
        # Prepend incomplete prefix if needed
        if is_incomplete:
            filename_core = f"0_Incomplete_{filename_core}"
        
        # Truncate if too long (reserve space for .pdf and collision suffix)
        max_core_length = MAX_FILENAME_LENGTH - 10  # Reserve for .pdf and _99 suffix
        if len(filename_core) > max_core_length:
            filename_core = filename_core[:max_core_length]
            logger.debug(f"Truncated filename to {max_core_length} characters")
        
        return filename_core
    
    def _extract_date(self, letter: Letter) -> Optional[str]:
        """
        Extract and format date from letter.
        
        Args:
            letter: Letter object
            
        Returns:
            Date in YYYYMMDD format, or None if not found
        """
        master_date = letter.master_date
        if master_date:
            # master_date is in YYYY-MM-DD format, convert to YYYYMMDD
            return master_date.replace('-', '')
        return None
    
    def _extract_sender(self, letter: Letter) -> Optional[str]:
        """
        Extract and sanitize sender name from letter.
        
        Takes extracted_name from address block, removes special characters,
        and uses the longest word if there are multiple words.
        
        Args:
            letter: Letter object
            
        Returns:
            Sanitized sender name, or None if not found
        """
        if not letter.pages:
            return None
        
        first_page = letter.pages[0]
        if not first_page.address_block.found or not first_page.address_block.extracted_name:
            return None
        
        extracted_name = first_page.address_block.extracted_name
        
        # Remove special characters (keep letters, numbers, spaces)
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', extracted_name)
        
        # Split into words and find the longest one
        words = sanitized.split()
        if not words:
            return None
        
        longest_word = max(words, key=len)
        return longest_word
    
    def _extract_topic(self, letter: Letter) -> Optional[str]:
        """
        Extract and sanitize topic/subject from letter.
        
        Removes stop words and keeps first three significant words.
        
        Args:
            letter: Letter object
            
        Returns:
            Sanitized topic string, or None if not found
        """
        master_subject = letter.master_subject
        if not master_subject:
            return None
        
        # Remove special characters (keep letters, numbers, spaces)
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', master_subject)
        
        # Split into words
        words = sanitized.split()
        
        # Filter out stop words and short words (less than 3 characters)
        significant_words = [
            word for word in words
            if word.lower() not in STOP_WORDS and len(word) >= 3
        ]
        
        # Take first three significant words
        topic_words = significant_words[:3]
        
        if not topic_words:
            # If no significant words, use first 3 words from original (also filtering short words)
            topic_words = [word for word in words if len(word) >= 3][:3]
            
            # If still empty, take any words (even short ones) as last resort
            if not topic_words:
                topic_words = words[:3]
        
        if not topic_words:
            return None
        
        return ''.join(topic_words)
    
    def _get_unique_filepath(self, filename_base: str) -> Path:
        """
        Get a unique filepath, handling collisions by appending _1, _2, etc.
        
        Args:
            filename_base: Base filename without extension
            
        Returns:
            Unique Path object
        """
        # Try the base filename first
        filepath = self.output_dir / f"{filename_base}.pdf"
        
        if not filepath.exists():
            return filepath
        
        # Handle collision with suffix
        counter = 1
        while True:
            filepath = self.output_dir / f"{filename_base}_{counter}.pdf"
            if not filepath.exists():
                logger.debug(f"Collision handled: appended _{counter} suffix")
                return filepath
            counter += 1
            
            # Safety check to avoid infinite loop
            if counter > 1000:
                raise RuntimeError(f"Too many collisions for filename: {filename_base}")
