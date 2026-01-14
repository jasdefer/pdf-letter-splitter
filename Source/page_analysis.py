#!/usr/bin/env python3

import pandas as pd
from page_data import PageData
from marker_detection import (
    detect_page_info,
    detect_greeting,
    detect_goodbye,
    detect_betreff,
    detect_address_block
)


def analyze_pages(ocr_df: pd.DataFrame) -> list[PageData]:
    if ocr_df.empty:
        return []
    
    if 'page_num' not in ocr_df.columns:
        raise ValueError("OCR DataFrame must have a 'page_num' column")
    
    page_numbers = sorted(ocr_df['page_num'].unique())
    
    page_data_list = []
    
    for page_num in page_numbers:
        page_df = ocr_df[ocr_df['page_num'] == page_num].copy()
        
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
