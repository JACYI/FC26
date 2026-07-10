# -*- coding: utf-8 -*-
"""
Page-level state machine: from any page state → LOGGED_IN.

OODA loop:
  Observe   → detect current page state (page_states.py)
  Orient    → consult transition table
  Decide    → select action for current state
  Act       → execute action (lightweight — no blind waits)
  Verify    → poll until state stabilizes, then continue loop

Principles:
  - Actions do NOT contain blind sleeps > 2s
  - All post-act waiting is done by the machine's polling loop
  - Polling tracks state changes and only returns when stable
  - FSU loading is detected and waited on transparently
"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.utils import _js, _click, click_text, fill_input, log
from src.page_states import (
    ALL_PAGE_STATES, Unknown,
    Loading, LoginPage, EmailForm, PasswordForm, VerifyCode,
    FSULoading, DialogOverlay, EnglishUI, LoggedIn,
)


# ── Action results ─────────────────────────────────────────────────────────

class ActionResult:
    """Result of a single action execution."""
    def __init__(self, success=True, data=None):
        self.success = success
        self.data = data or {}


# ═══════════════════════════════════════════════════════════════════════════
# Actions (lightweight — minimal waits, no polling)
# ═══════════════════════════════════════════════════════════════════════════

def act_wait_for_load(page):
    """Minimal wait — just check if still loading."""
    log("  [Action] wait_for_load")
    # The machine's poller handles the actual waiting
    return ActionResult(success=True)


def act_refresh(page):
    """Refresh page. Short wait for navigation to start."""
    log("  [Action] refresh")
    _js(page, "window.location.reload()")
    time.sleep(2)  # 2s for reload to initiate — rest handled by poller
    return ActionResult(success=True, data={"refreshed": True})


def act_navigate_to_ea(page):
    """Navigate browser to EA Web App URL."""
    log("  [Action] navigate_to_ea")
    _js(page, "window.location.href = 'https://www.ea.com/ea-sports-fc/ultimate-team/web-app/'")
    time.sleep(2)
    return ActionResult(success=True)


def act_click_login(page):
    """Click the login button on the landing page.

    Uses JS .click() with exact text match for reliability.
    Falls back to click_text (Playwright) if JS click fails.
    """
    log("  [Action] click_login")
    clicked = _js(page, """function() {
        var body = document.body.innerText || '';
        var onEA = window.location.href.indexOf('ultimate-team') >= 0;
        if (!onEA) return 'not_on_ea';

        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].offsetParent === null) continue;
            var t = (btns[i].innerText || '').trim();
            if (t === '登录' || t.indexOf('Login') >= 0 || t === '登录/注册') {
                btns[i].click();
                return 'clicked_js';
            }
        }
        return 'no_login_btn';
    }()""")

    if clicked == 'clicked_js':
        log("    Login button clicked (JS)")
        return ActionResult(success=True)

    if clicked == 'not_on_ea':
        log("    Not on EA page, skipping")
        return ActionResult(success=False, data={"error": "not_on_ea"})

    # Fallback: Playwright click_text with contains match
    log(f"    JS click failed ({clicked}), trying Playwright fallback...")
    clicked = click_text(page, "登录", timeout=3)
    if not clicked:
        clicked = click_text(page, "Login", timeout=3)
    if clicked:
        log("    Login button clicked (Playwright fallback)")
        return ActionResult(success=True)

    log("    Login button not found")
    return ActionResult(success=False, data={"error": "login_btn_not_found"})


def act_fill_email(page, email):
    """Fill email field and click Next. Does NOT wait for transition."""
    log("  [Action] fill_email")

    filled, actual = _fill_and_verify(page, "#email", email, "email")
    if not filled:
        return ActionResult(success=False, data={"error": "email_not_filled", "actual": actual})

    # Click Next
    next_btn = _js(page, """function() {
        var btn = document.getElementById('logInBtn');
        if (btn && btn.offsetParent !== null) { btn.click(); return 'clicked'; }
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim().toUpperCase();
            if ((t === 'NEXT' || t.indexOf('下一步') >= 0) && btns[i].offsetParent !== null) {
                btns[i].click(); return 'clicked_fallback';
            }
        }
        return 'no_next_btn';
    }()""")
    log(f"    Next: {next_btn}")
    return ActionResult(success='clicked' in str(next_btn), data={"next": next_btn})


def act_fill_password(page, password):
    """Fill password field and click Sign In. Does NOT wait for transition."""
    log("  [Action] fill_password")

    filled, actual = _fill_and_verify(page, "#password", password, "password")
    if not filled:
        return ActionResult(success=False, data={"error": "password_not_filled", "actual": actual})

    signin = _js(page, """function() {
        var btn = document.getElementById('logInBtn');
        if (btn && btn.offsetParent !== null) { btn.click(); return 'clicked'; }
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim();
            if ((t.indexOf('Sign') >= 0 || t.indexOf('登录') >= 0) && btns[i].offsetParent !== null) {
                btns[i].click(); return 'clicked_fallback';
            }
        }
        return 'no_signin_btn';
    }()""")
    log(f"    Sign In: {signin}")
    return ActionResult(success='clicked' in str(signin), data={"signin": signin})


def act_send_verification_code(page):
    """Trigger SEND CODE on the 2FA page."""
    log("  [Action] send_verification_code")
    sent = _js(page, """function() {
        var body = document.body.innerText || '';
        if (body.indexOf('SEND CODE') < 0) return 'no_send_code_btn';
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim();
            if (t === 'SEND CODE' && btns[i].offsetParent !== null) {
                btns[i].click(); return 'clicked';
            }
        }
        return 'send_code_not_found';
    }()""")
    log(f"    Send code: {sent}")
    return ActionResult(success='clicked' in str(sent), data={"status": sent})


def act_enter_verification_code(page, code):
    """Fill verification code and submit. Does NOT wait for redirect."""
    log("  [Action] enter_verification_code")

    filled, actual = _fill_and_verify(page, "#twoFactorCode", code, "code")
    if not filled:
        return ActionResult(success=False, data={"error": "code_not_filled", "actual": actual})

    # Check trust device
    _js(page, """function() {
        var cb = document.getElementById('trustThisDevice');
        if (cb && !cb.checked) cb.checked = true;
    }()""")

    submit = _js(page, """function() {
        var btn = document.getElementById('btnSubmit');
        if (btn && btn.offsetParent !== null) { btn.click(); return 'clicked'; }
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].innerText || '').trim();
            if (t.indexOf('Sign') >= 0 && btns[i].offsetParent !== null) {
                btns[i].click(); return 'clicked_fallback';
            }
        }
        return 'no_submit_btn';
    }()""")
    log(f"    Submit: {submit}")
    return ActionResult(success='clicked' in str(submit), data={"submit": submit})


def act_dismiss_dialog(page):
    """Try to dismiss any EA dialog overlay by clicking common dismiss buttons."""
    log("  [Action] dismiss_dialog")
    from src.page_states import DIALOG_DISMISS_BUTTONS
    for btn_text in DIALOG_DISMISS_BUTTONS:
        if click_text(page, btn_text, timeout=2):
            log(f"    Clicked '{btn_text}'")
            return ActionResult(success=True, data={"clicked": btn_text})
    log("    No dismiss button found/clickable")
    return ActionResult(success=False, data={"error": "no_dismiss_button"})


def act_switch_to_chinese(page):
    """Switch UI language from English to Simplified Chinese."""
    log("  [Action] switch_to_chinese")

    # Click Settings nav
    clicked = click_text(page, "Settings", timeout=3)
    if not clicked:
        log("    Settings button not found")
        return ActionResult(success=False, data={"error": "settings_not_found"})
    time.sleep(2)

    # Click Select Language
    clicked = click_text(page, "Select Language", timeout=3)
    if not clicked:
        log("    Select Language not found")
        return ActionResult(success=False, data={"error": "select_lang_not_found"})
    time.sleep(1)

    # Click Simplified Chinese
    clicked = click_text(page, "简体中文", timeout=3)
    if not clicked:
        clicked = click_text(page, "Simplified Chinese", timeout=2)
    if not clicked:
        clicked = click_text(page, "中文", timeout=2)

    if clicked:
        log("    Language switched to Chinese, page will refresh")
        return ActionResult(success=True, data={"switched": True})

    log("    Chinese option not found in language list")
    return ActionResult(success=False, data={"error": "chinese_option_not_found"})


def act_unknown_recovery(page):
    """When state is UNKNOWN, try to recover based on URL."""
    log("  [Action] unknown_recovery")
    url = _js(page, "window.location.href") or ""
    body = _js(page, "document.body.innerText") or ""

    if "signin.ea.com" in url:
        log("    On signin.ea.com, waiting for form to render")
        return ActionResult(success=True, data={"action": "wait_signin"})

    if "ultimate-team" in url and not body.strip():
        log("    EA page blank, need refresh")
        return ActionResult(success=False, data={"action": "needs_refresh"})

    log(f"    URL: {url[:80]}")
    return ActionResult(success=True, data={"action": "none"})


# ── Shared helper ──────────────────────────────────────────────────────────

def _fill_and_verify(page, selector, value, field_name="field"):
    """Fill a form field with fallback strategies, then verify value."""
    ok = fill_input(page, selector, value)
    if ok:
        log(f"    {field_name} filled and verified")
        return True, value

    actual = _js(page, f"function() {{ var el = document.querySelector('{selector}'); return el ? el.value : 'N/A'; }}()")
    log(f"    {field_name} fill FAILED (actual={repr(actual)[:30]})")
    return False, actual


# ═══════════════════════════════════════════════════════════════════════════
# Transition table
# ═══════════════════════════════════════════════════════════════════════════

TRANSITIONS = {
    Unknown: [
        (act_unknown_recovery, None),
        (act_refresh, None),
    ],
    Loading: [
        (act_wait_for_load, None),
        (act_refresh, None),
    ],
    LoginPage: [
        (act_click_login, None),
        (act_refresh, None),
    ],
    EmailForm: [
        (act_fill_email, None),  # → PASSWORD_FORM or back to EMAIL_FORM
    ],
    PasswordForm: [
        (act_fill_password, None),  # → LOGGED_IN, VERIFY_CODE, or back to LOGIN_PAGE
    ],
    VerifyCode: [
        (act_send_verification_code, None),
        (act_enter_verification_code, None),
    ],
    FSULoading: [],            # No actions — handled by poller, auto-resolves
    DialogOverlay: [
        (act_dismiss_dialog, None),   # Dismiss → next cycle re-detects
    ],
    EnglishUI: [
        (act_switch_to_chinese, None),  # Switch → page refresh → LOADING → ...
    ],
    LoggedIn: [],               # Goal state
}


# ═══════════════════════════════════════════════════════════════════════════
# State Machine
# ═══════════════════════════════════════════════════════════════════════════

class PageMachine:
    """
    State machine: any page state → LOGGED_IN.

    Instead of blind sleeps, the machine polls page state after each action,
    tracking changes until the page stabilizes or a known target is reached.

    Args:
        page: Playwright page or raw CDP page
        email: EA account email
        password: EA account password
        verification_code: 2FA code (if known), or None for interactive prompt
        interactive: If True, prompt user for 2FA code when needed
        max_cycles: Safety limit
        poll_interval: Seconds between state checks during post-act polling
        poll_stable_count: Consecutive identical states before considering stable
        poll_timeout: Max seconds to poll after an action
    """

    def __init__(self, page, email="", password="",
                 verification_code=None, interactive=True, max_cycles=30,
                 poll_interval=1.5, poll_stable_count=4, poll_timeout=45):
        self.page = page
        self.email = email
        self.password = password
        self.verification_code = verification_code
        self.interactive = interactive
        self.max_cycles = max_cycles
        self.poll_interval = poll_interval
        self.poll_stable_count = poll_stable_count
        self.poll_timeout = poll_timeout

        # Runtime
        self.current_state = Unknown
        self.history = []

    # ── Detection ───────────────────────────────────────────────────

    def detect(self):
        """Run all state detectors, return first match."""
        for state_cls in ALL_PAGE_STATES:
            try:
                if state_cls.detect(self.page):
                    return state_cls
            except Exception as e:
                log(f"  [WARN] Detection error ({state_cls.name}): {e}")
        return Unknown

    # ── Post-action polling ─────────────────────────────────────────

    def _poll_after_action(self, acted_from_state, action_fn):
        """
        Poll page state after executing an action.
        Returns when state stabilizes or timeout.

        Polling logic:
          1. Every `poll_interval` seconds, re-detect state
          2. If state is FSULoading or Loading: keep polling (progress in progress)
          3. If state is a known stable state (not Unknown/Loading/FSULoading):
             → return immediately (early exit)
          4. If same state for `poll_stable_count` consecutive checks:
             → consider stabilized, return
          5. If `poll_timeout` exceeded: return with current state

        Returns:
            The detected state class (after stability/early-exit)
        """
        log(f"  [Poll] waiting... (from {acted_from_state.name} via {action_fn.__name__})")

        state_chain = []       # All states seen during polling
        same_count = 0
        last_state = None
        start = time.time()

        _transient = {Unknown, Loading, FSULoading}
        _early_exit = {EmailForm, PasswordForm, VerifyCode, LoggedIn, LoginPage}

        for tick in range(int(self.poll_timeout / self.poll_interval) + 1):
            now = time.time()
            elapsed = now - start

            current = self.detect()
            state_chain.append(current)

            # Log every few ticks
            if tick % 3 == 0:
                elapsed_s = f"{elapsed:.1f}s"
                log(f"    [{elapsed_s}] state={current.name}")

            # ── Early exit: reached stable state ──
            if current in _early_exit:
                log(f"  → {current.name} (early exit, {elapsed:.1f}s)")
                return current

            # ── Still in transient (loading / FSU) → keep polling ──
            if current in _transient:
                same_count = 0   # Reset stability counter — this IS progress
                time.sleep(self.poll_interval)
                continue

            # ── Track stability ──
            if current == last_state:
                same_count += 1
                if same_count >= self.poll_stable_count:
                    log(f"  → {current.name} (stable x{same_count}, {elapsed:.1f}s)")
                    return current
            else:
                same_count = 0

            last_state = current

            # ── Timeout ──
            if elapsed >= self.poll_timeout:
                log(f"  → {current.name} (TIMEOUT {self.poll_timeout}s)")
                return current

            time.sleep(self.poll_interval)

        final = self.detect()
        log(f"  → {final.name} (max ticks)")
        return final

    # ── Action resolution ───────────────────────────────────────────

    def _resolve_action(self, action_fn):
        """Bind runtime params to a generic action function."""
        name = action_fn.__name__

        if name == "act_fill_email":
            return lambda: action_fn(self.page, self.email)

        if name == "act_fill_password":
            return lambda: action_fn(self.page, self.password)

        if name == "act_enter_verification_code":
            if self.verification_code:
                return lambda: action_fn(self.page, self.verification_code)
            if self.interactive:
                print("\n" + "=" * 50)
                print("  需要 2FA 验证码")
                print("  请查收邮件 (3079479814@qq.com)，包括垃圾邮件")
                print("=" * 50)
                code = input("  验证码: ").strip()
                if not code:
                    log("  用户未输入验证码")
                    return lambda: ActionResult(success=False, data={"error": "no_code"})
                self.verification_code = code
                return lambda: action_fn(self.page, code)
            log("  需要验证码但未提供 (interactive=False)")
            return lambda: ActionResult(success=False, data={"error": "code_required"})

        # Actions without runtime params
        return lambda: action_fn(self.page)

    # ── Main loop ───────────────────────────────────────────────────

    def run(self, goal_state=LoggedIn):
        """
        Execute OODA loop until goal_state or error.

        Each cycle: detect → act → poll → next
        """
        log(f"\n{'='*50}")
        log(f"PageMachine: goal={goal_state.name}")
        log(f"{'='*50}")

        for cycle in range(self.max_cycles):
            # ── Observe ──
            state_cls = self.detect()
            self.current_state = state_cls
            self.history.append(state_cls.name)
            log(f"\n[CYCLE {cycle}] State: {state_cls.name}")

            # ── Goal check ──
            if state_cls == goal_state:
                log(f"  ✅ Goal: {goal_state.name}")
                return {"success": True, "state": state_cls.name,
                        "history": self.history, "cycles": cycle + 1, "error": None}

            # ── Terminal: stuck Unknown ──
            if state_cls == Unknown and cycle > 5 and \
               all(s == "UNKNOWN" for s in self.history[-5:]):
                log(f"  ❌ Stuck UNKNOWN for {cycle} cycles")
                return {"success": False, "state": "UNKNOWN",
                        "history": self.history, "error": "stuck_unknown",
                        "cycles": cycle + 1}

            # ── Get transitions ──
            transitions = TRANSITIONS.get(state_cls, [])
            if not transitions:
                if state_cls == FSULoading:
                    # FSULoading has no actions — poller handles it. Fall through.
                    log("    FSU loading in progress — will be caught by poll")
                    time.sleep(self.poll_interval)
                    continue

                log(f"  ❌ No transitions from {state_cls.name}")
                return {"success": False, "state": state_cls.name,
                        "history": self.history,
                        "error": f"no_transitions_from_{state_cls.name}",
                        "cycles": cycle + 1}

            # ── Orient / Decide / Act / Poll ──
            acted = False
            for action_fn, _expected_state in transitions:
                try:
                    action = self._resolve_action(action_fn)
                    result = action()
                except Exception as e:
                    log(f"  [ERROR] {action_fn.__name__}: {e}")
                    continue

                if not result.success:
                    log(f"  [SKIP] {action_fn.__name__} failed: {result.data}")
                    continue

                # ── Poll (post-act waiting) ──
                new_state = self._poll_after_action(state_cls, action_fn)

                # Special: act_send_verification_code was just a trigger
                # Next cycle will try act_enter_verification_code
                if state_cls == VerifyCode and action_fn == act_send_verification_code:
                    log("    Code sent, next cycle → enter code")
                    acted = True
                    break

                # ── Check: state didn't change — try next transition (if any) ──
                # Prevents getting stuck when action reports success but
                # doesn't actually transition (e.g. click on non-interactive button).
                if new_state == state_cls and len(transitions) > 1:
                    log(f"    State unchanged ({state_cls.name}) after {action_fn.__name__}, trying next action...")
                    continue

                log(f"    {action_fn.__name__} → poll → {new_state.name}")
                acted = True
                break  # This action succeeded → next OODA cycle

            if not acted:
                log(f"  ❌ Actions exhausted for {state_cls.name}")
                return {"success": False, "state": state_cls.name,
                        "history": self.history,
                        "error": f"actions_exhausted_{state_cls.name}",
                        "cycles": cycle + 1}

        log(f"  ❌ Max cycles ({self.max_cycles})")
        return {"success": False, "state": self.current_state.name,
                "history": self.history, "error": "max_cycles",
                "cycles": self.max_cycles}
