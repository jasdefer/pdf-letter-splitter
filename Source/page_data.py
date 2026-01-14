#!/usr/bin/env python3

from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
import json


@dataclass
class PageInfoDetected:
    found: bool = False
    current: Optional[int] = None
    total: Optional[int] = None
    raw: Optional[str] = None


@dataclass
class TextMarker:
    found: bool = False
    raw: Optional[str] = None
    text: Optional[str] = None


@dataclass
class PageData:
    scan_page_num: int
    page_info: PageInfoDetected
    greeting: TextMarker
    goodbye: TextMarker
    betreff: TextMarker
    address_block: TextMarker


def write_page_data_to_json(page_data_list: list[PageData], output_path: Path) -> None:
    data_dicts = [asdict(page) for page in page_data_list]
    with open(output_path, 'w') as f:
        json.dump(data_dicts, f, indent=2)
