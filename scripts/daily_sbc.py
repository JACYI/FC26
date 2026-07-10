# -*- coding: utf-8 -*-
"""
Daily SBC automation entry point.
Runs repeatable SBCs: checks FSU loaded → executes each SBC → reports results.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import connect
from src.sbc.executor import SBCExecutor


def wait_for_fsu(page, timeout=120):
    """Wait for FSU plugin to finish loading player data."""
    print("[FSU] Waiting for plugin to load player data...")
    for i in range(timeout):
        text = page.inner_text("body")
        if "【FSU】" in text:
            print(f"  FSU loaded after {i}s")
            return True
        if "正在读取球员数据" in text:
            pass  # Still loading, wait
        time.sleep(1)
    print("  FSU load timeout")
    # Fallback check
    fsu_count = page.evaluate('document.querySelectorAll("[class*=fsu]").length')
    return fsu_count >= 2


def main():
    print("=" * 50)
    print("EA FC 26 - Daily SBC Automation")
    print("=" * 50)

    print("\n[CONNECT] Connecting to Chrome...")
    p, browser, page = connect()
    time.sleep(2)

    from src.utils import get_page_state
    state = get_page_state(page)
    print(f"  Current state: {state}")

    if state == "login_page":
        print("  Please login first (python scripts/login.py)")
        return

    if not wait_for_fsu(page):
        print("  FSU not detected, continuing without it")
    else:
        print("  FSU ready")

    executor = SBCExecutor(page)

    print("\n[NAV] Going to SBC Upgrades...")
    if not executor.navigate_to_sbc("Upgrades"):
        print("  Navigation failed, aborting")
        return

    available = executor.find_available_sbcs()
    print(f"\n[SCAN] Found {len(available)} available SBCs:")
    for sbc in available:
        print(f"  - {sbc}")

    if not available:
        print("\nNo SBCs to do today!")
        return

    results = {}
    for sbc_name in available:
        success = executor.run_sbc(sbc_name, tab="Upgrades")
        results[sbc_name] = "OK" if success else "FAILED"
        time.sleep(3)
        executor._go_home()
        time.sleep(2)
        executor.navigate_to_sbc("Upgrades")

    print("\n" + "=" * 50)
    print("DAILY SBC RESULTS")
    print("=" * 50)
    for name, status in results.items():
        print(f"  [{status}] {name}")

    ok_count = sum(1 for s in results.values() if s == "OK")
    print(f"\n{ok_count}/{len(results)} completed")

    print("\nDone. Browser remains open.")
    try:
        while browser.is_connected():
            time.sleep(3)
    except:
        pass
    finally:
        try:
            p.stop()
        except:
            pass


if __name__ == "__main__":
    main()
