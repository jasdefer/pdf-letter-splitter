#!/usr/bin/env python3
"""
Unit tests for marker detection functions.

Tests the detection of greetings, goodbyes, and other markers from OCR data.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

# Add Source directory to path to import the marker detection module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from marker_detection import detect_greeting
from page_analysis_data import TextMarker

# Test data constants
CHAR_WIDTH_PIXELS = 10  # Approximate width per character for test data
WORD_HEIGHT_PIXELS = 20  # Approximate height of words for test data


class TestDetectGreeting(unittest.TestCase):
    """Test cases for detect_greeting function."""
    
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
    
    def test_detect_german_greeting_sehr_geehrte(self):
        """Test detection of 'Sehr geehrte' greeting."""
        words_data = [
            ('Sehr', 100, 200, 1),
            ('geehrte', 150, 200, 1),
            ('Frau', 250, 200, 1),
            ('Müller,', 320, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Sehr geehrte Frau Müller,')
        self.assertAlmostEqual(result.x_rel, 0.1, places=2)  # 100/1000
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)  # 200/1500
    
    def test_detect_german_greeting_guten_tag(self):
        """Test detection of 'Guten Tag' greeting."""
        words_data = [
            ('Guten', 100, 300, 1),
            ('Tag', 170, 300, 1),
            ('Herr', 230, 300, 1),
            ('Schmidt,', 290, 300, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Guten Tag Herr Schmidt,')
        self.assertEqual(result.x_rel, 0.1)  # 100/1000
        self.assertEqual(result.y_rel, 0.2)  # 300/1500
    
    def test_detect_german_greeting_hallo(self):
        """Test detection of 'Hallo' greeting with comma (weak pattern)."""
        words_data = [
            ('Hallo', 100, 250, 1),
            ('zusammen,', 170, 250, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Hallo zusammen,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.167, places=2)
    
    def test_detect_german_greeting_liebe(self):
        """Test detection of 'Liebe' greeting with comma (weak pattern)."""
        words_data = [
            ('Liebe', 100, 220, 1),
            ('Anna,', 170, 220, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Liebe Anna,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.147, places=2)
    
    def test_detect_english_greeting_dear(self):
        """Test detection of 'Dear' greeting (strong pattern)."""
        words_data = [
            ('Dear', 100, 200, 1),
            ('Mr.', 160, 200, 1),
            ('Smith,', 210, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Dear Mr. Smith,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_detect_english_greeting_hello(self):
        """Test detection of 'Hello' greeting with comma (weak pattern)."""
        words_data = [
            ('Hello', 100, 200, 1),
            ('everyone,', 170, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Hello everyone,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_detect_english_greeting_good_morning(self):
        """Test detection of 'Good morning' greeting (strong pattern)."""
        words_data = [
            ('Good', 100, 200, 1),
            ('morning', 160, 200, 1),
            ('team,', 250, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Good morning team,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_no_greeting_found(self):
        """Test that no greeting returns found=False with null fields."""
        words_data = [
            ('This', 100, 200, 1),
            ('is', 150, 200, 1),
            ('some', 190, 200, 1),
            ('text', 250, 200, 1),
            ('without', 310, 200, 1),
            ('greeting.', 400, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_empty_dataframe(self):
        """Test that empty DataFrame returns found=False."""
        page_df = pd.DataFrame()
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_greeting_with_different_case(self):
        """Test that greeting detection is case-insensitive."""
        words_data = [
            ('DEAR', 100, 200, 1),
            ('JOHN,', 160, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'DEAR JOHN,')
    
    def test_greeting_in_second_line(self):
        """Test that greeting is found even if not on first line."""
        words_data = [
            ('Some', 100, 100, 1, 1),  # paragraph 1
            ('header', 170, 100, 1, 1),
            ('text', 250, 100, 1, 1),
            ('Dear', 100, 200, 1, 2),  # paragraph 2 (different par_num)
            ('Sir,', 160, 200, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        # raw should contain the full paragraph (which is just "Dear Sir,")
        self.assertEqual(result.raw, 'Dear Sir,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_relative_position_calculation(self):
        """Test that x_rel and y_rel are correctly calculated."""
        page_width = 2000
        page_height = 3000
        words_data = [
            ('Hallo', 500, 900, 1),
            ('Team,', 600, 900, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=page_width, page_height=page_height)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.x_rel, 0.25)  # 500/2000
        self.assertEqual(result.y_rel, 0.3)   # 900/3000
    
    def test_greeting_split_across_words(self):
        """Test detection when greeting phrase is split across OCR words."""
        # "Sehr geehrte" as two separate words
        words_data = [
            ('Sehr', 100, 200, 1),
            ('geehrte', 170, 200, 1),
            ('Damen', 280, 200, 1),
            ('und', 360, 200, 1),
            ('Herren,', 410, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # raw should contain the full line
        self.assertEqual(result.raw, 'Sehr geehrte Damen und Herren,')
        # Position should be at the start of "Sehr"
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_multiple_greetings_returns_first(self):
        """Test that if multiple greetings exist, the first one is returned."""
        words_data = [
            ('Hallo', 100, 100, 1, 1),  # paragraph 1
            ('Team,', 170, 100, 1, 1),
            ('Dear', 100, 200, 1, 2),  # paragraph 2 (different par_num)
            ('Sir,', 160, 200, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        # Should return the first greeting (Hallo Team,)
        self.assertEqual(result.raw, 'Hallo Team,')
        self.assertAlmostEqual(result.y_rel, 0.067, places=2)  # 100/1500, not 200/1500
    
    def test_missing_required_columns(self):
        """Test that missing required columns returns found=False."""
        # DataFrame missing 'page_width' and 'page_height' columns
        incomplete_data = {
            'level': [5, 5],
            'text': ['Dear', 'Sir'],
            'left': [100, 160],
            'top': [200, 200],
        }
        page_df = pd.DataFrame(incomplete_data)
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_null_page_dimensions(self):
        """Test that null page dimensions returns found=False."""
        words_data = [
            ('Dear', 100, 200, 1),
            ('Sir,', 160, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        # Set page dimensions to None
        page_df['page_width'] = None
        page_df['page_height'] = None
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_weak_greeting_without_comma_not_detected(self):
        """Test that weak greetings without comma are not detected (reduces false positives)."""
        # "Hallo" without comma should not match
        words_data = [
            ('Hallo', 100, 200, 1),
            ('ich', 170, 200, 1),
            ('bin', 220, 200, 1),
            ('hier', 280, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
    
    def test_liebe_in_body_text_not_detected(self):
        """Test that 'liebe' in body text (no comma) is not detected as greeting."""
        # "ich liebe" should not match as a greeting
        words_data = [
            ('Ich', 100, 200, 1),
            ('liebe', 160, 200, 1),
            ('das', 230, 200, 1),
            ('Wetter', 290, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
    
    def test_weak_greeting_with_too_many_words(self):
        """Test that weak greetings with more than 7 words before comma are not detected."""
        # "Hallo" followed by 8 words and comma should not match
        words_data = [
            ('Hallo', 100, 200, 1),
            ('eins', 170, 200, 1),
            ('zwei', 220, 200, 1),
            ('drei', 280, 200, 1),
            ('vier', 340, 200, 1),
            ('fünf', 400, 200, 1),
            ('sechs', 460, 200, 1),
            ('sieben', 530, 200, 1),
            ('acht,', 600, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
    
    def test_strong_greeting_without_comma_still_detected(self):
        """Test that strong greetings are detected even without comma."""
        # "Sehr geehrte" should match even without comma
        words_data = [
            ('Sehr', 100, 200, 1),
            ('geehrte', 170, 200, 1),
            ('Damen', 280, 200, 1),
            ('und', 360, 200, 1),
            ('Herren', 420, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Sehr geehrte Damen und Herren')
    
    def test_multiline_greeting_in_same_paragraph(self):
        """Test that greetings spanning multiple lines in same paragraph are detected."""
        # Greeting split across lines but in same paragraph
        words_data = [
            ('Sehr', 100, 200, 1, 1),  # line 1
            ('geehrte', 170, 200, 1, 1),
            ('Damen', 100, 220, 2, 1),  # line 2, same paragraph
            ('und', 170, 220, 2, 1),
            ('Herren,', 230, 220, 2, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_greeting(page_df)
        
        self.assertTrue(result.found)
        # Should match and return full paragraph text
        self.assertEqual(result.raw, 'Sehr geehrte Damen und Herren,')
        # Position should be at start of "Sehr"
        self.assertEqual(result.x_rel, 0.1)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)


if __name__ == '__main__':
    unittest.main()
