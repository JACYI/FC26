# -*- coding: utf-8 -*-
"""Find SBC nav button structure."""
from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Find all nav bar buttons
nav_btns = page.evaluate("""
Array.from(document.querySelectorAll('button.ut-tab-bar-item, [class*=tab-bar-item], [class*=TabBarItem]')).map(function(el) {
    return {tag: el.tagName, id: el.id, className: el.className.substring(0, 80), text: (el.innerText || '').substring(0, 20), rect: el.getBoundingClientRect()};
})
""")
print("Nav buttons found:", len(nav_btns))
for btn in nav_btns:
    print(" ", btn["text"], "-", btn["className"])

# Also find by text "SBC"
sbc_by_text = page.evaluate("""
Array.from(document.querySelectorAll('*')).filter(function(el) {
    return el.innerText && el.innerText.trim() === 'SBC' && el.offsetParent !== null;
}).map(function(el) {
    return {tag: el.tagName, id: el.id, className: el.className.substring(0, 60), rect: el.getBoundingClientRect()};
})
""")
print("\nSBC text elements:", sbc_by_text)

p.stop()
