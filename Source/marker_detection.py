#!/usr/bin/env python3

import pandas as pd
import re
from typing import Optional, Tuple, List
from datetime import datetime
from page_analysis_data import LetterPageIndex, TextMarker, AddressBlock, DateMarker

# Constants for greeting detection
LINE_GROUPING_TOLERANCE = 10  # Pixels tolerance for grouping words on the same line


def detect_letter_page_index(page_df: pd.DataFrame) -> LetterPageIndex:
    """
    Detect page index information from OCR data.
    
    Extracts current page number and total page count (if available) from patterns like:
    - Priority 1 (Total Info): "Seite X von Y", "Page X of Y", "Seite X / Y", etc.
    - Priority 2 (Continuation): "Fortsetzung auf Seite X", "Continued on page X"
    
    Uses 1-based indexing (matching text in the letter).
    Ignores standalone numbers to avoid false positives.
    
    Args:
        page_df: DataFrame containing OCR data for a single page with columns:
                 'text', 'left', 'top', 'page_width', 'page_height', etc.
    
    Returns:
        LetterPageIndex with:
            - found: True if page index detected
            - current: Current page number (1-based)
            - total: Total page count (1-based) or None if not available
            - raw: The matched text
            - x_rel: Relative x position (0..1) of indicator start
            - y_rel: Relative y position (0..1) of indicator start
    """
    # Priority 1: Total Information patterns (with both current and total)
    # Match patterns like "Seite 2 von 5", "Page 2 of 5", "Seite 2/5", "Page 2 / 5"
    # Case insensitive, flexible spacing around separators
    # Note: OCR engines often misread '/' as '|', 'I', or 'l', so we match all these characters
    total_info_patterns = [
        # German patterns
        r'\bSeite\s*(\d+)\s*von\s*(\d+)\b',                    # Seite X von Y
        r'\bSeite\s*(\d+)\s*[/|Il]\s*(\d+)\b',                 # Seite X/Y, Seite X|Y, Seite X I Y, etc.
        # English patterns
        r'\bPage\s*(\d+)\s*of\s*(\d+)\b',                      # Page X of Y
        r'\bPage\s*(\d+)\s*[/|Il]\s*(\d+)\b',                  # Page X/Y, Page X|Y, Page X I Y, etc.
    ]
    
    # Priority 2: Continuation/Partial Information patterns (current page only, implicit)
    # Match patterns like "Fortsetzung auf Seite 3", "Continued on page 3"
    # These indicate the NEXT page, so current = X-1
    continuation_patterns = [
        # German patterns
        r'\bFortsetzung\s+(?:auf|siehe)\s+Seite\s+(\d+)\b',  # Fortsetzung auf/siehe Seite X
        # English patterns
        r'\bContinued\s+on\s+page\s+(\d+)\b',                 # Continued on page X
    ]
    
    # Preprocess and group words
    paragraphs, page_width, page_height = _preprocess_and_group_words(page_df)
    
    if paragraphs is None:
        return LetterPageIndex(found=False, current=None, total=None, raw=None, x_rel=None, y_rel=None)
    
    # Priority 1: Search for total information patterns first
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check total information patterns
        for pattern in total_info_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Extract current and total page numbers
                current_page = int(match.group(1))
                total_pages = int(match.group(2))
                
                # Calculate relative position of the match
                x_rel, y_rel = _calculate_match_position(para_group, match, para_text, page_width, page_height)
                
                return LetterPageIndex(
                    found=True,
                    current=current_page,
                    total=total_pages,
                    raw=match.group(0),
                    x_rel=float(x_rel),
                    y_rel=float(y_rel)
                )
    
    # Priority 2: Search for continuation patterns (if no total info found)
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check continuation patterns
        for pattern in continuation_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Extract the next page number and calculate current (X-1)
                next_page = int(match.group(1))
                current_page = next_page - 1
                
                # Calculate relative position of the match
                x_rel, y_rel = _calculate_match_position(para_group, match, para_text, page_width, page_height)
                
                return LetterPageIndex(
                    found=True,
                    current=current_page,
                    total=None,  # Total not available for continuation patterns
                    raw=match.group(0),
                    x_rel=float(x_rel),
                    y_rel=float(y_rel)
                )
    
    # No match found
    return LetterPageIndex(found=False, current=None, total=None, raw=None, x_rel=None, y_rel=None)


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
    
    # Preprocess and group words
    paragraphs, page_width, page_height = _preprocess_and_group_words(page_df)
    
    if paragraphs is None:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Search for greetings using both strong and weak patterns
    return _search_patterns_in_paragraphs(
        paragraphs,
        [strong_greeting_patterns, weak_greeting_patterns],
        page_width,
        page_height
    )


def _preprocess_and_group_words(page_df: pd.DataFrame) -> Tuple[Optional['pd.core.groupby.DataFrameGroupBy'], Optional[float], Optional[float]]:
    """
    Preprocess OCR data and group words into paragraphs.
    
    Args:
        page_df: DataFrame containing OCR data for a single page
    
    Returns:
        Tuple of (paragraphs_groupby, page_width, page_height) or (None, None, None) if validation fails.
        paragraphs_groupby is a DataFrameGroupBy object for iterating over paragraphs.
    """
    # Handle empty or invalid DataFrame
    required_columns = ['level', 'text', 'left', 'top', 'page_width', 'page_height']
    if page_df.empty or not all(col in page_df.columns for col in required_columns):
        return None, None, None
    
    # Filter to word-level elements with non-empty text
    words_df = page_df[
        (page_df['level'] == 5) & 
        (page_df['text'].notna()) & 
        (page_df['text'].str.strip() != '')
    ].copy()
    
    if words_df.empty:
        return None, None, None
    
    # Get page dimensions (should be consistent across all rows)
    # Handle potential null values
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    if pd.isna(page_width) or pd.isna(page_height) or page_width <= 0 or page_height <= 0:
        return None, None, None
    
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
    
    return paragraphs, page_width, page_height


def _create_marker(para_group: pd.DataFrame, match: re.Match, para_text: str, 
                   page_width: float, page_height: float) -> TextMarker:
    """
    Create a TextMarker for a detected text pattern (greeting, goodbye, etc.).
    
    Args:
        para_group: DataFrame of words in the paragraph
        match: Regex match object
        para_text: Reconstructed paragraph text
        page_width: Page width in pixels
        page_height: Page height in pixels
    
    Returns:
        TextMarker with detected text information
    """
    # Calculate relative position of the match
    x_rel, y_rel = _calculate_match_position(para_group, match, para_text, page_width, page_height)
    
    # Store the full paragraph text as raw value for context and debugging
    return TextMarker(
        found=True,
        raw=para_text.strip(),
        x_rel=float(x_rel),
        y_rel=float(y_rel)
    )


def _calculate_match_position(para_group: pd.DataFrame, match: re.Match, para_text: str,
                              page_width: float, page_height: float) -> Tuple[float, float]:
    """
    Calculate the relative position (x_rel, y_rel) of a regex match within a paragraph.
    
    Args:
        para_group: DataFrame of words in the paragraph
        match: Regex match object
        para_text: Reconstructed paragraph text
        page_width: Page width in pixels
        page_height: Page height in pixels
    
    Returns:
        Tuple of (x_rel, y_rel) - relative position (0..1) of the match start
    """
    # Find the first word of the match in the para_group
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
    
    return x_rel, y_rel


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


def _search_patterns_in_paragraphs(paragraphs: 'pd.core.groupby.DataFrameGroupBy', 
                                   patterns_list: List[List[str]], 
                                   page_width: float, 
                                   page_height: float) -> TextMarker:
    """
    Search for text patterns in grouped paragraphs.
    
    Args:
        paragraphs: DataFrameGroupBy object for iterating over paragraphs
        patterns_list: List of regex pattern lists to search. Each sublist is searched in order.
        page_width: Page width in pixels
        page_height: Page height in pixels
    
    Returns:
        TextMarker with match information if found, otherwise TextMarker with found=False
    """
    # Search for patterns paragraph by paragraph
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check all pattern lists
        for patterns in patterns_list:
            for pattern in patterns:
                match = re.search(pattern, para_text, re.IGNORECASE)
                if match:
                    # Found a match! Return full paragraph as raw value
                    return _create_marker(para_group, match, para_text, page_width, page_height)
    
    # No match found
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


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
    
    # Preprocess and group words
    paragraphs, page_width, page_height = _preprocess_and_group_words(page_df)
    
    if paragraphs is None:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Search for goodbyes
    return _search_patterns_in_paragraphs(
        paragraphs,
        [goodbye_patterns],
        page_width,
        page_height
    )


def detect_subject(page_df: pd.DataFrame) -> TextMarker:
    """
    Detect the subject/topic of a letter from OCR data.
    
    Uses a two-step approach:
    1. Labeled subject detection: Look for explicit subject labels (Betreff, Subject, Re:, etc.)
       and extract the subject text that follows.
    2. Topic keyword detection: If no labeled subject is found, check for common topic keywords
       that are suitable as filename topics (Rechnung, Invoice, Mahnung, etc.).
    
    Args:
        page_df: DataFrame containing OCR data for a single page with columns:
                 'text', 'left', 'top', 'page_width', 'page_height', 'line_num', etc.
    
    Returns:
        TextMarker with:
            - found: True if subject/topic detected
            - raw: The matched subject text or keyword
            - x_rel: Relative x position (0..1) of subject start
            - y_rel: Relative y position (0..1) of subject start
    """
    # Step 1: Labeled subject detection
    labeled_subject = _detect_labeled_subject(page_df)
    if labeled_subject.found:
        return labeled_subject
    
    # Step 2: Topic keyword detection (fallback)
    return _detect_topic_keywords(page_df)


def _detect_labeled_subject(page_df: pd.DataFrame) -> TextMarker:
    """
    Detect explicit subject labels and extract the subject text that follows.
    
    Looks for patterns like:
    - German: Betreff, Betreff:, Betr., Betr:
    - English: Subject, Subject:, Re:
    
    Returns the text following the label as the subject.
    """
    # Subject label patterns
    # Match the label itself, including optional punctuation
    # Use capturing group to separate label from potential trailing punctuation
    label_patterns = [
        r'\bBetreff\b\s*:?\s*',     # Betreff or Betreff:
        r'\bBetr(\.|\s|:)+',       # Betr. or Betr:
        r'\bSubject\b\s*:?\s*',     # Subject or Subject:
        r'\bRe\s*:\s*',             # Re:
    ]
    
    # Preprocess and group words
    paragraphs, page_width, page_height = _preprocess_and_group_words(page_df)
    
    if paragraphs is None:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Search for labeled subject
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check all label patterns
        for pattern in label_patterns:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Found a label! Extract the subject text that follows
                label_end = match.end()
                
                # Get text after the label in this paragraph (including any trailing whitespace)
                subject_text_in_para = para_text[label_end:].strip()
                
                # Find the first word after the label
                first_word_after_label_idx = _find_first_word_after_position(
                    para_group, label_end, para_text
                )
                
                if subject_text_in_para:
                    # Subject text found in same paragraph
                    if first_word_after_label_idx is not None:
                        first_word = para_group.iloc[first_word_after_label_idx]
                        x_rel = first_word['left'] / page_width
                        y_rel = first_word['top'] / page_height
                    else:
                        # Fallback: use position of the label itself
                        label_word_idx = _find_first_word_of_match(para_group, match, para_text)
                        if label_word_idx is not None:
                            first_word = para_group.iloc[label_word_idx]
                        else:
                            first_word = para_group.iloc[0]
                        x_rel = first_word['left'] / page_width
                        y_rel = first_word['top'] / page_height
                    
                    return TextMarker(
                        found=True,
                        raw=subject_text_in_para,
                        x_rel=float(x_rel),
                        y_rel=float(y_rel)
                    )
                else:
                    # Label found but no text in same paragraph
                    # Try to get the next paragraph as subject text
                    next_para = _get_next_paragraph(paragraphs, para_key)
                    if next_para is not None:
                        next_para_text = ' '.join(next_para['text'].astype(str)).strip()
                        if next_para_text:
                            first_word = next_para.iloc[0]
                            x_rel = first_word['left'] / page_width
                            y_rel = first_word['top'] / page_height
                            return TextMarker(
                                found=True,
                                raw=next_para_text,
                                x_rel=float(x_rel),
                                y_rel=float(y_rel)
                            )
                    
                    # Label found but no subject text - return found=False
                    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


def _find_first_word_after_position(para_group: pd.DataFrame, char_pos: int, para_text: str) -> Optional[int]:
    """
    Find the index of the first word in para_group that starts after the given character position.
    
    Args:
        para_group: DataFrame of words in the paragraph
        char_pos: Character position in para_text
        para_text: Reconstructed paragraph text (words joined with single spaces)
    
    Returns:
        Index in para_group of the first word after char_pos, or None if not found
    """
    current_pos = 0
    for idx, (_, word_row) in enumerate(para_group.iterrows()):
        word_text = str(word_row['text'])
        word_start = current_pos
        word_end = current_pos + len(word_text)
        
        # Check if this word starts at or after char_pos
        if word_start >= char_pos:
            return idx
        
        # Account for the single space we added during reconstruction
        current_pos = word_end + 1
    
    return None


def _get_next_paragraph(paragraphs: 'pd.core.groupby.DataFrameGroupBy', current_key) -> Optional[pd.DataFrame]:
    """
    Get the next paragraph after the current one.
    
    Args:
        paragraphs: DataFrameGroupBy object for iterating over paragraphs
        current_key: Key of the current paragraph
    
    Returns:
        DataFrame of the next paragraph, or None if not found
    """
    found_current = False
    for para_key, para_group in paragraphs:
        if found_current:
            return para_group
        if para_key == current_key:
            found_current = True
    return None


def _detect_topic_keywords(page_df: pd.DataFrame) -> TextMarker:
    """
    Detect common topic keywords that are suitable as filename topics.
    
    This is a conservative fallback when no labeled subject is found.
    Looks for keywords like: Rechnung, Invoice, Mahnung, etc.
    
    Returns a TextMarker for the first matched keyword (not the full paragraph).
    """
    # Topic keyword patterns (conservative, curated list)
    # These are standalone words that typically appear in document subjects
    topic_keywords = [
        # German keywords
        r'\bRechnung\b',
        r'\bAbrechnung\b',
        r'\bBeitragsbescheid\b',
        r'\bSteuerbescheid\b',
        r'\bBescheid\b',
        r'\bMahnung\b',
        r'\bZahlungserinnerung\b',
        r'\bZahlungsaufforderung\b',
        r'\bKostenvoranschlag\b',
        r'\bBestellung\b',
        r'\bVersicherungsbescheid\b',
        r'\bLeistungsbescheid\b',
        r'\bBeitragsmitteilung\b',
        r'\bRentenbescheid\b',
        # English keywords
        r'\bInvoice\b',
        r'\bBilling\s+statement\b',
        r'\bPayment\s+reminder\b',
        r'\bReminder\b',
        r'\bTax\s+notice\b',
        r'\bTax\s+assessment\b',
        r'\bAssessment\s+notice\b',
    ]
    
    # Preprocess and group words
    paragraphs, page_width, page_height = _preprocess_and_group_words(page_df)
    
    if paragraphs is None:
        return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)
    
    # Search for topic keywords - return only the matched keyword, not full paragraph
    for para_key, para_group in paragraphs:
        # Reconstruct the paragraph text
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Check all keyword patterns
        for pattern in topic_keywords:
            match = re.search(pattern, para_text, re.IGNORECASE)
            if match:
                # Found a keyword! Return only the matched keyword text
                matched_keyword = match.group(0)
                
                # Find the first word of the match in the para_group
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
                
                return TextMarker(
                    found=True,
                    raw=matched_keyword,
                    x_rel=float(x_rel),
                    y_rel=float(y_rel)
                )
    
    # No match found
    return TextMarker(found=False, raw=None, x_rel=None, y_rel=None)


def detect_address_block(page_df: pd.DataFrame, target_zip: Optional[str] = None) -> AddressBlock:
    """
    Detect and extract address information from the recipient window area.
    
    Strategy:
    1. Filter to "Recipient Zone" (Top 30%, Left 50% of page)
    2. Use OCR-native hierarchy (block_num, par_num, line_num) to reconstruct lines
    3. Search for "ZIP City" anchor pattern (e.g., "12345 Berlin")
    4. Group lines above the anchor with similar left alignment and vertical proximity
    5. Select best candidate: prioritize target_zip match, then most lines, then topmost
    6. Extract name (top lines), street (line above ZIP), ZIP, and city
    
    Args:
        page_df: DataFrame containing OCR data for a single page
        target_zip: Optional target ZIP code to prioritize in case of multiple matches
    
    Returns:
        AddressBlock with extracted address information or found=False if no address detected
    """
    # Handle empty or invalid DataFrame
    required_columns = ['level', 'text', 'left', 'top', 'page_width', 'page_height']
    if page_df.empty or not all(col in page_df.columns for col in required_columns):
        return AddressBlock(found=False)
    
    # Filter to word-level elements with non-empty text
    words_df = page_df[
        (page_df['level'] == 5) & 
        (page_df['text'].notna()) & 
        (page_df['text'].str.strip() != '')
    ].copy()
    
    if words_df.empty:
        return AddressBlock(found=False)
    
    # Get page dimensions
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    if pd.isna(page_width) or pd.isna(page_height) or page_width <= 0 or page_height <= 0:
        return AddressBlock(found=False)
    
    # Step 1: Filter to Recipient Zone (Top 30%, Left 50%)
    top_30_percent = page_height * 0.3
    left_50_percent = page_width * 0.5
    
    recipient_zone_df = words_df[
        (words_df['top'] <= top_30_percent) &
        (words_df['left'] <= left_50_percent)
    ].copy()

    if recipient_zone_df.empty:
        return AddressBlock(found=False)
    
    # Step 2: Use OCR-native hierarchy to reconstruct lines
    # Use OCR-native line structure
    # Sort by block, paragraph, line, then left position
    recipient_zone_df = recipient_zone_df.sort_values(['block_num', 'par_num', 'line_num', 'left'])
    
    # Group by the structural hierarchy to reconstruct lines
    lines = []
    for (page_num, block_num, par_num, line_num), line_words in recipient_zone_df.groupby(['page_num', 'block_num', 'par_num', 'line_num'], sort=True):
        line_words = line_words.sort_values('left')
        line_text = ' '.join(line_words['text'].astype(str))
        line_left = line_words['left'].min()
        line_top = line_words['top'].min()
        lines.append({
            'text': line_text,
            'left': line_left,
            'top': line_top,
            'block_num': block_num,
            'par_num': par_num,
            'line_num': line_num,
            'words_df': line_words
        })
    
    if not lines:
        return AddressBlock(found=False)
    
    # Step 3: Find ZIP City anchor pattern and validate address block
    # German ZIP format: 5 digits followed by city name
    zip_city_pattern = r'\b(\d{5})\s+([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\s\-]+)'
    
    # Define tolerances
    left_alignment_tolerance = 30  # pixels
    vertical_gap_tolerance = 50  # pixels - maximum vertical distance between consecutive lines
    
    # Collect all valid address block candidates
    candidates = []
    
    # Iterate through all ZIP candidates and validate each one
    for anchor_line_idx, line in enumerate(lines):
        match = re.search(zip_city_pattern, line['text'])
        if not match:
            continue
        
        # Found a ZIP pattern - now validate it has a coherent address block
        anchor_line = line
        anchor_left = anchor_line['left']
        anchor_top = anchor_line['top']
        
        # Step 4: Try to group lines above this anchor with similar left alignment
        address_lines = []
        prev_top = anchor_top
        
        for idx in range(anchor_line_idx - 1, -1, -1):
            candidate_line = lines[idx]
            
            # Check vertical proximity - line should be close to the previous line  
            # (not just close to the anchor, but close to the line we just added)
            vertical_gap = prev_top - candidate_line['top']
            if vertical_gap > vertical_gap_tolerance:
                # Too far above the previous line, stop searching
                break
            
            # Check if line has similar left alignment
            if abs(candidate_line['left'] - anchor_left) <= left_alignment_tolerance:
                address_lines.insert(0, candidate_line)  # Insert at beginning to maintain order
                prev_top = candidate_line['top']
                # Limit to 4 lines above the anchor
                if len(address_lines) >= 4:
                    break
            else:
                # Stop if alignment breaks
                break
        
        # Validate: We need at least 1 line above the anchor for a valid address block
        if len(address_lines) >= 1:
            # Valid address block found! Store as a candidate
            extracted_zip = match.group(1)
            extracted_city = match.group(2).strip()
            
            # Calculate line count and position
            line_count = len(address_lines) + 1
            first_line = address_lines[0]
            
            candidates.append({
                'address_lines': address_lines,
                'anchor_line': anchor_line,
                'extracted_zip': extracted_zip,
                'extracted_city': extracted_city,
                'line_count': line_count,
                'first_line': first_line,
                'anchor_top': anchor_top
            })
    
    # No valid address block found
    if not candidates:
        return AddressBlock(found=False)
    
    # Step 5: Select the best candidate
    # Priority: 1) Matches target_zip, 2) Most lines, 3) Topmost (first in reading order)
    def candidate_score(candidate):
        zip_match = 1 if target_zip and candidate['extracted_zip'] == target_zip else 0
        # Return tuple: (zip_match, line_count, -anchor_top)
        # Higher zip_match and line_count are better, lower anchor_top (higher on page) is better
        return (zip_match, candidate['line_count'], -candidate['anchor_top'])
    
    best_candidate = max(candidates, key=candidate_score)
    
    # Step 6: Extract address components from best candidate
    address_lines = best_candidate['address_lines']
    extracted_zip = best_candidate['extracted_zip']
    extracted_city = best_candidate['extracted_city']
    line_count = best_candidate['line_count']
    first_line = best_candidate['first_line']
    # Last line in address_lines (just above anchor) is the street
    extracted_street = address_lines[-1]['text'].strip()
    
    # First line(s) are the name
    if len(address_lines) >= 2:
        # If we have 2+ lines above anchor, first lines are the name
        name_lines = address_lines[:-1]
        extracted_name = ' '.join([line['text'].strip() for line in name_lines])
    else:
        # Only 1 line above anchor - could be just street, no name
        extracted_name = None
        # In this case, the street might actually be the name
        # But we'll keep it as street for now
    
    # Calculate position (top-left of the first line)
    first_line = address_lines[0]
    x_rel = first_line['left'] / page_width
    y_rel = first_line['top'] / page_height
    
    # Total line count: address_lines + anchor line
    line_count = len(address_lines) + 1
    
    return AddressBlock(
        found=True,
        x_rel=float(x_rel),
        y_rel=float(y_rel),
        extracted_name=extracted_name,
        extracted_street=extracted_street,
        extracted_zip=extracted_zip,
        extracted_city=extracted_city,
        line_count=line_count
    )


def _has_inline_indicator(para_text: str, date_match: re.Match) -> bool:
    """
    Check if a date has an indicator word immediately to its left.
    
    Only matches if the indicator (e.g., "Datum:", "Date:", "vom") is directly
    before the date with only optional colons and whitespace in between.
    This avoids false positives from dates within sentences like 
    "Das Datum der ersten Lieferung war der 01.01.2023".
    
    Args:
        para_text: The paragraph text containing the date
        date_match: Regex match object for the date
    
    Returns:
        True if an indicator is immediately before the date
    """
    # Extract text before the date match
    text_before = para_text[:date_match.start()].strip()
    
    # Check if the text immediately before ends with a date indicator
    # Pattern: word ending with "datum" or "date" (case-insensitive), or "vom"/"dated"
    # followed by optional colon and whitespace
    inline_indicator_pattern = r'(?:\w*datum|\w*date|vom|dated)\s*:?\s*$'
    
    return bool(re.search(inline_indicator_pattern, text_before, re.IGNORECASE))


def _has_above_indicator(prev_para_group: pd.DataFrame, current_para_group: pd.DataFrame, 
                         page_width: float) -> bool:
    """
    Check if the previous paragraph contains a label-like indicator for the date.
    
    An indicator in the paragraph above is only considered valid if it behaves like
    a column label (i.e., it's the only significant text in that line or is 
    vertically aligned with the date).
    
    Args:
        prev_para_group: DataFrame of words in the previous paragraph
        current_para_group: DataFrame of words in the current paragraph (with date)
        page_width: Page width in pixels
    
    Returns:
        True if the previous paragraph is a valid label for the date
    """
    prev_para_text = ' '.join(prev_para_group['text'].astype(str)).strip()
    
    # Check if previous paragraph contains a date indicator keyword
    indicator_pattern = r'^\s*(?:\w*datum|\w*date|vom|dated)\s*:?\s*$'
    if not re.search(indicator_pattern, prev_para_text, re.IGNORECASE):
        return False
    
    # Check if the indicator is short (label-like, not a full sentence)
    # A label should be relatively short (e.g., "Datum:", "Date:")
    if len(prev_para_text.split()) > 3:
        return False
    
    # Check vertical alignment: the indicator should be roughly aligned with the date
    # Get horizontal position of the indicator
    prev_left = prev_para_group.iloc[0]['left'] if not prev_para_group.empty else 0
    curr_left = current_para_group.iloc[0]['left'] if not current_para_group.empty else 0
    
    # Allow for reasonable horizontal alignment tolerance (within 20% of page width)
    alignment_tolerance = page_width * 0.2
    
    return abs(prev_left - curr_left) <= alignment_tolerance


def detect_date(page_df: pd.DataFrame) -> DateMarker:
    """
    Detect the letter's creation date from OCR data.
    
    Searches only in the top 40% of the page for date patterns in multiple formats.
    Supports both German and English date formats and keyword indicators.
    
    Date formats supported:
    - DD.MM.YYYY (e.g., 12.05.2023)
    - DD. Month YYYY (e.g., 12. Mai 2023, 5. May 2023)
    - Month DD, YYYY (e.g., May 12, 2023)
    - YYYY-MM-DD (e.g., 2023-05-12)
    
    Keyword indicators: "Datum", "Date", "vom", "dated"
    - Inline: Indicator must be immediately before the date (e.g., "Datum: 12.05.2023")
    - Above: Indicator in previous paragraph must be label-like and vertically aligned
    
    Heuristics for selecting best candidate when multiple dates found:
    1. Prefer dates with keyword indicators (strict inline or above detection)
    2. Tie-breaker: highest x position (furthest right)
    3. Final tie-breaker: lowest y position (furthest top)
    
    Args:
        page_df: DataFrame containing OCR data for a single page with columns:
                 'text', 'left', 'top', 'page_width', 'page_height', etc.
    
    Returns:
        DateMarker with:
            - found: True if date detected
            - raw: The matched date text
            - date_value: Parsed datetime object
            - x_rel: Relative x position (0..1) of date start
            - y_rel: Relative y position (0..1) of date start
    """
    # Handle empty or invalid DataFrame
    required_columns = ['level', 'text', 'left', 'top', 'page_width', 'page_height']
    if page_df.empty or not all(col in page_df.columns for col in required_columns):
        return DateMarker(found=False)
    
    # Filter to word-level elements with non-empty text
    words_df = page_df[
        (page_df['level'] == 5) & 
        (page_df['text'].notna()) & 
        (page_df['text'].str.strip() != '')
    ].copy()
    
    if words_df.empty:
        return DateMarker(found=False)
    
    # Get page dimensions
    page_width = words_df['page_width'].iloc[0]
    page_height = words_df['page_height'].iloc[0]
    
    if pd.isna(page_width) or pd.isna(page_height) or page_width <= 0 or page_height <= 0:
        return DateMarker(found=False)
    
    # Filter to top 40% of page
    top_40_percent = page_height * 0.4
    top_zone_df = words_df[words_df['top'] <= top_40_percent].copy()
    
    if top_zone_df.empty:
        return DateMarker(found=False)
    
    # Group words by paragraph
    if all(col in top_zone_df.columns for col in ['page_num', 'block_num', 'par_num', 'line_num']):
        top_zone_df = top_zone_df.sort_values(['page_num', 'block_num', 'par_num', 'line_num', 'left'])
        paragraphs = top_zone_df.groupby(['page_num', 'block_num', 'par_num'])
    else:
        # Fallback: group by vertical position
        top_zone_df['line_group'] = (top_zone_df['top'] / LINE_GROUPING_TOLERANCE).round().astype(int)
        top_zone_df = top_zone_df.sort_values(['line_group', 'left'])
        paragraphs = top_zone_df.groupby('line_group')
    
    # Date patterns with flexible whitespace
    # Month names for multilingual support
    german_months = r'(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|Maerz)'
    english_months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
    
    date_patterns = [
        # DD.MM.YYYY with flexible spacing (e.g., 12.05.2023, 12 . 05 . 2023)
        (r'\b(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})\b', 'DD.MM.YYYY'),
        # DD. Month YYYY (e.g., 12. Mai 2023, 5. May 2023)
        (rf'\b(\d{{1,2}})\s*\.\s*({german_months}|{english_months})\s+(\d{{4}})\b', 'DD.Month.YYYY'),
        # Month DD, YYYY (e.g., May 12, 2023)
        (rf'\b({english_months})\s+(\d{{1,2}}),?\s+(\d{{4}})\b', 'Month.DD.YYYY'),
        # YYYY-MM-DD (e.g., 2023-05-12)
        (r'\b(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\b', 'YYYY-MM-DD'),
    ]
    
    # Collect all date candidates
    candidates = []
    para_list = list(paragraphs)
    
    for idx, (para_key, para_group) in enumerate(para_list):
        para_text = ' '.join(para_group['text'].astype(str))
        
        # Search for date patterns - collect ALL matches
        for pattern, format_name in date_patterns:
            for match in re.finditer(pattern, para_text, re.IGNORECASE):
                # Try to parse the date
                parsed_date = _parse_date_from_match(match, format_name)
                if parsed_date is not None:
                    # Calculate position
                    first_word_idx = _find_first_word_of_match(para_group, match, para_text)
                    if first_word_idx is not None:
                        first_word = para_group.iloc[first_word_idx]
                        x_rel = first_word['left'] / page_width
                        y_rel = first_word['top'] / page_height
                    else:
                        first_word = para_group.iloc[0]
                        x_rel = first_word['left'] / page_width
                        y_rel = first_word['top'] / page_height
                    
                    # Check for stricter inline indicators (immediately before date)
                    has_inline_indicator = _has_inline_indicator(para_text, match)
                    
                    # Check for stricter above indicators (label-like in previous paragraph)
                    has_above_indicator = False
                    if idx > 0:
                        prev_para_key, prev_para_group = para_list[idx - 1]
                        has_above_indicator = _has_above_indicator(prev_para_group, para_group, page_width)
                    
                    candidates.append({
                        'raw': match.group(0),
                        'date_value': parsed_date,
                        'x_rel': x_rel,
                        'y_rel': y_rel,
                        'has_indicator': has_inline_indicator or has_above_indicator,
                    })
    
    # No dates found
    if not candidates:
        return DateMarker(found=False)
    
    # Select best candidate using heuristics
    def candidate_score(candidate):
        # Prefer candidates with indicators
        indicator_score = 1 if candidate['has_indicator'] else 0
        # Higher x position (furthest right) is better
        x_score = candidate['x_rel']
        # Lower y position (furthest top) is better, so negate
        y_score = -candidate['y_rel']
        return (indicator_score, x_score, y_score)
    
    best_candidate = max(candidates, key=candidate_score)
    
    return DateMarker(
        found=True,
        raw=best_candidate['raw'],
        date_value=best_candidate['date_value'],
        x_rel=float(best_candidate['x_rel']),
        y_rel=float(best_candidate['y_rel'])
    )


def _parse_date_from_match(match: re.Match, format_name: str) -> Optional[datetime]:
    """
    Parse a datetime object from a regex match based on the format.
    
    Args:
        match: Regex match object
        format_name: Format identifier string
    
    Returns:
        datetime object or None if parsing fails
    """
    try:
        if format_name == 'DD.MM.YYYY':
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            return datetime(year, month, day)
        
        elif format_name == 'DD.Month.YYYY':
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))
            month = _parse_month_name(month_name)
            if month is None:
                return None
            return datetime(year, month, day)
        
        elif format_name == 'Month.DD.YYYY':
            month_name = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3))
            month = _parse_month_name(month_name)
            if month is None:
                return None
            return datetime(year, month, day)
        
        elif format_name == 'YYYY-MM-DD':
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return datetime(year, month, day)
        
        return None
    except (ValueError, OverflowError):
        # Invalid date (e.g., 32.13.2023)
        return None


def _parse_month_name(month_name: str) -> Optional[int]:
    """
    Parse month name (German or English) to month number.
    
    Args:
        month_name: Month name in German or English (full or abbreviated)
    
    Returns:
        Month number (1-12) or None if not recognized
    """
    month_map = {
        # German months
        'januar': 1, 'februar': 2, 'märz': 3, 'maerz': 3, 'april': 4,
        'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12,
        # English months (full)
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        # English months (abbreviated)
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5,
        'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    return month_map.get(month_name.lower())
