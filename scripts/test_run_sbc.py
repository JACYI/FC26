# -*- coding: utf-8 -*-
"""
Test: run one daily SBC to verify the full execution flow.
1. Connect + PageMachine login
2. Navigate SBC > Upgrades
3. Run SBCMachine to execute 每日青铜升级 (once, has 5/5 repeats)
4. Report result
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright
from src.page_machine import PageMachine
from src.page_states import LoggedIn
from src.utils import click_sbc_nav, navigate_sbc_category, log
from src.sbc.machine import SBCMachine

CDP_URL = "http://127.0.0.1:9222"
EMAIL = "3079479814@qq.com"
PASSWORD = "Yyh3079479814"

def print_log(msg):
    print(msg)
    sys.stdout.flush()

print_log("=" * 55)
print_log("FC26 Daily SBC Test Run")
print_log("=" * 55)

# ── Connect ──
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(CDP_URL)

page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team" in pg.url:
            page = pg
            break
    if page: break

if not page:
    page = browser.contexts[0].new_page()
    page.goto("https://www.ea.com/ea-sports-fc/ultimate-team/web-app/",
              wait_until="domcontentloaded", timeout=60000)

# ── Login ──
print_log("[1/3] Login (PageMachine)...")
machine = PageMachine(page, email=EMAIL, password=PASSWORD, interactive=True)
result = machine.run(goal_state=LoggedIn)
if not result["success"]:
    print_log(f"[FAIL] Login: {result.get('error')}")
    p.stop()
    sys.exit(1)
print_log(f"[OK] Logged in ({result['cycles']} cycles)")

# ── Navigate SBC > Upgrades ──
print_log("[2/3] Navigate SBC > Upgrades...")
click_sbc_nav(page)
time.sleep(3)
navigate_sbc_category(page, cat_name="升级", cat_id=2)
time.sleep(2)
print_log("[OK] On upgrades tab")

# ── Run SBCMachine for one SBC ──
print_log("[3/3] Execute daily Bronze upgrade...")
sbc_machine = SBCMachine(page, max_cycles=30, confirm_before_submit=False)
sbc_result = sbc_machine.run(target_sbcs=["每日青铜升级"])

print_log("")
print_log("=" * 55)
print_log("Result")
print_log("=" * 55)
print_log(f"  Completed: {sbc_result['completed']}")
print_log(f"  Failed:    {sbc_result['failed']}")
print_log(f"  Cycles:    {sbc_result['cycles']}")
if sbc_result.get('states'):
    print_log(f"  States:    {' → '.join(sbc_result['states'][:20])}")
    if len(sbc_result['states']) > 20:
        print_log(f"             ... ({len(sbc_result['states'])} total)")

print_log(f"\n{'=' * 55}")
if sbc_result['completed']:
    print_log(f"[OK] SBC completed successfully!")
else:
    print_log(f"[DONE] SBC not completed. Review log above.")
print_log(f"{'=' * 55}")
print_log("Browser kept open. Ctrl+C to exit.")

try:
    while browser.is_connected():
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    try: p.stop()
    except: pass
