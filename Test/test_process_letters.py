#!/usr/bin/env python3
"""
Test suite for OCR text extraction with positional data.

Validates that the process_letters.py script correctly extracts text with
bounding boxes from PDF files.
"""

import sys
import unittest
from pathlib import Path

# Add Source directory to path to import the extraction module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from process_letters import extract_text


class TestOCRExtractWithPositions(unittest.TestCase):
    """Test cases for OCR text extraction with positional data."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_pdf_path = Path(__file__).parent / 'test.pdf'
        self.assertTrue(self.test_pdf_path.exists(), 
                       f"Test PDF not found: {self.test_pdf_path}")
    
    def test_extract_text_returns_dataframe(self):
        """Test that extract_text returns a pandas DataFrame."""
        import pandas as pd
        
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Verify it's a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
    
    def test_dataframe_has_required_columns(self):
        """Test that the DataFrame has all required columns."""
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Base columns from Tesseract TSV
        required_base_columns = [
            'level', 'page_num', 'block_num', 'par_num', 'line_num', 
            'word_num', 'left', 'top', 'width', 'height', 'conf', 'text'
        ]
        
        # Derived columns
        required_derived_columns = ['right', 'bottom', 'page_width', 'page_height']
        
        all_required_columns = required_base_columns + required_derived_columns
        
        for col in all_required_columns:
            self.assertIn(col, result.columns, 
                         f"Expected column '{col}' not found in DataFrame")
    
    def test_dataframe_has_correct_page_count(self):
        """Test that the DataFrame contains data from 4 pages."""
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Verify page count is 4 as specified
        unique_pages = result['page_num'].unique()
        self.assertEqual(len(unique_pages), 4, 
                        "Expected test.pdf to have 4 pages")
        
        # Verify page numbers are 1, 2, 3, 4
        self.assertEqual(sorted(unique_pages.tolist()), [1, 2, 3, 4])
    
    def test_extracted_text_is_non_empty(self):
        """Test that extracted text is non-empty globally."""
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Filter to only word-level elements (level 5) with non-empty text
        word_rows = result[result['level'] == 5]
        text_rows = word_rows[word_rows['text'].notna() & (word_rows['text'].str.strip() != '')]
        
        # Verify that we extracted some text
        self.assertGreater(len(text_rows), 0, 
                          "Expected to extract non-empty text from the PDF")
    
    def test_derived_columns_are_correct(self):
        """Test that derived columns (right, bottom) are calculated correctly."""
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Filter to rows with non-null coordinates
        valid_rows = result[(result['left'].notna()) & (result['width'].notna())]
        
        if len(valid_rows) > 0:
            # Check that right = left + width
            self.assertTrue(
                (valid_rows['right'] == valid_rows['left'] + valid_rows['width']).all(),
                "right column should equal left + width"
            )
            
            # Check that bottom = top + height
            self.assertTrue(
                (valid_rows['bottom'] == valid_rows['top'] + valid_rows['height']).all(),
                "bottom column should equal top + height"
            )
    
    def test_page_dimensions_populated(self):
        """Test that page_width and page_height are populated for all rows."""
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Check that page_width and page_height are not null
        self.assertTrue(result['page_width'].notna().all(),
                       "page_width should be populated for all rows")
        self.assertTrue(result['page_height'].notna().all(),
                       "page_height should be populated for all rows")
        
        # Check that values are positive
        self.assertTrue((result['page_width'] > 0).all(),
                       "page_width should be positive")
        self.assertTrue((result['page_height'] > 0).all(),
                       "page_height should be positive")
    
    def test_dataframe_to_tsv(self):
        """Test that the DataFrame can be saved to TSV format."""
        import tempfile
        import os
        
        # Extract text from the test PDF
        result = extract_text(self.test_pdf_path)
        
        # Try to save to TSV (should not raise an exception)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as f:
            tsv_path = f.name
        
        try:
            result.to_csv(tsv_path, sep='\t', index=False)
            
            # Verify file was created and is not empty
            self.assertTrue(os.path.exists(tsv_path))
            self.assertGreater(os.path.getsize(tsv_path), 0)
        finally:
            # Clean up
            if os.path.exists(tsv_path):
                os.unlink(tsv_path)
    
    def test_missing_file_raises_error(self):
        """Test that missing input file raises FileNotFoundError."""
        non_existent_path = Path('/tmp/does_not_exist_12345.pdf')
        
        with self.assertRaises(FileNotFoundError):
            extract_text(non_existent_path)


if __name__ == '__main__':
    unittest.main()
