# -*- coding: utf-8 -*-
"""
Page state definitions for SBC automation.

Each state is a class with:
  - name: short string for logging
  - detect(page): static method returning True if page is in this state

Detection uses CDP _js() — raw JS querySelectorAll / innerText checks.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import _js


# ── State base ───────────────────────────────────────────────────────────

class SBCState:
    """Base class for page states."""
    name = ""

    @staticmethod
    def detect(page):
        return False


# ── State implementations ────────────────────────────────────────────────

class SBCHome(SBCState):
    """SBC page with tab bar and set list visible."""
    name = "SBC_HOME"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var t = document.body.innerText || '';
            // Tab bar has both '全部' and '升级' tabs — unique to SBC listing page
            var hasTabs = t.indexOf('全部') >= 0 && t.indexOf('升级') >= 0;
            // Set detail pages have '挑战状态' instead of tabs
            var noSetDetail = t.indexOf('挑战状态') < 0;
            var noSquadBuilder = t.indexOf('一键填充') < 0 && t.indexOf('阵容补全') < 0;
            return hasTabs && noSetDetail && noSquadBuilder;
        }()""")


class SetDetail(SBCState):
    """SBC group detail page showing set info and challenges."""
    name = "SET_DETAIL"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var t = document.body.innerText || '';
            // Set detail has '挑战状态' text (unique to SBC set detail page)
            var hasSetInfo = t.indexOf('挑战状态') >= 0;
            // Not on squad builder
            var noSquadBuilder = t.indexOf('一键填充') < 0 && t.indexOf('阵容补全') < 0;
            return hasSetInfo && noSquadBuilder;
        }()""")


class SquadBuilder(SBCState):
    """Squad builder page with 11 slots and FSU buttons."""
    name = "SQUAD_BUILDER"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var t = document.body.innerText || '';
            var hasFSU = t.indexOf('一键填充') >= 0 || t.indexOf('阵容补全') >= 0;
            if (!hasFSU) return false;
            // If submit is already enabled, let SubmitReady handle it
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var bt = btns[i].innerText || '';
                if ((bt.indexOf('提交') >= 0 || bt.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                    return btns[i].disabled === true;
                }
            }
            return true;
        }()""")


class SubmitReady(SBCState):
    """Squad meets requirements, Submit button is enabled."""
    name = "SUBMIT_READY"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if ((t.indexOf('提交') >= 0 || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                    return btns[i].disabled === false;
                }
            }
            return false;
        }()""")


class SubmitDisabled(SBCState):
    """Squad does NOT meet requirements, Submit button is disabled."""
    name = "SUBMIT_DISABLED"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if ((t.indexOf('提交') >= 0 || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                    return btns[i].disabled === true;
                }
            }
            return false;
        }()""")


class FSUWarning(SBCState):
    """FSU low-player warning dialog with 继续/返回 buttons."""
    name = "FSU_WARNING"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var t = document.body.innerText || '';
            var hasContinue = t.indexOf('继续') >= 0;
            var hasBack = t.indexOf('返回') >= 0;
            // FSU warning typically has both 继续 and 返回, but not squad builder
            return hasContinue && hasBack && t.indexOf('一键填充') < 0;
        }()""")


class RewardReady(SBCState):
    """Reward is available to claim (领取 button visible)."""
    name = "REWARD_READY"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if (t.indexOf('领取') >= 0 && btns[i].offsetParent !== null) {
                    return true;
                }
            }
            return false;
        }()""")


class ConfirmPopup(SBCState):
    """Generic confirm dialog with 确定 button."""
    name = "CONFIRM_POPUP"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if ((t.indexOf('确定') >= 0 || t.indexOf('确认') >= 0) && btns[i].offsetParent !== null) {
                    return true;
                }
            }
            return false;
        }()""")


class ErrorState(SBCState):
    """Unknown / unexpected page state."""
    name = "ERROR"

    @staticmethod
    def detect(page):
        return True  # Fallback — always matches


# ── Registry ─────────────────────────────────────────────────────────────

ALL_STATES = [
    SBCHome,
    SetDetail,
    SquadBuilder,      # FSU buttons present → highest priority in builder
    SubmitReady,       # Submit enabled, ready to submit
    SubmitDisabled,    # Submit disabled (fallback after SquadBuilder)
    FSUWarning,
    RewardReady,
    ConfirmPopup,
    ErrorState,  # Must be last (catch-all)
]
