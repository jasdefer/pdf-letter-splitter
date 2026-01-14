#!/usr/bin/env python3
"""
Orchestration for page-level marker detection.

This module provides the main entry point for analyzing OCR data and
creating PageData structures for all pages in a document.
"""

import pandas as pd
from page_data import PageData, PageInfoDetected, TextMarker
from marker_detection import (
    detect_page_info,
    detect_greeting,
    detect_goodbye,
    detect_betreff,
    detect_address_block
)


def analyze_pages(ocr_df: pd.DataFrame) -> list[PageData]:
    """
    Analyze all pages in an OCR DataFrame and create PageData instances.
    
    This is the main orchestration function that:
    - Iterates over all scanned pages in the OCR DataFrame
    - Creates a PageData instance per page
    - Calls all marker detection functions for that page
    - Returns a list of PageData in scan order
    
    Args:
        ocr_df: DataFrame containing OCR data for all pages.
                Must have a 'page_num' column with 1-indexed page numbers.
    
    Returns:
        List of PageData instances, one per page, in scan order
        
    Example:
        >>> ocr_df = extract_text(Path("document.pdf"))
        >>> pages = analyze_pages(ocr_df)
        >>> print(f"Analyzed {len(pages)} pages")
        >>> for page in pages:
        ...     print(f"Page {page.scan_page_num}: greeting={page.greeting.found}")
    """
    if ocr_df.empty:
        return []
    
    if 'page_num' not in ocr_df.columns:
        raise ValueError("OCR DataFrame must have a 'page_num' column")
    
    # Get unique page numbers in sorted order
    page_numbers = sorted(ocr_df['page_num'].unique())
    
    page_data_list = []
    
    for page_num in page_numbers:
        # Extract data for this page only
        page_df = ocr_df[ocr_df['page_num'] == page_num].copy()
        
        # Create PageData instance with all markers detected
        page_data = PageData(
            scan_page_num=int(page_num),
            page_info=detect_page_info(page_df),
            greeting=detect_greeting(page_df),
            goodbye=detect_goodbye(page_df),
            betreff=detect_betreff(page_df),
            address_block=detect_address_block(page_df)
        )
        
        page_data_list.append(page_data)
    
    return page_data_list
