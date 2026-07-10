# -*- coding: utf-8 -*-
"""Try logging in with different click methods."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Try dispatchEvent click on the login button
page.evaluate("""
var btn = document.querySelector('button.btn-standard.primary');
if (btn) {
    btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
}
""")
print("dispatched click event")
time.sleep(5)

print("URL:", page.url[:80])
if "signin.ea.com" in page.url:
    print("SUCCESS - redirected to signin!")
elif "ultimate-team/web-app" in page.url:
    body = page.inner_text("body")
    with open("data/after_dispatched.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])
    print("Still on EA page, saved body")
else:
    print("Other URL")

p.stop()
