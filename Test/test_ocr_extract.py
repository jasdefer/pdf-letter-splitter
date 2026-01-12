#!/usr/bin/env python3
"""
DEPRECATED: This test file is deprecated.

The extract_text.py script has been replaced by process_letters.py which
returns TSV data with positional information instead of plain text.

Please use test_process_letters.py for testing the new functionality.
"""

import unittest

class TestDeprecated(unittest.TestCase):
    """Placeholder to indicate deprecation."""
    
    def test_deprecated(self):
        """This test suite is deprecated."""
        self.skipTest("This test suite is deprecated. Use test_process_letters.py instead.")

if __name__ == '__main__':
    unittest.main()
