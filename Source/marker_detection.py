#!/usr/bin/env python3

import pandas as pd
import re
from typing import Optional
from page_analysis_data import LetterPageIndex, TextMarker

# Constants for greeting detection
LINE_GROUPING_TOLERANCE = 10  # Pixels tolerance for grouping words on the same line


def detect_letter_page_index(page_df: pd.DataFrame) -> LetterPageIndex:
    return LetterPageIndex(
        found = False,
        current = None,
        total = None,
        raw = None
    )


def detect_greeting(page_df: pd.DataFrame) -> TextMarker:
    """
    Detect common letter greetings in German and English from OCR data.
    
    Args:
        page_df: DataFrame containing OCR data for a single page with columns:
                 'text', 'left', 'top', 'page_width', 'page_height', 'line_num', etc.
    
    Returns:
        TextMarker with:
            - found: True if greeting detected
            - raw: The matched greeting text
            - x_rel: Relative x position (0..1) of greeting start
            - y_rel: Relative y position (0..1) of greeting start
    """
    # Handle empty or invalid DataFrame
    required_columns = ['level', 'text', 'left', 'top', 'page_width', 'page_height']
    if page_df.empty or not all(col in page_df.columns for col in required_columns):
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Greeting patterns for German and English
    # These patterns will be matched case-insensitively against reconstructed lines
    # Strong patterns: match without restrictions
    strong_greeting_patterns = [
        r'\bsehr\s+geehrte[rs]?\b',  # Sehr geehrte/r/s
        r'\bguten\s+tag\b',           # Guten Tag
        r'\bdear\b',                  # Dear
        r'\bgood\s+morning\b',        # Good morning
        r'\bgood\s+afternoon\b',      # Good afternoon
        r'\bgood\s+evening\b',        # Good evening
    ]
    
    # Weak patterns: must be followed by ≤7 words and end with comma to reduce false positives
    # Pattern: greeting keyword + 1-7 words + comma
    weak_greeting_patterns = [
        r'\bhallo\b(?:\s+\S+){1,7},',    # Hallo + up to 7 words + comma
        r'\bliebe[rs]?\b(?:\s+\S+){1,7},',  # Liebe/r/s + up to 7 words + comma
        r'\bhello\b(?:\s+\S+){1,7},',    # Hello + up to 7 words + comma
        r'\bhi\b(?:\s+\S+){1,7},',       # Hi + up to 7 words + comma
    ]
    
    # Filter to word-level elements with non-empty text
    words_df = page_df[
        (page_df['level'] == 5) & 
        (page_df['text'].notna()) & 
        (page_df['text'].str.strip() != '')
    ].copy()
    
    if words_df.empty:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Get page dimensions (should be consistent across all rows)
    # Handle potential null values
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    if pd.isna(page_width) or pd.isna(page_height) or page_width <= 0 or page_height <= 0:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Group words by paragraph to avoid line_num collisions across blocks/paragraphs
    # Note: line_num is only unique within a paragraph in Tesseract TSV output
    if all(col in words_df.columns for col in ['page_num', 'block_num', 'par_num', 'line_num']):
        # Group by paragraph (page_num, block_num, par_num)
        # Sort within each paragraph by line_num, then left position
        words_df = words_df.sort_values(['page_num', 'block_num', 'par_num', 'line_num', 'left'])
        paragraphs = words_df.groupby(['page_num', 'block_num', 'par_num'])
    else:
        # Fallback: group by vertical position (top coordinate)
        # Use a small tolerance for grouping words on the same line
        words_df['line_group'] = (words_df['top'] / LINE_GROUPING_TOLERANCE).round().astype(int)
        words_df = words_df.sort_values(['line_group', 'left'])
        paragraphs = words_df.groupby('line_group')
    
    # Search for greetings paragraph by paragraph
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check strong greeting patterns first
        for pattern in strong_greeting_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Found a greeting! Return full paragraph as raw value
                return _create_greeting_marker(para_group, match, para_text, page_width, page_height)
        
        # Check weak greeting patterns (with comma constraint)
        for pattern in weak_greeting_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Found a greeting! Return full paragraph as raw value
                return _create_greeting_marker(para_group, match, para_text, page_width, page_height)
    
    # No greeting found
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


def _create_greeting_marker(para_group: pd.DataFrame, match: re.Match, para_text: str, 
                            page_width: float, page_height: float) -> TextMarker:
    """
    Create a TextMarker for a detected greeting.
    
    Args:
        para_group: DataFrame of words in the paragraph
        match: Regex match object
        para_text: Reconstructed paragraph text
        page_width: Page width in pixels
        page_height: Page height in pixels
    
    Returns:
        TextMarker with greeting information
    """
    # Find the first word of the greeting in the para_group
    first_word_idx = _find_first_word_of_match(para_group, match, para_text)
    
    if first_word_idx is not None:
        first_word = para_group.iloc[first_word_idx]
        x_rel = first_word['left'] / page_width
        y_rel = first_word['top'] / page_height
    else:
        # Fallback: use first word in paragraph
        first_word = para_group.iloc[0]
        x_rel = first_word['left'] / page_width
        y_rel = first_word['top'] / page_height
    
    # Store the full paragraph text as raw value for context and debugging
    return TextMarker(
        found=True,
        raw=para_text.strip(),
        x_rel=float(x_rel),
        y_rel=float(y_rel)
    )


def _find_first_word_of_match(para_group: pd.DataFrame, match: re.Match, para_text: str) -> Optional[int]:
    """
    Find the index of the first word in para_group that corresponds to the regex match.
    
    Args:
        para_group: DataFrame of words in the paragraph
        match: Regex match object
        para_text: Reconstructed paragraph text (words joined with single spaces)
    
    Returns:
        Index in para_group of the first word, or None if not found
    """
    match_start = match.start()
    
    # Count characters in reconstructed text to find which word the match starts in
    # Note: para_text is reconstructed with single spaces, so we use consistent spacing here
    current_pos = 0
    for idx, (_, word_row) in enumerate(para_group.iterrows()):
        word_text = str(word_row['text'])
        word_start = current_pos
        word_end = current_pos + len(word_text)
        
        # Check if match starts within this word's range
        if word_start <= match_start < word_end:
            return idx
        
        # Account for the single space we added during reconstruction
        current_pos = word_end + 1
    
    return None


def detect_goodbye(page_df: pd.DataFrame) -> TextMarker:
    """
    Detect common letter closing/goodbye phrases in German and English from OCR data.
    
    Args:
        page_df: DataFrame containing OCR data for a single page with columns:
                 'text', 'left', 'top', 'page_width', 'page_height', 'line_num', etc.
    
    Returns:
        TextMarker with:
            - found: True if goodbye detected
            - raw: The matched goodbye text
            - x_rel: Relative x position (0..1) of goodbye start
            - y_rel: Relative y position (0..1) of goodbye start
    """
    # Handle empty or invalid DataFrame
    required_columns = ['level', 'text', 'left', 'top', 'page_width', 'page_height']
    if page_df.empty or not all(col in page_df.columns for col in required_columns):
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Goodbye patterns for German and English
    # These patterns will be matched case-insensitively against reconstructed lines
    # Note: More specific (multi-word) patterns must come before less specific (single-word) patterns
    # German patterns handle umlaut variations: ü->ue, ß->ss
    goodbye_patterns = [
        # German patterns (multi-word first, then single-word)
        r'\bmit\s+freundlichen\s+gr(ü|ue)(ß|ss)e?n?\b',  # Mit freundlichen Grüßen/Gruessen
        r'\bmit\s+besten\s+gr(ü|ue)(ß|ss)e?n?\b',        # Mit besten Grüßen/Gruessen
        r'\bmit\s+herzlichen\s+gr(ü|ue)(ß|ss)e?n?\b',    # Mit herzlichen Grüßen/Gruessen
        r'\bfreundliche\s+gr(ü|ue)(ß|ss)e?\b',           # Freundliche Grüße/Gruesse
        r'\bviele\s+gr(ü|ue)(ß|ss)e?\b',                 # Viele Grüße/Gruesse
        r'\bliebe\s+gr(ü|ue)(ß|ss)e?\b',                 # Liebe Grüße/Gruesse
        r'\bbeste\s+gr(ü|ue)(ß|ss)e?\b',                 # Beste Grüße/Gruesse
        r'\bhochachtungsvoll\b',                          # Hochachtungsvoll
        # English patterns (multi-word first, then single-word)
        r'\byours\s+sincerely\b',                         # Yours sincerely
        r'\byours\s+faithfully\b',                        # Yours faithfully
        r'\byours\s+truly\b',                             # Yours truly
        r'\bkind\s+regards\b',                            # Kind regards
        r'\bbest\s+regards\b',                            # Best regards
        r'\bwarm\s+regards\b',                            # Warm regards
        r'\bwarmest\s+regards\b',                         # Warmest regards
        r'\bsincerely\b',                                 # Sincerely (must come after "yours sincerely")
        r'\bcordially\b',                                 # Cordially
        r'\brespectfully\b',                              # Respectfully
    ]
    
    # Filter to word-level elements with non-empty text
    words_df = page_df[
        (page_df['level'] == 5) & 
        (page_df['text'].notna()) & 
        (page_df['text'].str.strip() != '')
    ].copy()
    
    if words_df.empty:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Get page dimensions (should be consistent across all rows)
    # Handle potential null values
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    if pd.isna(page_width) or pd.isna(page_height) or page_width <= 0 or page_height <= 0:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Group words by paragraph to avoid line_num collisions across blocks/paragraphs
    # Note: line_num is only unique within a paragraph in Tesseract TSV output
    if all(col in words_df.columns for col in ['page_num', 'block_num', 'par_num', 'line_num']):
        # Group by paragraph (page_num, block_num, par_num)
        # Sort within each paragraph by line_num, then left position
        words_df = words_df.sort_values(['page_num', 'block_num', 'par_num', 'line_num', 'left'])
        paragraphs = words_df.groupby(['page_num', 'block_num', 'par_num'])
    else:
        # Fallback: group by vertical position (top coordinate)
        # Use a small tolerance for grouping words on the same line
        words_df['line_group'] = (words_df['top'] / LINE_GROUPING_TOLERANCE).round().astype(int)
        words_df = words_df.sort_values(['line_group', 'left'])
        paragraphs = words_df.groupby('line_group')
    
    # Search for goodbyes paragraph by paragraph
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check goodbye patterns
        for pattern in goodbye_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Found a goodbye! Return full paragraph as raw value
                return _create_goodbye_marker(para_group, match, para_text, page_width, page_height)
    
    # No goodbye found
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


def _create_goodbye_marker(para_group: pd.DataFrame, match: re.Match, para_text: str, 
                           page_width: float, page_height: float) -> TextMarker:
    """
    Create a TextMarker for a detected goodbye.
    
    Args:
        para_group: DataFrame of words in the paragraph
        match: Regex match object
        para_text: Reconstructed paragraph text
        page_width: Page width in pixels
        page_height: Page height in pixels
    
    Returns:
        TextMarker with goodbye information
    """
    # Find the first word of the goodbye in the para_group
    first_word_idx = _find_first_word_of_match(para_group, match, para_text)
    
    if first_word_idx is not None:
        first_word = para_group.iloc[first_word_idx]
        x_rel = first_word['left'] / page_width
        y_rel = first_word['top'] / page_height
    else:
        # Fallback: use first word in paragraph
        first_word = para_group.iloc[0]
        x_rel = first_word['left'] / page_width
        y_rel = first_word['top'] / page_height
    
    # Store the full paragraph text as raw value for context and debugging
    return TextMarker(
        found=True,
        raw=para_text.strip(),
        x_rel=float(x_rel),
        y_rel=float(y_rel)
    )


def detect_betreff(page_df: pd.DataFrame) -> TextMarker:
    return TextMarker(
        found = False,
        raw = None,
        x_rel = None,
        y_rel = None
    )


def detect_address_block(page_df: pd.DataFrame) -> TextMarker:
    return TextMarker(
        found = False,
        raw = None,
        x_rel = None,
        y_rel = None
    )
