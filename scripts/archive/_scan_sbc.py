# -*- coding: utf-8 -*-
"""Navigate to SBC Upgrades tab and dump the listing to file."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Click SBC nav button
page.evaluate("document.querySelector('button.ut-tab-bar-item.icon-sbc').click()")
time.sleep(5)

# Click Upgrades sub-tab using text content search
page.evaluate("""
var btns = document.querySelectorAll('button');
for (var i = 0; i < btns.length; i++) {
    var t = btns[i].innerText || '';
    if ((t.indexOf('升级') >= 0 || t.indexOf('Upgrades') >= 0) && btns[i].offsetParent !== null) {
        btns[i].click();
    }
}
""")
time.sleep(5)

body = page.inner_text("body")
with open("data/sbc_upgrades.txt", "w", encoding="utf-8") as f:
    f.write(body)
print("Written to data/sbc_upgrades.txt (" + str(len(body)) + " chars)")

p.stop()
