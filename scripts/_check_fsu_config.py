# -*- coding: utf-8 -*-
"""Check FSU config switch states."""
import sys, os, time, json
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

from src.utils import click_sbc_nav, navigate_sbc_category, open_sbc_squad_builder, _js

# Navigate to SBC > 升级
print("Navigating to SBC > 升级...")
click_sbc_nav(page)
time.sleep(4)
r = navigate_sbc_category(page, "升级", 2)
print(f"  {r}")
time.sleep(2)

# Enter 每日青铜升级 to get to squad builder (cheapest to enter)
print("Entering 每日青铜升级...")
r = open_sbc_squad_builder(page, "每日青铜升级")
print(f"  {r}")
time.sleep(3)

# Check if FSU dialog is present
body = _js(page, "document.body.innerText.substring(0, 500)")
print(f"\nBody: {body[:200]}")

# Open FSU config
has_config_btn = _js(page, """function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').indexOf('排除球员配置') >= 0 && btns[i].offsetParent !== null) {
            btns[i].scrollIntoView({block: 'center'});
            var r = btns[i].getBoundingClientRect();
            return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
        }
    }
    return null;
}()""")
print(f"\n排除球员配置 button: {'found' if has_config_btn else 'NOT FOUND'}")

if has_config_btn:
    page.mouse.click(has_config_btn[0], has_config_btn[1])
    time.sleep(2)

    # Read toggle states
    toggles = _js(page, """function() {
        var labels = document.querySelectorAll('.ut-toggle-cell-view--label');
        var results = [];
        for (var i = 0; i < labels.length; i++) {
            var text = (labels[i].innerText || '').trim();
            var cell = labels[i].closest('.ut-toggle-cell-view');
            var toggle = cell ? cell.querySelector('.ut-toggle-control') : null;
            var isOn = toggle ? toggle.classList.contains('toggled') : '?';
            results.push(text + ' = ' + (isOn ? 'ON' : 'OFF'));
        }
        return results;
    }()""")
    print("\nFSU Config switches:")
    for t in toggles:
        print(f"  {t}")

    # Close FSU config
    close_btn = _js(page, """function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if ((btns[i].innerText || '').trim() === '关闭' && btns[i].offsetParent !== null) {
                var r = btns[i].getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }
        }
        return null;
    }()""")
    if close_btn:
        page.mouse.click(close_btn[0], close_btn[1])
        time.sleep(1)
        print("  Config closed")
else:
    print("  Cannot open FSU config - no button found")

p.stop()
