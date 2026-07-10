# -*- coding: utf-8 -*-
"""Re-login using standard Playwright click with longer waits."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

print("URL:", page.url[:80])

# Get bounding box and mouse-click
box = page.locator('button.btn-standard.primary').bounding_box()
if not box:
    print("Login button not found!")
    p.stop()
    exit(1)

print("Button box:", box)
page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
print("Clicked Login, waiting for redirect...")

# Wait longer for redirect to signin.ea.com
for i in range(20):
    time.sleep(2)
    if "signin.ea.com" in page.url:
        print("Redirected to signin after", (i+1)*2, "s")
        break
    print("  waiting...", page.url[:60])

if "signin.ea.com" not in page.url:
    print("Not on signin, saving state...")
    body = page.inner_text("body")
    with open("data/after_login_click.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])
    p.stop()
    exit(1)

# Fill email
page.locator("#email").wait_for(timeout=10000)
page.locator("#email").fill("3079479814@qq.com")
time.sleep(1)
page.locator("#logInBtn").click()
print("Email entered")
time.sleep(3)

# Fill password
page.locator("#password").wait_for(timeout=10000)
page.locator("#password").fill("Yyh3079479814")
time.sleep(1)
# Click Sign In - use button text search
page.locator("button:has-text('Sign'), button:has-text('登录')").first.click()
print("Password submitted")
time.sleep(5)

print("URL after signin:", page.url[:80])
body = page.inner_text("body")
if "ultimate-team/web-app" in page.url:
    print("LOGGED IN!")
elif "twoFactorCode" in body or "验证" in body:
    print("NEEDS 2FA CODE")
    with open("data/needs_2fa.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])
else:
    with open("data/after_signin.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])
    print("Other state")

p.stop()
