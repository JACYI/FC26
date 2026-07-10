# -*- coding: utf-8 -*-
"""Login: wait longer for SPA init, then click."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

print("URL:", page.url[:80])

# Wait for page to fully render - the SPA takes time to boot
print("Waiting 15s for SPA to fully initialize...")
try:
    page.wait_for_load_state("networkidle", timeout=20000)
except:
    pass
time.sleep(15)

# Check if more content loaded
body = page.inner_text("body")
print("Body length:", len(body))

# Try Playwright click with force
btn = page.locator("button.btn-standard.primary")
if btn.is_visible(timeout=3000):
    print("Button visible, clicking...")
    btn.click(force=True)
    time.sleep(5)
    print("URL after click:", page.url[:80])

    if "signin.ea.com" in page.url:
        print("SUCCESS on signin page!")
    else:
        body2 = page.inner_text("body")
        with open("data/after_long_wait.txt", "w", encoding="utf-8") as f:
            f.write(body2[:500])
        print("Still on EA page")

        # Try playwright locator with has-text
        page.locator("button", has_text="登录").first.click(force=True)
        time.sleep(5)
        print("URL after 2nd click:", page.url[:80])

        if "signin.ea.com" not in page.url:
            # Try using keyboard Tab + Enter
            for _ in range(5):
                page.keyboard.press("Tab")
                time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(5)
            print("URL after Tab+Enter:", page.url[:80])
else:
    print("Button not visible")
    with open("data/btn_not_visible.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])

# Final dump if still on EA
if "signin.ea.com" in page.url:
    print("LOGGING IN...")
    page.locator("#email").fill("3079479814@qq.com")
    page.locator("#logInBtn").click()
    time.sleep(3)
    page.locator("#password").fill("Yyh3079479814")
    page.locator("button:has-text('Sign')").first.click()
    time.sleep(5)
    print("URL after full login:", page.url[:80])

p.stop()
