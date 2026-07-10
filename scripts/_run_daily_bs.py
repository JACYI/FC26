# -*- coding: utf-8 -*-
"""Run daily bronze + silver SBCs. Resets to SBC hub first."""
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

from src.utils import click_sbc_nav, navigate_sbc_category, _js

# Step 1: Reset to SBC hub
print("[1/5] Going to SBC hub...")
click_sbc_nav(page)
time.sleep(5)

# Verify we're on SBC page
body = _js(page, "document.body.innerText.substring(0, 200)")
print(f"  Body: {body[:100]}")

# Step 2: Switch to 升级 tab
print("[2/5] Switching to 升级 tab...")
r = navigate_sbc_category(page, "升级", 2)
print(f"  {r}")
time.sleep(3)

# Step 3: Run state machine for bronze + silver
print("[3/5] Starting state machine...")
from src.sbc.machine import SBCMachine
machine = SBCMachine(page, max_cycles=50)
result = machine.run(target_sbcs=["每日青铜升级", "每日白银升级"])

# Step 4: Report
print(f"\n[4/5] Results:")
print(f"  Completed: {result['completed']}")
print(f"  Failed: {result['failed']}")
print(f"  Cycles: {result['cycles']}")

# Step 5: Summary
print(f"\n[5/5] Summary:")
for sbc in ["每日青铜升级", "每日白银升级"]:
    status = "OK" if sbc in result.get("completed", []) else ("FAILED" if sbc in result.get("failed", []) else "SKIPPED")
    print(f"  [{status}] {sbc}")

p.stop()
