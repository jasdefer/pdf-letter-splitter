#!/usr/bin/env python3

import pandas as pd
from page_analysis_data import LetterPageIndex, TextMarker


def detect_letter_page_index(page_df: pd.DataFrame) -> LetterPageIndex:
    raise NotImplementedError


def detect_greeting(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_goodbye(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_betreff(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_address_block(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError
