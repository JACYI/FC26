# -*- coding: utf-8 -*-
"""Click SBC nav via coordinates."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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

if not page:
    print("EA page not found")
    p.stop()
    sys.exit(1)

print(f"URL: {page.url[:70]}")

# Get SBC button coordinates
coords = page.evaluate("""() => {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if (t === 'SBC' && btns[i].offsetParent !== null) {
            btns[i].scrollIntoView({block: 'center'});
            var r = btns[i].getBoundingClientRect();
            return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};
        }
    }
    return null;
}""")
print(f"SBC button coords: {coords}")

if coords:
    page.mouse.click(coords["x"], coords["y"])
    print(f"mouse.click({coords['x']}, {coords['y']})")
    time.sleep(4)
    body = page.inner_text("body")[:300]
    print(f"Body: {body}")
else:
    print("SBC button not found")

p.stop()
