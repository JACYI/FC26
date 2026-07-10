# -*- coding: utf-8 -*-
"""Fix FSU config: ensure 仅限不可交易球员 = ON."""
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

# Check where we are
body = _js(page, "document.body.innerText.substring(0, 200)")
print(f"Body: {body[:100]}")

is_squad_builder = "排除球员配置" in body
is_sbc_home = "全部" in body and "升级" in body

if not is_squad_builder:
    print("Not in squad builder, navigating...")
    from src.utils import click_sbc_nav, navigate_sbc_category, open_sbc_squad_builder
    click_sbc_nav(page)
    time.sleep(4)
    navigate_sbc_category(page, "升级", 2)
    time.sleep(2)
    open_sbc_squad_builder(page, "每日青铜升级")
    time.sleep(3)

# Open FSU config
print("Open FSU config...")
pos = _js(page, """function() {
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
if pos:
    page.mouse.click(pos[0], pos[1])
    time.sleep(2)
else:
    print("  Config button not found")
    p.stop()
    sys.exit(1)

# Toggle - click the toggle control directly, not the label
print("Toggle 仅限不可交易球员 -> ON...")
result = _js(page, """function() {
    var labels = document.querySelectorAll('.ut-toggle-cell-view--label');
    for (var i = 0; i < labels.length; i++) {
        var el = labels[i];
        if ((el.innerText || '').trim() === '仅限不可交易球员') {
            var cell = el.closest('.ut-toggle-cell-view');
            if (!cell) return 'no cell';
            var toggle = cell.querySelector('.ut-toggle-control');
            if (!toggle) return 'no toggle';
            var isOn = toggle.classList.contains('toggled');
            if (isOn) return 'already_on';
            // Click the toggle control itself
            var r = toggle.getBoundingClientRect();
            return JSON.stringify({x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)});
        }
    }
    return 'label_not_found';
}()""")
print(f"  Toggle pos: {result}")

if result and isinstance(result, str) and result.startswith("{"):
    import json
    pos = json.loads(result)
    page.mouse.click(pos["x"], pos["y"])
    print(f"  Clicked toggle at ({pos['x']}, {pos['y']})")
    time.sleep(1)
else:
    print(f"  No toggle to click: {result}")

# Verify
print("\nVerify daily switches:")
switches = _js(page, """function() {
    var labels = document.querySelectorAll('.ut-toggle-cell-view--label');
    var r = [];
    for (var i = 0; i < labels.length; i++) {
        var text = (labels[i].innerText || '').trim();
        var cell = labels[i].closest('.ut-toggle-cell-view');
        var toggle = cell ? cell.querySelector('.ut-toggle-control') : null;
        var isOn = toggle ? toggle.classList.contains('toggled') : '?';
        if (text === '仅限不可交易球员' || text === '排除指定联赛球员(5)' || text === '优先使用球员仓库球员') {
            r.push(text + ' = ' + (isOn ? 'ON' : 'OFF'));
        }
    }
    return r;
}()""")
for s in switches:
    print(f"  {s}")

# Close
close_pos = _js(page, """function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').trim() === '关闭' && btns[i].offsetParent !== null) {
            var r = btns[i].getBoundingClientRect();
            return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
        }
    }
    return null;
}()""")
if close_pos:
    page.mouse.click(close_pos[0], close_pos[1])
    time.sleep(1)
    print("Config closed")

print("\nDone")
p.stop()
