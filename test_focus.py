#!/usr/bin/env python3
"""Simple test script to verify browser focus functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.automation_focus import BrowserFocusController

def test_focus():
    """Test browser focus functionality."""
    focus = BrowserFocusController()

    print("Testing browser focus...")
    print(f"Browser keywords: {focus._browser_keywords}")

    # Try to focus browser
    success = focus.ensure_browser_focus(allow_taskbar=True, preserve_tab=False)
    print(f"Focus result: {success}")

    if success:
        print("✓ Browser focus successful!")
    else:
        print("✗ Browser focus failed")

    return success

if __name__ == "__main__":
    test_focus()