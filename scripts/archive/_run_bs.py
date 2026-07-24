# -*- coding: utf-8 -*-
"""Run daily bronze + silver SBCs from SBC hub."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
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

from src.utils import navigate_sbc_category, log
from src.sbc.machine import SBCMachine

# Switch to 升级 tab
print("[1/4] Switch to 升级 tab...")
r = navigate_sbc_category(page, "升级", 2)
print(f"  {r}")
time.sleep(3)

# Run state machine
print("[2/4] Running state machine for 每日青铜升级 + 每日白银升级...")
machine = SBCMachine(page, max_cycles=50)
result = machine.run(target_sbcs=["每日青铜升级", "每日白银升级"])

# Report
print(f"\n[3/4] Results:")
print(f"  Completed: {result['completed']}")
print(f"  Failed: {result['failed']}")
print(f"  Cycles: {result['cycles']}")

print(f"\n[4/4] Summary:")
for sbc in ["每日青铜升级", "每日白银升级"]:
    if sbc in result.get("completed", []):
        print(f"  [OK] {sbc}")
    elif sbc in result.get("failed", []):
        print(f"  [FAIL] {sbc}")
    else:
        print(f"  [-] {sbc} (skipped)")

p.stop()
