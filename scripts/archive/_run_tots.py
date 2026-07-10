# -*- coding: utf-8 -*-
"""Run TOTS Crafting Upgrade once with refactored executor."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright
from src.sbc.executor import SBCExecutor

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Wait for FSU data
page.wait_for_function(
    'typeof repositories !== "undefined" && repositories.Item.club.items.values().length > 100',
    timeout=60000)
print("FSU ready:", page.evaluate("repositories.Item.club.items.values().length"), "players")

# Dismiss any FSU dialog
for btn_text in ["确定", "OK", "确认"]:
    try:
        btn = page.locator(f"text={btn_text}").first
        if btn.is_visible(timeout=1000):
            btn.click(force=True, timeout=2000)
            time.sleep(1)
    except:
        pass

executor = SBCExecutor(page)
result = executor.run_sbc("TOTS制作升级", tab="Upgrades")
print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")
