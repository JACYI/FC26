# -*- coding: utf-8 -*-
"""
Test: TOTS Crafting Upgrade with manual submit confirmation.

Uses Playwright exclusively (no raw CDP event loop conflict).
Pauses at submit-ready for user review (confirm_before_submit=True).
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.utils import navigate_sbc_category, click_sbc_nav, get_page_text, log
from src.sbc.machine import SBCMachine


def main():
    log("\n" + "=" * 50)
    log("TEST: TOTS 制作升级 — 手动确认提交")
    log("=" * 50)

    # ── Connect Playwright + Login ──
    log("\n[PW] Connecting...")
    from src.login import connect as pw_connect, navigate_to_ea, do_login

    p, browser, pw_page = pw_connect()
    if not pw_page:
        log("[FATAL] No browser page")
        print("No browser page")
        return

    navigate_to_ea(pw_page)
    if not do_login(pw_page):
        log("[FATAL] Login failed")
        print("Login failed")
        return

    # ── Navigate to SBC hub ──
    log("\n[NAV] SBC...")
    if not click_sbc_nav(pw_page):
        log("[FATAL] SBC nav failed")
        print("SBC nav failed")
        return
    time.sleep(4)

    # If page is not on SBC hub (e.g. left on a squad builder from previous run),
    # reset navigation stack first
    body = pw_page.inner_text("body")
    log(f"  Body: {body[:200]}")
    if "全部" not in body or "升级" not in body:
        log("[NAV] Not on SBC hub, resetting navigation...")
        from src.utils import go_to_sbc_hub
        go_to_sbc_hub(pw_page)
        time.sleep(3)
        body = pw_page.inner_text("body")
        log(f"  Body after reset: {body[:200]}")

    # ── Switch to 升级 tab ──
    log("[NAV] 升级 tab...")
    result = navigate_sbc_category(pw_page, "升级", 2)
    log(f"  {result}")
    time.sleep(3)
    body = pw_page.inner_text("body")
    log(f"  Body after: {body[:300]}")

    # ── Run state machine ──
    machine = SBCMachine(pw_page, confirm_before_submit=True)
    targets = ["TOTS 制作升级"]
    log(f"\n[MACHINE] Starting with targets: {targets}")

    result = machine.run(target_sbcs=targets)

    # Report
    log(f"\n{'='*50}")
    log("TEST COMPLETE")
    log(f"  Completed: {result['completed']}")
    log(f"  Failed: {result['failed']}")
    log(f"  Cycles: {result['cycles']}")
    log(f"{'='*50}")

    print(f"\nCompleted: {result['completed']}")
    print(f"Failed: {result['failed']}")
    print(f"States: {' -> '.join(result['states'])}")


if __name__ == "__main__":
    main()
