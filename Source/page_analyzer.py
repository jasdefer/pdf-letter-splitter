#!/usr/bin/env python3

import pandas as pd
from page_analysis_data import PageAnalysis
from marker_detection import (
    detect_letter_page_index,
    detect_greeting,
    detect_goodbye,
    detect_betreff,
    detect_address_block
)


def analyze_pages(ocr_df: pd.DataFrame) -> list[PageAnalysis]:
    if ocr_df.empty:
        return []
    
    if 'page_num' not in ocr_df.columns:
        raise ValueError("OCR DataFrame must have a 'page_num' column")
    
    page_numbers = sorted(ocr_df['page_num'].unique())
    
    page_analysis_list = []
    
    for page_num in page_numbers:
        page_df = ocr_df[ocr_df['page_num'] == page_num].copy()
        
        page_analysis = PageAnalysis(
            scan_page_num=int(page_num),
            letter_page_index=detect_letter_page_index(page_df),
            greeting=detect_greeting(page_df),
            goodbye=detect_goodbye(page_df),
            betreff=detect_betreff(page_df),
            address_block=detect_address_block(page_df)
        )
        
        page_analysis_list.append(page_analysis)
    
    return page_analysis_list
