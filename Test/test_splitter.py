#!/usr/bin/env python3
"""
Unit tests for the splitter module.

Tests the document splitting logic, scoring engine, and Letter grouping.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from splitter import Letter, TransitionScorer, group_pages_into_letters, SPLIT_THRESHOLD
from page_analysis_data import (
    PageAnalysis, LetterPageIndex, TextMarker, AddressBlock, DateMarker, SenderBlock
)


class TestLetter(unittest.TestCase):
    """Test cases for the Letter dataclass."""
    
    def test_letter_creation(self):
        """Test creating a Letter with pages."""
        page1 = self._create_page(scan_page_num=1)
        page2 = self._create_page(scan_page_num=2)
        letter = Letter(pages=[page1, page2])
        
        self.assertEqual(len(letter.pages), 2)
        self.assertEqual(letter.pages[0].scan_page_num, 1)
        self.assertEqual(letter.pages[1].scan_page_num, 2)
    
    def test_master_date_found(self):
        """Test extracting date from first page."""
        date_val = datetime(2024, 11, 5)
        page = self._create_page(
            scan_page_num=1,
            date=DateMarker(found=True, date_value=date_val, raw="2024-11-05", x_rel=0.5, y_rel=0.2)
        )
        letter = Letter(pages=[page])
        
        self.assertEqual(letter.master_date, "2024-11-05")
    
    def test_master_date_not_found(self):
        """Test master_date returns None when no date."""
        page = self._create_page(scan_page_num=1)
        letter = Letter(pages=[page])
        
        self.assertIsNone(letter.master_date)
    
    def test_master_date_empty_letter(self):
        """Test master_date with empty letter."""
        letter = Letter(pages=[])
        
        self.assertIsNone(letter.master_date)
    
    def test_master_subject_found(self):
        """Test extracting subject from first page."""
        page = self._create_page(
            scan_page_num=1,
            subject=TextMarker(found=True, raw="Important Notice", x_rel=0.1, y_rel=0.3)
        )
        letter = Letter(pages=[page])
        
        self.assertEqual(letter.master_subject, "Important Notice")
    
    def test_master_subject_not_found(self):
        """Test master_subject returns None when no subject."""
        page = self._create_page(scan_page_num=1)
        letter = Letter(pages=[page])
        
        self.assertIsNone(letter.master_subject)
    
    def test_master_subject_empty_letter(self):
        """Test master_subject with empty letter."""
        letter = Letter(pages=[])
        
        self.assertIsNone(letter.master_subject)
    
    def test_master_sender_found(self):
        """Test extracting sender from first page."""
        page = self._create_page(
            scan_page_num=1,
            sender=SenderBlock(
                found=True,
                sender_name="Allianz Versicherung"
            )
        )
        letter = Letter(pages=[page])
        
        self.assertEqual(letter.master_sender, "Allianz Versicherung")
    
    def test_master_sender_not_found(self):
        """Test master_sender returns None when no sender."""
        page = self._create_page(scan_page_num=1)
        letter = Letter(pages=[page])
        
        self.assertIsNone(letter.master_sender)
    
    def test_master_sender_empty_letter(self):
        """Test master_sender with empty letter."""
        letter = Letter(pages=[])
        
        self.assertIsNone(letter.master_sender)
    
    def _create_page(self, scan_page_num=1, date=None, subject=None, sender=None):
        """Helper to create a minimal PageAnalysis object."""
        return PageAnalysis(
            scan_page_num=scan_page_num,
            letter_page_index=LetterPageIndex(),
            greeting=TextMarker(),
            goodbye=TextMarker(),
            subject=subject or TextMarker(),
            address_block=AddressBlock(),
            date=date or DateMarker(),
            sender=sender
        )


class TestTransitionScorer(unittest.TestCase):
    """Test cases for the TransitionScorer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scorer = TransitionScorer()
    
    def test_definitive_marker_new_index_at_top(self):
        """Test +1000 for current page index == 1 at top."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            letter_page_index=LetterPageIndex(found=True, current=1, total=3, raw="Page 1 of 3", x_rel=0.5, y_rel=0.1)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 1000)
        self.assertIn("New Index (+1000)", factors)
    
    def test_definitive_marker_new_index_in_middle(self):
        """Test +200 for current page index == 1 in middle of page."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            letter_page_index=LetterPageIndex(found=True, current=1, total=3, raw="Page 1 of 3", x_rel=0.5, y_rel=0.5)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 200)
        self.assertIn("New Index in middle (+200)", factors)
    
    def test_definitive_marker_last_page(self):
        """Test +1000 for previous page being the last page."""
        prev_page = self._create_page(
            letter_page_index=LetterPageIndex(found=True, current=3, total=3, raw="Page 3 of 3", x_rel=0.5, y_rel=0.9)
        )
        curr_page = self._create_page()
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 1000)
        self.assertIn("Last Index of Previous (+1000)", factors)
    
    def test_address_block_at_top(self):
        """Test +450 for address block in top third."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.2, line_count=4)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 450)
        self.assertIn("Address Block at top (+450)", factors)
    
    def test_address_block_lower(self):
        """Test +75 for address block below top third."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.5, line_count=4)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertEqual(score, 75)
        self.assertIn("Address Block lower (+75)", factors)
    
    def test_subject_at_top(self):
        """Test +300 for subject in top half."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            subject=TextMarker(found=True, raw="Subject Line", x_rel=0.1, y_rel=0.4)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 300)
        self.assertIn("Subject at top (+300)", factors)
    
    def test_subject_lower(self):
        """Test +50 for subject in lower half."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            subject=TextMarker(found=True, raw="Subject Line", x_rel=0.1, y_rel=0.6)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertEqual(score, 50)
        self.assertIn("Subject lower (+50)", factors)
    
    def test_greeting_at_top(self):
        """Test +250 for greeting in top half."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.3)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 250)
        self.assertIn("Greeting at top (+250)", factors)
    
    def test_greeting_lower(self):
        """Test +50 for greeting in lower half."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.7)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertEqual(score, 50)
        self.assertIn("Greeting lower (+50)", factors)
    
    def test_date_at_top(self):
        """Test +50 for date marker in top third."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            date=DateMarker(found=True, raw="2024-11-05", x_rel=0.8, y_rel=0.2)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 50)
        self.assertIn("Date at top (+50)", factors)
    
    def test_penalty_address_below_subject(self):
        """Test -350 penalty when address is below subject."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.6, line_count=4),
            subject=TextMarker(found=True, raw="Subject", x_rel=0.1, y_rel=0.3)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        # Subject at top gives +300, but address below subject gives -350
        # Address lower gives +75
        # Net: 300 + 75 - 350 = 25
        self.assertEqual(score, 25)
        self.assertIn("Address below Subject (-350)", factors)
    
    def test_penalty_address_below_greeting(self):
        """Test -350 penalty when address is below greeting."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.6, line_count=4),
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.3)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        # Greeting at top gives +250, address lower gives +75, penalty -350
        # Net: 250 + 75 - 350 = -25
        self.assertEqual(score, -25)
        self.assertIn("Address below Greeting (-350)", factors)
    
    def test_penalty_subject_below_greeting(self):
        """Test -200 penalty when subject is below greeting."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            subject=TextMarker(found=True, raw="Subject", x_rel=0.1, y_rel=0.6),
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.3)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        # Greeting at top: +250, Subject lower: +50, Penalty: -200
        # Net: 250 + 50 - 200 = 100
        self.assertEqual(score, 100)
        self.assertIn("Subject below Greeting (-200)", factors)
    
    def test_penalty_goodbye_at_top(self):
        """Test -100 penalty when goodbye is at top third."""
        prev_page = self._create_page()
        curr_page = self._create_page(
            goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.2)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertEqual(score, -100)
        self.assertIn("Goodbye at top (-100)", factors)
    
    def test_single_page_bonus(self):
        """Test +200 bonus when previous page is a complete letter."""
        prev_page = self._create_page(
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.2),
            goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.8)
        )
        curr_page = self._create_page()
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        self.assertGreaterEqual(score, 200)
        self.assertIn("Previous page complete letter (+200)", factors)
    
    def test_combined_scoring(self):
        """Test multiple factors combining."""
        prev_page = self._create_page(
            letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.9),
            greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.2),
            goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.8)
        )
        curr_page = self._create_page(
            letter_page_index=LetterPageIndex(found=True, current=1, total=2, raw="Page 1 of 2", x_rel=0.5, y_rel=0.1),
            address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.15, line_count=4),
            subject=TextMarker(found=True, raw="Notice", x_rel=0.1, y_rel=0.3),
            date=DateMarker(found=True, raw="2024-11-05", x_rel=0.8, y_rel=0.2)
        )
        
        score, factors = self.scorer.score_transition(prev_page, curr_page)
        
        # Expected: 1000 (prev last) + 200 (complete letter) + 1000 (new index) 
        #           + 450 (address) + 300 (subject) + 50 (date) = 3000
        self.assertGreaterEqual(score, 3000)
        self.assertGreater(len(factors), 3)
    
    def _create_page(self, letter_page_index=None, greeting=None, goodbye=None, 
                     subject=None, address_block=None, date=None):
        """Helper to create a PageAnalysis object with specified fields."""
        return PageAnalysis(
            scan_page_num=1,
            letter_page_index=letter_page_index or LetterPageIndex(),
            greeting=greeting or TextMarker(),
            goodbye=goodbye or TextMarker(),
            subject=subject or TextMarker(),
            address_block=address_block or AddressBlock(),
            date=date or DateMarker()
        )


class TestGroupPagesIntoLetters(unittest.TestCase):
    """Test cases for the group_pages_into_letters function."""
    
    def test_empty_input(self):
        """Test grouping with no pages."""
        result = group_pages_into_letters([])
        
        self.assertEqual(len(result), 0)
    
    def test_single_page(self):
        """Test grouping with a single page."""
        page = self._create_page(scan_page_num=1)
        result = group_pages_into_letters([page])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].pages), 1)
        self.assertEqual(result[0].pages[0].scan_page_num, 1)
    
    def test_two_pages_no_split(self):
        """Test two pages that should stay together."""
        page1 = self._create_page(
            scan_page_num=1,
            letter_page_index=LetterPageIndex(found=True, current=1, total=2, raw="Page 1 of 2", x_rel=0.5, y_rel=0.9)
        )
        page2 = self._create_page(
            scan_page_num=2,
            letter_page_index=LetterPageIndex(found=True, current=2, total=2, raw="Page 2 of 2", x_rel=0.5, y_rel=0.9)
        )
        
        result = group_pages_into_letters([page1, page2])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].pages), 2)
    
    def test_split_on_threshold(self):
        """Test splitting when score exceeds threshold."""
        page1 = self._create_page(
            scan_page_num=1,
            letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.9)
        )
        page2 = self._create_page(
            scan_page_num=2,
            letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.1)
        )
        
        result = group_pages_into_letters([page1, page2])
        
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].pages), 1)
        self.assertEqual(len(result[1].pages), 1)
        self.assertEqual(result[0].pages[0].scan_page_num, 1)
        self.assertEqual(result[1].pages[0].scan_page_num, 2)
    
    def test_multiple_letters(self):
        """Test splitting multiple letters."""
        pages = [
            self._create_page(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=2, raw="Page 1 of 2", x_rel=0.5, y_rel=0.1)
            ),
            self._create_page(
                scan_page_num=2,
                letter_page_index=LetterPageIndex(found=True, current=2, total=2, raw="Page 2 of 2", x_rel=0.5, y_rel=0.9)
            ),
            self._create_page(
                scan_page_num=3,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.1),
                address_block=AddressBlock(found=True, x_rel=0.1, y_rel=0.15, line_count=4)
            ),
            self._create_page(
                scan_page_num=4,
                letter_page_index=LetterPageIndex(found=True, current=1, total=3, raw="Page 1 of 3", x_rel=0.5, y_rel=0.1)
            ),
            self._create_page(
                scan_page_num=5,
                letter_page_index=LetterPageIndex(found=True, current=2, total=3, raw="Page 2 of 3", x_rel=0.5, y_rel=0.9)
            ),
            self._create_page(
                scan_page_num=6,
                letter_page_index=LetterPageIndex(found=True, current=3, total=3, raw="Page 3 of 3", x_rel=0.5, y_rel=0.9)
            ),
        ]
        
        result = group_pages_into_letters(pages)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(len(result[0].pages), 2)  # Pages 1-2
        self.assertEqual(len(result[1].pages), 1)  # Page 3
        self.assertEqual(len(result[2].pages), 3)  # Pages 4-6
    
    def test_single_page_letters(self):
        """Test multiple single-page letters."""
        pages = [
            self._create_page(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.1),
                greeting=TextMarker(found=True, raw="Dear Sir", x_rel=0.1, y_rel=0.2),
                goodbye=TextMarker(found=True, raw="Sincerely", x_rel=0.1, y_rel=0.8)
            ),
            self._create_page(
                scan_page_num=2,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.1),
                greeting=TextMarker(found=True, raw="Hello", x_rel=0.1, y_rel=0.2),
                goodbye=TextMarker(found=True, raw="Best regards", x_rel=0.1, y_rel=0.8)
            ),
        ]
        
        result = group_pages_into_letters(pages)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].pages), 1)
        self.assertEqual(len(result[1].pages), 1)
    
    def test_validation_warning_for_gaps(self):
        """Test that validation warns about gaps in page indices."""
        # Create pages with a gap: 1, 2, 4 (missing 3)
        pages = [
            self._create_page(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=4, raw="Page 1 of 4", x_rel=0.5, y_rel=0.1)
            ),
            self._create_page(
                scan_page_num=2,
                letter_page_index=LetterPageIndex(found=True, current=2, total=4, raw="Page 2 of 4", x_rel=0.5, y_rel=0.9)
            ),
            self._create_page(
                scan_page_num=3,
                letter_page_index=LetterPageIndex(found=True, current=4, total=4, raw="Page 4 of 4", x_rel=0.5, y_rel=0.9)
            ),
        ]
        
        # This should log a warning but still group them together
        result = group_pages_into_letters(pages)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].pages), 3)
    
    def test_with_date_and_subject(self):
        """Test extracting master date and subject."""
        date_val = datetime(2024, 11, 5)
        pages = [
            self._create_page(
                scan_page_num=1,
                letter_page_index=LetterPageIndex(found=True, current=1, total=1, raw="Page 1 of 1", x_rel=0.5, y_rel=0.1),
                date=DateMarker(found=True, raw="2024-11-05", date_value=date_val, x_rel=0.8, y_rel=0.2),
                subject=TextMarker(found=True, raw="Important Notice", x_rel=0.1, y_rel=0.3)
            ),
        ]
        
        result = group_pages_into_letters(pages)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].master_date, "2024-11-05")
        self.assertEqual(result[0].master_subject, "Important Notice")
    
    def _create_page(self, scan_page_num=1, letter_page_index=None, greeting=None, 
                     goodbye=None, subject=None, address_block=None, date=None):
        """Helper to create a PageAnalysis object."""
        return PageAnalysis(
            scan_page_num=scan_page_num,
            letter_page_index=letter_page_index or LetterPageIndex(),
            greeting=greeting or TextMarker(),
            goodbye=goodbye or TextMarker(),
            subject=subject or TextMarker(),
            address_block=address_block or AddressBlock(),
            date=date or DateMarker()
        )


if __name__ == '__main__':
    unittest.main()
