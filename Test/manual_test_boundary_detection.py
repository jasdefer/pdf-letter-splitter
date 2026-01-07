#!/usr/bin/env python3
"""
Manual test script for boundary detection with mock LLM responses.

This script demonstrates the boundary detection functionality without requiring
a running LLM server by mocking the LLM responses.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from detect_boundaries import (
    BoundaryDecision,
    detect_boundaries,
    group_pages_into_letters,
    detect_and_log_boundaries
)

# Constant for parsing page numbers from prompts (German format)
PAGE_NUMBER_PATTERN = r'SEITE (\d+):'


def create_mock_llm_client():
    """Create a mock LLM client that returns predefined responses."""
    mock_client = Mock()
    
    # Define responses for different page pairs
    # This simulates:
    # - Pages 1-2: continuation (same letter)
    # - Pages 2-3: boundary (new letter starts at page 3)
    # - Pages 3-4: continuation (same letter)
    responses = {
        (1, 2): '{"boundary": false, "confidence": 0.95, "reason": "Fortlaufender Text, gleicher Absender"}',
        (2, 3): '{"boundary": true, "confidence": 0.92, "reason": "Neuer Absender, neues Datum erkannt"}',
        (3, 4): '{"boundary": false, "confidence": 0.88, "reason": "Fortsetzung des Briefes, Seitennummer vorhanden"}',
    }
    
    def mock_generate(prompt):
        # Extract page numbers from the prompt using the pattern
        import re
        matches = re.findall(PAGE_NUMBER_PATTERN, prompt)
        if len(matches) >= 2:
            page_i = int(matches[0])
            page_j = int(matches[1])
            return responses.get((page_i, page_j), '{"boundary": false, "confidence": 0.5, "reason": "Default"}')
        return '{"boundary": false, "confidence": 0.5, "reason": "Could not parse pages"}'
    
    mock_client.generate = mock_generate
    return mock_client


def test_with_mock_data():
    """Test boundary detection with mock page data."""
    # Create sample pages (simulating OCR output)
    pages = [
        {
            "page_number": 1,
            "text": """
Absender: Max Mustermann GmbH
Musterstraße 123
12345 Berlin

Datum: 15.11.2024

Betreff: Rechnung Nr. 2024-001

Sehr geehrte Damen und Herren,

hiermit übersenden wir Ihnen unsere Rechnung für die im Oktober 2024
erbrachten Dienstleistungen...
            """
        },
        {
            "page_number": 2,
            "text": """
Seite 2

Fortsetzung der Rechnung...

Positionen:
1. Beratungsleistung: 1.500,00 EUR
2. Implementierung: 2.500,00 EUR

Gesamtsumme: 4.000,00 EUR

Mit freundlichen Grüßen
Max Mustermann GmbH
            """
        },
        {
            "page_number": 3,
            "text": """
Finanzamt Berlin
Steuerabteilung
Hauptstraße 456
10115 Berlin

Datum: 20.11.2024

Betreff: Steuerbescheid 2023

Sehr geehrter Herr Mustermann,

anbei erhalten Sie Ihren Steuerbescheid für das Jahr 2023.
            """
        },
        {
            "page_number": 4,
            "text": """
Seite 2 des Steuerbescheids

Berechnung:
Einkommen: 50.000 EUR
Steuersatz: 25%
Zu zahlende Steuer: 12.500 EUR

Mit freundlichen Grüßen
Finanzamt Berlin
            """
        }
    ]
    
    print("=" * 80)
    print("MANUAL TEST: Boundary Detection with Mock Data")
    print("=" * 80)
    print()
    
    # Create mock LLM client
    mock_client = create_mock_llm_client()
    
    # Detect boundaries
    print("Detecting boundaries...")
    decisions = detect_boundaries(pages, mock_client)
    
    print()
    print("BOUNDARY DETECTION RESULTS:")
    print("-" * 80)
    for page_i, page_j, decision in decisions:
        print(f"Pages ({page_i}, {page_j}): boundary={decision.is_boundary}, "
              f"confidence={decision.confidence:.2f}")
        print(f"  Reason: {decision.reason}")
    
    # Group pages into letters
    print()
    print("LETTER GROUPINGS:")
    print("-" * 80)
    letters = group_pages_into_letters(pages, decisions)
    
    for idx, letter_pages in enumerate(letters, 1):
        print(f"Letter {idx}: {len(letter_pages)} page(s) - {letter_pages}")
    
    print()
    print("Expected result:")
    print("  - Letter 1: Pages 1-2 (Invoice from Max Mustermann GmbH)")
    print("  - Letter 2: Pages 3-4 (Tax notice from Finanzamt Berlin)")
    print()
    print("=" * 80)


if __name__ == '__main__':
    test_with_mock_data()
