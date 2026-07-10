# -*- coding: utf-8 -*-
"""Thin wrapper — set Web App language to Simplified Chinese."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Replicate original CLI behavior: connect then call set_language
from src.utils import connect, wait_for_page, ensure_logged_in
from src.language import set_language
import time

p, browser, page = connect()
try:
    print("=" * 40)
    print("EA FC 26 - Set Language to Chinese")
    print("=" * 40)

    if not ensure_logged_in(page):
        print("Need to login first. Run login.py or login manually.")
        sys.exit(1)

    success = set_language(page)
    if success:
        page.screenshot(path="language_set.png")
        print("Language set successfully! Screenshot: language_set.png")
    else:
        print("Failed to set language")

    print("\nBrowser remains open. Press Ctrl+C to exit.")
    while browser.is_connected():
        time.sleep(3)
except KeyboardInterrupt:
    print("\nExiting...")
except Exception as e:
    print(f"\nError: {e}")
    page.screenshot(path="lang_error.png")
finally:
    try:
        p.stop()
    except:
        pass
