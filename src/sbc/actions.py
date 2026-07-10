# -*- coding: utf-8 -*-
"""
Individual stable actions for SBC automation.

Each action is a configurable class following:
  check → recover → act → verify

Constructor accepts configuration params.
execute(page) returns ActionResult with expected next state.
"""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import (
    click_text, click_sbc_nav, navigate_sbc_category, get_set_statuses,
    push_sbc_set, open_sbc_squad_builder, is_submit_ready, get_page_text,
    log, _js, _click
)
from src.sbc.states import (
    SBCHome, SetDetail, SquadBuilder, SubmitReady, FSUWarning, RewardReady
)


# ── Action result ────────────────────────────────────────────────────────

class ActionResult:
    """Result of executing an action."""

    def __init__(self, success=True, expected_state=None, data=None):
        self.success = success
        self.expected_state = expected_state  # State class expected after action
        self.data = data or {}


# ── Action base ──────────────────────────────────────────────────────────

class Action:
    """Base class for all SBC actions."""

    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def execute(self, page):
        raise NotImplementedError

    def __repr__(self):
        params = ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items())
        if params:
            return f"Action({self.name}, {params})"
        return f"Action({self.name})"


# ── Individual actions ──────────────────────────────────────────────────

class ClickSBCNav(Action):
    """Click SBC button in left nav bar."""

    def __init__(self):
        super().__init__("click_sbc_nav")

    def execute(self, page):
        log("  [Action] click_sbc_nav")
        click_sbc_nav(page)
        time.sleep(4)
        return ActionResult(success=True, expected_state=SBCHome)


class SwitchUpgradesTab(Action):
    """Switch to the 升级 tab via view model API."""

    def __init__(self, cat_name="升级", cat_id=2):
        super().__init__("switch_upgrades_tab", cat_name=cat_name, cat_id=cat_id)

    def execute(self, page):
        log("  [Action] switch_upgrades_tab")
        result = navigate_sbc_category(page, self.kwargs["cat_name"], self.kwargs["cat_id"])
        log(f"    Result: {result}")
        ok = result.get("ok", False)
        return ActionResult(success=ok, expected_state=SBCHome, data=result)


class CheckAvailableSBCs(Action):
    """Check which target SBCs still have repeats remaining."""

    def __init__(self, targets=None):
        super().__init__("check_available_sbcs", targets=targets or [])
        self.targets = targets or ["每日青铜升级", "每日白银升级"]

    def execute(self, page):
        log(f"  [Action] check_available_sbcs (targets={self.targets})")
        statuses = get_set_statuses(page, targets=self.targets)
        available = []
        if isinstance(statuses, dict) and "error" not in statuses:
            for name, info in statuses.items():
                if isinstance(info, dict):
                    if info.get("complete"):
                        continue
                    # repeatsLeft > 0 = has remaining; maxRepeats == 0 = unlimited
                    if info.get("repeatsLeft", 0) > 0 or info.get("maxRepeats", 0) == 0:
                        available.append(name)
        log(f"    Available: {available}")
        log(f"    Full status: {json.dumps(statuses, ensure_ascii=False)}")
        return ActionResult(success=True, expected_state=None, data={
            "statuses": statuses,
            "available": available,
        })


class EnterSBCSet(Action):
    """Navigate into an SBC set via VC push.

    Args:
        direct_to_squad: If True, go directly to SquadBuilder (skip SET_DETAIL).
                         Required for hidden/single-segment SBCs like TOTS Crafting Upgrade.
    """

    def __init__(self, set_name="", direct_to_squad=False):
        super().__init__("enter_sbc_set", set_name=set_name, direct_to_squad=direct_to_squad)
        self.set_name = set_name
        self.direct_to_squad = direct_to_squad

    def execute(self, page):
        set_name = self.kwargs.get("set_name", self.set_name)
        direct = self.kwargs.get("direct_to_squad", self.direct_to_squad)
        log(f"  [Action] enter_sbc_set: {set_name} (direct_to_squad={direct})")

        if direct:
            result = open_sbc_squad_builder(page, set_name)
            time.sleep(5)
            log(f"    Squad builder result: {result}")
            # Dismiss any FSU dialog (导入方案 popup) — find the dialog container, then click "确定"
            dismissed = _js(page, """function() {
                // Check if the import dialog is visible
                var body = document.body.innerText || '';
                if (body.indexOf('导入方案') < 0) return 'no_dialog';
                // Find 确定 button inside dialog context (search from bottom up — modal dialogs are last in DOM)
                var btns = document.querySelectorAll('button');
                for (var i = btns.length - 1; i >= 0; i--) {
                    var t = (btns[i].innerText || '').trim();
                    if (t === '确定' && btns[i].offsetParent !== null) {
                        btns[i].scrollIntoView({block: 'center'});
                        var r = btns[i].getBoundingClientRect();
                        return JSON.stringify({x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)});
                    }
                }
                return 'no_confirm_btn';
            }()""")
            if dismissed and isinstance(dismissed, str) and dismissed.startswith("{"):
                import json
                pos = json.loads(dismissed)
                if "x" in pos and "y" in pos:
                    _click(page, pos["x"], pos["y"])
                    log(f"    Dismissed FSU import dialog @({pos['x']},{pos['y']})")
                    time.sleep(2)
            else:
                log(f"    FSU dialog check: {dismissed}")
            ok = result.get("ok", False)
            return ActionResult(success=ok, expected_state=SquadBuilder, data=result)
        else:
            result = push_sbc_set(page, set_name)
            time.sleep(5)
            log(f"    Push result: {result}")
            ok = result.get("ok", False)
            return ActionResult(success=ok, expected_state=SetDetail, data=result)


class ClickStartChallenge(Action):
    """Click into the squad builder from SET_DETAIL page.
    Priority: challenge table row > 开始挑战 > 前往挑战."""

    def __init__(self):
        super().__init__("click_start_challenge")

    def execute(self, page):
        log("  [Action] click_start_challenge")
        body = get_page_text(page)
        if "提交" in body:
            log("    Already on squad builder (提交 visible)")
            return ActionResult(success=True, expected_state=SquadBuilder)

        # Priority 1: click challenge table row
        clicked = _js(page, """function() {
            var rows = document.querySelectorAll('.ut-sbc-challenge-table-row-view');
            for (var i = 0; i < rows.length; i++) {
                if (rows[i].offsetParent !== null) {
                    rows[i].scrollIntoView({block: 'center'});
                    var r = rows[i].getBoundingClientRect();
                    return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
                }
            }
            return null;
        }()""")
        if clicked and len(clicked) == 2:
            from src.utils import _click
            _click(page, clicked[0], clicked[1])
            log(f"    Clicked challenge row at ({clicked[0]}, {clicked[1]})")
            time.sleep(5)
            return ActionResult(success=True, expected_state=SquadBuilder)

        # Priority 2: text buttons
        for btn in ["开始挑战", "前往挑战"]:
            if btn in body:
                log(f"    Clicking '{btn}'...")
                if click_text(page, btn):
                    time.sleep(5)
                    log(f"    Clicked '{btn}', waiting for squad builder")
                    return ActionResult(success=True, expected_state=SquadBuilder)

        log(f"    Body snippet: {body[:500]}")
        from src.utils import get_visible_buttons
        btns = get_visible_buttons(page)
        log(f"    Visible buttons: {btns}")
        log("    No clickable challenge found")
        return ActionResult(success=False, expected_state=None)


class ClickFSUFill(Action):
    """Click FSU one-click fill button."""

    def __init__(self, fill_mode="auto", fallback_order=None):
        """
        fill_mode:
          "auto"     — try 一键填充(优先重复) then 阵容补全
          "one_click" — 一键填充(优先重复) only
          "lineup"    — 阵容补全 only
        """
        super().__init__("click_fsu_fill", fill_mode=fill_mode)
        if fill_mode == "auto":
            self.buttons = fallback_order or ["一键填充(优先重复)", "一键填充", "阵容补全"]
        else:
            self.buttons = fallback_order or [fill_mode]

    def execute(self, page):
        log(f"  [Action] click_fsu_fill (mode={self.kwargs['fill_mode']})")
        for btn_text in self.buttons:
            clicked = _js(page, f"""function() {{
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    var t = (btns[i].innerText || '').trim();
                    if (t === '{btn_text}' && btns[i].offsetParent !== null) {{
                        btns[i].click();
                        return 'clicked';
                    }}
                }}
                return 'not_found';
            }}()""")
            if clicked == 'clicked':
                log(f"    FSU '{btn_text}' clicked (JS)")
                time.sleep(5)
                return ActionResult(success=True, expected_state=SubmitReady)
        # Fallback: click_text with contains match
        for btn_text in self.buttons:
            if click_text(page, btn_text, timeout=3):
                log(f"    FSU '{btn_text}' clicked (click_text fallback)")
                time.sleep(5)
                return ActionResult(success=True, expected_state=SubmitReady)
        log("    No FSU fill button found")
        all_btns = _js(page, """function() {
            var b = document.querySelectorAll('button');
            return Array.from(b).filter(function(x) { return x.offsetParent !== null; }).map(function(x) {
                return (x.innerText || '').trim().substring(0, 40);
            });
        }()""")
        log(f"    Visible buttons on page: {all_btns}")
        return ActionResult(success=False, expected_state=None)


class ClickSubmit(Action):
    """Click the Submit button."""

    def __init__(self):
        super().__init__("click_submit")

    def execute(self, page):
        log("  [Action] click_submit")
        clicked = _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].innerText || '').trim();
                if ((t === '提交' || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                    btns[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }()""")
        if clicked == 'not_found':
            log("    Submit button not found")
            return ActionResult(success=False, expected_state=None)
        log("    Submit clicked")
        time.sleep(4)
        return ActionResult(success=True, expected_state=None)


class DismissFSUWarning(Action):
    """Dismiss FSU low-player warning by clicking 继续."""

    def __init__(self):
        super().__init__("dismiss_fsu_warning")

    def execute(self, page):
        log("  [Action] dismiss_fsu_warning")
        clicked = _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].innerText || '').trim();
                if ((t === '继续' || t.indexOf('Continue') >= 0) && btns[i].offsetParent !== null) {
                    btns[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }()""")
        if clicked == 'not_found':
            if click_text(page, "继续", timeout=3):
                log("    FSU warning dismissed (click_text fallback)")
                time.sleep(3)
                return ActionResult(success=True, expected_state=RewardReady)
            log("    No FSU warning found")
            return ActionResult(success=False, expected_state=None)
        log("    FSU warning dismissed (JS)")
        time.sleep(3)
        return ActionResult(success=True, expected_state=RewardReady)


class ClaimReward(Action):
    """Claim SBC reward."""

    def __init__(self):
        super().__init__("claim_reward")

    def execute(self, page):
        log("  [Action] claim_reward")
        clicked = _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].innerText || '').trim();
                if ((t === '领取' || t.indexOf('Claim') >= 0) && btns[i].offsetParent !== null) {
                    btns[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }()""")
        if clicked == 'not_found':
            if click_text(page, "领取", timeout=3):
                log("    Reward claimed (click_text fallback)")
                time.sleep(3)
                return ActionResult(success=True, expected_state=SBCHome)
            log("    No claim button")
            return ActionResult(success=False, expected_state=None)
        log("    Reward claimed (JS)")
        time.sleep(3)
        return ActionResult(success=True, expected_state=SBCHome)


class ClickConfirm(Action):
    """Click 确定 on a confirm dialog."""

    def __init__(self):
        super().__init__("click_confirm")

    def execute(self, page):
        log("  [Action] click_confirm")
        clicked = _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].innerText || '').trim();
                if ((t === '确定' || t === '确认' || t.indexOf('Confirm') >= 0) && btns[i].offsetParent !== null) {
                    btns[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }()""")
        if clicked == 'not_found':
            if click_text(page, "确定", timeout=3) or click_text(page, "确认", timeout=2):
                log("    Confirm clicked (click_text fallback)")
                time.sleep(2)
                return ActionResult(success=True, expected_state=SBCHome)
            log("    No confirm button")
            return ActionResult(success=False, expected_state=None)
        log("    Confirm clicked (JS)")
        time.sleep(2)
        return ActionResult(success=True, expected_state=SBCHome)


class GoBackToHub(Action):
    """Navigate back to SBC hub from inside an SBC."""

    def __init__(self):
        super().__init__("go_back_to_hub")

    def execute(self, page):
        log("  [Action] go_back_to_hub")
        click_sbc_nav(page)
        time.sleep(3)
        click_text(page, "返回", timeout=3)
        time.sleep(3)
        return ActionResult(success=True, expected_state=SBCHome)
