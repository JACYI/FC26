# -*- coding: utf-8 -*-
"""Capture specific parts with Playwright native clicks."""
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

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]
page.wait_for_load_state("networkidle")

# 1. SBC Upgrades tab
print("=== SBC Upgrades ===")
page.locator("button.ut-tab-bar-item span:text('SBC')").click()
time.sleep(4)
page.wait_for_load_state("networkidle")

# Get SBC sub-navigation HTML
subnav = page.evaluate("""() => {
    // Find the SBC sub-tabs (category filter area)
    var cats = document.querySelectorAll('[class*="category"], [class*="subfilter"], [class*="tab"]');
    return Array.from(cats).filter(function(el) {
        return el.offsetParent !== null && el.querySelectorAll('button').length > 0;
    }).map(function(el) {
        var btns = el.querySelectorAll('button');
        return {
            container: el.className.substring(0, 100),
            buttons: Array.from(btns).filter(function(b) { return b.offsetParent !== null; }).map(function(b) {
                return { text: (b.innerText || '').trim(), classes: b.className.substring(0, 60) };
            })
        };
    });
}""")
save_json("sbc_subnav.json", subnav)

# Try clicking each possible tab label
tab_found = None
for label in ["升级", "Upgrades", "所有", "All"]:
    tb = page.locator(f"button:text-is('{label}')")
    if tb.count() > 0:
        tb.click()
        tab_found = label
        print(f"  Clicked tab: {label}")
        break
    # Try contains match
    tb = page.locator(f"button:has-text('{label}')")
    if tb.count() > 0:
        tb.first.click()
        tab_found = label
        print(f"  Clicked tab (contains): {label}")
        break

if not tab_found:
    print("  No standard tab found, listing all buttons...")
    all_btns = page.evaluate("""() => {
        var btns = Array.from(document.querySelectorAll('button')).filter(function(b) { return b.offsetParent !== null; });
        return btns.map(function(b) { return { text: (b.innerText || '').trim(), classes: b.className.substring(0, 80) }; });
    }""")
    save_json("sbc_all_buttons.json", all_btns)
else:
    time.sleep(4)
    page.wait_for_load_state("networkidle")
    save("sbc_upgrades_v2.txt", page.inner_text("body"))

# 2. SBC Squad Builder
print("\n=== SBC Squad Builder Check ===")
# Go into any available SBC to see squad builder
page.evaluate("""() => {
    var items = document.querySelectorAll('.ut-tab-bar-item');
    for (var i = 0; i < items.length; i++) {
        if ((items[i].innerText || '').trim() === 'SBC') {
            items[i].click(); return;
        }
    }
}""")
time.sleep(3)
page.wait_for_load_state("networkidle")

# Click the first available foundation/upgrade SBC
sbc_entered = page.evaluate("""() => {
    var tiles = document.querySelectorAll('[class*="tile"], [class*="set"], .ut-sbc-set-tile-view');
    for (var i = 0; i < tiles.length; i++) {
        if (tiles[i].offsetParent !== null) {
            var text = (tiles[i].innerText || '').trim();
            if (text.length > 0) {
                tiles[i].click();
                return text.substring(0, 100);
            }
        }
    }
    return 'none';
}""")
print(f"  Clicked SBC tile: {sbc_entered}")
time.sleep(4)
page.wait_for_load_state("networkidle")
save("sbc_tile_entry.txt", page.inner_text("body"))

# Check for "开始挑战" or "Start Challenge" button
clicked_challenge = page.evaluate("""() => {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if ((t.indexOf('开始') >= 0 || t.indexOf('Start') >= 0 || t.indexOf('Challenge') >= 0) && btns[i].offsetParent !== null) {
            btns[i].click();
            return t;
        }
    }
    return 'none';
}""")
print(f"  Clicked challenge: {clicked_challenge}")
time.sleep(5)
page.wait_for_load_state("networkidle")
save("sbc_squad_builder.txt", page.inner_text("body"))

# Check FSU cards in squad builder
sq_info = page.evaluate("""() => {
    return {
        fsuCards: document.querySelectorAll('.fsu-cards').length,
        fsuRating: document.querySelectorAll('.fsu-cards-rating').length,
        fsuButtons: Array.from(document.querySelectorAll('button')).filter(function(b) {
            return (b.innerText || '').indexOf('FSU') >= 0 || (b.innerText || '').indexOf('一键') >= 0;
        }).map(function(b) { return { text: (b.innerText || '').trim().substring(0, 40), visible: b.offsetParent !== null }; }),
        hasSubmit: document.body.innerText.indexOf('提交') >= 0,
        hasFSU: document.body.innerText.indexOf('FSU') >= 0,
    };
}""")
save_json("squad_builder_fsu.json", sq_info)
print(f"  Squad builder FSU state: {json.dumps(sq_info, ensure_ascii=False)}")

# 3. Check FSU events.info.build from the userscript context
print("\n=== FSU Config State ===")
fsu_config = page.evaluate("""() => {
    try {
        // Try to access FSU internal state through GM_setValue in localStorage
        var fsuState = {};
        // Check localStorage for FSU settings
        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            if (key.indexOf('fsu') >= 0 || key.indexOf('FSU') >= 0 || key.indexOf('_') >= 0) {
                try {
                    fsuState[key] = JSON.parse(localStorage.getItem(key));
                } catch(e) {
                    fsuState[key] = localStorage.getItem(key).substring(0, 200);
                }
            }
        }
        return fsuState;
    } catch(e) {
        return { error: e.message };
    }
}""")
save_json("fsu_localstorage.json", fsu_config)

# 4. Try to check what UTItemViewFactory.createLargeItem returns
print("\n=== Item View Factory ===")
factory_info = page.evaluate("""() => {
    var info = {};
    if (typeof UTItemViewFactory !== 'undefined') {
        info.UTItemViewFactory = {
            methods: Object.getOwnPropertyNames(UTItemViewFactory).filter(function(m) { return m.indexOf('create') >= 0; }),
        };
        if (UTItemViewFactory.createLargeItem) {
            info.createLargeItemSource = (UTItemViewFactory.createLargeItem + '').substring(0, 2000);
        }
        if (UTItemViewFactory.createItem) {
            info.createItemSource = (UTItemViewFactory.createItem + '').substring(0, 2000);
        }
        // List all classes that have 'ItemView' in them
        info.itemViewClasses = [];
        for (var key in window) {
            if (key.indexOf('ItemView') >= 0 && key.indexOf('prototype') < 0) {
                info.itemViewClasses.push(key);
            }
        }
    }
    return info;
}""")
save_json("item_factory.json", factory_info)

p.stop()
print("\nDone!")
