# -*- coding: utf-8 -*-
"""Navigate to SBC Upgrades and save listing to file."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Click SBC nav
page.evaluate("document.querySelector('button.ut-tab-bar-item.icon-sbc').click()")
time.sleep(5)

# Click Upgrades sub-tab
page.evaluate("""
var btns = document.querySelectorAll('button');
for (var i = 0; i < btns.length; i++) {
    var t = btns[i].innerText || '';
    if (t.indexOf('升级') >= 0 && btns[i].offsetParent !== null) {
        btns[i].click();
        break;
    }
}
""")
time.sleep(5)

body = page.inner_text("body")
with open("data/sbc_list.txt", "w", encoding="utf-8") as f:
    f.write(body)

p.stop()
