# -*- coding: utf-8 -*-
"""Check current state and finish login."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

print("URL:", page.url[:80])
body = page.inner_text("body")
print("Has email field:", page.evaluate("!!document.getElementById('email')"))
print("Has password field:", page.evaluate("!!document.getElementById('password')"))
print("Has logInBtn:", page.evaluate("!!document.getElementById('logInBtn')"))

# Get all visible buttons on the page
btns = page.evaluate("""
Array.from(document.querySelectorAll('button, [role="button"]')).filter(function(el) {
    return el.offsetParent !== null;
}).map(function(el) {
    return {tag: el.tagName, id: el.id, text: (el.innerText || '').substring(0, 30)};
})
""")
print("Visible clickable elements:", btns)

if page.locator("#password").is_visible(timeout=2000):
    page.locator("#password").fill("Yyh3079479814")
    time.sleep(1)
    print("Password filled")
    # Try clicking logInBtn
    if page.locator("#logInBtn").is_visible(timeout=2000):
        page.locator("#logInBtn").click()
        print("Clicked logInBtn")
        time.sleep(5)
        print("URL after:", page.url[:80])

p.stop()
