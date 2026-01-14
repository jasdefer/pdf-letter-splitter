#!/usr/bin/env python3
"""
Data structures for per-page analysis of OCR-processed PDF documents.

This module defines strongly-typed structures that represent all information
about a single scanned page, including detected markers (greetings, closings,
page numbering, etc.) and their evidence.
"""

from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class PageInfoDetected:
    """
    Represents detected page numbering information like "Seite 2 von 4".
    
    Attributes:
        found: Whether page numbering was detected
        current: Current page number (e.g., 2 in "Seite 2 von 4")
        total: Total page count (e.g., 4 in "Seite 2 von 4")
        raw: Raw matched text from the page, if any
    """
    found: bool = False
    current: Optional[int] = None
    total: Optional[int] = None
    raw: Optional[str] = None


@dataclass
class TextMarker:
    """
    Generic marker for text-based signals (greeting, goodbye, subject, address).
    
    Attributes:
        found: Whether the marker was detected
        raw: Matched text or short excerpt, if any
        text: Normalized or extracted value, if applicable
    """
    found: bool = False
    raw: Optional[str] = None
    text: Optional[str] = None


@dataclass
class PageData:
    """
    Represents all detected information for a single scanned page.
    
    This is the central container for page-level signals and extracted facts.
    One PageData instance corresponds to exactly one scanned page in the PDF.
    
    Attributes:
        scan_page_num: Page number in the scanned PDF (1-indexed)
        page_info: Detected page numbering information
        greeting: Detected greeting marker
        goodbye: Detected goodbye/closing marker
        betreff: Detected subject line marker
        address_block: Detected address block marker
    """
    scan_page_num: int
    page_info: PageInfoDetected
    greeting: TextMarker
    goodbye: TextMarker
    betreff: TextMarker
    address_block: TextMarker
    
    def to_dict(self) -> dict:
        """
        Convert PageData to a dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the PageData instance
        """
        return asdict(self)
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """
        Convert PageData to a JSON string.
        
        Args:
            indent: Number of spaces for indentation (None for compact)
            
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PageData':
        """
        Create a PageData instance from a dictionary.
        
        Args:
            data: Dictionary containing PageData fields
            
        Returns:
            PageData instance
        """
        return cls(
            scan_page_num=data['scan_page_num'],
            page_info=PageInfoDetected(**data['page_info']),
            greeting=TextMarker(**data['greeting']),
            goodbye=TextMarker(**data['goodbye']),
            betreff=TextMarker(**data['betreff']),
            address_block=TextMarker(**data['address_block'])
        )


def page_data_list_to_json(page_data_list: list[PageData], indent: Optional[int] = 2) -> str:
    """
    Convert a list of PageData instances to a JSON string.
    
    Args:
        page_data_list: List of PageData instances
        indent: Number of spaces for indentation (None for compact)
        
    Returns:
        JSON string representation of the list
    """
    data_dicts = [page.to_dict() for page in page_data_list]
    return json.dumps(data_dicts, indent=indent)
