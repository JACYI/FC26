# -*- coding: utf-8 -*-
"""Check current page state."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
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

from src.utils import _js

btns = _js(page, """function() {
    var b = document.querySelectorAll('button');
    return Array.from(b).filter(function(x) { return x.offsetParent !== null; }).map(function(x) {
        return (x.innerText || '').trim().substring(0, 40);
    });
}()""")
print("Visible buttons:")
for b in btns:
    print(f"  - '{b}'")

body = _js(page, "document.body.innerText.substring(0, 400)")
print(f"\nBody: {body}")
p.stop()
