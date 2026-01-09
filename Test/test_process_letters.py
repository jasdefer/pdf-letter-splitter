#!/usr/bin/env python3
"""
Test for the unified process_letters.py entry point.

Tests the integration between extract_text and analyze_letters modules.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))


class TestProcessLetters(unittest.TestCase):
    """Test cases for the unified letter processing pipeline."""
    
    @patch('process_letters.extract_text_from_pdf')
    @patch('process_letters.analyze_documents')
    def test_process_pdf_letters_integration(self, mock_analyze, mock_extract):
        """Test the complete pipeline integration."""
        from process_letters import process_pdf_letters
        
        # Mock OCR extraction result
        mock_extract.return_value = {
            'page_count': 5,
            'pages': [
                {'page_number': 1, 'text': 'Letter 1 page 1 text'},
                {'page_number': 2, 'text': 'Letter 1 page 2 text'},
                {'page_number': 3, 'text': 'Letter 2 page 1 text'},
                {'page_number': 4, 'text': 'Letter 2 page 2 text'},
                {'page_number': 5, 'text': 'Letter 2 page 3 text'},
            ]
        }
        
        # Mock letter analysis result
        mock_analyze.return_value = [
            {
                'date': '2026-01-15',
                'sender': 'Company A',
                'topic': 'Invoice',
                'page_count': 2,
                'start_page': 1
            },
            {
                'date': '2026-01-20',
                'sender': 'Company B',
                'topic': 'Report',
                'page_count': 3,
                'start_page': 3
            }
        ]
        
        # Run the pipeline
        result = process_pdf_letters(Path('test.pdf'))
        
        # Verify extract_text was called correctly
        mock_extract.assert_called_once()
        self.assertEqual(mock_extract.call_args[0][0], Path('test.pdf'))
        
        # Verify analyze_documents was called with correct page texts
        mock_analyze.assert_called_once()
        page_texts = mock_analyze.call_args[0][0]
        self.assertEqual(len(page_texts), 5)
        self.assertEqual(page_texts[0], 'Letter 1 page 1 text')
        
        # Verify output structure
        self.assertEqual(result['input_file'], 'test.pdf')
        self.assertEqual(result['total_pages'], 5)
        self.assertEqual(result['letters_found'], 2)
        self.assertEqual(len(result['letters']), 2)
        
        # Verify letter data is passed through
        self.assertEqual(result['letters'][0]['sender'], 'Company A')
        self.assertEqual(result['letters'][1]['sender'], 'Company B')
    
    @patch('process_letters.extract_text_from_pdf')
    @patch('process_letters.analyze_documents')
    def test_process_with_options(self, mock_analyze, mock_extract):
        """Test that OCR options are passed correctly."""
        from process_letters import process_pdf_letters
        
        mock_extract.return_value = {
            'page_count': 1,
            'pages': [{'page_number': 1, 'text': 'Test'}]
        }
        mock_analyze.return_value = []
        
        # Call with custom options
        process_pdf_letters(
            Path('test.pdf'),
            rotate=False,
            deskew=False,
            jobs=4
        )
        
        # Verify options were passed to extract_text
        call_kwargs = mock_extract.call_args[1]
        self.assertEqual(call_kwargs['rotate'], False)
        self.assertEqual(call_kwargs['deskew'], False)
        self.assertEqual(call_kwargs['jobs'], 4)
    
    @patch('process_letters.extract_text_from_pdf')
    @patch('process_letters.analyze_documents')
    def test_empty_pdf(self, mock_analyze, mock_extract):
        """Test handling of empty PDF."""
        from process_letters import process_pdf_letters
        
        mock_extract.return_value = {
            'page_count': 0,
            'pages': []
        }
        mock_analyze.return_value = []
        
        result = process_pdf_letters(Path('empty.pdf'))
        
        self.assertEqual(result['total_pages'], 0)
        self.assertEqual(result['letters_found'], 0)
        self.assertEqual(result['letters'], [])
    
    @patch('process_letters.extract_text_from_pdf')
    @patch('process_letters.analyze_documents')
    def test_single_letter(self, mock_analyze, mock_extract):
        """Test PDF with single letter."""
        from process_letters import process_pdf_letters
        
        mock_extract.return_value = {
            'page_count': 3,
            'pages': [
                {'page_number': 1, 'text': 'Page 1'},
                {'page_number': 2, 'text': 'Page 2'},
                {'page_number': 3, 'text': 'Page 3'},
            ]
        }
        
        mock_analyze.return_value = [
            {
                'date': '2026-01-15',
                'sender': 'Company',
                'topic': 'Letter',
                'page_count': 3,
                'start_page': 1
            }
        ]
        
        result = process_pdf_letters(Path('single.pdf'))
        
        self.assertEqual(result['letters_found'], 1)
        self.assertEqual(result['letters'][0]['page_count'], 3)


if __name__ == '__main__':
    unittest.main()
