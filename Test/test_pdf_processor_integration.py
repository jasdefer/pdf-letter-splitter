#!/usr/bin/env python3
"""
Integration tests for the pdf_processor module with real PDF files.

Tests the complete PDF splitting workflow.
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

# Try to import pypdf
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class TestPDFProcessorIntegration(unittest.TestCase):
    """Integration tests for PDF processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / 'output'
        self.processor = PDFProcessor(self.output_dir)
        
        # Path to test PDF (should exist in Test directory)
        self.test_pdf_path = Path(__file__).parent / 'test_multi_page.pdf'
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipIf(PdfReader is None, "pypdf not installed")
    def test_process_single_letter_single_page(self):
        """Test processing a single letter with one page."""
        if not self.test_pdf_path.exists():
            self.skipTest("Test PDF not found")
        
        # Create a single letter with page 1
        date_val = datetime(2026, 1, 22)
        page = self._create_page(
            scan_page_num=1,
            date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
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
        
        # Process the letter
        created_files = self.processor.process_letters(self.test_pdf_path, [letter])
        
        # Verify results
        self.assertEqual(len(created_files), 1)
        self.assertTrue(created_files[0].exists())
        self.assertEqual(created_files[0].name, "20260122-Allianz-Invoice.pdf")
        
        # Verify the PDF has 1 page
        reader = PdfReader(str(created_files[0]))
        self.assertEqual(len(reader.pages), 1)
    
    @unittest.skipIf(PdfReader is None, "pypdf not installed")
    def test_process_single_letter_multiple_pages(self):
        """Test processing a single letter with multiple pages."""
        if not self.test_pdf_path.exists():
            self.skipTest("Test PDF not found")
        
        # Create a single letter with pages 1-3
        date_val = datetime(2026, 1, 22)
        pages = [
            self._create_page(
                scan_page_num=1,
                date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
                sender=SenderBlock(
                found=True,
                sender_name="Allianz"
            ),
                subject=TextMarker(
                    found=True,
                    raw="Annual Report",
                    x_rel=0.1,
                    y_rel=0.3
                )
            ),
            self._create_page(scan_page_num=2),
            self._create_page(scan_page_num=3),
        ]
        letter = Letter(pages=pages)
        
        # Process the letter
        created_files = self.processor.process_letters(self.test_pdf_path, [letter])
        
        # Verify results
        self.assertEqual(len(created_files), 1)
        self.assertTrue(created_files[0].exists())
        self.assertEqual(created_files[0].name, "20260122-Allianz-AnnualReport.pdf")
        
        # Verify the PDF has 3 pages
        reader = PdfReader(str(created_files[0]))
        self.assertEqual(len(reader.pages), 3)
    
    @unittest.skipIf(PdfReader is None, "pypdf not installed")
    def test_process_multiple_letters(self):
        """Test processing multiple letters from the same PDF."""
        if not self.test_pdf_path.exists():
            self.skipTest("Test PDF not found")
        
        # Create two letters
        date_val1 = datetime(2026, 1, 22)
        letter1 = Letter(pages=[
            self._create_page(
                scan_page_num=1,
                date=DateMarker(found=True, date_value=date_val1, raw="2026-01-22"),
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
        ])
        
        date_val2 = datetime(2026, 1, 23)
        letter2 = Letter(pages=[
            self._create_page(
                scan_page_num=2,
                date=DateMarker(found=True, date_value=date_val2, raw="2026-01-23"),
                sender=SenderBlock(
                found=True,
                sender_name="Deutsche Bank"
            ),
                subject=TextMarker(
                    found=True,
                    raw="Statement",
                    x_rel=0.1,
                    y_rel=0.3
                )
            ),
            self._create_page(scan_page_num=3)
        ])
        
        # Process the letters
        created_files = self.processor.process_letters(self.test_pdf_path, [letter1, letter2])
        
        # Verify results
        self.assertEqual(len(created_files), 2)
        
        # Check first letter
        self.assertTrue(created_files[0].exists())
        self.assertEqual(created_files[0].name, "20260122-Allianz-Invoice.pdf")
        reader1 = PdfReader(str(created_files[0]))
        self.assertEqual(len(reader1.pages), 1)
        
        # Check second letter
        self.assertTrue(created_files[1].exists())
        self.assertEqual(created_files[1].name, "20260123-Deutsche-Statement.pdf")
        reader2 = PdfReader(str(created_files[1]))
        self.assertEqual(len(reader2.pages), 2)
    
    @unittest.skipIf(PdfReader is None, "pypdf not installed")
    def test_process_incomplete_letter(self):
        """Test processing a letter with incomplete metadata."""
        if not self.test_pdf_path.exists():
            self.skipTest("Test PDF not found")
        
        # Create a letter with missing date
        page = self._create_page(
            scan_page_num=1,
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
        
        # Process the letter
        created_files = self.processor.process_letters(self.test_pdf_path, [letter])
        
        # Verify results
        self.assertEqual(len(created_files), 1)
        self.assertTrue(created_files[0].exists())
        # Should be marked as incomplete
        self.assertTrue(created_files[0].name.startswith("0_Incomplete_"))
        self.assertIn("Allianz", created_files[0].name)
    
    @unittest.skipIf(PdfReader is None, "pypdf not installed")
    def test_process_with_collision(self):
        """Test processing with filename collision."""
        if not self.test_pdf_path.exists():
            self.skipTest("Test PDF not found")
        
        # Create two letters with the same metadata
        date_val = datetime(2026, 1, 22)
        
        def create_identical_letter(page_num):
            return Letter(pages=[
                self._create_page(
                    scan_page_num=page_num,
                    date=DateMarker(found=True, date_value=date_val, raw="2026-01-22"),
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
            ])
        
        letter1 = create_identical_letter(1)
        letter2 = create_identical_letter(2)
        
        # Process the letters
        created_files = self.processor.process_letters(self.test_pdf_path, [letter1, letter2])
        
        # Verify results
        self.assertEqual(len(created_files), 2)
        
        # First file should have the base name
        self.assertEqual(created_files[0].name, "20260122-Allianz-Invoice.pdf")
        
        # Second file should have _1 suffix
        self.assertEqual(created_files[1].name, "20260122-Allianz-Invoice_1.pdf")
    
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
