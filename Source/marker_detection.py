#!/usr/bin/env python3

import pandas as pd
from page_data import PageInfoDetected, TextMarker


def detect_page_info(page_df: pd.DataFrame) -> PageInfoDetected:
    raise NotImplementedError


def detect_greeting(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_goodbye(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_betreff(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError


def detect_address_block(page_df: pd.DataFrame) -> TextMarker:
    raise NotImplementedError
