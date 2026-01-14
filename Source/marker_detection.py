#!/usr/bin/env python3

import pandas as pd
import re
from typing import Optional, Tuple
from page_analysis_data import LetterPageIndex, TextMarker


def detect_letter_page_index(page_df: pd.DataFrame) -> LetterPageIndex:
    raise NotImplementedError


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
    if page_df.empty or 'level' not in page_df.columns:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Greeting patterns for German and English
    # These patterns will be matched case-insensitively against reconstructed lines
    greeting_patterns = [
        # German patterns
        r'\bsehr\s+geehrte[rs]?\b',  # Sehr geehrte/r/s
        r'\bguten\s+tag\b',           # Guten Tag
        r'\bhallo\b',                 # Hallo
        r'\bliebe[rs]?\b',            # Liebe/r/s
        # English patterns
        r'\bdear\b',                  # Dear
        r'\bhello\b',                 # Hello
        r'\bhi\b',                    # Hi
        r'\bgood\s+morning\b',        # Good morning
        r'\bgood\s+afternoon\b',      # Good afternoon
        r'\bgood\s+evening\b',        # Good evening
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
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    # Group words by line to reconstruct text line by line
    if 'line_num' in words_df.columns:
        # Sort by line_num and position within line
        words_df = words_df.sort_values(['line_num', 'left'])
        lines = words_df.groupby('line_num')
    else:
        # Fallback: group by vertical position (top coordinate)
        # Use a small tolerance for grouping words on the same line
        words_df['line_group'] = (words_df['top'] / 10).round().astype(int)
        words_df = words_df.sort_values(['line_group', 'left'])
        lines = words_df.groupby('line_group')
    
    # Search for greetings line by line
    for line_key, line_group in lines:
        # Reconstruct the line text
        line_text = ' '.join(line_group['text'].astype(str))
        
        # Check each greeting pattern
        for pattern in greeting_patterns:
            match = re.search(pattern, line_text, re.IGNORECASE)
            if match:
                # Found a greeting! Get the position of the first word in the match
                matched_text = match.group(0)
                
                # Find the first word of the greeting in the line_group
                # We need to map back from the reconstructed text to the original words
                first_word_idx = _find_first_word_of_match(line_group, match, line_text)
                
                if first_word_idx is not None:
                    first_word = line_group.iloc[first_word_idx]
                    x_rel = first_word['left'] / page_width
                    y_rel = first_word['top'] / page_height
                else:
                    # Fallback: use first word in line
                    first_word = line_group.iloc[0]
                    x_rel = first_word['left'] / page_width
                    y_rel = first_word['top'] / page_height
                
                return TextMarker(
                    found=True,
                    raw=matched_text,
                    x_rel=float(x_rel),
                    y_rel=float(y_rel)
                )
    
    # No greeting found
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


def _find_first_word_of_match(line_group: pd.DataFrame, match: re.Match, line_text: str) -> Optional[int]:
    """
    Find the index of the first word in line_group that corresponds to the regex match.
    
    Args:
        line_group: DataFrame of words in the line
        match: Regex match object
        line_text: Reconstructed line text
    
    Returns:
        Index in line_group of the first word, or None if not found
    """
    match_start = match.start()
    
    # Count characters in reconstructed text to find which word the match starts in
    current_pos = 0
    for idx, (_, word_row) in enumerate(line_group.iterrows()):
        word_text = str(word_row['text'])
        word_start = current_pos
        word_end = current_pos + len(word_text)
        
        # Check if match starts within this word's range
        if word_start <= match_start < word_end:
            return idx
        
        # Account for space after word
        current_pos = word_end + 1
    
    return None


def detect_goodbye(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_betreff(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_address_block(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError
