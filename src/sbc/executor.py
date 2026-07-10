# -*- coding: utf-8 -*-
"""
State-aware SBC execution orchestrator.

Navigation: click_text() one-liner for all buttons/tabs.
Exception: entering an SBC set uses VC push via page.evaluate().

Orchestrates the SBC flow using SBCMachine (OODA loop) internally.
"""
import sys, os, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import click_sbc_nav, click_text, navigate_sbc_category, get_set_statuses, log
from src.sbc.machine import SBCMachine


class SBCExecutor:
    """Orchestrates SBC automation with state machine OODA loop."""

    def __init__(self, page):
        self.page = page
        self.machine = SBCMachine(page)

    # ── Navigation helpers (for external use) ──────────────────────

    def navigate_to_sbc(self):
        """Click SBC nav button (legacy)."""
        log("[NAV] SBC...")
        click_sbc_nav(self.page)
        time.sleep(4)
        return True

    def switch_to_upgrades(self):
        """Switch to 升级 tab (legacy)."""
        result = navigate_sbc_category(self.page, "升级", 2)
        log(f"  Switch to 升级: {result}")
        time.sleep(2)
        return result.get("ok", False)

    def check_available_sbcs(self):
        """Check available daily SBCs (legacy). Returns list of names."""
        statuses = get_set_statuses(self.page)
        available = []
        if isinstance(statuses, dict) and "error" not in statuses:
            for name, info in statuses.items():
                if isinstance(info, dict):
                    if not info.get("complete") and info.get("repeatsLeft", 0) > 0:
                        available.append(name)
        return available

    def go_back(self):
        """Navigate back to SBC hub (legacy)."""
        click_sbc_nav(self.page)
        time.sleep(3)
        click_text(self.page, "返回", timeout=3)
        time.sleep(3)

    # ── State machine execution ────────────────────────────────────

    def run_sbc(self, sbc_name):
        """Complete one SBC using the state machine. Returns True if successful."""
        log(f"\n{'='*50}")
        log(f"RUN: {sbc_name}")
        log(f"{'='*50}")

        result = self.machine.run(target_sbcs=[sbc_name])

        if sbc_name in result["completed"]:
            return True

        log(f"  [X] SBC failed: {sbc_name}")
        return False

    def run_all(self, target_sbcs, navigate_first=True):
        """Run multiple SBCs using state machine.

        Args:
            target_sbcs: List of SBC names to process
            navigate_first: If True, navigate to SBC page first
        """
        if navigate_first:
            self.navigate_to_sbc()
            self.switch_to_upgrades()

        # Run the machine once with all targets (it handles the full loop)
        result = self.machine.run(target_sbcs=target_sbcs)

        log(f"\n{'='*50}")
        log(f"ALL DONE: {len(result['completed'])}/{len(target_sbcs)}")
        log(f"  Completed: {result['completed']}")
        log(f"  Failed: {result['failed']}")
        log(f"{'='*50}")

        return result
