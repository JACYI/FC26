# -*- coding: utf-8 -*-
"""
Bronze & Silver Daily SBC — State machine OODA loop.

Flow: connect → SBC > 升级 → machine.run(targets=[青铜, 白银])
The state machine handles: check status → VC push → challenge → FSU fill → submit → claim
"""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.utils import connect, click_sbc_nav, navigate_sbc_category, log
from src.sbc.machine import SBCMachine


def main():
    log("\n" + "=" * 50)
    log("BSG CDP - State Machine Bronze & Silver Daily SBC")
    log("=" * 50)

    page = connect()
    log("[CONNECT] Connected")

    # Navigate to SBC section
    log("\n[NAV] SBC...")
    click_sbc_nav(page)
    time.sleep(4)

    # Switch to 升级 tab
    log("[NAV] 升级...")
    result = navigate_sbc_category(page, "升级", 2)
    log(f"  {result}")
    time.sleep(2)

    # Create state machine and run
    machine = SBCMachine(page)
    targets = ["每日青铜升级", "每日白银升级"]
    log(f"\n[MACHINE] Starting with targets: {targets}")

    result = machine.run(target_sbcs=targets)

    # Report
    log(f"\n{'='*50}")
    log("BSG COMPLETE")
    log(f"  Completed: {result['completed']}")
    log(f"  Failed: {result['failed']}")
    log(f"  Cycles: {result['cycles']}")
    log(f"{'='*50}")

    print(f"\nCompleted: {result['completed']}")
    print(f"Failed: {result['failed']}")


if __name__ == "__main__":
    main()
