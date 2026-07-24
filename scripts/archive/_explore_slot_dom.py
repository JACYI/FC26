# -*- coding: utf-8 -*-
"""Deep DOM exploration: filled slot structure and click targets."""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.login import connect, navigate_to_ea
from src.utils import wait_for_page

LOG = os.path.join(os.path.dirname(__file__), "_slot_dom.txt")
def log(msg=""):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

p, browser, page = connect()
if not page:
    log("Failed to connect")
    sys.exit(1)

page.set_viewport_size({"width": 1280, "height": 900})
time.sleep(1)
navigate_to_ea(page)

from src.sbc.executor import SBCExecutor
executor = SBCExecutor(page)

# Navigate SBC > 升级 via JS
log("[NAV] SBC...")
page.evaluate("""function() {
    var btns = document.querySelectorAll('button.ut-tab-bar-item');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').indexOf('SBC') >= 0) btns[i].click();
    }
}()""")
time.sleep(3)
log("[NAV] 升级...")
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').indexOf('升级') >= 0) btns[i].click();
    }
}()""")
time.sleep(3)

# Click 每日青铜升级
log("[NAV] 每日青铜升级...")
page.evaluate("""function() {
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var t = all[i].innerText || '';
        if (t.indexOf('每日青铜') >= 0) { all[i].click(); return; }
    }
}()""")
time.sleep(3)

body = page.inner_text("body")
if "个 SBC" in body and "提交" not in body:
    log("-> Segment list...")
    page.locator(".ut-sbc-set-tile-view").first.click(force=True, timeout=5000)
    time.sleep(3)
    wait_for_page(page, timeout=10)

# FSU fill
log("[FSU] Filling...")
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = btns[i].innerText || '';
        if (t.indexOf('一键填充') >= 0) { btns[i].click(); return; }
    }
}()""")
time.sleep(5)

# === PART 1: DEEP DOM ANALYSIS of a filled slot ===
log("\n=== SLOT DOM STRUCTURE ===")
slot_dom = page.evaluate("""function() {
    var slot = document.querySelector('.ut-squad-slot-view[index="0"]');
    if (!slot) return 'no slot';

    var r = {
        tag: slot.tagName,
        class: slot.className.substring(0, 120),
        index: slot.getAttribute('index'),
        childCount: slot.children.length,
        children: []
    };

    for (var i = 0; i < slot.children.length; i++) {
        var c = slot.children[i];
        var cr = c.getBoundingClientRect();
        var child = {
            i: i, tag: c.tagName, class: (c.className || '').substring(0, 120),
            visible: c.offsetParent !== null,
            cx: Math.round(cr.left + cr.width/2), cy: Math.round(cr.top + cr.height/2),
            w: Math.round(cr.width), h: Math.round(cr.height),
            kids: c.querySelectorAll('*').length,
            text: (c.innerText || '').trim().substring(0, 80)
        };
        r.children.push(child);
    }

    // Find ALL elements with pointer cursor or click handlers
    var all = slot.querySelectorAll('*');
    r.clickTargets = [];
    for (var i = 0; i < all.length; i++) {
        var style = window.getComputedStyle(all[i]);
        var cr = all[i].getBoundingClientRect();
        if ((style.cursor === 'pointer' || all[i].onclick || all[i].getAttribute('onclick') || all[i].tagName === 'BUTTON' || all[i].getAttribute('role') === 'button') && cr.width > 0 && cr.height > 0) {
            r.clickTargets.push({
                tag: all[i].tagName,
                class: (all[i].className || '').substring(0, 60),
                text: (all[i].innerText || '').trim().substring(0, 30),
                cx: Math.round(cr.left + cr.width/2),
                cy: Math.round(cr.top + cr.height/2),
                w: Math.round(cr.width), h: Math.round(cr.height)
            });
        }
    }

    // Player card
    var card = slot.querySelector('.small.player.item.ut-item-loaded:not(.fsu-cards)');
    if (card) {
        var car = card.getBoundingClientRect();
        r.playerCard = {
            class: card.className.substring(0, 120),
            cx: Math.round(car.left + car.width/2), cy: Math.round(car.top + car.height/2),
            w: Math.round(car.width), h: Math.round(car.height)
        };
    }

    return r;
}()""")
log(json.dumps(slot_dom, indent=2, ensure_ascii=False, default=str))

# === PART 2: Try clicking different targets and observe results ===
log("\n=== CLICK TEST: Different targets ===")

def try_click(label, cx, cy, wait=3):
    log(f"\n[CLICK] {label} at ({cx},{cy})...")
    page.mouse.click(cx, cy)
    time.sleep(wait)
    # Check what appeared
    result = page.evaluate("""function() {
        var info = {};
        var dlg = document.querySelector('.view-modal-container.form-modal');
        info.dialog = dlg && dlg.offsetParent !== null ? (dlg.innerText || '').substring(0, 200) : null;
        var detail = document.querySelector('.ut-split-view.sidebar-right');
        if (detail && detail.offsetParent !== null) {
            info.detailPanel = (detail.innerText || '').substring(0, 300);
        }
        // All visible buttons on right side
        var allBtnTexts = [];
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].offsetParent !== null) {
                var t = (btns[i].innerText || '').trim();
                if (t && t.length < 40) allBtnTexts.push(t);
            }
        }
        info.buttons = allBtnTexts;
        return info;
    }()""")
    log(f"  Dialog: {result.get('dialog', 'none')[:100]}")
    if result.get('detailPanel'):
        log(f"  Detail: {result['detailPanel'][:200]}")
    return result

# Reset by re-doing FSU fill (in case previous click changed state)
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = btns[i].innerText || '';
        if (t.indexOf('一键填充') >= 0) { btns[i].click(); return; }
    }
}()""")
time.sleep(5)

# Test 1: Click player CARD body (not the × button)
card = page.evaluate("""function() {
    var slot = document.querySelector('.ut-squad-slot-view[index="0"]');
    var card = slot.querySelector('.small.player.item.ut-item-loaded:not(.fsu-cards)');
    if (!card) return null;
    var r = card.getBoundingClientRect();
    return {cx: Math.round(r.left + r.width/2), cy: Math.round(r.top + r.height/2), w: Math.round(r.width), h: Math.round(r.height)};
}()""")
if card:
    result1 = try_click("player card center", card['cx'], card['cy'])

# Test 2: Click the pedestal area (bottom part of slot)
pedestal = page.evaluate("""function() {
    var slot = document.querySelector('.ut-squad-slot-view[index="0"]');
    var r = slot.getBoundingClientRect();
    // Bottom center = pedestal area
    return {cx: Math.round(r.left + r.width/2), cy: Math.round(r.top + r.height - 10)};
}()""")
result2 = try_click("pedestal bottom", pedestal['cx'], pedestal['cy'])

# Re-fill, then Test 3: Click top-right corner of slot (the × button area)
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = btns[i].innerText || '';
        if (t.indexOf('一键填充') >= 0) { btns[i].click(); return; }
    }
}()""")
time.sleep(5)
slot_rect = page.evaluate("""function() {
    var slot = document.querySelector('.ut-squad-slot-view[index="0"]');
    var r = slot.getBoundingClientRect();
    return {cx: Math.round(r.left + r.width/2), cy: Math.round(r.top + r.height/2), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height)};
}()""")
# Top-right area (× button location)
result3 = try_click("top-right (× area)", slot_rect['right'] - 15, slot_rect['top'] + 15)

log("\n[DONE] Full log saved.")
