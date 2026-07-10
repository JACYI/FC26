# -*- coding: utf-8 -*-
"""Thin wrapper — switch Web App language (e.g., English)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils import connect, wait_for_page
from src.language import switch_language
import time

target = sys.argv[1] if len(sys.argv) > 1 else "English"

p, browser, page = connect()
try:
    print("=" * 40)
    print(f"EA FC 26 - Switch Language to '{target}'")
    print("=" * 40)

    success = switch_language(page, target)
    if success:
        filename = f"lang_{target[:4]}.png"
        page.screenshot(path=filename)
        print(f"Switched to '{target}'! Screenshot: {filename}")
    else:
        print(f"Failed to switch to '{target}'")

    print("\nBrowser remains open. Press Ctrl+C to exit.")
    while browser.is_connected():
        time.sleep(3)
except KeyboardInterrupt:
    print("\nExiting...")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        p.stop()
    except:
        pass
