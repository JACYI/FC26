# -*- coding: utf-8 -*-
"""Quick connect + navigate to EA Web App, then run daily SBC."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.login import connect, navigate_to_ea, do_login, check_fsu
from src.sbc.executor import SBCExecutor

p, browser, page = connect()
if not page:
    print("Failed to connect")
    sys.exit(1)

print(f"Current URL: {page.url[:80]}")
if "ultimate-team" not in page.url:
    navigate_to_ea(page)
    print(f"After nav: {page.url[:80]}")

do_login(page)
check_fsu(page)
print("Ready for SBC!")

executor = SBCExecutor(page)
if not executor.navigate_to_sbc("Upgrades"):
    print("Navigation failed")
else:
    available = executor.find_available_sbcs()
    print(f"\nAvailable SBCs: {available}")
    for sbc_name in available:
        success = executor.run_sbc(sbc_name, tab="Upgrades")
        print(f"  [{ 'OK' if success else 'FAIL' }] {sbc_name}")
        time.sleep(3)
        executor._go_home()
        time.sleep(2)
        executor.navigate_to_sbc("Upgrades")

print("\nDone. Browser stays open.")
try:
    while browser.is_connected():
        time.sleep(3)
except:
    pass
try:
    p.stop()
except:
    pass
