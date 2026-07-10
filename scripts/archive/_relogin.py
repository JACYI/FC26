# -*- coding: utf-8 -*-
"""Re-login to EA Web App from Chinese login page."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Click Login button
page.evaluate("""
var btns = document.querySelectorAll('button');
for (var i = 0; i < btns.length; i++) {
    var t = btns[i].innerText || '';
    if ((t.indexOf('登录') >= 0 || t.indexOf('Login') >= 0) && btns[i].offsetParent !== null) {
        btns[i].click();
        break;
    }
}
""")
print("Clicked Login")
time.sleep(5)
print("URL:", page.url[:80])

# Email form
page.locator("#email").wait_for(timeout=10000)
page.locator("#email").fill("3079479814@qq.com")
page.locator("#logInBtn").click()
print("Email entered, clicked NEXT")
time.sleep(3)

# Password form
page.locator("#password").wait_for(timeout=10000)
page.locator("#password").fill("Yyh3079479814")
time.sleep(1)

# Click Sign In - look for any clickable element with Sign/登录 text
page.evaluate("""
var btns = document.querySelectorAll('button, a, [role="button"]');
for (var i = 0; i < btns.length; i++) {
    var t = btns[i].innerText || '';
    if ((t.indexOf('Sign') >= 0 || t.indexOf('登录') >= 0) && btns[i].offsetParent !== null) {
        btns[i].click();
        break;
    }
}
""")
print("Clicked Sign In")
time.sleep(5)
print("After Sign In URL:", page.url[:80])

# Check result
body = page.inner_text("body")
if "ultimate-team/web-app" in page.url:
    print("LOGGED IN!")
elif "twoFactorCode" in page.url or "验证" in body:
    print("NEEDS VERIFICATION CODE")
    with open("data/login_2fa.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])
else:
    print("Unknown state, saving body...")
    with open("data/login_state.txt", "w", encoding="utf-8") as f:
        f.write(body[:500])

p.stop()
