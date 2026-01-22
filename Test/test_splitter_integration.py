#!/usr/bin/env python3
"""
Integration test for the splitter in process_letters workflow.
Verifies that the splitter is properly integrated into the main processing flow.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from page_analyzer import analyze_pages
from page_analysis_data import PageAnalysis, LetterPageIndex, TextMarker, AddressBlock, DateMarker
from splitter import group_pages_into_letters
import pandas as pd


class TestSplitterIntegration(unittest.TestCase):
    """Test integration of splitter with page analysis workflow."""
    
    def test_splitter_with_analyzed_pages(self):
        """Test that splitter works with analyzed pages from page_analyzer."""
        # Create mock pages similar to what analyze_pages would return
        pages = [
            PageAnalysis(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=2, raw="Page 1 of 2", x_rel=0.5, y_rel=0.9),
                greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.25),
                goodbye=TextMarker(found=False),
                subject=TextMarker(found=True, raw="Invoice", x_rel=0.1, y_rel=0.2),
                address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.1, line_count=4),
                date=DateMarker(found=True, raw="2024-11-05", date_value=datetime(2024, 11, 5), x_rel=0.8, y_rel=0.12)
            ),
            PageAnalysis(
                scan_page_num=2,
                letter_page_index=LetterPageIndex(found=True, current=2, total=2, raw="Page 2 of 2", x_rel=0.5, y_rel=0.9),
                greeting=TextMarker(found=False),
                goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.8),
                subject=TextMarker(found=False),
                address_block=AddressBlock(found=False),
                date=DateMarker(found=False)
            ),
            PageAnalysis(
                scan_page_num=3,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.9),
                greeting=TextMarker(found=True, raw="Hello", x_rel=0.1, y_rel=0.3),
                goodbye=TextMarker(found=True, raw="Best regards", x_rel=0.1, y_rel=0.75),
                subject=TextMarker(found=True, raw="Notice", x_rel=0.1, y_rel=0.25),
                address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.15, line_count=3),
                date=DateMarker(found=True, raw="2024-11-06", date_value=datetime(2024, 11, 6), x_rel=0.8, y_rel=0.15)
            ),
        ]
        
        # Group pages into letters
        letters = group_pages_into_letters(pages)
        
        # Verify results
        self.assertEqual(len(letters), 2, "Should identify 2 letters")
        
        # First letter should be pages 1-2
        self.assertEqual(len(letters[0].pages), 2)
        self.assertEqual([p.scan_page_num for p in letters[0].pages], [1, 2])
        self.assertEqual(letters[0].master_date, "2024-11-05")
        self.assertEqual(letters[0].master_subject, "Invoice")
        
        # Second letter should be page 3
        self.assertEqual(len(letters[1].pages), 1)
        self.assertEqual([p.scan_page_num for p in letters[1].pages], [3])
        self.assertEqual(letters[1].master_date, "2024-11-06")
        self.assertEqual(letters[1].master_subject, "Notice")
    
    def test_workflow_with_empty_pages(self):
        """Test that workflow handles empty page list."""
        pages = []
        letters = group_pages_into_letters(pages)
        self.assertEqual(len(letters), 0, "Should return empty list for no pages")
    
    def test_workflow_with_single_page(self):
        """Test that workflow handles single page."""
        pages = [
            PageAnalysis(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.9),
                greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.25),
                goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.8),
                subject=TextMarker(found=True, raw="Letter", x_rel=0.1, y_rel=0.2),
                address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.1, line_count=4),
                date=DateMarker(found=True, raw="2024-11-05", date_value=datetime(2024, 11, 5), x_rel=0.8, y_rel=0.12)
            )
        ]
        
        letters = group_pages_into_letters(pages)
        
        self.assertEqual(len(letters), 1)
        self.assertEqual(len(letters[0].pages), 1)
        self.assertEqual(letters[0].master_date, "2024-11-05")
        self.assertEqual(letters[0].master_subject, "Letter")


if __name__ == '__main__':
    unittest.main()
