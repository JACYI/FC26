# -*- coding: utf-8 -*-
"""Capture EA Web App - v2 with proper nav handling."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ea_structure")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(name, content):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved {name}")

def save_json(name, data):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {name}")

print("=" * 60)
print("EA FC 26 - Page Structure Capture v2")
print("=" * 60)

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]
page.wait_for_load_state("networkidle")
print(f"URL: {page.url[:80]}")

# 1. Navigate to SBC
print("\n[1] SBC page + sub-tab structure...")
page.evaluate("""() => {
    var items = document.querySelectorAll('.ut-tab-bar-item');
    for (var i = 0; i < items.length; i++) {
        if ((items[i].innerText || '').trim() === 'SBC' && items[i].offsetParent !== null) {
            items[i].click(); return true;
        }
    } return false;
}""")
time.sleep(5)
page.wait_for_load_state("networkidle")
save("sbc_main.txt", page.inner_text("body"))

tabs_html = page.evaluate("""() => {
    var tabs = document.querySelectorAll('[class*="subfilter"], [class*="tab"], [class*="category"]');
    return Array.from(tabs).filter(t => t.offsetParent !== null && (t.innerText || '').trim().length > 0)
        .map(t => ({ tag: t.tagName, text: (t.innerText || '').trim().substring(0, 50), classes: t.className.substring(0, 80), html: t.outerHTML.substring(0, 300) }));
}""")
save_json("sbc_tabs.json", tabs_html)

# Try each tab label
for tab_name in ["升级", "Upgrades"]:
    clicked = page.evaluate("""(text) => {
        var all = document.querySelectorAll('button, a, [class*="tab"], [class*="category"], [class*="subfilter"]');
        for (var i = 0; i < all.length; i++) {
            var t = (all[i].innerText || '').trim();
            if (t === text && all[i].offsetParent !== null) {
                all[i].click(); return true;
            }
        } return false;
    }""", tab_name)
    if clicked:
        print(f"  Clicked tab: {tab_name}")
        break
time.sleep(4)
page.wait_for_load_state("networkidle")
save("sbc_upgrades.txt", page.inner_text("body"))

# 2. Squad builder - check FSU overlay
print("\n[2] Checking squad builder FSU state...")
# Go back to SBC main first
page.evaluate("""() => {
    var items = document.querySelectorAll('.ut-tab-bar-item');
    for (var i = 0; i < items.length; i++) {
        if ((items[i].innerText || '').trim() === 'SBC' && items[i].offsetParent !== null) {
            items[i].click(); return true;
        }
    } return false;
}""")
time.sleep(4)
page.wait_for_load_state("networkidle")

squad_info = page.evaluate("""() => {
    var info = {};
    info.visibleText = (document.body.innerText || '').substring(0, 500);
    var btns = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null);
    info.buttons = btns.map(b => ({ text: (b.innerText || '').trim().substring(0, 40) }));
    info.fsuCards = document.querySelectorAll('.fsu-cards').length;
    info.fsuRating = document.querySelectorAll('.fsu-cards-rating').length;
    return info;
}""")
save_json("sbc_home.json", squad_info)

# 3. Club page
print("\n[3] Club > Players...")
page.evaluate("""() => {
    var items = document.querySelectorAll('.ut-tab-bar-item');
    for (var i = 0; i < items.length; i++) {
        if ((items[i].innerText || '').trim() === '俱乐部' && items[i].offsetParent !== null) {
            items[i].click(); return true;
        }
    } return false;
}""")
time.sleep(4)
page.wait_for_load_state("networkidle")
save("club_main.txt", page.inner_text("body"))

for tab_name in ["球员", "Players"]:
    clicked = page.evaluate("""(text) => {
        var all = document.querySelectorAll('button, a, [class*="tab"]');
        for (var i = 0; i < all.length; i++) {
            var t = (all[i].innerText || '').trim();
            if (t === text && all[i].offsetParent !== null) {
                all[i].click(); return true;
            }
        } return false;
    }""", tab_name)
    if clicked:
        print(f"  Clicked tab: {tab_name}")
        break
time.sleep(4)
page.wait_for_load_state("networkidle")
save("club_players.txt", page.inner_text("body"))

card_info = page.evaluate("""() => {
    var items = document.querySelectorAll('.listFUTItem');
    for (var i = 0; i < items.length; i++) {
        if (items[i].offsetParent !== null) {
            return {
                html: items[i].outerHTML.substring(0, 3000),
                fsuCards: items[i].querySelectorAll('.fsu-cards').length,
                fsuRating: items[i].querySelectorAll('.fsu-cards-rating').length
            };
        }
    }
    return { html: 'none', fsuCards: 0, fsuRating: 0 };
}""")
save_json("player_card.json", card_info)

# 4. Pack view and class details
print("\n[4] Capturing view class details...")
pack_details = page.evaluate("""() => {
    var info = {};
    if (typeof UTPackAnimationView !== 'undefined') {
        var proto = UTPackAnimationView.prototype;
        info.generateItemSource = proto.generateItem ? proto.generateItem.toString().substring(0, 1500) : 'no source';
    }
    if (typeof UTPackAnimationViewController !== 'undefined') {
        info.runAnimationSource = UTPackAnimationViewController.prototype.runAnimation.toString().substring(0, 2000);
    }
    if (typeof UTPlayerItemView !== 'undefined') {
        info.renderItemSource = (UTPlayerItemView.prototype.renderItem + '').substring(0, 500);
    }
    if (typeof events !== 'undefined' && events.info && events.info.build) {
        info.FSU_build = events.info.build;
    }
    if (typeof events !== 'undefined' && events.info && events.info.set) {
        info.FSU_set = {};
        var keys = ['sbc_autofill', 'sbc_dupfill', 'sbc_squadcmpl', 'sbc_top', 'card_style', 'card_pos', 'card_price', 'card_other', 'card_meta', 'card_low', 'goldenrange'];
        keys.forEach(function(k) { if (k in events.info.set) info.FSU_set[k] = events.info.set[k]; });
    }
    return info;
}""")
save_json("view_details.json", pack_details)

p.stop()
print(f"\nDone! Data in: {OUTPUT_DIR}")
