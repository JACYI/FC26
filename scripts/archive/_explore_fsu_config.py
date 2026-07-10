# -*- coding: utf-8 -*-
"""Read FSU config dialog with proper UTF-8 output."""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True)
try:
    page.wait_for_function('document.body.innerText.indexOf("全部") >= 0', timeout=20000)
except:
    page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True)
    time.sleep(8)
page.locator("text=升级").first.click(force=True)
try:
    page.wait_for_function('document.body.innerText.indexOf("每日青铜升级") >= 0', timeout=15000)
except:
    pass
time.sleep(2)
page.get_by_text("每日青铜升级", exact=False).first.click(force=True)
time.sleep(3)

# Click config button
page.get_by_text("排除球员配置", exact=False).first.click(force=True)
time.sleep(3)

# Read dialog body content
dialog_text = page.evaluate("""
() => {
    const dialog = document.querySelector('.ea-dialog-view--body');
    if (!dialog) return 'no dialog';
    return dialog.innerText;
}
""")

with open("data/fsu_config_labels.txt", "w", encoding="utf-8") as f:
    f.write("=== FSU Config Dialog Labels ===\n")
    f.write(dialog_text)
    f.write("\n\n")

# Also extract each toggle label separately
toggles = page.evaluate("""
() => {
    const results = [];
    const cells = document.querySelectorAll('.ut-toggle-cell-view');
    for (let cell of cells) {
        const label = cell.querySelector('.ut-toggle-cell-view--label');
        const toggle = cell.querySelector('.ut-toggle-control');
        results.push({
            label: label ? label.innerText.trim() : '?',
            isOn: toggle ? toggle.classList.contains('toggled') : false
        });
    }
    return results;
}
""")

with open("data/fsu_config_labels.txt", "a", encoding="utf-8") as f:
    f.write("\n=== Toggle States ===\n")
    for t in toggles:
        f.write(f"  {t['label']:<30} -> {'ON' if t['isOn'] else 'OFF'}\n")

print("Saved to data/fsu_config_labels.txt")
p.stop()
