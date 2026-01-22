#!/usr/bin/env python3
"""
Unit tests for detect_letter_page_index function.

Tests the detection of page index information from OCR data.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

# Add Source directory to path to import the marker detection module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from marker_detection import detect_letter_page_index
from page_analysis_data import LetterPageIndex

# Test data constants
CHAR_WIDTH_PIXELS = 10  # Approximate width per character for test data
WORD_HEIGHT_PIXELS = 20  # Approximate height of words for test data


class TestDetectLetterPageIndex(unittest.TestCase):
    """Test cases for detect_letter_page_index function."""
    
    def _create_test_dataframe(self, words_data, page_width=1000, page_height=1500):
        """
        Helper to create a minimal OCR DataFrame for testing.
        
        Args:
            words_data: List of tuples (text, left, top, line_num) or (text, left, top, line_num, par_num)
            page_width: Page width in pixels
            page_height: Page height in pixels
        
        Returns:
            DataFrame mimicking OCR output
        """
        rows = []
        for idx, word_data in enumerate(words_data):
            if len(word_data) == 4:
                text, left, top, line_num = word_data
                par_num = 1  # Default to paragraph 1
            else:
                text, left, top, line_num, par_num = word_data
            
            rows.append({
                'level': 5,  # Word level
                'page_num': 1,
                'block_num': 1,
                'par_num': par_num,
                'line_num': line_num,
                'word_num': idx + 1,
                'left': left,
                'top': top,
                'width': len(text) * CHAR_WIDTH_PIXELS,
                'height': WORD_HEIGHT_PIXELS,
                'conf': 90,
                'text': text,
                'page_width': page_width,
                'page_height': page_height,
            })
        return pd.DataFrame(rows)
    
    # ========== Priority 1: Total Information Patterns ==========
    
    def test_detect_german_seite_von_pattern(self):
        """Test detection of 'Seite X von Y' pattern."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('2', 160, 1400, 1),
            ('von', 180, 1400, 1),
            ('5', 220, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 5)
        self.assertEqual(result.raw, 'Seite 2 von 5')
        self.assertAlmostEqual(result.x_rel, 0.1, places=2)  # 100/1000
        self.assertAlmostEqual(result.y_rel, 0.933, places=2)  # 1400/1500
    
    def test_detect_german_seite_slash_pattern_no_spaces(self):
        """Test detection of 'Seite X/Y' pattern without spaces."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('3/7', 160, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 3)
        self.assertEqual(result.total, 7)
        self.assertIn('Seite', result.raw)
        self.assertIn('3', result.raw)
        self.assertIn('7', result.raw)
    
    def test_detect_german_seite_slash_pattern_with_spaces(self):
        """Test detection of 'Seite X / Y' pattern with spaces around slash."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('1', 160, 1400, 1),
            ('/', 180, 1400, 1),
            ('4', 200, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertEqual(result.total, 4)
        self.assertIn('Seite', result.raw)
    
    def test_detect_english_page_of_pattern(self):
        """Test detection of 'Page X of Y' pattern."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('4', 160, 1400, 1),
            ('of', 180, 1400, 1),
            ('10', 210, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 4)
        self.assertEqual(result.total, 10)
        self.assertEqual(result.raw, 'Page 4 of 10')
        self.assertAlmostEqual(result.x_rel, 0.1, places=2)
    
    def test_detect_english_page_slash_pattern_no_spaces(self):
        """Test detection of 'Page X/Y' pattern without spaces."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('2/8', 160, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 8)
        self.assertIn('Page', result.raw)
    
    def test_detect_english_page_slash_pattern_with_spaces(self):
        """Test detection of 'Page X / Y' pattern with spaces around slash."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('5', 160, 1400, 1),
            ('/', 180, 1400, 1),
            ('6', 200, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 5)
        self.assertEqual(result.total, 6)
        self.assertIn('Page', result.raw)
    
    def test_case_insensitivity(self):
        """Test that pattern matching is case-insensitive."""
        # Test lowercase
        words_data = [
            ('seite', 100, 1400, 1),
            ('1', 160, 1400, 1),
            ('von', 180, 1400, 1),
            ('3', 220, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertEqual(result.total, 3)
        
        # Test uppercase
        words_data = [
            ('PAGE', 100, 1400, 1),
            ('2', 160, 1400, 1),
            ('OF', 180, 1400, 1),
            ('3', 220, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 3)
    
    # ========== OCR Robustness: Handle misread separators ==========
    
    def test_detect_pipe_separator_instead_of_slash(self):
        """Test detection when OCR misreads '/' as '|' (pipe)."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('2|3', 160, 1400, 1),  # OCR read slash as pipe
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 3)
        self.assertIn('Seite', result.raw)
    
    def test_detect_capital_i_separator_instead_of_slash(self):
        """Test detection when OCR misreads '/' as 'I' (capital i)."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('3', 160, 1400, 1),
            ('I', 180, 1400, 1),  # OCR read slash as capital I
            ('5', 200, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 3)
        self.assertEqual(result.total, 5)
    
    def test_detect_lowercase_l_separator_instead_of_slash(self):
        """Test detection when OCR misreads '/' as 'l' (lowercase L)."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('1', 160, 1400, 1),
            ('l', 180, 1400, 1),  # OCR read slash as lowercase l
            ('4', 200, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertEqual(result.total, 4)
    
    def test_detect_no_space_around_separator(self):
        """Test detection of 'Seite 2/2' with no spaces around slash."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('2/2', 160, 1400, 1),  # No spaces around slash
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 2)
    
    def test_detect_mixed_spacing_and_misread_separator(self):
        """Test detection with OCR misread separator and spacing variations."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('7|10', 160, 1400, 1),  # No spaces and pipe instead of slash
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 7)
        self.assertEqual(result.total, 10)
    
    # ========== Priority 2: Continuation Patterns ==========
    
    def test_detect_german_fortsetzung_auf_pattern(self):
        """Test detection of 'Fortsetzung auf Seite X' pattern."""
        words_data = [
            ('Fortsetzung', 100, 1400, 1),
            ('auf', 240, 1400, 1),
            ('Seite', 280, 1400, 1),
            ('3', 340, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)  # Current is 3-1 = 2
        self.assertIsNone(result.total)  # Total not available for continuation
        self.assertEqual(result.raw, 'Fortsetzung auf Seite 3')
        self.assertAlmostEqual(result.x_rel, 0.1, places=2)
        self.assertAlmostEqual(result.y_rel, 0.933, places=2)
    
    def test_detect_german_fortsetzung_siehe_pattern(self):
        """Test detection of 'Fortsetzung siehe Seite X' pattern."""
        words_data = [
            ('Fortsetzung', 100, 1400, 1),
            ('siehe', 240, 1400, 1),
            ('Seite', 300, 1400, 1),
            ('4', 360, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 3)  # Current is 4-1 = 3
        self.assertIsNone(result.total)
        self.assertIn('Fortsetzung', result.raw)
    
    def test_detect_english_continued_on_page_pattern(self):
        """Test detection of 'Continued on page X' pattern."""
        words_data = [
            ('Continued', 100, 1400, 1),
            ('on', 200, 1400, 1),
            ('page', 230, 1400, 1),
            ('5', 280, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 4)  # Current is 5-1 = 4
        self.assertIsNone(result.total)
        self.assertEqual(result.raw, 'Continued on page 5')
        self.assertAlmostEqual(result.x_rel, 0.1, places=2)
    
    def test_continuation_pattern_case_insensitivity(self):
        """Test that continuation patterns are case-insensitive."""
        words_data = [
            ('fortsetzung', 100, 1400, 1),
            ('auf', 240, 1400, 1),
            ('seite', 280, 1400, 1),
            ('2', 340, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertIsNone(result.total)
    
    # ========== Priority: Total info should be preferred over continuation ==========
    
    def test_priority_total_info_over_continuation(self):
        """Test that total information patterns are prioritized over continuation patterns."""
        # Create data with both types: total info should be found first
        words_data = [
            # Continuation pattern
            ('Fortsetzung', 100, 200, 1, 1),
            ('auf', 240, 200, 1, 1),
            ('Seite', 280, 200, 1, 1),
            ('5', 340, 200, 1, 1),
            # Total info pattern (should be preferred)
            ('Seite', 100, 1400, 2, 2),
            ('3', 160, 1400, 2, 2),
            ('von', 180, 1400, 2, 2),
            ('4', 220, 1400, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        # Should find the total info pattern (Seite 3 von 4)
        self.assertTrue(result.found)
        self.assertEqual(result.current, 3)
        self.assertEqual(result.total, 4)
        self.assertIn('von', result.raw)
    
    # ========== Edge Cases ==========
    
    def test_no_match_with_standalone_number(self):
        """Test that standalone numbers are ignored (no false positives)."""
        words_data = [
            ('-', 100, 1400, 1),
            ('1', 120, 1400, 1),
            ('-', 140, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.current)
        self.assertIsNone(result.total)
    
    def test_no_match_with_numbered_list(self):
        """Test that numbered lists are ignored."""
        words_data = [
            ('2.', 100, 1400, 1),
            ('Important', 140, 1400, 1),
            ('information', 260, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        page_df = pd.DataFrame()
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.current)
        self.assertIsNone(result.total)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_missing_required_columns(self):
        """Test handling of DataFrame with missing columns."""
        page_df = pd.DataFrame({
            'text': ['Seite', '1', 'von', '2'],
        })
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
    
    def test_no_word_level_data(self):
        """Test handling of DataFrame with no word-level (level=5) data."""
        rows = [
            {'level': 1, 'text': 'Page 1 of 2', 'left': 100, 'top': 100, 
             'page_width': 1000, 'page_height': 1500},
        ]
        page_df = pd.DataFrame(rows)
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
    
    def test_invalid_page_dimensions(self):
        """Test handling of invalid page dimensions."""
        words_data = [
            ('Seite', 100, 1400, 1),
            ('1', 160, 1400, 1),
            ('von', 180, 1400, 1),
            ('2', 220, 1400, 1),
        ]
        # Create with invalid dimensions
        page_df = self._create_test_dataframe(words_data, page_width=0, page_height=0)
        
        result = detect_letter_page_index(page_df)
        
        self.assertFalse(result.found)
    
    # ========== Real-world Scenarios ==========
    
    def test_page_index_in_footer(self):
        """Test detection of page index in document footer."""
        words_data = [
            # Document content
            ('Some', 100, 100, 1, 1),
            ('content', 160, 100, 1, 1),
            ('here', 250, 100, 1, 1),
            # Footer with page index
            ('Seite', 450, 1400, 2, 2),
            ('2', 510, 1400, 2, 2),
            ('von', 530, 1400, 2, 2),
            ('5', 580, 1400, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 2)
        self.assertEqual(result.total, 5)
    
    def test_page_index_with_surrounding_text(self):
        """Test detection when page index is surrounded by other text."""
        words_data = [
            ('Document', 100, 1400, 1),
            ('footer', 200, 1400, 1),
            ('-', 270, 1400, 1),
            ('Page', 290, 1400, 1),
            ('1', 350, 1400, 1),
            ('of', 370, 1400, 1),
            ('3', 400, 1400, 1),
            ('-', 420, 1400, 1),
            ('Confidential', 440, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertEqual(result.total, 3)
    
    def test_multiple_page_indicators_first_wins(self):
        """Test that when multiple indicators exist, the first one is returned."""
        words_data = [
            # First indicator (should be found)
            ('Seite', 100, 100, 1, 1),
            ('1', 160, 100, 1, 1),
            ('von', 180, 100, 1, 1),
            ('2', 220, 100, 1, 1),
            # Second indicator (should be ignored)
            ('Page', 100, 1400, 2, 2),
            ('1', 160, 1400, 2, 2),
            ('of', 180, 1400, 2, 2),
            ('3', 220, 1400, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 1)
        self.assertEqual(result.total, 2)
        # Should match the German pattern
        self.assertIn('Seite', result.raw)
    
    def test_large_page_numbers(self):
        """Test detection with larger page numbers (e.g., 42 of 100)."""
        words_data = [
            ('Page', 100, 1400, 1),
            ('42', 160, 1400, 1),
            ('of', 200, 1400, 1),
            ('100', 230, 1400, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_letter_page_index(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.current, 42)
        self.assertEqual(result.total, 100)


if __name__ == '__main__':
    unittest.main()
