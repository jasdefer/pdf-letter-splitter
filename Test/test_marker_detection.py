#!/usr/bin/env python3
"""
Unit tests for marker detection functions.

Tests the detection of greetings, goodbyes, and other markers from OCR data.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add Source directory to path to import the marker detection module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from marker_detection import detect_greeting, detect_goodbye, detect_subject, detect_address_block, detect_date
from page_analysis_data import TextMarker, AddressBlock, DateMarker

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




class TestDetectGoodbye(unittest.TestCase):
    """Test cases for detect_goodbye function."""
    
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
    
    def test_detect_german_goodbye_mit_freundlichen_gruessen(self):
        """Test detection of 'Mit freundlichen Grüßen' goodbye."""
        words_data = [
            ('Mit', 100, 1200, 1),
            ('freundlichen', 150, 1200, 1),
            ('Grüßen', 280, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Mit freundlichen Grüßen')
        self.assertEqual(result.x_rel, 0.1)  # 100/1000
        self.assertEqual(result.y_rel, 0.8)  # 1200/1500
    
    def test_detect_german_goodbye_freundliche_gruesse(self):
        """Test detection of 'Freundliche Grüße' goodbye."""
        words_data = [
            ('Freundliche', 100, 1200, 1),
            ('Grüße', 230, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Freundliche Grüße')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_german_goodbye_mit_besten_gruessen(self):
        """Test detection of 'Mit besten Grüßen' goodbye."""
        words_data = [
            ('Mit', 100, 1200, 1),
            ('besten', 150, 1200, 1),
            ('Grüßen', 230, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Mit besten Grüßen')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_german_goodbye_hochachtungsvoll(self):
        """Test detection of 'Hochachtungsvoll' goodbye."""
        words_data = [
            ('Hochachtungsvoll', 100, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Hochachtungsvoll')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_german_goodbye_viele_gruesse(self):
        """Test detection of 'Viele Grüße' goodbye."""
        words_data = [
            ('Viele', 100, 1200, 1),
            ('Grüße', 170, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Viele Grüße')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_english_goodbye_sincerely(self):
        """Test detection of 'Sincerely' goodbye."""
        words_data = [
            ('Sincerely,', 100, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Sincerely,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_english_goodbye_kind_regards(self):
        """Test detection of 'Kind regards' goodbye."""
        words_data = [
            ('Kind', 100, 1200, 1),
            ('regards,', 170, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Kind regards,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_english_goodbye_best_regards(self):
        """Test detection of 'Best regards' goodbye."""
        words_data = [
            ('Best', 100, 1200, 1),
            ('regards', 170, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Best regards')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_english_goodbye_yours_faithfully(self):
        """Test detection of 'Yours faithfully' goodbye."""
        words_data = [
            ('Yours', 100, 1200, 1),
            ('faithfully,', 170, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Yours faithfully,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_detect_english_goodbye_yours_sincerely(self):
        """Test detection of 'Yours sincerely' goodbye."""
        words_data = [
            ('Yours', 100, 1200, 1),
            ('sincerely,', 170, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Yours sincerely,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_no_goodbye_found(self):
        """Test that no goodbye returns found=False with null fields."""
        words_data = [
            ('This', 100, 200, 1),
            ('is', 150, 200, 1),
            ('some', 190, 200, 1),
            ('text', 250, 200, 1),
            ('without', 310, 200, 1),
            ('goodbye.', 400, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_empty_dataframe(self):
        """Test that empty DataFrame returns found=False."""
        page_df = pd.DataFrame()
        
        result = detect_goodbye(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_goodbye_with_different_case(self):
        """Test that goodbye detection is case-insensitive."""
        words_data = [
            ('SINCERELY', 100, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'SINCERELY')
    
    def test_goodbye_split_across_words(self):
        """Test detection when goodbye phrase is split across OCR words."""
        # "Mit freundlichen Grüßen" as three separate words
        words_data = [
            ('Mit', 100, 1200, 1),
            ('freundlichen', 150, 1200, 1),
            ('Grüßen', 280, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Mit freundlichen Grüßen')
        # Position should be at the start of "Mit"
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_relative_position_calculation(self):
        """Test that x_rel and y_rel are correctly calculated."""
        page_width = 2000
        page_height = 3000
        words_data = [
            ('Sincerely', 500, 2400, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=page_width, page_height=page_height)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.x_rel, 0.25)  # 500/2000
        self.assertEqual(result.y_rel, 0.8)   # 2400/3000
    
    def test_missing_required_columns(self):
        """Test that missing required columns returns found=False."""
        # DataFrame missing 'page_width' and 'page_height' columns
        incomplete_data = {
            'level': [5, 5],
            'text': ['Best', 'regards'],
            'left': [100, 160],
            'top': [1200, 1200],
        }
        page_df = pd.DataFrame(incomplete_data)
        
        result = detect_goodbye(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_null_page_dimensions(self):
        """Test that null page dimensions returns found=False."""
        words_data = [
            ('Sincerely', 100, 1200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        # Set page dimensions to None
        page_df['page_width'] = None
        page_df['page_height'] = None
        
        result = detect_goodbye(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_goodbye_with_umlaut_variations(self):
        """Test that goodbye detection handles umlaut variations (ü vs u)."""
        # Test with 'u' instead of 'ü'
        words_data = [
            ('Mit', 100, 1200, 1),
            ('freundlichen', 150, 1200, 1),
            ('Gruessen', 280, 1200, 1),  # 'ue' instead of 'ü'
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Mit freundlichen Gruessen')
    
    def test_goodbye_in_middle_paragraph(self):
        """Test that goodbye is found even if not in first paragraph."""
        words_data = [
            ('Some', 100, 100, 1, 1),  # paragraph 1
            ('text', 170, 100, 1, 1),
            ('Best', 100, 1200, 1, 2),  # paragraph 2
            ('regards', 170, 1200, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Best regards')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_multiple_goodbyes_returns_first(self):
        """Test that if multiple goodbyes exist, the first one is returned."""
        words_data = [
            ('Sincerely', 100, 1100, 1, 1),  # paragraph 1
            ('Best', 100, 1200, 1, 2),  # paragraph 2
            ('regards', 170, 1200, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        # Should return the first goodbye (Sincerely)
        self.assertEqual(result.raw, 'Sincerely')
        self.assertAlmostEqual(result.y_rel, 0.733, places=2)  # 1100/1500, not 1200/1500
    
    def test_multiline_goodbye_in_same_paragraph(self):
        """Test that goodbyes spanning multiple lines in same paragraph are detected."""
        # Goodbye split across lines but in same paragraph
        words_data = [
            ('Mit', 100, 1200, 1, 1),  # line 1
            ('freundlichen', 150, 1200, 1, 1),
            ('Grüßen', 100, 1220, 2, 1),  # line 2, same paragraph
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        # Should match and return full paragraph text
        self.assertEqual(result.raw, 'Mit freundlichen Grüßen')
        # Position should be at start of "Mit"
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)
    
    def test_goodbye_with_additional_text(self):
        """Test that goodbye is detected even with additional text in paragraph."""
        words_data = [
            ('Mit', 100, 1200, 1, 1),  # par_num=1
            ('freundlichen', 150, 1200, 1, 1),
            ('Grüßen,', 280, 1200, 1, 1),
            ('John', 100, 1220, 1, 2),  # par_num=2 (different paragraph)
            ('Doe', 170, 1220, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_goodbye(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        # Should detect the first paragraph with goodbye (not the second paragraph)
        self.assertEqual(result.raw, 'Mit freundlichen Grüßen,')
        self.assertEqual(result.x_rel, 0.1)
        self.assertEqual(result.y_rel, 0.8)


class TestDetectSubject(unittest.TestCase):
    """Test cases for detect_subject function."""
    
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
    
    # Step 1: Labeled subject detection tests
    
    def test_detect_labeled_subject_betreff_colon(self):
        """Test detection of 'Betreff:' with subject text."""
        words_data = [
            ('Betreff:', 100, 200, 1),
            ('Rechnung', 200, 200, 1),
            ('April', 300, 200, 1),
            ('2024', 380, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNotNone(result.raw)
        self.assertEqual(result.raw, 'Rechnung April 2024')
        self.assertEqual(result.x_rel, 0.2)  # 200/1000 (start of "Rechnung")
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)  # 200/1500
    
    def test_detect_labeled_subject_betreff_no_colon(self):
        """Test detection of 'Betreff' without colon."""
        words_data = [
            ('Betreff', 100, 200, 1),
            ('Mahnung', 200, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Mahnung')
        self.assertEqual(result.x_rel, 0.2)  # 200/1000
    
    def test_detect_labeled_subject_betr_dot(self):
        """Test detection of 'Betr.' with subject text."""
        words_data = [
            ('Betr.', 100, 200, 1),
            ('Ihre', 180, 200, 1),
            ('Bestellung', 230, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Ihre Bestellung')
        self.assertEqual(result.x_rel, 0.18)  # 180/1000
    
    def test_detect_labeled_subject_betr_colon(self):
        """Test detection of 'Betr:' with subject text."""
        words_data = [
            ('Betr:', 100, 200, 1),
            ('Steuerbescheid', 180, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Steuerbescheid')
        self.assertEqual(result.x_rel, 0.18)  # 180/1000
    
    def test_detect_labeled_subject_subject_colon(self):
        """Test detection of 'Subject:' with subject text."""
        words_data = [
            ('Subject:', 100, 200, 1),
            ('Invoice', 200, 200, 1),
            ('Payment', 280, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Invoice Payment')
        self.assertEqual(result.x_rel, 0.2)  # 200/1000
    
    def test_detect_labeled_subject_subject_no_colon(self):
        """Test detection of 'Subject' without colon."""
        words_data = [
            ('Subject', 100, 200, 1),
            ('Tax', 200, 200, 1),
            ('Assessment', 250, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Tax Assessment')
        self.assertEqual(result.x_rel, 0.2)  # 200/1000
    
    def test_detect_labeled_subject_re_colon(self):
        """Test detection of 'Re:' with subject text."""
        words_data = [
            ('Re:', 100, 200, 1),
            ('Your', 160, 200, 1),
            ('application', 220, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Your application')
        self.assertEqual(result.x_rel, 0.16)  # 160/1000
    
    def test_detect_labeled_subject_next_line(self):
        """Test detection when subject text is on next line."""
        words_data = [
            ('Betreff:', 100, 200, 1, 1),  # Label in paragraph 1
            ('Rechnung', 100, 220, 1, 2),  # Subject in paragraph 2
            ('März', 200, 220, 1, 2),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Rechnung März')
        self.assertEqual(result.x_rel, 0.1)  # 100/1000 (start of next paragraph)
        self.assertAlmostEqual(result.y_rel, 0.147, places=2)  # 220/1500
    
    def test_detect_labeled_subject_case_insensitive(self):
        """Test that labeled subject detection is case-insensitive."""
        words_data = [
            ('BETREFF:', 100, 200, 1),
            ('Important', 200, 200, 1),
            ('Notice', 300, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, 'Important Notice')
    
    def test_detect_labeled_subject_only_label_no_text(self):
        """Test that only a label without text returns found=False."""
        words_data = [
            ('Betreff:', 100, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
    
    # Step 2: Topic keyword detection tests
    
    def test_detect_topic_keyword_rechnung(self):
        """Test detection of topic keyword 'Rechnung'."""
        words_data = [
            ('Ihre', 100, 200, 1),
            ('Rechnung', 160, 200, 1),
            ('vom', 260, 200, 1),
            ('15.04.2024', 320, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Rechnung', result.raw)
        # Position should be at the matched keyword "Rechnung"
        self.assertEqual(result.x_rel, 0.16)  # Position of "Rechnung" (160/1000)
        self.assertAlmostEqual(result.y_rel, 0.133, places=2)
    
    def test_detect_topic_keyword_invoice(self):
        """Test detection of topic keyword 'Invoice'."""
        words_data = [
            ('Invoice', 100, 200, 1),
            ('Number', 180, 200, 1),
            ('12345', 270, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Invoice', result.raw)
    
    def test_detect_topic_keyword_mahnung(self):
        """Test detection of topic keyword 'Mahnung'."""
        words_data = [
            ('Zweite', 100, 200, 1),
            ('Mahnung', 180, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Mahnung', result.raw)
    
    def test_detect_topic_keyword_steuerbescheid(self):
        """Test detection of topic keyword 'Steuerbescheid'."""
        words_data = [
            ('Ihr', 100, 200, 1),
            ('Steuerbescheid', 150, 200, 1),
            ('2023', 300, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Steuerbescheid', result.raw)
    
    def test_detect_topic_keyword_bescheid(self):
        """Test detection of topic keyword 'Bescheid'."""
        words_data = [
            ('Bescheid', 100, 200, 1),
            ('über', 200, 200, 1),
            ('Leistungen', 260, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Bescheid', result.raw)
    
    def test_detect_topic_keyword_zahlungserinnerung(self):
        """Test detection of topic keyword 'Zahlungserinnerung'."""
        words_data = [
            ('Zahlungserinnerung', 100, 200, 1),
            ('Kundennummer', 280, 200, 1),
            ('54321', 420, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Zahlungserinnerung', result.raw)
    
    def test_detect_topic_keyword_billing_statement(self):
        """Test detection of topic keyword 'Billing statement'."""
        words_data = [
            ('Monthly', 100, 200, 1),
            ('Billing', 180, 200, 1),
            ('statement', 260, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Billing', result.raw)
        self.assertIn('statement', result.raw)
    
    def test_detect_topic_keyword_payment_reminder(self):
        """Test detection of topic keyword 'Payment reminder'."""
        words_data = [
            ('Payment', 100, 200, 1),
            ('reminder', 200, 200, 1),
            ('notice', 290, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('Payment', result.raw)
        self.assertIn('reminder', result.raw)
    
    def test_detect_topic_keyword_case_insensitive(self):
        """Test that topic keyword detection is case-insensitive."""
        words_data = [
            ('RECHNUNG', 100, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('RECHNUNG', result.raw)
    
    # Priority tests: labeled subject takes precedence over keywords
    
    def test_labeled_subject_takes_precedence(self):
        """Test that labeled subject is detected even if keywords are present."""
        words_data = [
            ('Betreff:', 100, 200, 1, 1),
            ('Wichtige', 200, 200, 1, 1),
            ('Mitteilung', 300, 200, 1, 1),
            ('Rechnung', 100, 220, 1, 2),  # Keyword in different paragraph
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        # Should return the labeled subject, not the keyword
        self.assertEqual(result.raw, 'Wichtige Mitteilung')
        self.assertNotEqual(result.raw, 'Rechnung')
    
    # Edge cases
    
    def test_no_subject_found(self):
        """Test that no subject returns found=False with null fields."""
        words_data = [
            ('This', 100, 200, 1),
            ('is', 150, 200, 1),
            ('some', 190, 200, 1),
            ('random', 250, 200, 1),
            ('text', 330, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_empty_dataframe(self):
        """Test that empty DataFrame returns found=False."""
        page_df = pd.DataFrame()
        
        result = detect_subject(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
        self.assertIsNone(result.x_rel)
        self.assertIsNone(result.y_rel)
    
    def test_missing_required_columns(self):
        """Test that missing required columns returns found=False."""
        incomplete_data = {
            'level': [5, 5],
            'text': ['Betreff:', 'Test'],
            'left': [100, 200],
            'top': [200, 200],
        }
        page_df = pd.DataFrame(incomplete_data)
        
        result = detect_subject(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.raw)
    
    def test_null_page_dimensions(self):
        """Test that null page dimensions returns found=False."""
        words_data = [
            ('Betreff:', 100, 200, 1),
            ('Test', 200, 200, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        page_df['page_width'] = None
        page_df['page_height'] = None
        
        result = detect_subject(page_df)
        
        self.assertFalse(result.found)
    
    def test_multiple_keywords_returns_first(self):
        """Test that if multiple keywords exist, the first one is returned."""
        words_data = [
            ('Rechnung', 100, 100, 1, 1),  # First keyword
            ('und', 200, 100, 1, 1),
            ('Mahnung', 100, 200, 1, 2),  # Second keyword
        ]
        page_df = self._create_test_dataframe(words_data)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        # Should return the first keyword paragraph
        self.assertIn('Rechnung', result.raw)
        self.assertAlmostEqual(result.y_rel, 0.067, places=2)  # 100/1500, not 200/1500
    
    def test_relative_position_calculation(self):
        """Test that x_rel and y_rel are correctly calculated."""
        page_width = 2000
        page_height = 3000
        words_data = [
            ('Betreff:', 500, 900, 1),
            ('Test', 700, 900, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=page_width, page_height=page_height)
        
        result = detect_subject(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.x_rel, 0.35)  # 700/2000 (start of subject text)
        self.assertEqual(result.y_rel, 0.3)   # 900/3000


class TestDetectAddressBlock(unittest.TestCase):
    """Test cases for detect_address_block function."""
    
    def _create_test_dataframe(self, words_data, page_width=1000, page_height=1500):
        """
        Helper to create a minimal OCR DataFrame for testing.
        
        Args:
            words_data: List of tuples (text, left, top, line_num)
            page_width: Page width in pixels
            page_height: Page height in pixels
        
        Returns:
            DataFrame mimicking OCR output
        """
        rows = []
        for idx, word_data in enumerate(words_data):
            text, left, top, line_num = word_data
            
            rows.append({
                'level': 5,  # Word level
                'page_num': 1,
                'block_num': 1,
                'par_num': 1,
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
    
    def test_detect_basic_address_block(self):
        """Test detection of a basic address block with name, street, ZIP, and city."""
        words_data = [
            # Name line
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            # Street line
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            # ZIP City line (anchor)
            ('12345', 100, 140, 3),
            ('Berlin', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_name, 'Max Mustermann')
        self.assertEqual(result.extracted_street, 'Hauptstraße 42')
        self.assertEqual(result.extracted_zip, '12345')
        self.assertEqual(result.extracted_city, 'Berlin')
        self.assertEqual(result.line_count, 3)
        self.assertEqual(result.x_rel, 0.1)  # 100/1000
        self.assertAlmostEqual(result.y_rel, 0.067, places=2)  # 100/1500
    
    def test_detect_address_block_with_multiple_name_lines(self):
        """Test detection of address block with multiple name lines."""
        words_data = [
            # Name line 1
            ('Firma', 100, 80, 1),
            ('GmbH', 170, 80, 1),
            # Name line 2
            ('Max', 100, 100, 2),
            ('Mustermann', 150, 100, 2),
            # Street line
            ('Hauptstraße', 100, 120, 3),
            ('42', 220, 120, 3),
            # ZIP City line (anchor)
            ('12345', 100, 140, 4),
            ('Berlin', 180, 140, 4),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_name, 'Firma GmbH Max Mustermann')
        self.assertEqual(result.extracted_street, 'Hauptstraße 42')
        self.assertEqual(result.extracted_zip, '12345')
        self.assertEqual(result.extracted_city, 'Berlin')
        self.assertEqual(result.line_count, 4)
    
    def test_detect_address_block_minimal_two_lines(self):
        """Test detection of minimal address block with only street and ZIP/City."""
        words_data = [
            # Street line
            ('Hauptstraße', 100, 120, 1),
            ('42', 220, 120, 1),
            # ZIP City line (anchor)
            ('12345', 100, 140, 2),
            ('Berlin', 180, 140, 2),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertIsNone(result.extracted_name)  # No name line
        self.assertEqual(result.extracted_street, 'Hauptstraße 42')
        self.assertEqual(result.extracted_zip, '12345')
        self.assertEqual(result.extracted_city, 'Berlin')
        self.assertEqual(result.line_count, 2)
    
    def test_detect_address_block_with_umlaut_city(self):
        """Test detection with German umlauts in city name."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('12345', 100, 140, 3),
            ('München', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_zip, '12345')
        self.assertEqual(result.extracted_city, 'München')
    
    def test_detect_address_block_with_hyphenated_city(self):
        """Test detection with hyphenated city name."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('12345', 100, 140, 3),
            ('Frankfurt-Oder', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_city, 'Frankfurt-Oder')
    
    def test_detect_address_block_with_multi_word_city(self):
        """Test detection with multi-word city name."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('12345', 100, 140, 3),
            ('Bad', 180, 140, 3),
            ('Homburg', 220, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_zip, '12345')
        self.assertIn('Bad', result.extracted_city)
        self.assertIn('Homburg', result.extracted_city)
    
    def test_spatial_constraint_top_30_percent(self):
        """Test that addresses outside top 30% are not detected."""
        # Address at 50% height (outside top 30%)
        words_data = [
            ('Max', 100, 750, 1),  # 750/1500 = 50% height
            ('Mustermann', 150, 750, 1),
            ('Hauptstraße', 100, 770, 2),
            ('42', 220, 770, 2),
            ('12345', 100, 790, 3),
            ('Berlin', 180, 790, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)  # Should not be found outside recipient zone
    
    def test_spatial_constraint_left_50_percent(self):
        """Test that addresses outside left 50% are not detected."""
        # Address at 60% width (outside left 50%)
        words_data = [
            ('Max', 600, 100, 1),  # 600/1000 = 60% width
            ('Mustermann', 650, 100, 1),
            ('Hauptstraße', 600, 120, 2),
            ('42', 720, 120, 2),
            ('12345', 600, 140, 3),
            ('Berlin', 680, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)  # Should not be found outside recipient zone
    
    def test_spatial_constraint_within_recipient_zone(self):
        """Test that addresses within recipient zone are detected."""
        # Address at top-left (within recipient zone)
        words_data = [
            ('Max', 100, 100, 1),  # Well within top 30% and left 50%
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('12345', 100, 140, 3),
            ('Berlin', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
    
    def test_no_zip_pattern_found(self):
        """Test that no address is found if ZIP pattern is missing."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            # No ZIP/City line
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
    
    def test_invalid_zip_format(self):
        """Test that 4-digit ZIP is not matched (requires 5 digits)."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('1234', 100, 140, 3),  # Only 4 digits
            ('Berlin', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
    
    def test_invalid_zip_format_six_digits(self):
        """Test that 6-digit ZIP is not matched (requires exactly 5 digits)."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 100, 120, 2),
            ('42', 220, 120, 2),
            ('123456', 100, 140, 3),  # 6 digits
            ('Berlin', 180, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
    
    def test_left_alignment_tolerance(self):
        """Test that lines with similar left alignment are grouped."""
        # Lines with slight left alignment variation (within tolerance)
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
            ('Hauptstraße', 110, 120, 2),  # 10 pixels off
            ('42', 230, 120, 2),
            ('12345', 105, 140, 3),  # 5 pixels off
            ('Berlin', 185, 140, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.line_count, 3)
    
    def test_left_alignment_break(self):
        """Test that lines with significantly different left alignment are not grouped."""
        words_data = [
            ('Header', 50, 80, 1),  # Far left, should not be included
            ('Text', 80, 80, 1),
            ('Max', 100, 100, 2),
            ('Mustermann', 150, 100, 2),
            ('Hauptstraße', 100, 120, 3),
            ('42', 220, 120, 3),
            ('12345', 100, 140, 4),
            ('Berlin', 180, 140, 4),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        # Should only include lines with similar left alignment to anchor
        # Header line should not be included
        self.assertEqual(result.line_count, 3)
        self.assertNotIn('Header', result.extracted_name or '')
    
    def test_empty_dataframe(self):
        """Test that empty DataFrame returns found=False."""
        page_df = pd.DataFrame()
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
        self.assertIsNone(result.extracted_name)
        self.assertIsNone(result.extracted_street)
        self.assertIsNone(result.extracted_zip)
        self.assertIsNone(result.extracted_city)
        self.assertIsNone(result.line_count)
    
    def test_missing_required_columns(self):
        """Test that missing required columns returns found=False."""
        incomplete_data = {
            'level': [5, 5],
            'text': ['Max', 'Mustermann'],
            'left': [100, 150],
            'top': [100, 100],
        }
        page_df = pd.DataFrame(incomplete_data)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
    
    def test_null_page_dimensions(self):
        """Test that null page dimensions returns found=False."""
        words_data = [
            ('Max', 100, 100, 1),
            ('Mustermann', 150, 100, 1),
        ]
        page_df = self._create_test_dataframe(words_data)
        page_df['page_width'] = None
        page_df['page_height'] = None
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)
    
    def test_only_zip_city_no_lines_above(self):
        """Test that only ZIP/City without lines above is not detected."""
        words_data = [
            ('12345', 100, 140, 1),
            ('Berlin', 180, 140, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertFalse(result.found)  # Need at least 1 line above anchor
    
    def test_relative_position_calculation(self):
        """Test that x_rel and y_rel are correctly calculated."""
        page_width = 2000
        page_height = 3000
        words_data = [
            ('Max', 500, 300, 1),
            ('Mustermann', 600, 300, 1),
            ('Hauptstraße', 500, 330, 2),
            ('42', 720, 330, 2),
            ('12345', 500, 360, 3),
            ('Berlin', 680, 360, 3),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=page_width, page_height=page_height)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.x_rel, 0.25)  # 500/2000
        self.assertEqual(result.y_rel, 0.1)   # 300/3000
    
    def test_max_four_lines_above_anchor(self):
        """Test that at most 4 lines above anchor are included."""
        words_data = [
            ('Line1', 100, 60, 1),   # 5th line above anchor
            ('Line2', 100, 80, 2),   # 4th line above anchor (should be included)
            ('Line3', 100, 100, 3),  # 3rd line above anchor
            ('Line4', 100, 120, 4),  # 2nd line above anchor
            ('Line5', 100, 140, 5),  # 1st line above anchor (street)
            ('12345', 100, 160, 6),  # Anchor
            ('Berlin', 180, 160, 6),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        self.assertTrue(result.found)
        # Should include at most 4 lines above anchor + anchor = 5 total
        self.assertLessEqual(result.line_count, 5)
        # Line1 should not be included
        self.assertNotIn('Line1', result.extracted_name or '')
    
    def test_detect_address_block_with_ocr_native_structure(self):
        """Test detection using OCR-native hierarchy with realistic data."""
        # This test uses real OCR data structure with block_num, par_num, line_num
        # to ensure the implementation correctly handles the OCR engine's layout analysis
        rows = [
            # Page-level (level 1)
            {'level': 1, 'page_num': 1, 'block_num': 0, 'par_num': 0, 'line_num': 0, 'word_num': 0,
             'left': 0, 'top': 0, 'width': 1242, 'height': 1755, 'conf': -1.0, 'text': '',
             'page_width': 1242, 'page_height': 1755},
            
            # Block 7 - Address block
            # Line 1: "*k4000""
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 1, 'word_num': 1,
             'left': 422, 'top': 371, 'width': 52, 'height': 11, 'conf': 79.090668, 'text': '"*k4000"""',
             'page_width': 1242, 'page_height': 1755},
            
            # Line 2: MyCompany GmbH
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 2, 'word_num': 1,
             'left': 171, 'top': 390, 'width': 70, 'height': 15, 'conf': 91.679695, 'text': 'MyCompany',
             'page_width': 1242, 'page_height': 1755},
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 2, 'word_num': 2,
             'left': 248, 'top': 390, 'width': 54, 'height': 15, 'conf': 96.494873, 'text': 'GmbH',
             'page_width': 1242, 'page_height': 1755},
            
            # Line 3: Blumengarten 2
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 3, 'word_num': 1,
             'left': 170, 'top': 412, 'width': 111, 'height': 18, 'conf': 91.335503, 'text': 'Blumengarten',
             'page_width': 1242, 'page_height': 1755},
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 3, 'word_num': 2,
             'left': 288, 'top': 412, 'width': 19, 'height': 14, 'conf': 96.766068, 'text': '2',
             'page_width': 1242, 'page_height': 1755},
            
            # Line 4: 22041 Hamburg (ZIP + City - the anchor)
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 4, 'word_num': 1,
             'left': 170, 'top': 434, 'width': 51, 'height': 14, 'conf': 96.503525, 'text': '22041',
             'page_width': 1242, 'page_height': 1755},
            {'level': 5, 'page_num': 1, 'block_num': 7, 'par_num': 1, 'line_num': 4, 'word_num': 2,
             'left': 228, 'top': 434, 'width': 77, 'height': 18, 'conf': 96.04438, 'text': 'Hamburg',
             'page_width': 1242, 'page_height': 1755},
        ]
        
        page_df = pd.DataFrame(rows)
        result = detect_address_block(page_df)
        
        # The address should be detected
        self.assertTrue(result.found, "Address block should be detected using OCR-native structure")
        
        # Verify extracted components
        self.assertEqual(result.extracted_zip, '22041', "ZIP code should be extracted correctly")
        self.assertEqual(result.extracted_city, 'Hamburg', "City should be extracted correctly")
        self.assertEqual(result.extracted_street, 'Blumengarten 2', "Street should be extracted correctly")
        self.assertIn('MyCompany', result.extracted_name, "Company name should be in extracted_name")
        self.assertIn('GmbH', result.extracted_name, "GmbH should be in extracted_name")
        
        # Verify line count (MyCompany GmbH, Blumengarten 2, 22041 Hamburg = 3 lines)
        self.assertEqual(result.line_count, 3, "Should count 3 lines (name, street, zip+city)")
        
        # Verify position is within recipient zone
        self.assertLess(result.x_rel, 0.5, "x_rel should be in left 50%")
        self.assertLess(result.y_rel, 0.3, "y_rel should be in top 30%")
    
    def test_skip_sender_address_find_recipient(self):
        """Test that sender address with ZIP is skipped in favor of recipient address."""
        # Simulate a page with sender address at top-right and recipient at top-left
        # Sender appears first in reading order but has no aligned lines above it
        words_data = [
            # Sender address (top-right, outside recipient zone or misaligned)
            # Just the ZIP line with no lines above it
            ('12345', 400, 100, 1),  # Sender ZIP (right side, outside left 50% or will fail validation)
            ('SenderCity', 480, 100, 1),
            
            # Recipient address (top-left, well-formed with name and street above ZIP)
            ('Jane', 100, 120, 2),
            ('Doe', 150, 120, 2),
            ('Musterstraße', 100, 140, 3),
            ('10', 230, 140, 3),
            ('54321', 100, 160, 4),  # Recipient ZIP (should be found)
            ('RecipientCity', 180, 160, 4),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        # Should find the recipient address, not the sender
        self.assertTrue(result.found, "Should find recipient address")
        self.assertEqual(result.extracted_zip, '54321', "Should extract recipient ZIP, not sender")
        self.assertEqual(result.extracted_city, 'RecipientCity', "Should extract recipient city")
        self.assertIn('Jane', result.extracted_name or '', "Should include recipient name")
        self.assertEqual(result.extracted_street, 'Musterstraße 10', "Should extract recipient street")
    
    def test_multiple_zip_candidates_pick_valid_one(self):
        """Test that when multiple ZIP patterns exist, we pick the one with valid address block."""
        # First ZIP has no aligned lines above (invalid - different left position)
        # Second ZIP has proper address block structure (valid)
        words_data = [
            # Invalid ZIP candidate - line above has different alignment
            ('Unrelated', 50, 80, 1),  # Different left position (50 vs 100)
            ('text', 120, 80, 1),
            ('99999', 100, 100, 2),  # ZIP - line above is not aligned (50 vs 100)
            ('InvalidCity', 180, 100, 2),
            
            # Some other text
            ('Other', 50, 120, 3),
            ('content', 100, 120, 3),
            
            # Valid ZIP candidate - has proper name and street above with same alignment
            ('Max', 100, 150, 4),
            ('Mustermann', 150, 150, 4),
            ('Hauptstraße', 100, 170, 5),
            ('42', 220, 170, 5),
            ('12345', 100, 190, 6),  # Valid ZIP
            ('Berlin', 180, 190, 6),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        # Should find the valid address block
        self.assertTrue(result.found, "Should find the valid address block")
        self.assertEqual(result.extracted_zip, '12345', "Should extract the valid ZIP")
        self.assertEqual(result.extracted_city, 'Berlin', "Should extract the valid city")
        self.assertEqual(result.extracted_name, 'Max Mustermann', "Should extract name from valid block")
        self.assertEqual(result.extracted_street, 'Hauptstraße 42', "Should extract street from valid block")
    
    def test_prefer_address_with_most_lines(self):
        """Test that when multiple valid addresses exist, the one with most lines is selected."""
        words_data = [
            # First address: 2 lines above ZIP (3 total)
            ('Jane', 100, 80, 1),
            ('Doe', 150, 80, 1),
            ('Street1', 100, 100, 2),
            ('10', 180, 100, 2),
            ('11111', 100, 120, 3),
            ('CityA', 180, 120, 3),
            
            # Gap of 60+ pixels between addresses
            
            # Second address: 3 lines above ZIP (4 total) - should be preferred
            ('Max', 100, 200, 4),
            ('Mustermann', 150, 200, 4),
            ('Company', 100, 220, 5),
            ('GmbH', 180, 220, 5),
            ('Street2', 100, 240, 6),
            ('20', 180, 240, 6),
            ('22222', 100, 260, 7),
            ('CityB', 180, 260, 7),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        # Should prefer the address with more lines (4 vs 3)
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_zip, '22222', "Should select address with most lines")
        self.assertEqual(result.line_count, 4, "Should have 4 lines total")
        self.assertIn('Max', result.extracted_name or '', "Should extract name from larger block")
        self.assertIn('Company', result.extracted_name or '', "Should include company in name")
    
    def test_target_zip_prioritization(self):
        """Test that target_zip parameter prioritizes matching address over line count."""
        words_data = [
            # First address: 4 lines total, ZIP=11111
            ('Company', 100, 80, 1),
            ('GmbH', 180, 80, 1),
            ('Max', 100, 100, 2),
            ('Mustermann', 150, 100, 2),
            ('Street1', 100, 120, 3),
            ('10', 180, 120, 3),
            ('11111', 100, 140, 4),
            ('CityA', 180, 140, 4),
            
            # Gap of 60+ pixels between addresses
            
            # Second address: 3 lines total, ZIP=22222 (target)
            ('Jane', 100, 220, 5),
            ('Doe', 150, 220, 5),
            ('Street2', 100, 240, 6),
            ('20', 180, 240, 6),
            ('22222', 100, 260, 7),
            ('CityB', 180, 260, 7),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        # Without target_zip, should prefer first (more lines)
        result_no_target = detect_address_block(page_df)
        self.assertEqual(result_no_target.extracted_zip, '11111', "Without target, should prefer more lines")
        
        # With target_zip, should prefer matching ZIP even with fewer lines
        result_with_target = detect_address_block(page_df, target_zip='22222')
        self.assertEqual(result_with_target.extracted_zip, '22222', "With target, should prefer matching ZIP")
        self.assertEqual(result_with_target.line_count, 3, "Target address has 3 lines")
    
    def test_vertical_gap_limit(self):
        """Test that lines with excessive vertical gap are not included in address block."""
        words_data = [
            # Line far above (should be excluded due to vertical gap)
            ('FarAbove', 100, 50, 1),
            ('Text', 180, 50, 1),
            
            # Proper address block (close together)
            ('Max', 100, 180, 2),
            ('Mustermann', 150, 180, 2),
            ('Street', 100, 200, 3),
            ('10', 180, 200, 3),
            ('12345', 100, 220, 4),
            ('City', 180, 220, 4),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_address_block(page_df)
        
        # Should not include the far above line
        self.assertTrue(result.found)
        self.assertEqual(result.line_count, 3, "Should have 3 lines (name, street, ZIP+city)")
        self.assertNotIn('FarAbove', result.extracted_name or '', "Should not include text with large gap")
        self.assertIn('Max', result.extracted_name or '', "Should include properly spaced lines")


class TestDetectDate(unittest.TestCase):
    """Test cases for detect_date function."""
    
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
    
    def test_detect_german_date_with_datum_prefix(self):
        """Test detection of German date with 'Datum:' prefix."""
        words_data = [
            # Header paragraph with Datum label
            ('Datum:', 100, 100, 1, 1),
            ('12.05.2023', 200, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, '12.05.2023')
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 5)
        self.assertEqual(result.date_value.day, 12)
        self.assertAlmostEqual(result.x_rel, 0.2, places=2)  # 200/1000
        self.assertAlmostEqual(result.y_rel, 0.067, places=2)  # 100/1500
    
    def test_detect_date_right_aligned_header(self):
        """Test detection of date right-aligned in header without prefix."""
        words_data = [
            # Some header text on left
            ('Company', 100, 100, 1, 1),
            ('Name', 180, 100, 1, 1),
            # Date on right side of header
            ('15.03.2024', 800, 100, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, '15.03.2024')
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2024)
        self.assertEqual(result.date_value.month, 3)
        self.assertEqual(result.date_value.day, 15)
        self.assertAlmostEqual(result.x_rel, 0.8, places=2)  # 800/1000
    
    def test_detect_date_in_footer_ignored(self):
        """Test that dates in footer (below top 40%) are ignored."""
        words_data = [
            # Date in footer (well below 40% of page height = 600)
            ('Date:', 100, 1000, 1, 1),  # 1000/1500 = 66.7% from top
            ('25.12.2023', 180, 1000, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        # Date should not be found because it's below top 40%
        self.assertFalse(result.found)
    
    def test_detect_date_corrupted_spacing(self):
        """Test detection of date with corrupted spacing (e.g., OCR artifacts)."""
        words_data = [
            # Date with extra spaces (corrupted OCR output)
            ('12', 100, 100, 1, 1),
            ('.', 130, 100, 1, 1),
            ('05', 150, 100, 1, 1),
            ('.', 180, 100, 1, 1),
            ('2023', 200, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        # The raw text will contain spaces due to how words are joined
        self.assertIn('12', result.raw)
        self.assertIn('05', result.raw)
        self.assertIn('2023', result.raw)
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 5)
        self.assertEqual(result.date_value.day, 12)
    
    def test_detect_english_date_month_dd_yyyy(self):
        """Test detection of English date format 'Month DD, YYYY'."""
        words_data = [
            ('Date:', 100, 100, 1, 1),
            ('May', 180, 100, 1, 1),
            ('12,', 230, 100, 1, 1),
            ('2023', 270, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('May', result.raw)
        self.assertIn('12', result.raw)
        self.assertIn('2023', result.raw)
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 5)
        self.assertEqual(result.date_value.day, 12)
    
    def test_detect_german_date_dd_month_yyyy(self):
        """Test detection of German date format 'DD. Month YYYY'."""
        words_data = [
            ('vom', 100, 100, 1, 1),
            ('5.', 160, 100, 1, 1),
            ('Mai', 200, 100, 1, 1),
            ('2023', 250, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertIn('5.', result.raw)
        self.assertIn('Mai', result.raw)
        self.assertIn('2023', result.raw)
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 5)
        self.assertEqual(result.date_value.day, 5)
    
    def test_detect_iso_date_format(self):
        """Test detection of ISO date format 'YYYY-MM-DD'."""
        words_data = [
            ('dated', 100, 100, 1, 1),
            ('2023-05-12', 180, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, '2023-05-12')
        self.assertIsNotNone(result.date_value)
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 5)
        self.assertEqual(result.date_value.day, 12)
    
    def test_detect_date_prefers_with_indicator(self):
        """Test that dates with indicators are preferred over dates without."""
        words_data = [
            # Date without indicator (top-left)
            ('10.01.2023', 100, 100, 1, 1),
            # Date with indicator (top-right, but has "Datum:")
            ('Datum:', 700, 120, 2, 2),
            ('20.02.2023', 780, 120, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        # Should prefer the date with the indicator
        self.assertEqual(result.raw, '20.02.2023')
        self.assertEqual(result.date_value.day, 20)
        self.assertEqual(result.date_value.month, 2)
    
    def test_detect_date_indicator_in_previous_paragraph(self):
        """Test that indicator in previous paragraph is recognized."""
        words_data = [
            # Indicator in one paragraph
            ('Datum:', 100, 100, 1, 1),
            # Date in next paragraph
            ('15.06.2023', 100, 130, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        self.assertEqual(result.raw, '15.06.2023')
        self.assertEqual(result.date_value.year, 2023)
        self.assertEqual(result.date_value.month, 6)
        self.assertEqual(result.date_value.day, 15)
    
    def test_detect_date_rightmost_when_no_indicators(self):
        """Test that rightmost date is preferred when no indicators present."""
        words_data = [
            # Date on left
            ('10.01.2023', 100, 100, 1, 1),
            # Date on right (should be preferred)
            ('20.02.2023', 800, 100, 2, 2),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertTrue(result.found)
        # Should prefer the rightmost date
        self.assertEqual(result.raw, '20.02.2023')
        self.assertAlmostEqual(result.x_rel, 0.8, places=2)
    
    def test_detect_date_invalid_date_ignored(self):
        """Test that invalid dates (e.g., 32.13.2023) are ignored."""
        words_data = [
            # Invalid date (day 32, month 13)
            ('32.13.2023', 100, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        # Invalid date should not be detected
        self.assertFalse(result.found)
    
    def test_detect_date_no_date_present(self):
        """Test that no date is detected when none is present."""
        words_data = [
            ('Some', 100, 100, 1, 1),
            ('text', 180, 100, 1, 1),
            ('without', 250, 100, 1, 1),
            ('dates', 340, 100, 1, 1),
        ]
        page_df = self._create_test_dataframe(words_data, page_width=1000, page_height=1500)
        
        result = detect_date(page_df)
        
        self.assertFalse(result.found)


if __name__ == '__main__':
    unittest.main()
