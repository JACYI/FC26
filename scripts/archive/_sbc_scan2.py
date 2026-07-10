# -*- coding: utf-8 -*-
"""Use eval_on_selector to click SBC nav, then scan Upgrades tab."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Click SBC nav button using Playwright locator
sbc_btn = page.locator("button.ut-tab-bar-item.icon-sbc")
sbc_btn.wait_for(state="visible", timeout=5000)
sbc_btn.click(force=True)
print("Clicked SBC nav")
time.sleep(5)

# Click Upgrades sub-tab
upgrade_btn = page.locator("button:has-text('升级')")
upgrade_btn.wait_for(state="visible", timeout=5000)
upgrade_btn.click(force=True)
print("Clicked 升级 tab")
time.sleep(5)

body = page.inner_text("body")
with open("data/sbc_list2.txt", "w", encoding="utf-8") as f:
    f.write(body)
print("Written to data/sbc_list2.txt (" + str(len(body)) + " chars)")

p.stop()
