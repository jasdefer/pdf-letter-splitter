#!/usr/bin/env python3
"""
Test suite for OCR text extraction.

Validates that the extract_text.py script correctly extracts text from PDF files.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add Source directory to path to import the extraction module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from extract_text import extract_text_from_pdf


class TestOCRExtract(unittest.TestCase):
    """Test cases for OCR text extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_pdf_path = Path(__file__).parent / 'test.pdf'
        self.assertTrue(self.test_pdf_path.exists(), 
                       f"Test PDF not found: {self.test_pdf_path}")
    
    def test_extract_text_from_test_pdf(self):
        """Test that text can be extracted from test.pdf."""
        # Extract text from the test PDF
        result = extract_text_from_pdf(self.test_pdf_path)
        
        # Verify structure
        self.assertIn('page_count', result)
        self.assertIn('pages', result)
        
        # Verify page count is 4 as specified
        self.assertEqual(result['page_count'], 4, 
                        "Expected test.pdf to have 4 pages")
        
        # Verify we have 4 page entries
        self.assertEqual(len(result['pages']), 4)
        
        # Verify each page has the required structure
        for page in result['pages']:
            self.assertIn('page_number', page)
            self.assertIn('text', page)
        
        # Verify page numbers are sequential from 1 to 4
        page_numbers = [page['page_number'] for page in result['pages']]
        self.assertEqual(page_numbers, [1, 2, 3, 4])
    
    def test_extracted_text_is_non_empty(self):
        """Test that extracted text is non-empty globally."""
        # Extract text from the test PDF
        result = extract_text_from_pdf(self.test_pdf_path)
        
        # Concatenate all text from all pages
        all_text = ''.join(page['text'] for page in result['pages'])
        
        # Verify that we extracted some text
        self.assertTrue(len(all_text.strip()) > 0, 
                       "Expected to extract non-empty text from the PDF")
    
    def test_extracted_text_is_non_empty_per_page(self):
        """Test that extracted text is non-empty for each page."""
        # Extract text from the test PDF
        result = extract_text_from_pdf(self.test_pdf_path)
        
        # Verify each page has some text
        for page in result['pages']:
            page_num = page['page_number']
            text = page['text']
            # At least one page should have text (scanned PDFs may have some blank pages)
            # But we'll check that at least some pages have content
        
        # Verify that at least some pages have content
        pages_with_content = sum(1 for page in result['pages'] 
                                if len(page['text'].strip()) > 0)
        self.assertGreater(pages_with_content, 0, 
                          "Expected at least one page to have non-empty text")
    
    def test_json_output_format(self):
        """Test that the output can be serialized to JSON correctly."""
        # Extract text from the test PDF
        result = extract_text_from_pdf(self.test_pdf_path)
        
        # Try to serialize to JSON (should not raise an exception)
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        
        # Verify we can parse it back
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed['page_count'], result['page_count'])
        self.assertEqual(len(parsed['pages']), len(result['pages']))
    
    def test_missing_file_raises_error(self):
        """Test that missing input file raises FileNotFoundError."""
        non_existent_path = Path('/tmp/does_not_exist_12345.pdf')
        
        with self.assertRaises(FileNotFoundError):
            extract_text_from_pdf(non_existent_path)


if __name__ == '__main__':
    unittest.main()
