# -*- coding: utf-8 -*-
"""Navigation debug - save page state at each step"""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.login import connect, navigate_to_ea

p, browser, page = connect()
page.set_viewport_size({"width": 1280, "height": 900})
time.sleep(1)
navigate_to_ea(page)

# SBC nav
page.locator("button.ut-tab-bar-item.icon-sbc").first.click(force=True, timeout=5000)
time.sleep(4)

# Save upgrades page
body = page.inner_text("body")
with open("_sbc_upgrades.txt", "w", encoding="utf-8") as f:
    f.write(body)
print(f"Upgrades page saved ({len(body)} chars)")

# Try clicking 升级 tab via JS
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = btns[i].innerText || '';
        if (t.indexOf('升级') >= 0 && btns[i].offsetParent !== null) {
            btns[i].click(); return;
        }
    }
}()""")
time.sleep(4)

# Save after tab click
body = page.inner_text("body")
with open("_sbc_after_tab.txt", "w", encoding="utf-8") as f:
    f.write(body)
print(f"After tab click saved ({len(body)} chars)")

# Look at what's available
if "一键完成" in body:
    idx = body.index("一键完成")
    print(f"Found '一键完成' context: {body[max(0,idx-30):idx+50]}")

# Try clicking any upgrade SBC tile
clicked = page.evaluate("""function() {
    var all = document.querySelectorAll('[class*=tile], [class*=Tile]');
    for (var i = 0; i < all.length; i++) {
        if (all[i].offsetParent !== null) {
            var t = all[i].innerText || '';
            if ((t.indexOf('升级') >= 0 || t.indexOf('Upgrade') >= 0) && t.length < 100) {
                all[i].click();
                return 'clicked: ' + t.substring(0, 40);
            }
        }
    }
    return 'no tile found';
}()""")
print(f"Tile click result: {clicked}")
time.sleep(4)

body = page.inner_text("body")
with open("_after_tile_click.txt", "w", encoding="utf-8") as f:
    f.write(body)

if "提交" in body:
    print("-> On squad builder! (submit found)")
elif "个 SBC" in body:
    print("-> On segment list page")
    seg_count = page.evaluate("document.querySelectorAll('.ut-sbc-set-tile-view').length")
    print(f"  Segments found: {seg_count}")
    if seg_count > 0:
        first_seg = page.evaluate("""function() {
            var el = document.querySelector('.ut-sbc-set-tile-view');
            return (el.innerText || '').substring(0, 100);
        }()""")
        print(f"  First segment text: {first_seg[:80]}")
else:
    print("-> Unknown page state")
