#!/usr/bin/env python3

from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime
import json


@dataclass
class LetterPageIndex:
    found: bool = False
    current: Optional[int] = None
    total: Optional[int] = None
    raw: Optional[str] = None
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None


@dataclass
class TextMarker:
    found: bool = False
    raw: Optional[str] = None
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None


@dataclass
class AddressBlock:
    found: bool = False
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None
    extracted_name: Optional[str] = None
    extracted_street: Optional[str] = None
    extracted_zip: Optional[str] = None
    extracted_city: Optional[str] = None
    line_count: Optional[int] = None


@dataclass
class DateMarker:
    found: bool = False
    raw: Optional[str] = None
    date_value: Optional[datetime] = None
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None


@dataclass
class PageAnalysis:
    scan_page_num: int
    letter_page_index: LetterPageIndex
    greeting: TextMarker
    goodbye: TextMarker
    subject: TextMarker
    address_block: AddressBlock
    date: DateMarker


def write_page_analysis_to_json(page_analysis_list: list[PageAnalysis], output_path: Path) -> None:
    data_dicts = [asdict(page) for page in page_analysis_list]
    with open(output_path, 'w') as f:
        json.dump(data_dicts, f, indent=2)
