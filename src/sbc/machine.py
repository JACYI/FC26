# -*- coding: utf-8 -*-
"""
State machine runner for SBC automation.

Implements the OODA loop:
  Observe   → detect current page state
  Orient    → decide next action based on transition table + context
  Decide    → select best action (handles dynamic params)
  Act       → execute action
  Verify    → re-detect state, log transition, adapt if mismatch

Safety: max_cycles prevents infinite loops.
History: all state transitions are recorded for debugging.
"""
import sys, os, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import log
from src.sbc.states import ALL_STATES, ErrorState, SBCHome, SetDetail, SquadBuilder
from src.sbc.actions import (
    EnterSBCSet, CheckAvailableSBCs, ClickSubmit
)
from src.sbc.transitions import get_transitions


class SBCMachine:
    """State machine that runs the SBC OODA loop."""

    def __init__(self, page, max_cycles=50, confirm_before_submit=False):
        self.page = page
        self.max_cycles = max_cycles
        self.confirm_before_submit = confirm_before_submit

        # Runtime state
        self.current_state = None
        self.history = []               # List of visited state names
        self.available_sbcs = []        # SBCs with repeats remaining
        self.completed = []             # Successfully completed SBCs
        self.failed = []                # Failed SBCs
        self.target_sbcs = []           # SBCs to process this run
        self.sbc_index = 0              # Index into target_sbcs
        self._checked = False           # Whether CheckAvailableSBCs has run
        self._current_sbc = None        # SBC we're currently processing

    # ── Detection ───────────────────────────────────────────────────

    def detect_state(self):
        """Run all state detectors, return first match."""
        for state_cls in ALL_STATES:
            try:
                if state_cls.detect(self.page):
                    return state_cls
            except Exception as e:
                log(f"  [WARN] State detection error ({state_cls.name}): {e}")
        return ErrorState

    # ── Decision ────────────────────────────────────────────────────

    def _resolve_action(self, action_template):
        """Resolve a template action into a concrete action with runtime params."""
        if isinstance(action_template, CheckAvailableSBCs):
            if self._checked:
                return None  # Already checked, move to next transition
            action_template.targets = self.target_sbcs
            return action_template

        if isinstance(action_template, EnterSBCSet):
            if self.sbc_index < len(self.available_sbcs):
                sbc_name = self.available_sbcs[self.sbc_index]
                self._current_sbc = sbc_name  # Track before execution for cleanup on failure
                log(f"  [MACHINE] Target SBC: {sbc_name}")
                # Use direct_to_squad=True for hidden/single-segment SBCs
                return EnterSBCSet(sbc_name, direct_to_squad=True)
            return None  # No more SBCs to process

        return action_template

    # ── Loop ────────────────────────────────────────────────────────

    def run(self, target_sbcs=None):
        """Main OODA loop.

        Args:
            target_sbcs: List of SBC names to attempt (e.g. ["每日青铜升级", "每日白银升级"])
        """
        if target_sbcs:
            self.target_sbcs = target_sbcs

        log(f"\n{'='*50}")
        log(f"MACHINE RUN: targets={self.target_sbcs}")
        log(f"{'='*50}")

        for cycle in range(self.max_cycles):
            # ── Observe ──
            state_cls = self.detect_state()
            self.current_state = state_cls
            self.history.append(state_cls.name)
            log(f"\n[CYCLE {cycle}] State: {state_cls.name}")

            # ── Check termination ──
            if self._should_stop():
                log(f"  [MACHINE] Stop condition met")
                break

            # ── Orient / Decide — try transitions in order ──
            transitions = get_transitions(state_cls)
            acted = False

            if not transitions:
                if state_cls == ErrorState:
                    log("  [MACHINE] Error state — no actions defined")
                else:
                    log(f"  [MACHINE] No transitions from {state_cls.name}")
                break

            for action_template, expected_state in transitions:
                # Resolve dynamic params
                action = self._resolve_action(action_template)
                if action is None:
                    continue

                log(f"  Try: {action} -> {expected_state.name if expected_state else '?'}")

                # ── Pre-flight: confirm before submit ──
                if self.confirm_before_submit and isinstance(action, ClickSubmit):
                    if not self._confirm_submit():
                        log("  [MACHINE] User declined submit, stopping")
                        self._skip_current_sbc()
                        return self._summary()  # Stop the machine entirely

                # ── Act ──
                try:
                    result = action.execute(self.page)
                except Exception as e:
                    log(f"  [ERROR] Action failed: {e}")
                    continue  # Try next transition

                if not result.success:
                    log(f"  [WARN] Action returned failure: {result.data}")
                    # Still track result for failure accounting
                    self._handle_result(action, result, self.current_state)
                    continue  # Try next transition

                # ── Verify (re-detect) ──
                time.sleep(1)
                new_state = self.detect_state()
                self.current_state = new_state
                log(f"  -> State after: {new_state.name}")

                # ── State unchanged after action → try next transition ──
                if new_state == state_cls and len(transitions) > 1:
                    log(f"  [WARN] State unchanged ({state_cls.name}), trying next action...")
                    continue

                # Handle action results
                self._handle_result(action, result, new_state)
                acted = True
                break  # Successful action → next cycle

            if not acted:
                log(f"  [MACHINE] All transitions exhausted for {state_cls.name}")
                break

        # Cleanup: any SBC still in progress → mark as failed
        if self._current_sbc:
            sbc_name = self._current_sbc
            if sbc_name not in self.failed and sbc_name not in self.completed:
                self.failed.append(sbc_name)
                log(f"  [MACHINE] Failed (unfinished): {sbc_name}")
            self._current_sbc = None

        return self._summary()

    # ── Internal helpers ────────────────────────────────────────────

    def _summary(self):
        """Return final result and log summary."""
        log(f"\n{'='*50}")
        log(f"MACHINE DONE")
        log(f"  Completed: {self.completed}")
        log(f"  Failed: {self.failed}")
        log(f"  Cycles: {len(self.history)}")
        log(f"  States: {' -> '.join(self.history)}")
        log(f"{'='*50}")
        return {
            "completed": self.completed,
            "failed": self.failed,
            "cycles": len(self.history),
            "states": self.history,
        }

    def _handle_result(self, action, result, new_state):
        """Process action result and update machine state."""

        def _mark_done(sbc_name, failed=False):
            """Mark an SBC as completed or failed and advance index."""
            if failed:
                if sbc_name not in self.failed:
                    self.failed.append(sbc_name)
                log(f"  [MACHINE] Failed: {sbc_name}")
            else:
                if sbc_name not in self.completed:
                    self.completed.append(sbc_name)
                    log(f"  [MACHINE] Completed: {sbc_name}")
            self.sbc_index += 1
            self._current_sbc = None

        # CheckAvailableSBCs updates our available list
        if isinstance(action, CheckAvailableSBCs):
            self.available_sbcs = result.data.get("available", [])
            self._checked = True
            log(f"  [MACHINE] Available SBCs: {self.available_sbcs}")

        # EnterSBCSet → track which SBC we're processing
        if isinstance(action, EnterSBCSet):
            set_name = action.kwargs.get("set_name")
            self._current_sbc = set_name
            # If VC push itself failed, mark as failed immediately
            if not result.success:
                _mark_done(set_name, failed=True)

        # Back at SBCHome after processing an SBC → mark complete
        if new_state == SBCHome and self._current_sbc:
            _mark_done(self._current_sbc, failed=False)

    def _confirm_submit(self):
        """Dump squad info and ask user to confirm submit.
        Returns True to proceed, False to skip.
        """
        # Scrape visible player info from the page
        from src.utils import get_page_text, get_visible_buttons
        body = get_page_text(self.page)
        buttons = get_visible_buttons(self.page)

        msg = ["", "=" * 50, "CONFIRM SUBMIT — 请检查球员", "=" * 50]
        msg.append(f"  SBC: {self._current_sbc or '?'}")
        msg.append(f"  Page text snippet: {body[:200].strip()}")
        msg.append("  Visible buttons:")
        for b in buttons:
            msg.append(f"    - {b}")
        msg.append("=" * 50)
        msg.append("Can submit? Check the squad in the browser window.")
        msg.append("Submit and continue? (y/n): ")
        full = "\n".join(msg)

        log(full)           # Write to log file
        print(f"\n{full}", end="", flush=True)  # Write to console

        try:
            reply = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            reply = "n"

        confirmed = reply == "y" or reply == "yes"
        log(f"  User response: {'YES' if confirmed else 'NO'}")
        return confirmed

    def _skip_current_sbc(self):
        """Skip the current SBC (user declined or error)."""
        if self._current_sbc:
            sbc_name = self._current_sbc
            if sbc_name not in self.failed and sbc_name not in self.completed:
                self.failed.append(sbc_name)
                log(f"  [MACHINE] Skipped: {sbc_name}")
            self.sbc_index += 1
            self._current_sbc = None

    def _should_stop(self):
        """Check if the machine should stop running."""
        state = self.current_state

        # Error state → stop
        if state == ErrorState:
            # Check if it's the ONLY one that matches
            for st in ALL_STATES:
                if st != ErrorState:
                    try:
                        if st.detect(self.page):
                            return False  # Found a real state
                    except:
                        pass
            return True

        # Checked availability and found nothing → stop
        if self._checked and not self.available_sbcs:
            log("  [MACHINE] No available SBCs")
            return True

        # All available SBCs processed → stop
        if self._checked and self.sbc_index >= len(self.available_sbcs):
            return True

        return False
