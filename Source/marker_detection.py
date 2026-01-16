#!/usr/bin/env python3

import pandas as pd
import re
from typing import Optional, Tuple, List
from page_analysis_data import LetterPageIndex, TextMarker, AddressBlock

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


def detect_address_block(page_df: pd.DataFrame) -> AddressBlock:
    """
    Detect and extract address information from the recipient window area.
    
    Strategy:
    1. Filter to "Recipient Zone" (Top 30%, Left 50% of page)
    2. Search for "ZIP City" anchor pattern (e.g., "12345 Berlin")
    3. Group 2-4 lines above the anchor with similar left alignment
    4. Extract name (top lines), street (line above ZIP), ZIP, and city
    
    Args:
        page_df: DataFrame containing OCR data for a single page
    
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
    
    # Step 2: Group words into lines based on vertical position
    # Sort by top position, then left position
    recipient_zone_df = recipient_zone_df.sort_values(['top', 'left'])
    
    # Group words into lines using a tolerance for vertical alignment
    recipient_zone_df['line_group'] = (recipient_zone_df['top'] / LINE_GROUPING_TOLERANCE).round().astype(int)
    
    # Reconstruct lines
    lines = []
    for line_group_id, line_words in recipient_zone_df.groupby('line_group', sort=True):
        line_words = line_words.sort_values('left')
        line_text = ' '.join(line_words['text'].astype(str))
        line_left = line_words['left'].min()
        line_top = line_words['top'].min()
        lines.append({
            'text': line_text,
            'left': line_left,
            'top': line_top,
            'line_group_id': line_group_id,
            'words_df': line_words
        })
    
    if not lines:
        return AddressBlock(found=False)
    
    # Step 3: Find ZIP City anchor pattern
    # German ZIP format: 5 digits followed by city name
    zip_city_pattern = r'\b(\d{5})\s+([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\s\-]+)'
    
    anchor_line_idx = None
    zip_match = None
    
    for idx, line in enumerate(lines):
        match = re.search(zip_city_pattern, line['text'])
        if match:
            anchor_line_idx = idx
            zip_match = match
            break
    
    if anchor_line_idx is None or zip_match is None:
        return AddressBlock(found=False)
    
    # Extract ZIP and City from anchor
    extracted_zip = zip_match.group(1)
    extracted_city = zip_match.group(2).strip()
    
    # Step 4: Group lines above the anchor with similar left alignment
    anchor_line = lines[anchor_line_idx]
    anchor_left = anchor_line['left']
    
    # Define tolerance for left alignment (allow some variation)
    left_alignment_tolerance = 30  # pixels
    
    # Find lines above the anchor with similar left alignment
    address_lines = []
    for idx in range(anchor_line_idx - 1, -1, -1):
        line = lines[idx]
        # Check if line has similar left alignment
        if abs(line['left'] - anchor_left) <= left_alignment_tolerance:
            address_lines.insert(0, line)  # Insert at beginning to maintain order
            # Limit to 4 lines above the anchor (2-4 lines total including anchor)
            if len(address_lines) >= 4:
                break
        else:
            # Stop if alignment breaks
            break
    
    # We need at least 1 line above the anchor for a valid address
    if len(address_lines) == 0:
        return AddressBlock(found=False)
    
    # Step 5: Extract address components
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
