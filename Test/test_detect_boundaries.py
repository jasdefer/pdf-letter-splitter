#!/usr/bin/env python3
"""
Test suite for boundary detection module.

Tests the LLM-based letter boundary detection functionality.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add Source directory to path to import the detection module
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from detect_boundaries import (
    BoundaryDecision,
    LLMClient,
    create_boundary_prompt,
    parse_llm_response,
    detect_boundaries,
    group_pages_into_letters,
)


class TestBoundaryDecision(unittest.TestCase):
    """Test cases for BoundaryDecision class."""
    
    def test_initialization(self):
        """Test that BoundaryDecision initializes correctly."""
        decision = BoundaryDecision(is_boundary=True, confidence=0.95, reason="Test reason")
        
        self.assertTrue(decision.is_boundary)
        self.assertEqual(decision.confidence, 0.95)
        self.assertEqual(decision.reason, "Test reason")
    
    def test_repr(self):
        """Test string representation."""
        decision = BoundaryDecision(is_boundary=False, confidence=0.85, reason="Test")
        repr_str = repr(decision)
        
        self.assertIn("False", repr_str)
        self.assertIn("0.85", repr_str)
        self.assertIn("Test", repr_str)


class TestLLMClient(unittest.TestCase):
    """Test cases for LLMClient."""
    
    def test_initialization(self):
        """Test that LLMClient initializes with correct defaults."""
        client = LLMClient()
        
        self.assertEqual(client.base_url, "http://llm:8080")
        self.assertEqual(client.temperature, 0.0)
    
    def test_custom_initialization(self):
        """Test LLMClient with custom parameters."""
        client = LLMClient(host="localhost", port=9000, temperature=0.5)
        
        self.assertEqual(client.base_url, "http://localhost:9000")
        self.assertEqual(client.temperature, 0.5)
    
    @patch('detect_boundaries.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful LLM generation."""
        # Mock successful response with OpenAI-compatible format
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = LLMClient()
        result = client.generate("Test prompt")
        
        self.assertEqual(result, "Test response")
        mock_post.assert_called_once()
    
    @patch('detect_boundaries.requests.post')
    def test_generate_failure(self, mock_post):
        """Test LLM generation failure."""
        # Mock failed response
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        client = LLMClient()
        
        with self.assertRaises(RuntimeError):
            client.generate("Test prompt")


class TestCreateBoundaryPrompt(unittest.TestCase):
    """Test cases for prompt creation."""
    
    def test_prompt_contains_page_numbers(self):
        """Test that prompt includes page numbers."""
        prompt = create_boundary_prompt("Text A", "Text B", 1, 2)
        
        self.assertIn("1", prompt)
        self.assertIn("2", prompt)
    
    def test_prompt_contains_page_texts(self):
        """Test that prompt includes page texts."""
        prompt = create_boundary_prompt("First page text", "Second page text", 1, 2)
        
        self.assertIn("First page text", prompt)
        self.assertIn("Second page text", prompt)
    
    def test_prompt_is_in_german(self):
        """Test that prompt is primarily in German."""
        prompt = create_boundary_prompt("Text A", "Text B", 1, 2)
        
        # Check for German keywords
        self.assertIn("Seite", prompt)
        self.assertIn("Brief", prompt)
    
    def test_prompt_requests_json(self):
        """Test that prompt requests JSON response."""
        prompt = create_boundary_prompt("Text A", "Text B", 1, 2)
        
        self.assertIn("JSON", prompt)
        self.assertIn("boundary", prompt)
        self.assertIn("confidence", prompt)
        self.assertIn("reason", prompt)


class TestParseLLMResponse(unittest.TestCase):
    """Test cases for parsing LLM responses."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"boundary": true, "confidence": 0.95, "reason": "New sender"}'
        decision = parse_llm_response(response)
        
        self.assertTrue(decision.is_boundary)
        self.assertEqual(decision.confidence, 0.95)
        self.assertEqual(decision.reason, "New sender")
    
    def test_parse_missing_field(self):
        """Test that missing fields raise ValueError."""
        response = '{"boundary": true, "confidence": 0.9}'
        
        with self.assertRaises(ValueError) as context:
            parse_llm_response(response)
        
        self.assertIn("reason", str(context.exception))
    
    def test_parse_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        response = 'Not valid JSON at all'
        
        with self.assertRaises(ValueError):
            parse_llm_response(response)
    
    def test_parse_invalid_confidence_range(self):
        """Test that confidence out of range raises ValueError."""
        response = '{"boundary": true, "confidence": 1.5, "reason": "Test"}'
        
        with self.assertRaises(ValueError):
            parse_llm_response(response)


class TestDetectBoundaries(unittest.TestCase):
    """Test cases for detect_boundaries function."""
    
    def test_empty_pages(self):
        """Test with empty page list."""
        mock_client = Mock()
        result = detect_boundaries([], mock_client)
        
        self.assertEqual(result, [])
    
    def test_single_page(self):
        """Test with single page (no boundaries to detect)."""
        pages = [{"page_number": 1, "text": "Page 1 text"}]
        mock_client = Mock()
        
        result = detect_boundaries(pages, mock_client)
        
        self.assertEqual(result, [])
    
    @patch('detect_boundaries.create_boundary_prompt')
    @patch('detect_boundaries.parse_llm_response')
    def test_two_pages(self, mock_parse, mock_prompt):
        """Test boundary detection with two pages."""
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"}
        ]
        
        mock_client = Mock()
        mock_client.generate.return_value = '{"boundary": true, "confidence": 0.9, "reason": "New letter"}'
        
        mock_prompt.return_value = "Test prompt"
        mock_parse.return_value = BoundaryDecision(True, 0.9, "New letter")
        
        result = detect_boundaries(pages, mock_client)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 1)  # page_i
        self.assertEqual(result[0][1], 2)  # page_j
        self.assertTrue(result[0][2].is_boundary)


class TestGroupPagesIntoLetters(unittest.TestCase):
    """Test cases for grouping pages into letters."""
    
    def test_empty_pages(self):
        """Test with empty page list."""
        result = group_pages_into_letters([], [])
        self.assertEqual(result, [])
    
    def test_single_page(self):
        """Test with single page."""
        pages = [{"page_number": 1, "text": "Page 1"}]
        result = group_pages_into_letters(pages, [])
        
        self.assertEqual(result, [[1]])
    
    def test_all_one_letter(self):
        """Test when all pages belong to one letter."""
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"},
            {"page_number": 3, "text": "Page 3"}
        ]
        decisions = [
            (1, 2, BoundaryDecision(False, 0.9, "Continuation")),
            (2, 3, BoundaryDecision(False, 0.85, "Continuation"))
        ]
        
        result = group_pages_into_letters(pages, decisions)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], [1, 2, 3])
    
    def test_multiple_letters(self):
        """Test grouping into multiple letters."""
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"},
            {"page_number": 3, "text": "Page 3"},
            {"page_number": 4, "text": "Page 4"}
        ]
        decisions = [
            (1, 2, BoundaryDecision(False, 0.9, "Continuation")),
            (2, 3, BoundaryDecision(True, 0.95, "New letter")),
            (3, 4, BoundaryDecision(False, 0.85, "Continuation"))
        ]
        
        result = group_pages_into_letters(pages, decisions)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [1, 2])
        self.assertEqual(result[1], [3, 4])
    
    def test_page_one_always_starts_letter(self):
        """Test that page 1 always starts a letter."""
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"}
        ]
        decisions = [
            (1, 2, BoundaryDecision(True, 0.95, "New letter"))
        ]
        
        result = group_pages_into_letters(pages, decisions)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [1])
        self.assertEqual(result[1], [2])


if __name__ == '__main__':
    unittest.main()
