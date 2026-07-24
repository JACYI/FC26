# -*- coding: utf-8 -*-
"""
Test the PageMachine login state machine.
1. Connect to Chrome via Playwright CDP
2. Navigate to EA Web App (if not already on it)
3. Run PageMachine state machine → LOGGED_IN
4. Print result and keep browser open
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright
from src.page_machine import PageMachine
from src.page_states import LoggedIn

CDP_URL = "http://127.0.0.1:9222"
EA_URL = "https://www.ea.com/ea-sports-fc/ultimate-team/web-app/"
EMAIL = "3079479814@qq.com"
PASSWORD = "Yyh3079479814"
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "scripts", "bsg_cdp_log.txt")

def print_log(msg):
    print(msg)
    sys.stdout.flush()

print_log("=" * 55)
print_log("PageMachine Login Test")
print_log("=" * 55)

# Connect
print_log(f"[CONNECT] Connecting to Chrome on {CDP_URL}...")
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(CDP_URL)
print_log("[OK] Connected")

# Find EA tab or create one
page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        print_log(f"  Tab: {pg.url[:100]}")
        if "ultimate-team" in pg.url:
            page = pg
            print_log(f"[OK] Found EA tab")
            break
    if page:
        break

if not page:
    print_log(f"[NAV] No EA tab found, navigating to EA...")
    page = browser.contexts[0].new_page()
    page.goto(EA_URL, wait_until="domcontentloaded", timeout=60000)
    print_log(f"[NAV] Navigated to {EA_URL}")
else:
    # Bring tab to front and refresh in case stale
    try:
        page.bring_to_front()
    except:
        pass

# Run state machine
print_log(f"\n{'=' * 55}")
print_log(f"Starting PageMachine...")
print_log(f"{'=' * 55}")

machine = PageMachine(
    page,
    email=EMAIL,
    password=PASSWORD,
    interactive=True,
    poll_interval=1.5,
    poll_stable_count=4,
    poll_timeout=45,
)

result = machine.run(goal_state=LoggedIn)

# Print result
print_log(f"\n{'=' * 55}")
print_log(f"Result:")
print_log(f"  Success: {result.get('success')}")
print_log(f"  State:   {result.get('state')}")
print_log(f"  Cycles:  {result.get('cycles')}")
print_log(f"  Error:   {result.get('error')}")
if result.get('history'):
    print_log(f"  History: {' → '.join(result['history'])}")
print_log(f"{'=' * 55}")

if result.get("success"):
    print_log(f"\n[OK] Login successful! Browser kept open.")
else:
    print_log(f"\n[FAIL] Login failed. Check log file: {LOG_FILE}")
    print_log(f"  Debug: tail {LOG_FILE}")

# Keep browser open for inspection
print_log(f"\n[WAIT] Keeping browser open. Press Ctrl+C to exit.")
try:
    while browser.is_connected():
        time.sleep(3)
except KeyboardInterrupt:
    print_log("\n[EXIT] User interrupted")
except:
    pass
finally:
    try:
        p.stop()
    except:
        pass
