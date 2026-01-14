#!/usr/bin/env python3
"""
Test suite for page data structures and marker detection.

Validates PageData, PageInfoDetected, TextMarker classes, marker detection
functions, and the orchestration logic.
"""

import sys
import unittest
import json
from pathlib import Path

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

import pandas as pd
from page_data import PageData, PageInfoDetected, TextMarker, page_data_list_to_json
from marker_detection import (
    detect_page_info,
    detect_greeting,
    detect_goodbye,
    detect_betreff,
    detect_address_block
)
from page_analysis import analyze_pages


class TestPageDataStructures(unittest.TestCase):
    """Test cases for PageData and related data structures."""
    
    def test_page_info_detected_default_values(self):
        """Test PageInfoDetected with default values."""
        page_info = PageInfoDetected()
        self.assertFalse(page_info.found)
        self.assertIsNone(page_info.current)
        self.assertIsNone(page_info.total)
        self.assertIsNone(page_info.raw)
    
    def test_page_info_detected_with_values(self):
        """Test PageInfoDetected with explicit values."""
        page_info = PageInfoDetected(
            found=True,
            current=2,
            total=4,
            raw="Seite 2 von 4"
        )
        self.assertTrue(page_info.found)
        self.assertEqual(page_info.current, 2)
        self.assertEqual(page_info.total, 4)
        self.assertEqual(page_info.raw, "Seite 2 von 4")
    
    def test_text_marker_default_values(self):
        """Test TextMarker with default values."""
        marker = TextMarker()
        self.assertFalse(marker.found)
        self.assertIsNone(marker.raw)
        self.assertIsNone(marker.text)
    
    def test_text_marker_with_values(self):
        """Test TextMarker with explicit values."""
        marker = TextMarker(
            found=True,
            raw="Sehr geehrte Damen und Herren",
            text="Sehr geehrte Damen und Herren"
        )
        self.assertTrue(marker.found)
        self.assertEqual(marker.raw, "Sehr geehrte Damen und Herren")
        self.assertEqual(marker.text, "Sehr geehrte Damen und Herren")
    
    def test_page_data_structure(self):
        """Test PageData structure with all fields."""
        page_data = PageData(
            scan_page_num=1,
            page_info=PageInfoDetected(),
            greeting=TextMarker(),
            goodbye=TextMarker(),
            betreff=TextMarker(),
            address_block=TextMarker()
        )
        self.assertEqual(page_data.scan_page_num, 1)
        self.assertIsInstance(page_data.page_info, PageInfoDetected)
        self.assertIsInstance(page_data.greeting, TextMarker)
        self.assertIsInstance(page_data.goodbye, TextMarker)
        self.assertIsInstance(page_data.betreff, TextMarker)
        self.assertIsInstance(page_data.address_block, TextMarker)
    
    def test_page_data_to_dict(self):
        """Test PageData.to_dict() method."""
        page_data = PageData(
            scan_page_num=2,
            page_info=PageInfoDetected(found=True, current=2, total=4),
            greeting=TextMarker(found=True, raw="Hello"),
            goodbye=TextMarker(),
            betreff=TextMarker(),
            address_block=TextMarker()
        )
        result_dict = page_data.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['scan_page_num'], 2)
        self.assertEqual(result_dict['page_info']['found'], True)
        self.assertEqual(result_dict['page_info']['current'], 2)
        self.assertEqual(result_dict['greeting']['found'], True)
        self.assertEqual(result_dict['greeting']['raw'], "Hello")
    
    def test_page_data_to_json(self):
        """Test PageData.to_json() method."""
        page_data = PageData(
            scan_page_num=1,
            page_info=PageInfoDetected(),
            greeting=TextMarker(),
            goodbye=TextMarker(),
            betreff=TextMarker(),
            address_block=TextMarker()
        )
        json_str = page_data.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed['scan_page_num'], 1)
    
    def test_page_data_from_dict(self):
        """Test PageData.from_dict() method."""
        data = {
            'scan_page_num': 3,
            'page_info': {'found': False, 'current': None, 'total': None, 'raw': None},
            'greeting': {'found': True, 'raw': 'Greetings', 'text': 'Greetings'},
            'goodbye': {'found': False, 'raw': None, 'text': None},
            'betreff': {'found': False, 'raw': None, 'text': None},
            'address_block': {'found': False, 'raw': None, 'text': None}
        }
        page_data = PageData.from_dict(data)
        
        self.assertEqual(page_data.scan_page_num, 3)
        self.assertFalse(page_data.page_info.found)
        self.assertTrue(page_data.greeting.found)
        self.assertEqual(page_data.greeting.raw, 'Greetings')
    
    def test_page_data_list_to_json(self):
        """Test page_data_list_to_json() function."""
        pages = [
            PageData(
                scan_page_num=1,
                page_info=PageInfoDetected(),
                greeting=TextMarker(),
                goodbye=TextMarker(),
                betreff=TextMarker(),
                address_block=TextMarker()
            ),
            PageData(
                scan_page_num=2,
                page_info=PageInfoDetected(found=True, current=2, total=2),
                greeting=TextMarker(),
                goodbye=TextMarker(),
                betreff=TextMarker(),
                address_block=TextMarker()
            )
        ]
        
        json_str = page_data_list_to_json(pages)
        parsed = json.loads(json_str)
        
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['scan_page_num'], 1)
        self.assertEqual(parsed[1]['scan_page_num'], 2)
        self.assertTrue(parsed[1]['page_info']['found'])


class TestMarkerDetection(unittest.TestCase):
    """Test cases for marker detection functions."""
    
    def setUp(self):
        """Create sample DataFrame for testing."""
        self.sample_df = pd.DataFrame({
            'page_num': [1, 1, 1],
            'text': ['Hello', 'World', 'Test'],
            'level': [5, 5, 5]
        })
    
    def test_detect_page_info_returns_correct_type(self):
        """Test detect_page_info returns PageInfoDetected."""
        result = detect_page_info(self.sample_df)
        self.assertIsInstance(result, PageInfoDetected)
    
    def test_detect_page_info_stub_returns_not_found(self):
        """Test detect_page_info stub returns found=False."""
        result = detect_page_info(self.sample_df)
        self.assertFalse(result.found)
    
    def test_detect_greeting_returns_correct_type(self):
        """Test detect_greeting returns TextMarker."""
        result = detect_greeting(self.sample_df)
        self.assertIsInstance(result, TextMarker)
    
    def test_detect_greeting_stub_returns_not_found(self):
        """Test detect_greeting stub returns found=False."""
        result = detect_greeting(self.sample_df)
        self.assertFalse(result.found)
    
    def test_detect_goodbye_returns_correct_type(self):
        """Test detect_goodbye returns TextMarker."""
        result = detect_goodbye(self.sample_df)
        self.assertIsInstance(result, TextMarker)
    
    def test_detect_goodbye_stub_returns_not_found(self):
        """Test detect_goodbye stub returns found=False."""
        result = detect_goodbye(self.sample_df)
        self.assertFalse(result.found)
    
    def test_detect_betreff_returns_correct_type(self):
        """Test detect_betreff returns TextMarker."""
        result = detect_betreff(self.sample_df)
        self.assertIsInstance(result, TextMarker)
    
    def test_detect_betreff_stub_returns_not_found(self):
        """Test detect_betreff stub returns found=False."""
        result = detect_betreff(self.sample_df)
        self.assertFalse(result.found)
    
    def test_detect_address_block_returns_correct_type(self):
        """Test detect_address_block returns TextMarker."""
        result = detect_address_block(self.sample_df)
        self.assertIsInstance(result, TextMarker)
    
    def test_detect_address_block_stub_returns_not_found(self):
        """Test detect_address_block stub returns found=False."""
        result = detect_address_block(self.sample_df)
        self.assertFalse(result.found)


class TestPageAnalysis(unittest.TestCase):
    """Test cases for page analysis orchestration."""
    
    def test_analyze_pages_empty_dataframe(self):
        """Test analyze_pages with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = analyze_pages(empty_df)
        self.assertEqual(len(result), 0)
    
    def test_analyze_pages_missing_page_num_column(self):
        """Test analyze_pages raises error if page_num column missing."""
        df = pd.DataFrame({
            'text': ['Hello', 'World']
        })
        with self.assertRaises(ValueError):
            analyze_pages(df)
    
    def test_analyze_pages_single_page(self):
        """Test analyze_pages with single page."""
        df = pd.DataFrame({
            'page_num': [1, 1, 1],
            'text': ['Hello', 'World', 'Test'],
            'level': [5, 5, 5]
        })
        result = analyze_pages(df)
        
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], PageData)
        self.assertEqual(result[0].scan_page_num, 1)
    
    def test_analyze_pages_multiple_pages(self):
        """Test analyze_pages with multiple pages."""
        df = pd.DataFrame({
            'page_num': [1, 1, 2, 2, 3, 3],
            'text': ['Page', '1', 'Page', '2', 'Page', '3'],
            'level': [5, 5, 5, 5, 5, 5]
        })
        result = analyze_pages(df)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].scan_page_num, 1)
        self.assertEqual(result[1].scan_page_num, 2)
        self.assertEqual(result[2].scan_page_num, 3)
    
    def test_analyze_pages_returns_page_data_with_all_markers(self):
        """Test that analyze_pages populates all marker fields."""
        df = pd.DataFrame({
            'page_num': [1],
            'text': ['Test'],
            'level': [5]
        })
        result = analyze_pages(df)
        
        page = result[0]
        self.assertIsInstance(page.page_info, PageInfoDetected)
        self.assertIsInstance(page.greeting, TextMarker)
        self.assertIsInstance(page.goodbye, TextMarker)
        self.assertIsInstance(page.betreff, TextMarker)
        self.assertIsInstance(page.address_block, TextMarker)
    
    def test_analyze_pages_maintains_page_order(self):
        """Test that analyze_pages returns pages in correct order."""
        df = pd.DataFrame({
            'page_num': [3, 1, 2, 3, 1, 2],
            'text': ['A', 'B', 'C', 'D', 'E', 'F'],
            'level': [5, 5, 5, 5, 5, 5]
        })
        result = analyze_pages(df)
        
        self.assertEqual(len(result), 3)
        self.assertEqual([p.scan_page_num for p in result], [1, 2, 3])
    
    def test_analyze_pages_json_serializable(self):
        """Test that analyze_pages results can be serialized to JSON."""
        df = pd.DataFrame({
            'page_num': [1, 2],
            'text': ['Hello', 'World'],
            'level': [5, 5]
        })
        result = analyze_pages(df)
        
        # Convert to JSON
        json_str = page_data_list_to_json(result)
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['scan_page_num'], 1)
        self.assertEqual(parsed[1]['scan_page_num'], 2)


class TestIntegrationWithOCR(unittest.TestCase):
    """Integration tests with real OCR extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_pdf_path = Path(__file__).parent / 'test.pdf'
        if not self.test_pdf_path.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_path}")
    
    def test_analyze_pages_with_real_ocr_data(self):
        """Test analyze_pages with real OCR data from test.pdf."""
        from process_letters import extract_text
        
        # Extract OCR data
        ocr_df = extract_text(self.test_pdf_path)
        
        # Analyze pages
        pages = analyze_pages(ocr_df)
        
        # Verify we got results for all pages
        self.assertEqual(len(pages), 4)  # test.pdf has 4 pages
        
        # Verify page numbers are correct
        self.assertEqual([p.scan_page_num for p in pages], [1, 2, 3, 4])
        
        # Verify all marker fields exist
        for page in pages:
            self.assertIsInstance(page.page_info, PageInfoDetected)
            self.assertIsInstance(page.greeting, TextMarker)
            self.assertIsInstance(page.goodbye, TextMarker)
            self.assertIsInstance(page.betreff, TextMarker)
            self.assertIsInstance(page.address_block, TextMarker)
    
    def test_analyze_pages_json_output_with_real_data(self):
        """Test JSON serialization with real OCR data."""
        from process_letters import extract_text
        
        # Extract OCR data
        ocr_df = extract_text(self.test_pdf_path)
        
        # Analyze pages
        pages = analyze_pages(ocr_df)
        
        # Convert to JSON
        json_str = page_data_list_to_json(pages)
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed), 4)
        
        # Verify structure
        for i, page_dict in enumerate(parsed):
            self.assertEqual(page_dict['scan_page_num'], i + 1)
            self.assertIn('page_info', page_dict)
            self.assertIn('greeting', page_dict)
            self.assertIn('goodbye', page_dict)
            self.assertIn('betreff', page_dict)
            self.assertIn('address_block', page_dict)


if __name__ == '__main__':
    unittest.main()
