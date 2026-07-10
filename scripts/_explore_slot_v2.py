# -*- coding: utf-8 -*-
"""Explore slot DOM after FSU fill in TOTS Crafting Upgrade."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.login import connect, navigate_to_ea, launch_chrome

LOG = os.path.join(os.path.dirname(__file__), "_slot_v2.txt")
def log(msg=""):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    safe = msg.encode("ascii", errors="replace").decode("ascii")
    print(safe)

log("[LAUNCH] Starting Chrome...")
if not launch_chrome():
    log("  Failed")
    sys.exit(1)
time.sleep(2)

p, browser, page = connect()
page.set_viewport_size({"width": 1280, "height": 900})
time.sleep(1)
navigate_to_ea(page)

# === NAV: SBC > Upgrades tab ===
log("[NAV] SBC...")
page.locator("button.ut-tab-bar-item.icon-sbc").first.click(force=True, timeout=5000)
time.sleep(4)

log("[NAV] 升级 tab (evaluate + indexOf)...")
page.evaluate("""function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = btns[i].innerText || '';
        if (t.indexOf('升级') >= 0 && btns[i].offsetParent !== null) btns[i].click();
    }
}()""")
time.sleep(4)

# === Click TOTS 制作升级 tile ===
log("[NAV] TOTS 制作升级 tile...")
page.evaluate("""function() {
    var tiles = document.querySelectorAll('[class*=tile], [class*=Tile]');
    for (var i = 0; i < tiles.length; i++) {
        var t = tiles[i].innerText || '';
        if (t.indexOf('TOTS 制作升级') >= 0 && tiles[i].offsetParent !== null) {
            tiles[i].click(); return;
        }
    }
}()""")
time.sleep(4)

body = page.inner_text("body")
log("After tile click: %d chars" % len(body))
log("  Submit= %s" % ("提交" in body))
log("  AutoFill= %s" % ("一键填充" in body))
log("  QuickDone= %s" % ("一键完成" in body))
log("  FSU= %s" % ("【FSU】" in body))

if "提交" not in body:
    log("[FAIL] Not on squad builder")
    with open("_debug_page.txt", "w", encoding="utf-8") as f:
        f.write(body)
    sys.exit(1)

# === FSU: 一键填充 ===
log("[FSU] Finding fill buttons...")
btns = page.evaluate("""function() {
    var btns = document.querySelectorAll("button");
    var r = [];
    for (var i = 0; i < btns.length; i++) {
        if (btns[i].offsetParent !== null) {
            var t = (btns[i].innerText || "").trim();
            if (t) r.push(t.substring(0, 30));
        }
    }
    return r;
}()""")
for b in btns:
    log("  btn: %s" % b)

if "一键填充" in btns:
    log("[FSU] Clicking 一键填充...")
    page.evaluate("""function() {
        var btns = document.querySelectorAll("button");
        for (var i = 0; i < btns.length; i++) {
            if ((btns[i].innerText || "").indexOf("一键填充") >= 0) btns[i].click();
        }
    }()""")
    time.sleep(5)
elif "一键完成" in btns:
    log("[FSU] Clicking 一键完成...")
    page.evaluate("""function() {
        var btns = document.querySelectorAll("button");
        for (var i = 0; i < btns.length; i++) {
            if ((btns[i].innerText || "").indexOf("一键完成") >= 0) btns[i].click();
        }
    }()""")
    time.sleep(5)

# Check slots
slots = page.evaluate("""function() {
    var views = document.querySelectorAll("[class*=slot], [class*=Slot]");
    var r = {total: 0, filled: 0, items: []};
    for (var i = 0; i < views.length; i++) {
        var cr = views[i].getBoundingClientRect();
        if (cr.width > 50 && cr.height > 50 && cr.left > 0 && cr.top > 50) {
            r.total++;
            var card = views[i].querySelector("[class*=player], [class*=Player]");
            if (card) r.filled++;
            r.items.push({
                class: (views[i].className || "").substring(0, 60),
                cx: Math.round(cr.left + cr.width/2),
                cy: Math.round(cr.top + cr.height/2),
                w: Math.round(cr.width), h: Math.round(cr.height)
            });
        }
    }
    return r;
}()""")
log("\nSlots: %s" % json.dumps(slots, ensure_ascii=False))

# Find player cards
players = page.evaluate("""function() {
    var cards = document.querySelectorAll("[class*=player i]");
    var r = [];
    for (var i = 0; i < cards.length; i++) {
        var cr = cards[i].getBoundingClientRect();
        if (cr.width > 30 && cr.height > 30 && cr.left > 0 && cr.top > 50) {
            r.push({
                class: (cards[i].className || "").substring(0, 80),
                cx: Math.round(cr.left + cr.width/2),
                cy: Math.round(cr.top + cr.height/2),
                w: Math.round(cr.width), h: Math.round(cr.height)
            });
        }
    }
    return r;
}()""")
log("\nPlayer cards: %d" % len(players))
for p in players[:5]:
    log("  [%s] at (%d, %d) %dx%d" % (p["class"].split()[-1] if p["class"].split() else "?", p["cx"], p["cy"], p["w"], p["h"]))

# === Click first player card ===
if players:
    p = players[0]
    log("\n=== Clicking player card at (%d, %d) ===" % (p["cx"], p["cy"]))
    page.mouse.click(p["cx"], p["cy"])
    time.sleep(3)

    result = page.evaluate("""function() {
        var r = {};
        var dlg = document.querySelector(".view-modal-container.form-modal");
        r.dialog = dlg && dlg.offsetParent !== null ? (dlg.innerText || "").substring(0, 400) : null;
        var right = document.querySelector(".ut-split-view.sidebar-right");
        r.rightPanel = right && right.offsetParent !== null ? (right.innerText || "").substring(0, 500) : null;
        var btns = document.querySelectorAll("button");
        r.buttons = [];
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].offsetParent !== null) {
                var t = (btns[i].innerText || "").trim();
                if (t) r.buttons.push(t.substring(0, 30));
            }
        }
        var all = document.querySelectorAll("*");
        r.replacementText = [];
        for (var i = 0; i < all.length; i++) {
            var t = all[i].innerText || "";
            var keywords = ["替换", "同评分", "满足需求", "交换", "替代", "换人", "选择球员", "更换"];
            for (var k = 0; k < keywords.length; k++) {
                if (t.indexOf(keywords[k]) >= 0 && all[i].offsetParent !== null) {
                    var rect = all[i].getBoundingClientRect();
                    r.replacementText.push({
                        text: t.substring(0, 80),
                        cx: Math.round(rect.left + rect.width/2),
                        cy: Math.round(rect.top + rect.height/2)
                    });
                    break;
                }
            }
        }
        // FSU specific panels
        var fsu = document.querySelectorAll("[class*=fsu], [class*=FSU]");
        r.fsuVisible = [];
        for (var i = 0; i < fsu.length; i++) {
            if (fsu[i].offsetParent !== null) {
                var ft = (fsu[i].innerText || "").trim();
                if (ft) r.fsuVisible.push(ft.substring(0, 100));
            }
        }
        return r;
    }()""")
    log("\n=== After card click ===")
    log(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    with open("_after_card_click.txt", "w", encoding="utf-8") as f:
        f.write(page.inner_text("body"))

    # Try replacement if found
    repl = result.get("replacementText", [])
    if repl:
        log("\n=== Trying %d replacement option(s) ===" % len(repl))
        for opt in repl[:3]:
            log("  Clicking: %s" % opt["text"][:40])
            page.mouse.click(opt["cx"], opt["cy"])
            time.sleep(3)
            body2 = page.inner_text("body")
            log("  After: Submit=%s, AutoFill=%s" % ("提交" in body2, "一键填充" in body2))
        with open("_after_replacement.txt", "w", encoding="utf-8") as f:
            f.write(page.inner_text("body"))
    else:
        log("\nNo replacement options found")
else:
    log("[WARN] No player cards found")

log("\n[DONE]")
