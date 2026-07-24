# -*- coding: utf-8 -*-
"""Check page structure for squad builder vs listing."""
import sys, os, time, json
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

# Navigate to SBC > Upgrades
page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True, timeout=5000)
time.sleep(2)
page.get_by_text("升级", exact=False).first.click(force=True, timeout=5000)
time.sleep(3)

# Check squad builder elements
r = page.evaluate("""function() {
    return {
        slots: document.querySelectorAll(".ut-squad-slot-view").length,
        tiles: document.querySelectorAll(".ut-sbc-set-tile-view").length,
        overlays: document.querySelectorAll('[class*="overlay"],[class*="Overlay"]').length,
        modals: document.querySelectorAll('[class*="modal"],[class*="Modal"]').length,
        submitBtns: document.querySelectorAll('button').length
    };
}()""")
print("Page structure:", json.dumps(r, indent=2))

# Get tabs
tabs = page.evaluate("""function() {
    var t = document.querySelectorAll('.ut-tab-bar-item');
    var r = [];
    for (var i = 0; i < t.length; i++) {
        r.push((t[i].innerText || '').trim().replace(/\\n/g, '|'));
    }
    return r;
}()""")
print("Tabs:", tabs)

# Get all buttons text
btns = page.evaluate("""function() {
    var b = document.querySelectorAll('button');
    var r = [];
    for (var i = 0; i < b.length; i++) {
        var t = (b[i].innerText || '').trim().substring(0, 30);
        if (t) r.push(t.replace(/\\n/g, '|'));
    }
    return r;
}()""")
print("Buttons:", btns)

p.stop()
