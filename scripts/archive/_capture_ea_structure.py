# -*- coding: utf-8 -*-
"""Capture EA FC 26 Web App page structure for optimization reference."""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.utils import _js
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
print("EA FC 26 - Page Structure Capture")
print("=" * 60)

# Connect
print("\n[1] Connecting to Chrome CDP...")
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]
page.wait_for_load_state("networkidle")
print(f"  URL: {page.url[:100]}")

# Capture state
print("\n[2] Capturing current state...")
save_json("00_state.json", {
    "url": page.url,
    "title": page.title(),
    "state": page.evaluate("() => { var t = document.body.innerText || ''; if(t.indexOf('登录') >=0 || t.indexOf('Sign In') >=0) return 'login_page'; if(t.indexOf('SBC') >=0 || t.indexOf('俱乐部') >=0) return 'logged_in'; return 'unknown'; }"),
})
body_text = page.inner_text("body")
save("00_body.txt", body_text[:15000])

# Nav + UI structure
print("\n[3] Capturing navigation and UI...")
nav_info = _js(page, """() => {
    var btns = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null);
    return {
        visibleButtons: btns.map(b => ({
            text: (b.innerText || '').trim().substring(0, 60),
            classes: b.className.substring(0, 80),
        })),
        buttonCount: btns.length,
    };
}""")
save_json("01_nav.json", nav_info)

# FSU state
print("\n[4] Capturing FSU DOM state...")
fsu_dom = _js(page, """() => {
    return {
        fsuElements: document.querySelectorAll('[class*="fsu"]').length,
        fsuButtons: Array.from(document.querySelectorAll('button')).filter(b =>
            (b.innerText || '').includes('FSU') ||
            (b.innerText || '').includes('一键') ||
            (b.innerText || '').includes('填充') ||
            (b.innerText || '').includes('补全')
        ).map(b => ({
            text: (b.innerText || '').trim().substring(0, 50),
            visible: b.offsetParent !== null,
        })),
        fsuCards: document.querySelectorAll('.fsu-cards').length,
    };
}""")
save_json("02_fsu_dom.json", fsu_dom)

# SBC > Upgrades
print("\n[5] Navigating to SBC > Upgrades...")
try:
    _js(page, """() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if ((btns[i].innerText || '').indexOf('SBC') >= 0 && btns[i].offsetParent !== null) {
                btns[i].click(); return true;
            }
        } return false;
    }""")
    time.sleep(5)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Click Upgrades tab
    _js(page, """() => {
        var btns = document.querySelectorAll('button, a');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim();
            if ((t === 'Upgrades' || t === '升级') && btns[i].offsetParent !== null) {
                btns[i].click(); return t;
            }
        } return 'not_found';
    }""")
    time.sleep(4)
    page.wait_for_load_state("networkidle", timeout=15000)
    save("10_sbc_upgrades.txt", page.inner_text("body"))
    print("  SBC Upgrades captured")
except Exception as e:
    print(f"  SBC nav error: {e}")

# Club > Players
print("\n[6] Navigating to Club > Players...")
try:
    _js(page, """() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if ((btns[i].innerText || '').indexOf('Club') >= 0 && btns[i].offsetParent !== null) {
                btns[i].click(); return true;
            }
        } return false;
    }""")
    time.sleep(4)
    page.wait_for_load_state("networkidle", timeout=15000)

    _js(page, """() => {
        var btns = document.querySelectorAll('button, a');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim();
            if ((t === 'Players' || t === '球员') && btns[i].offsetParent !== null) {
                btns[i].click(); return true;
            }
        } return false;
    }""")
    time.sleep(4)
    page.wait_for_load_state("networkidle", timeout=15000)
    save("20_club_players.txt", page.inner_text("body"))

    # Player card HTML structure
    card_html = _js(page, """() => {
        var items = document.querySelectorAll('.listFUTItem');
        for (var i = 0; i < items.length; i++) {
            if (items[i].offsetParent !== null) {
                return items[i].outerHTML.substring(0, 3000);
            }
        } return 'no visible items';
    }""")
    save("21_card_html.txt", str(card_html))
    print("  Club Players captured")
except Exception as e:
    print(f"  Club nav error: {e}")

# View classes (pack, player item)
print("\n[7] Capturing view class hierarchy...")
view_classes = _js(page, """() => {
    var info = {};
    if (typeof UTPackAnimationViewController !== 'undefined') {
        info.UTPackAnimationViewController = {
            methods: Object.getOwnPropertyNames(UTPackAnimationViewController.prototype).filter(m => m[0] !== '_'),
        };
    } else {
        info.UTPackAnimationViewController = 'not found';
    }
    if (typeof UTPlayerItemView !== 'undefined') {
        info.UTPlayerItemView = {
            methods: Object.getOwnPropertyNames(UTPlayerItemView.prototype).filter(m => m[0] !== '_').slice(0, 30),
        };
    } else {
        info.UTPlayerItemView = 'not found';
    }
    if (typeof UTSquadBuilderViewController !== 'undefined') {
        info.UTSquadBuilderViewController = {
            methods: Object.getOwnPropertyNames(UTSquadBuilderViewController.prototype).filter(m => m[0] !== '_').slice(0, 20),
        };
    } else {
        info.UTSquadBuilderViewController = 'not found';
    }
    // Check if pack animation uses UTPlayerItemView
    if (typeof UTPackAnimationView !== 'undefined') {
        info.UTPackAnimationView = {
            methods: Object.getOwnPropertyNames(UTPackAnimationView.prototype).filter(m => m[0] !== '_'),
        };
    }
    // Grab FSU events.info.build state
    if (typeof info !== 'undefined' && info.build) {
        info.FSU_build = info.build;
    }
    if (typeof info !== 'undefined' && info.set) {
        info.FSU_set = info.set;
    }
    return info;
}""")
save_json("30_view_classes.json", view_classes)

# Check the FSU rating display in current cards
print("\n[8] Checking FSU rating display on current cards...")
rating_check = _js(page, """() => {
    var ratings = document.querySelectorAll('.fsu-cards-rating');
    var results = [];
    ratings.forEach(function(el) {
        results.push({
            text: el.textContent,
            visible: el.offsetParent !== null,
            parent: el.parentElement ? el.parentElement.className.substring(0, 60) : null,
        });
    });
    return { count: ratings.length, items: results.slice(0, 10) };
}""")
save_json("31_rating_display.json", rating_check)

p.stop()
print(f"\nAll data saved to: {OUTPUT_DIR}")
