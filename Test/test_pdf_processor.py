#!/usr/bin/env python3
"""
Unit tests for the pdf_processor module.

Tests the PDF splitting, filename construction, sanitization, and collision handling.
"""

import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from pdf_processor import PDFProcessor
from splitter import Letter
from page_analysis_data import (
    PageAnalysis, LetterPageIndex, TextMarker, AddressBlock, DateMarker, SenderBlock
)


class TestPDFProcessor(unittest.TestCase):
    """Test cases for the PDFProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / 'output'
        self.processor = PDFProcessor(self.output_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_output_dir_creation(self):
        """Test that output directory is created."""
        self.assertTrue(self.output_dir.exists())
        self.assertTrue(self.output_dir.is_dir())
    
    def test_extract_date_valid(self):
        """Test date extraction with valid date."""
        date_val = datetime(2026, 1, 22)
        page = self._create_page(
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22")
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_date(letter)
        
        self.assertEqual(result, "20260122")
    
    def test_extract_date_none(self):
        """Test date extraction when no date is found."""
        page = self._create_page()
        letter = Letter(pages=[page])
        
        result = self.processor._extract_date(letter)
        
        self.assertIsNone(result)
    
    def test_extract_sender_single_word(self):
        """Test sender extraction with single word name."""
        page = self._create_page(
            sender=SenderBlock(
                found=True,
                sender_name="Allianz"
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_sender(letter)
        
        self.assertEqual(result, "Allianz")
    
    def test_extract_sender_multiple_words(self):
        """Test sender extraction with multiple words - uses longest."""
        page = self._create_page(
            sender=SenderBlock(
                found=True,
                sender_name="Deutsche Telekom AG"
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_sender(letter)
        
        # "Deutsche" (8 chars) is longer than "Telekom" (7 chars)
        self.assertEqual(result, "Deutsche")
    
    def test_extract_sender_with_special_characters(self):
        """Test sender extraction with special characters removed."""
        page = self._create_page(
            sender=SenderBlock(
                found=True,
                sender_name="Müller & Co. GmbH"
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_sender(letter)
        
        # Special characters should be removed
        self.assertEqual(result, "Mller")
    
    def test_extract_sender_none(self):
        """Test sender extraction when no address block is found."""
        page = self._create_page()
        letter = Letter(pages=[page])
        
        result = self.processor._extract_sender(letter)
        
        self.assertIsNone(result)
    
    def test_extract_topic_simple(self):
        """Test topic extraction with simple subject."""
        page = self._create_page(
            subject=TextMarker(
                found=True,
                raw="Invoice Payment Reminder",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        # Should keep first 3 significant words, concatenated
        self.assertEqual(result, "InvoicePaymentReminder")
    
    def test_extract_topic_with_stop_words(self):
        """Test topic extraction filtering stop words."""
        page = self._create_page(
            subject=TextMarker(
                found=True,
                raw="Notice for the Annual Meeting",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        # 'for', 'the' should be filtered out
        # Should keep: Notice, Annual, Meeting
        self.assertEqual(result, "NoticeAnnualMeeting")
    
    def test_extract_topic_german_stop_words(self):
        """Test topic extraction with German stop words."""
        page = self._create_page(
            subject=TextMarker(
                found=True,
                raw="Mahnung für die Rechnung",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        # 'für', 'die' should be filtered out
        # Should keep: Mahnung, Rechnung
        self.assertEqual(result, "MahnungRechnung")
    
    def test_extract_topic_with_special_characters(self):
        """Test topic extraction removes special characters."""
        page = self._create_page(
            subject=TextMarker(
                found=True,
                raw="Tax-Return & Documents!",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        # Special characters should be removed
        self.assertEqual(result, "TaxReturnDocuments")
    
    def test_extract_topic_max_three_words(self):
        """Test topic extraction limits to 3 words."""
        page = self._create_page(
            subject=TextMarker(
                found=True,
                raw="Important Annual Financial Statement Review Report",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        # Should only take first 3 significant words
        words = result
        # All are significant, so first 3
        self.assertEqual(result, "ImportantAnnualFinancial")
    
    def test_extract_topic_none(self):
        """Test topic extraction when no subject is found."""
        page = self._create_page()
        letter = Letter(pages=[page])
        
        result = self.processor._extract_topic(letter)
        
        self.assertIsNone(result)
    
    def test_construct_filename_complete(self):
        """Test filename construction with all metadata."""
        date_val = datetime(2026, 1, 22)
        page = self._create_page(
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
            sender=SenderBlock(
                found=True,
                sender_name="Allianz Versicherung"
            ),
            subject=TextMarker(
                found=True,
                raw="Invoice Payment Reminder",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Format: YYYYMMDD-Sender-Topic
        self.assertEqual(result, "20260122-Versicherung-InvoicePaymentReminder")
    
    def test_construct_filename_incomplete_missing_date(self):
        """Test filename with missing date is marked incomplete."""
        page = self._create_page(
            sender=SenderBlock(
                found=True,
                sender_name="Allianz"
            ),
            subject=TextMarker(
                found=True,
                raw="Invoice",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Should be prepended with 0_Incomplete_
        self.assertTrue(result.startswith("0_Incomplete_"))
        self.assertIn("Allianz", result)
        self.assertIn("Invoice", result)
    
    def test_construct_filename_incomplete_missing_sender(self):
        """Test filename with missing sender is marked incomplete."""
        date_val = datetime(2026, 1, 22)
        page = self._create_page(
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
            subject=TextMarker(
                found=True,
                raw="Invoice",
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Should be prepended with 0_Incomplete_
        self.assertTrue(result.startswith("0_Incomplete_"))
        self.assertIn("20260122", result)
        self.assertIn("Invoice", result)
    
    def test_construct_filename_incomplete_missing_topic(self):
        """Test filename with missing topic is marked incomplete."""
        date_val = datetime(2026, 1, 22)
        page = self._create_page(
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
            sender=SenderBlock(
                found=True,
                sender_name="Allianz"
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Should be prepended with 0_Incomplete_
        self.assertTrue(result.startswith("0_Incomplete_"))
        self.assertIn("20260122", result)
        self.assertIn("Allianz", result)
    
    def test_construct_filename_all_missing(self):
        """Test filename when all metadata is missing."""
        page = self._create_page()
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Should be 0_Incomplete_Unknown or similar
        self.assertTrue(result.startswith("0_Incomplete_"))
    
    def test_construct_filename_truncation(self):
        """Test that very long filenames are truncated."""
        date_val = datetime(2026, 1, 22)
        long_subject = "A " * 200  # Very long subject
        page = self._create_page(
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
            sender=SenderBlock(
                found=True,
                sender_name="Allianz"
            ),
            subject=TextMarker(
                found=True,
                raw=long_subject,
                x_rel=0.1,
                y_rel=0.3
            )
        )
        letter = Letter(pages=[page])
        
        result = self.processor._construct_filename(letter)
        
        # Should be truncated to a reasonable length
        self.assertLessEqual(len(result), 200)
    
    def test_get_unique_filepath_no_collision(self):
        """Test getting unique filepath with no collision."""
        filename_base = "20260122-Allianz-Invoice"
        
        result = self.processor._get_unique_filepath(filename_base)
        
        self.assertEqual(result.name, "20260122-Allianz-Invoice.pdf")
        self.assertEqual(result.parent, self.output_dir)
    
    def test_get_unique_filepath_with_collision(self):
        """Test getting unique filepath with collision."""
        filename_base = "20260122-Allianz-Invoice"
        
        # Create a file that will collide
        collision_file = self.output_dir / "20260122-Allianz-Invoice.pdf"
        collision_file.touch()
        
        result = self.processor._get_unique_filepath(filename_base)
        
        # Should append _1
        self.assertEqual(result.name, "20260122-Allianz-Invoice_1.pdf")
    
    def test_get_unique_filepath_multiple_collisions(self):
        """Test getting unique filepath with multiple collisions."""
        filename_base = "20260122-Allianz-Invoice"
        
        # Create files that will collide
        (self.output_dir / "20260122-Allianz-Invoice.pdf").touch()
        (self.output_dir / "20260122-Allianz-Invoice_1.pdf").touch()
        (self.output_dir / "20260122-Allianz-Invoice_2.pdf").touch()
        
        result = self.processor._get_unique_filepath(filename_base)
        
        # Should append _3
        self.assertEqual(result.name, "20260122-Allianz-Invoice_3.pdf")
    
    def _create_page(self, scan_page_num=1, date=None, subject=None, address_block=None, sender=None):
        """Helper to create a minimal PageAnalysis object."""
        return PageAnalysis(
            scan_page_num=scan_page_num,
            letter_page_index=LetterPageIndex(),
            greeting=TextMarker(),
            goodbye=TextMarker(),
            subject=subject or TextMarker(),
            address_block=address_block or AddressBlock(),
            date=date or DateMarker(),
            sender=sender
        )


if __name__ == '__main__':
    unittest.main()
