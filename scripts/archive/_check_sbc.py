# -*- coding: utf-8 -*-
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

# Dismiss FSU dialog
for btn_text in ["确定", "OK", "确认"]:
    try:
        btn = page.locator(f"text={btn_text}").first
        if btn.is_visible(timeout=1000):
            btn.click(force=True, timeout=2000)
            time.sleep(1)
    except:
        pass

# Navigate to SBC
nav_btn = page.locator("button.ut-tab-bar-item.icon-sbc")
bbox = nav_btn.bounding_box()
page.mouse.click(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
time.sleep(5)

# Dismiss FSU dialog
for btn_text in ["确定", "OK", "确认"]:
    try:
        btn = page.locator(f"text={btn_text}").first
        if btn.is_visible(timeout=2000):
            btn.click(force=True, timeout=3000)
            time.sleep(1)
    except:
        pass

# Search entire document for element containing TOTS制作升级
targets = page.evaluate("""() => {
    let results = [];
    let all = document.querySelectorAll('*');
    for (let a of all) {
        let t = (a.innerText || '').replace(/\\s+/g, '');
        if (t.indexOf('TOTS制作升级') >= 0) {
            let rect = a.getBoundingClientRect();
            if (rect.width > 20 && rect.height > 20) {
                let centerX = rect.left + rect.width/2;
                let centerY = rect.top + rect.height/2;
                results.push({
                    tag: a.tagName,
                    cls: (a.className || '').substring(0, 80),
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    centerX: Math.round(centerX), centerY: Math.round(centerY),
                    visible: rect.x < window.innerWidth && rect.y < window.innerHeight && rect.x + rect.width > 0 && rect.y + rect.height > 0
                });
            }
        }
    }
    return results;
}""")
print(f"\nFound {len(targets)} elements containing 'TOTS制作升级':")
for t in targets:
    print(f"  {t['tag']}.{t['cls']}")
    print(f"    @({t['x']},{t['y']}) {t['w']}x{t['h']} center=({t['centerX']},{t['centerY']}) visible={t['visible']}")

if targets:
    # Click the largest visible one
    visible = [t for t in targets if t['visible']]
    if visible:
        target = max(visible, key=lambda t: t['w'] * t['h'])
    else:
        target = max(targets, key=lambda t: t['w'] * t['h'])

    cx, cy = target['centerX'], target['centerY']
    print(f"\nClicking largest at ({cx}, {cy})...")
    page.mouse.click(cx, cy)
    time.sleep(5)

    # Check page state
    body = page.inner_text("body")
    with open("data/after_click.txt", "w", encoding="utf-8") as f:
        f.write(body)

    print(f"Contains '提交': {'提交' in body}")
    print(f"Contains 'Submit': {'Submit' in body}")
    print(f"Contains '一键填充': {'一键填充' in body}")
    print(f"Contains 'SBC': {'SBC' in body}")

    slots = page.evaluate("document.querySelectorAll('[class*=\"slot\"], [class*=\"Slot\"]').length")
    print(f"Squad slots: {slots}")

    # Check for squad builder page
    has_squad = page.evaluate("""() => {
        let btnTexts = Array.from(document.querySelectorAll('button')).map(b => (b.innerText || '').trim()).filter(t => t.length > 0);
        return btnTexts;
    }""")
    print("Buttons:", [b for b in has_squad if b])
