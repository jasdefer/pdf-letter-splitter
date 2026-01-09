#!/usr/bin/env python3
"""
Integration test demonstrating the letter analysis module with sample data.

This test uses mock OCR data to validate the complete workflow.
"""

import sys
from pathlib import Path

# Add Source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Source'))

from analyze_letters import analyze_documents


def main():
    """Demonstrate letter analysis with sample data."""
    
    # Sample OCR data representing multiple letters
    sample_pages = [
        # Letter 1, Page 1
        """Finanzamt München
Steuerstraße 123
80333 München

Datum: 15. Januar 2026
Betreff: Steuerbescheid 2025

Sehr geehrte Damen und Herren,

hiermit erhalten Sie Ihren Steuerbescheid für das Jahr 2025.
Die Steuer beträgt 5.432,10 EUR.""",
        
        # Letter 1, Page 2
        """Seite 2

Details der Berechnung:
Einkommen: 45.000 EUR
Abzüge: 3.500 EUR
Steuersatz: 25%

Bitte überweisen Sie den Betrag bis zum 28.02.2026.""",
        
        # Letter 2, Page 1
        """TechCorp GmbH
Innovationsweg 42
10115 Berlin

Date: January 20, 2026
Subject: Annual Report 2025
Page 1 of 2

Dear Shareholders,

We are pleased to present our annual report for 2025.
The company achieved record revenues of 125M EUR.""",
        
        # Letter 2, Page 2
        """Page 2 of 2

Financial Highlights:
- Revenue: 125M EUR (+15%)
- Profit: 18M EUR (+22%)
- R&D Investment: 12M EUR

Thank you for your continued support.""",
        
        # Letter 3, Page 1
        """Dr. Schmidt Medical Practice
Gesundheitsplatz 7
60311 Frankfurt

09.02.2026
RE: Appointment Confirmation

Dear Patient,

This letter confirms your appointment on March 5, 2026 at 10:00 AM.

Please arrive 15 minutes early for registration."""
    ]
    
    print("Analyzing sample documents...\n")
    print("=" * 70)
    
    # Analyze the documents
    letters = analyze_documents(sample_pages)
    
    # Display results
    print(f"\nFound {len(letters)} letter(s):\n")
    
    for i, letter in enumerate(letters, 1):
        print(f"Letter {i}:")
        print(f"  Start Page: {letter['start_page']}")
        print(f"  Page Count: {letter['page_count']}")
        print(f"  Date:       {letter['date'] or 'Not found'}")
        print(f"  Sender:     {letter['sender'] or 'Not found'}")
        print(f"  Topic:      {letter['topic'] or 'Not found'}")
        print()
    
    print("=" * 70)
    
    # Verify expected results
    print("\nValidation:")
    
    expected_letter_count = 3
    if len(letters) == expected_letter_count:
        print(f"✓ Correct number of letters detected: {expected_letter_count}")
    else:
        print(f"✗ Expected {expected_letter_count} letters, found {len(letters)}")
        return 1
    
    # Check first letter
    if letters[0]['page_count'] == 2:
        print("✓ Letter 1 has correct page count: 2")
    else:
        print(f"✗ Letter 1 should have 2 pages, found {letters[0]['page_count']}")
    
    if letters[0]['sender'] and 'Finanzamt' in letters[0]['sender']:
        print("✓ Letter 1 sender correctly identified: Finanzamt")
    else:
        print(f"✗ Letter 1 sender not correctly identified: {letters[0]['sender']}")
    
    # Check second letter
    if letters[1]['page_count'] == 2:
        print("✓ Letter 2 has correct page count: 2")
    else:
        print(f"✗ Letter 2 should have 2 pages, found {letters[1]['page_count']}")
    
    if letters[1]['sender'] and 'TechCorp' in letters[1]['sender']:
        print("✓ Letter 2 sender correctly identified: TechCorp")
    else:
        print(f"✗ Letter 2 sender not correctly identified: {letters[1]['sender']}")
    
    # Check third letter
    if letters[2]['page_count'] == 1:
        print("✓ Letter 3 has correct page count: 1")
    else:
        print(f"✗ Letter 3 should have 1 page, found {letters[2]['page_count']}")
    
    if letters[2]['topic'] and 'Appointment' in letters[2]['topic']:
        print("✓ Letter 3 topic correctly identified: Appointment")
    else:
        print(f"✗ Letter 3 topic not correctly identified: {letters[2]['topic']}")
    
    print("\n" + "=" * 70)
    print("Integration test completed successfully!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
