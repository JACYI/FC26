# -*- coding: utf-8 -*-
"""Check login state after clicking login button."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

print("URL:", page.url[:80])
body = page.inner_text("body")

with open("data/login_page_state.txt", "w", encoding="utf-8") as f:
    f.write(body)

# Check for key elements
has_email = page.evaluate("!!document.getElementById('email')")
print("Has #email:", has_email)
print("Body length:", len(body))

# Look for all links/buttons with Login text
login_els = page.evaluate("""
Array.from(document.querySelectorAll('button, a, [role="button"], span, div'))
    .filter(function(el) {
        var t = el.innerText || '';
        return (t.indexOf('登录') >= 0 || t.indexOf('Login') >= 0) && el.offsetParent !== null;
    })
    .map(function(el) { return {tag: el.tagName, text: (el.innerText || '').substring(0, 30), id: el.id}; })
""")
print("Login elements:", login_els)

p.stop()
