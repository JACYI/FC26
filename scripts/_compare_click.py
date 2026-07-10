# -*- coding: utf-8 -*-
"""Compare old locator.click vs new coordinate click head-to-head."""
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

from src.utils import _js

# First go to Home
def click_nav(page, text):
    pos = _js(page, f"""function() {{
        var nav = document.querySelector('nav.ut-tab-bar');
        if (!nav) return null;
        var btns = nav.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {{
            if ((btns[i].innerText || '').trim() === '{text}' && btns[i].offsetParent !== null) {{
                btns[i].scrollIntoView({{block: 'center'}});
                var r = btns[i].getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }}
        }}
        return null;
    }}()""")
    if pos:
        page.mouse.click(pos[0], pos[1])
        return True
    return False

def go_home():
    click_nav(page, "主页")
    time.sleep(3)

go_home()

# Ensure we're on Home
body = _js(page, "document.body.innerText.substring(0, 50)")
print("On Home:", '主页' in body)

# --- Test 1: Playwright locator with :has-text ---
print("\n=== Test 1: locator('button:has-text(\"SBC\")').click(force=True) ===")

# Check what Playwright matches for has-text
matches = _js(page, """function() {
    var all = document.querySelectorAll('button');
    var results = [];
    for (var i = 0; i < all.length; i++) {
        if (all[i].offsetParent === null) continue;
        var text = (all[i].innerText || '').toLowerCase();
        if (text.indexOf('sbc') >= 0) {
            var r = all[i].getBoundingClientRect();
            results.push({
                index: i,
                innerText: (all[i].innerText || '').trim(),
                rect: {l: Math.round(r.left), t: Math.round(r.top)},
                center: {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)}
            });
        }
    }
    return results;
}()""")
print(f"Playwright has-text matches ({len(matches)}):")
for m in matches:
    print(f"  [{m['index']}] '{m['innerText']}' center=({m['center']['x']},{m['center']['y']})")

# Try the old locator approach
try:
    page.locator("button:has-text('SBC')").first.wait_for(state="visible", timeout=3000)
    old_clicked = True
    print("  wait_for: OK")
except Exception as e:
    old_clicked = False
    print(f"  wait_for: FAILED ({str(e)[:50]})")

if old_clicked:
    try:
        page.locator("button:has-text('SBC')").first.click(force=True, timeout=3000)
        print("  click: OK")
    except Exception as e:
        print(f"  click: FAILED ({str(e)[:50]})")

time.sleep(3)
body_after = _js(page, "document.body.innerText.substring(0, 100)")
print(f"  Body after: {repr(body_after[:80])}")
is_sbc = "全部" in body_after and "升级" in body_after
print(f"  SBC loaded: {is_sbc}")

if is_sbc:
    print("  => OLD locator method WORKED")
else:
    print("  => OLD locator method FAILED")

# Go back to Home for the next test
go_home()

# --- Test 2: New coordinate-based click ---
print("\n=== Test 2: click_nav_by_text (coordinate-based) ===")
from src.utils import click_nav_by_text
click_nav_by_text(page, "SBC")
time.sleep(3)
body_after = _js(page, "document.body.innerText.substring(0, 100)")
print(f"  Body after: {repr(body_after[:80])}")
is_sbc = "全部" in body_after and "升级" in body_after
print(f"  SBC loaded: {is_sbc}")
print(f"  => {'Coordinate method WORKED' if is_sbc else 'Coordinate method FAILED'}")

# --- Test 3: EC what did Playwright actually compute? ---
print("\n=== Test 3: What coordinates does Playwright use? ===")
go_home()
time.sleep(2)

# Get the locator's internal element handle and check its bounding box
locator = page.locator("button:has-text('SBC')").first
try:
    box = locator.bounding_box(timeout=3000)
    print(f"  Playwright bounding_box: {box}")
    if box:
        pw_center_x = box['x'] + box['width']/2
        pw_center_y = box['y'] + box['height']/2
        print(f"  Playwright center: ({pw_center_x:.0f}, {pw_center_y:.0f})")

        # Now get our own coordinates
        our_coords = _js(page, """function() {
            var nav = document.querySelector('nav.ut-tab-bar');
            var btns = nav.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if ((btns[i].innerText || '').trim() === 'SBC' && btns[i].offsetParent !== null) {
                    btns[i].scrollIntoView({block: 'center'});
                    var r = btns[i].getBoundingClientRect();
                    return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
                }
            }
            return null;
        }()""")
        print(f"  Our coordinates: ({our_coords[0]}, {our_coords[1]})")

        diff_x = abs(pw_center_x - our_coords[0])
        diff_y = abs(pw_center_y - our_coords[1])
        print(f"  Difference: ({diff_x:.0f}, {diff_y:.0f}) pixels")

        if diff_x < 1 and diff_y < 1:
            print("  => Coordinates MATCH, issue is elsewhere")
        else:
            print("  => Coordinates DIFFER! Playwright computes different center!")
except Exception as e:
    print(f"  bounding_box failed: {str(e)[:50]}")

p.stop()
