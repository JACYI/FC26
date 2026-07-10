# -*- coding: utf-8 -*-
"""Click 关闭 button."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

pos = _js(page, """function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if (t === '关闭' && btns[i].offsetParent !== null) {
            var r = btns[i].getBoundingClientRect();
            return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
        }
    }
    return null;
}()""")
if pos:
    page.mouse.click(pos[0], pos[1])
    print(f"Clicked 关闭 at ({pos[0]}, {pos[1]})")
    time.sleep(3)
    body = _js(page, "document.body.innerText.substring(0, 200)")
    print(f"Body: {body[:100]}")
else:
    print("关闭 not found")

p.stop()
