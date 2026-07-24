# -*- coding: utf-8 -*-
"""Test click_nav_by_text fix - avoid encoding issues."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout = open(1, 'w', encoding='utf-8', closefd=False)

from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team" in pg.url:
            page = pg
            break
    if page:
        break

from src.utils import click_nav_by_text, _js

# Check what nav buttons exist
nav_btns = _js(page, """function() {
    var nav = document.querySelector('nav.ut-tab-bar');
    if (!nav) return 'no nav';
    var btns = nav.querySelectorAll('button');
    return Array.from(btns).filter(function(b) { return b.offsetParent !== null; }).map(function(b) {
        return (b.innerText || '').trim();
    });
}()""")
print("Nav buttons:", nav_btns)

# Check current page
body = _js(page, "document.body.innerText.substring(0, 100)")
print("Body before:", repr(body))

# Click SBC via new function
print("\nClicking SBC...")
click_nav_by_text(page, "SBC")
time.sleep(4)

body = _js(page, "document.body.innerText.substring(0, 100)")
print("Body after SBC click:", repr(body))

# Check if SBC page loaded
has_sbc = body and ("全部" in body or "SBC配" in body)
print("SBC nav:", "OK" if has_sbc else "FAILED")

p.stop()
