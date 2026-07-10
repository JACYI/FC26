# -*- coding: utf-8 -*-
"""Check HTML around Login button."""
from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Get the Login div outerHTML
html = page.evaluate("document.getElementById('Login') ? document.getElementById('Login').outerHTML : 'no element'")
with open("data/login_html.txt", "w", encoding="utf-8") as f:
    f.write(html)
print("HTML written to data/login_html.txt")

# Try clicking the Login div at (center_x, center_y)
rect = page.evaluate("var r = document.getElementById('Login').getBoundingClientRect(); return {x: r.left + r.width/2, y: r.top + r.height/2}")
print("Login rect:", rect)
page.mouse.click(rect["x"], rect["y"])
print("Clicked Login at center")

import time
time.sleep(5)
print("URL after click:", page.url[:80])

p.stop()
