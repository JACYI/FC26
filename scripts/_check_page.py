# -*- coding: utf-8 -*-
"""Check page state after each navigation step"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.login import connect, navigate_to_ea
from src.utils import wait_for_page

p, browser, page = connect()
page.set_viewport_size({"width": 1280, "height": 900})
time.sleep(1)
navigate_to_ea(page)

def save_state(label):
    body = page.inner_text("body")
    with open(f"_nav_{label}.txt", "w", encoding="utf-8") as f:
        f.write(body)
    print(f"[{label}] URL: {page.url[:60]}")
    print(f"  Body length: {len(body)} chars")
    # Key markers
    for kw in ["SBC", "升级", "Upgrades", "一键填充", "每日青铜", "提交", "个 SBC", "全部"]:
        if kw in body:
            # Find context
            idx = body.index(kw)
            print(f"  Found '{kw}' at pos {idx}: ...{body[max(0,idx-10):idx+len(kw)+20]}...")

save_state("start")

# Step 1: Click SBC
page.evaluate("""function() {
    var btns = document.querySelectorAll('button.ut-tab-bar-item');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').indexOf('SBC') >= 0) {
            btns[i].click(); return 'clicked';
        }
    }
    return 'not found';
}()""")
time.sleep(4)
save_state("after_sbc")

# Step 2: Click 升级 tab
page.evaluate("""function() {
    var all = document.querySelectorAll('button, div, span, a');
    for (var i = 0; i < all.length; i++) {
        var t = all[i].innerText || '';
        if (t.indexOf('升级') >= 0 && all[i].offsetParent !== null && all[i].tagName === 'BUTTON') {
            all[i].click(); return 'clicked upgrade btn';
        }
    }
    return 'not found';
}()""")
time.sleep(4)
save_state("after_upgrade_tab")

# Step 3: Click 每日青铜升级
page.evaluate("""function() {
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var t = all[i].innerText || '';
        if (t.indexOf('每日青铜升级') >= 0 && all[i].offsetParent !== null) {
            // Find the clickable parent
            var parent = all[i].closest('a, button, [onclick], [class*=tile], [class*=Tile], [class*=card], [class*=Card]');
            if (parent) { parent.click(); return 'clicked tile'; }
            all[i].click(); return 'clicked text';
        }
    }
    return 'not found';
}()""")
time.sleep(4)
save_state("after_sbc_click")

# Check for segment or squad builder
body = page.inner_text("body")
if "个 SBC" in body and "提交" not in body:
    print("\n-> On segment list page, clicking first segment...")
    page.locator(".ut-sbc-set-tile-view").first.click(force=True, timeout=5000)
    time.sleep(3)
    save_state("after_segment")

if "提交" in body:
    print("\n-> On squad builder page!")
    # Check for FSU
    print(f"  FSU detected: {'【FSU】' in body}")
    print(f"  一键填充 detected: {'一键填充' in body}")
    # Check for slot
    has_slots = page.evaluate("document.querySelectorAll('.ut-squad-slot-view').length")
    print(f"  Slot count: {has_slots}")
else:
    print(f"\n-> Unknown state, body keywords:")
    for kw in ["开始挑战", "一键完成", "可重复", "造价预估", "SBC计数", "FSU"]:
        if kw in body:
            idx = body.index(kw)
            print(f"  '{kw}': {body[max(0,idx-5):idx+len(kw)+30]}")

input("Press Enter to continue exploration...")
