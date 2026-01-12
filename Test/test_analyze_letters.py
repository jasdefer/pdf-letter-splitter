#!/usr/bin/env python3
"""
Test suite for letter segmentation and metadata extraction.

Validates the analyze_letters.py module functionality.
"""

import sys
import unittest
from pathlib import Path

# Add Source directory to path to import the analysis module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from analyze_letters import (
    find_date,
    find_sender,
    find_topic,
    analyze_documents,
    _calculate_header_score,
)


class TestDateExtraction(unittest.TestCase):
    """Test cases for date extraction."""
    
    def test_iso_format(self):
        """Test ISO format date extraction."""
        text = "Document Date: 2026-01-09\nSome other content"
        date = find_date(text)
        self.assertEqual(date, "2026-01-09")
    
    def test_european_format(self):
        """Test European DD.MM.YYYY format."""
        text = "Datum: 09.01.2026\nRest of document"
        date = find_date(text)
        self.assertEqual(date, "2026-01-09")
    
    def test_us_format(self):
        """Test US MM/DD/YYYY format."""
        # Use 13th month indicator to make it unambiguous (13 can only be day in European format)
        text = "Date: 12/15/2026\nContent here"
        date = find_date(text)
        # With European priority, this should be interpreted as DD/MM = invalid (>12 month)
        # Fall through to US format: 12/15/2026 = December 15, 2026
        self.assertEqual(date, "2026-12-15")
    
    def test_german_month_name(self):
        """Test German month name format."""
        text = "Datum: 15. Januar 2026\nInhalt"
        date = find_date(text)
        self.assertEqual(date, "2026-01-15")
    
    def test_english_month_name(self):
        """Test English month name format."""
        text = "Date: January 15, 2026\nContent"
        date = find_date(text)
        self.assertEqual(date, "2026-01-15")
    
    def test_date_in_body_not_header(self):
        """Test that dates deep in document are not extracted."""
        # Create text with date only at bottom
        lines = ['Line ' + str(i) for i in range(50)]
        lines.append('Meeting scheduled for 2026-12-25')
        text = '\n'.join(lines)
        
        # Should not find date (it's not in top section)
        date = find_date(text)
        self.assertIsNone(date)
    
    def test_no_date(self):
        """Test when no date is present."""
        text = "Some document without a date\nJust text here"
        date = find_date(text)
        self.assertIsNone(date)
    
    def test_empty_text(self):
        """Test with empty text."""
        self.assertIsNone(find_date(""))
        self.assertIsNone(find_date(None))


class TestSenderExtraction(unittest.TestCase):
    """Test cases for sender identification."""
    
    def test_company_with_gmbh(self):
        """Test extraction of German company name."""
        text = "Mustermann GmbH\nMusterstraße 123\n12345 Musterstadt"
        sender = find_sender(text)
        self.assertIsNotNone(sender)
        self.assertIn("Mustermann", sender)
    
    def test_company_with_inc(self):
        """Test extraction of US company name."""
        text = "Example Corp Inc\n123 Main Street\nNew York, NY"
        sender = find_sender(text)
        self.assertIsNotNone(sender)
        self.assertIn("Example", sender)
    
    def test_person_name(self):
        """Test extraction of person name."""
        text = "John Smith\n123 Any Street\nCity, State"
        sender = find_sender(text)
        self.assertIsNotNone(sender)
        self.assertIn("John", sender)
    
    def test_skip_page_numbers(self):
        """Test that page numbers are skipped."""
        text = "Page 1\nMustermann GmbH\nMusterstraße 123"
        sender = find_sender(text)
        self.assertIsNotNone(sender)
        self.assertIn("Mustermann", sender)
        self.assertNotIn("Page", sender)
    
    def test_finanzamt(self):
        """Test extraction of German government office."""
        text = "Finanzamt München\nSteuer-Nr: 123/456/78910"
        sender = find_sender(text)
        self.assertIsNotNone(sender)
        self.assertIn("Finanzamt", sender)
    
    def test_no_sender(self):
        """Test when no clear sender is found."""
        text = "123\n456\n|||---|||"
        sender = find_sender(text)
        # May return None or something unclear
        # Main point is not to crash
        self.assertTrue(sender is None or isinstance(sender, str))
    
    def test_empty_text(self):
        """Test with empty text."""
        self.assertIsNone(find_sender(""))
        self.assertIsNone(find_sender(None))


class TestTopicExtraction(unittest.TestCase):
    """Test cases for topic/subject extraction."""
    
    def test_subject_line_english(self):
        """Test extraction of English subject line."""
        text = "Date: 2026-01-09\nSubject: Annual Tax Report\nDear Customer"
        topic = find_topic(text)
        self.assertEqual(topic, "Annual Tax Report")
    
    def test_betreff_german(self):
        """Test extraction of German subject line."""
        text = "Datum: 09.01.2026\nBetreff: Steuerbescheid 2025\nSehr geehrte Damen"
        topic = find_topic(text)
        self.assertEqual(topic, "Steuerbescheid 2025")
    
    def test_re_line(self):
        """Test extraction with RE: prefix."""
        text = "Date: 2026-01-09\nRE: Invoice Payment\nDear Sir"
        topic = find_topic(text)
        self.assertEqual(topic, "Invoice Payment")
    
    def test_all_caps_heading(self):
        """Test fallback to ALL CAPS heading."""
        text = "Company Name\nAddress\nIMPORTANT NOTICE\nDear Customer"
        topic = find_topic(text)
        self.assertEqual(topic, "IMPORTANT NOTICE")
    
    def test_capitalized_heading(self):
        """Test fallback to capitalized heading."""
        text = "Company Name\nAddress\nAnnual Report Summary\nDear Customer"
        topic = find_topic(text)
        self.assertIsNotNone(topic)
        self.assertIn("Annual", topic)
    
    def test_no_topic(self):
        """Test when no topic is found."""
        text = "just some text\nwithout clear topic\nno headings here"
        topic = find_topic(text)
        # May be None or may find something
        self.assertTrue(topic is None or isinstance(topic, str))
    
    def test_empty_text(self):
        """Test with empty text."""
        self.assertIsNone(find_topic(""))
        self.assertIsNone(find_topic(None))


class TestHeaderScoring(unittest.TestCase):
    """Test cases for header score calculation."""
    
    def test_complete_header(self):
        """Test scoring with all header elements."""
        text = """Mustermann GmbH
Musterstraße 123
12345 Musterstadt

Datum: 15. Januar 2026
Betreff: Jahresbericht 2025

Sehr geehrte Damen und Herren,

Content of the letter..."""
        
        result = _calculate_header_score(text)
        # Should have high score (date + sender + subject + salutation)
        self.assertGreater(result['total_score'], 60)
        self.assertTrue(result['date']['found'])
        self.assertTrue(result['sender']['found'])
        self.assertTrue(result['topic']['found'])
        self.assertTrue(result['salutation']['found'])
    
    def test_minimal_header(self):
        """Test scoring with minimal header elements."""
        text = "Some content without clear header structure"
        result = _calculate_header_score(text)
        self.assertLess(result['total_score'], 40)
    
    def test_page_one_marker(self):
        """Test that page 1 marker increases score."""
        text = "Page 1 of 3\nSome content"
        result = _calculate_header_score(text)
        self.assertGreater(result['total_score'], 20)
        self.assertTrue(result['page_marker']['found'])
        self.assertEqual(result['page_marker']['value'], 'Page 1')
    
    def test_empty_text(self):
        """Test with empty text."""
        result = _calculate_header_score("")
        self.assertEqual(result['total_score'], 0)
        self.assertFalse(result['date']['found'])
        self.assertFalse(result['sender']['found'])


class TestDocumentAnalysis(unittest.TestCase):
    """Test cases for end-to-end document analysis."""
    
    def test_single_letter(self):
        """Test analysis of a single letter."""
        pages = [
            """Mustermann GmbH
Datum: 15.01.2026
Betreff: Test Letter

Dear Customer,

This is page 1.""",
            "This is page 2 of the same letter.",
            "This is page 3, still the same letter."
        ]
        
        letters = analyze_documents(pages)
        
        self.assertEqual(len(letters), 1)
        self.assertEqual(letters[0]['page_count'], 3)
        self.assertEqual(letters[0]['start_page'], 1)
        self.assertIsNotNone(letters[0]['date'])
        self.assertIsNotNone(letters[0]['sender'])
    
    def test_multiple_letters(self):
        """Test analysis of multiple letters."""
        pages = [
            """Company A Inc
Date: 2026-01-09
Subject: First Letter

Dear Customer,
Content of first letter.""",
            "Continuation of first letter, page 2.",
            """Company B GmbH
Datum: 10.01.2026
Betreff: Second Letter

Dear Sir,
Content of second letter.""",
            "Continuation of second letter."
        ]
        
        letters = analyze_documents(pages)
        
        self.assertEqual(len(letters), 2)
        
        # First letter
        self.assertEqual(letters[0]['page_count'], 2)
        self.assertEqual(letters[0]['start_page'], 1)
        
        # Second letter
        self.assertEqual(letters[1]['page_count'], 2)
        self.assertEqual(letters[1]['start_page'], 3)
    
    def test_empty_pages_list(self):
        """Test with empty pages list."""
        letters = analyze_documents([])
        self.assertEqual(letters, [])
    
    def test_single_page(self):
        """Test with single page."""
        pages = ["Simple one-page document"]
        letters = analyze_documents(pages)
        
        self.assertEqual(len(letters), 1)
        self.assertEqual(letters[0]['page_count'], 1)
    
    def test_metadata_extraction(self):
        """Test that metadata is properly extracted."""
        pages = [
            """Example Company Ltd
Date: January 15, 2026
Subject: Important Notice

Dear Customer,

Please review this notice."""
        ]
        
        letters = analyze_documents(pages)
        
        self.assertEqual(len(letters), 1)
        letter = letters[0]
        
        # Check metadata
        self.assertEqual(letter['date'], '2026-01-15')
        self.assertIn('Example', letter['sender'])
        self.assertIn('Important', letter['topic'])
        self.assertEqual(letter['page_count'], 1)
        self.assertEqual(letter['start_page'], 1)
    
    def test_missing_metadata(self):
        """Test handling of missing metadata."""
        pages = [
            """Just some content
without proper headers
or metadata"""
        ]
        
        letters = analyze_documents(pages)
        
        self.assertEqual(len(letters), 1)
        letter = letters[0]
        
        # Metadata should be None
        self.assertIsNone(letter['date'])
        self.assertEqual(letter['page_count'], 1)
    
    def test_letter_boundary_detection(self):
        """Test that letter boundaries are properly detected."""
        pages = [
            # Strong header indicators
            """Company A
Date: 2026-01-15
Subject: Letter A
Page 1 of 1

Content here.""",
            # Weak continuation page
            "Just continuation text without headers",
            # Strong header again - new letter
            """Company B
Date: 2026-01-16  
Subject: Letter B
Page 1 of 2

New letter content.""",
            "More continuation"
        ]
        
        letters = analyze_documents(pages)
        
        # Should detect 2 separate letters
        self.assertEqual(len(letters), 2)
        self.assertEqual(letters[0]['page_count'], 2)
        self.assertEqual(letters[1]['page_count'], 2)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_very_short_pages(self):
        """Test with very short page content."""
        pages = ["A", "B", "C"]
        letters = analyze_documents(pages)
        # Should not crash
        self.assertIsInstance(letters, list)
    
    def test_very_long_page(self):
        """Test with very long page content."""
        long_text = "Line\n" * 1000
        pages = [long_text]
        letters = analyze_documents(pages)
        self.assertEqual(len(letters), 1)
    
    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Company Ñame GmbH\nDate: 15.01.2026\nSubject: Tëst Tøpic"
        date = find_date(text)
        sender = find_sender(text)
        topic = find_topic(text)
        
        # Should handle special characters without crashing
        self.assertIsNotNone(date)
        self.assertIsNotNone(sender)
        self.assertIsNotNone(topic)
    
    def test_all_blank_pages(self):
        """Test with all blank pages."""
        pages = ["", "   ", "\n\n\n"]
        letters = analyze_documents(pages)
        # Should handle gracefully
        self.assertIsInstance(letters, list)


if __name__ == '__main__':
    unittest.main()
