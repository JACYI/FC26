# -*- coding: utf-8 -*-
"""
Page-level state definitions: from blank page → logged-in app.

Each state is a class with:
  - name: short string for logging
  - detect(page): static method returning True if page is in this state

Detection uses _js() — works with both raw CDP and Playwright pages.
Designed to be used by PageMachine (src/page_machine.py).
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.utils import _js


# ── Known EA dialog dismiss buttons ─────────────────────────────────────────
# Shared between DialogOverlay detector and dismiss action.
# Ordered by priority: button texts checked at the start of body text first.
DIALOG_DISMISS_BUTTONS = [
    "了解",       # What's New / 新功能 dialog
    "知道了",     # Generic info dialog
    "Got it",     # English What's New
    "OK",
    "关闭",       # Close button
    "确定",       # Generic confirm
    "确认",       # Alternative confirm
]


class PageState:
    """Base class for page states."""
    name = ""

    @staticmethod
    def detect(page):
        return False


class Unknown(PageState):
    """Catch-all: none of the known states matched."""
    name = "UNKNOWN"

    @staticmethod
    def detect(page):
        return True  # Always matches — must be last in registry


class Loading(PageState):
    """
    SPA loading animation or blank page.
    - readyState may still be 'complete' from SPA shell
    - body either empty or just <title> text
    - getAppMain() not yet available
    """
    name = "LOADING"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var hasGam = typeof getAppMain !== 'undefined';
                var body = document.body.innerText || '';
                var isThin = body.length < 80;
                var noSBC = body.indexOf('SBC') < 0;
                var noLogin = body.indexOf('登录') < 0 && body.indexOf('Login') < 0;
                // On EA domain but no app state → still loading
                var onEA = window.location.href.indexOf('ultimate-team') >= 0;
                return onEA && (isThin || !hasGam) && noSBC && noLogin;
            } catch(e) {
                return false;
            }
        }()""")


class LoginPage(PageState):
    """
    EA landing page: "登录" / "Login" button visible.
    - URL: ultimate-team/web-app/
    - Body contains login button text + user agreement / cookie notice
    - getAppMain() may or may not be available
    """
    name = "LOGIN_PAGE"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var body = document.body.innerText || '';
                var hasLogin = body.indexOf('登录') >= 0 || body.indexOf('Login') >= 0;
                if (!hasLogin) return false;
                var onEA = window.location.href.indexOf('ultimate-team') >= 0;
                if (!onEA) return false;
                var noSBC = body.indexOf('SBC') < 0;
                if (!noSBC) return false;

                // Must have a visible login button (exact text match)
                var btns = document.querySelectorAll('button');
                var hasLoginBtn = false;
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].offsetParent === null) continue;
                    var t = (btns[i].innerText || '').trim();
                    if (t === '登录' || t.indexOf('Login') >= 0 || t === '登录/注册') {
                        hasLoginBtn = true; break;
                    }
                }
                if (!hasLoginBtn) return false;

                var hasAgreement = body.indexOf('用户协议') >= 0 || body.indexOf('User Agreement') >= 0
                                || body.indexOf('Cookie') >= 0 || body.indexOf('FSU') >= 0;
                return hasAgreement;
            } catch(e) {
                return false;
            }
        }()""")


class EmailForm(PageState):
    """
    EA sign-in: email input visible.
    - URL: signin.ea.com
    - #email element present and visible
    """
    name = "EMAIL_FORM"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var url = window.location.href;
                if (url.indexOf('signin.ea.com') < 0) return false;
                var el = document.getElementById('email');
                return el !== null && el.offsetParent !== null;
            } catch(e) {
                return false;
            }
        }()""")


class PasswordForm(PageState):
    """
    EA sign-in: password input visible.
    - URL: signin.ea.com
    - #password element present and visible
    """
    name = "PASSWORD_FORM"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var url = window.location.href;
                if (url.indexOf('signin.ea.com') < 0) return false;
                var el = document.getElementById('password');
                return el !== null && el.offsetParent !== null;
            } catch(e) {
                return false;
            }
        }()""")


class VerifyCode(PageState):
    """
    2FA verification: code input visible.
    - URL: signin.ea.com
    - #twoFactorCode input present and visible
    """
    name = "VERIFY_CODE"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var url = window.location.href;
                if (url.indexOf('signin.ea.com') < 0) return false;
                var el = document.getElementById('twoFactorCode');
                return el !== null && el.offsetParent !== null;
            } catch(e) {
                return false;
            }
        }()""")


class FSULoading(PageState):
    """
    FSU plugin loading player data.
    - Body contains '正在读取球员数据' or 'Loading player' text
    - Only active when the main app UI is NOT yet rendered.
      If SBC/Home is present alongside FSU loading text, the page is
      considered LOGGED_IN (FSU loads in background after login).
    - Transient — poller waits for this to resolve.
    """
    name = "FSU_LOADING"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var body = document.body.innerText || '';
                var isLoading = body.indexOf('正在读取球员数据') >= 0
                    || body.indexOf('Loading player') >= 0;
                if (!isLoading) return false;
                // Only FSULoading if main app UI isn't ready yet
                var appReady = body.indexOf('SBC') >= 0;
                return !appReady;
            } catch(e) {
                return false;
            }
        }()""")


class DialogOverlay(PageState):
    """
    EA dialog/popup overlay on top of the main app.
    - Appears after login or page transitions (What's New, Welcome, promos)
    - Body has both app UI (SBC, Home) AND dialog keywords + dismiss button
    - Transient — should be dismissed before treating page as truly LOGGED_IN

    Detection: app UI present + known dialog keyword + dismiss button visible
    """
    name = "DIALOG_OVERLAY"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var body = document.body.innerText || '';
                var hasApp = body.indexOf('SBC') >= 0;
                if (!hasApp) return false;

                // Known EA dialog keywords
                var kw = ['What\\'s New', '新功能', 'Welcome', '欢迎',
                          'What\\'s Hot', '热门', '了解', '提示'];
                var hasKW = false;
                for (var i = 0; i < kw.length; i++) {
                    if (body.indexOf(kw[i]) >= 0) { hasKW = true; break; }
                }
                if (!hasKW) return false;

                // Check for a dismiss button (visible, not disabled)
                var btns = document.querySelectorAll('button');
                var dismissTexts = ['了解', '知道了', 'Got it', 'OK',
                                    '关闭', '确定', '确认'];
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].offsetParent === null || btns[i].disabled) continue;
                    var t = (btns[i].innerText || '').trim();
                    for (var j = 0; j < dismissTexts.length; j++) {
                        if (t === dismissTexts[j] || t.indexOf(dismissTexts[j]) >= 0) {
                            return true;
                        }
                    }
                }
                return false;
            } catch(e) {
                return false;
            }
        }()""")


class EnglishUI(PageState):
    """
    App is logged in but UI is in English when Simplified Chinese is expected.
    - Body has SBC + English nav labels (Squads, Home)
    - Chinese nav labels (阵容, 主页) are absent
    - Action: switch language via Settings → Select Language → 简体中文
    """
    name = "ENGLISH_UI"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var body = document.body.innerText || '';
                var url = window.location.href;
                if (url.indexOf('ultimate-team') < 0) return false;
                var hasSBC = body.indexOf('SBC') >= 0;
                if (!hasSBC) return false;
                // English indicators (nav labels)
                var hasSquads = body.indexOf('Squads') >= 0;
                var hasHome = body.indexOf('Home') >= 0;
                // Chinese equivalents absent → English UI
                var noChineseNav = body.indexOf('阵容') < 0 && body.indexOf('主页') < 0;
                return (hasSquads || hasHome) && noChineseNav;
            } catch(e) {
                return false;
            }
        }()""")


class LoggedIn(PageState):
    """
    EA app main interface: logged in.
    - URL: ultimate-team/web-app/
    - Body contains SBC nav item and at least one main section (Home / Squads / 主页)
    """
    name = "LOGGED_IN"

    @staticmethod
    def detect(page):
        return _js(page, """function() {
            try {
                var body = document.body.innerText || '';
                var url = window.location.href;
                var onEA = url.indexOf('ultimate-team') >= 0;
                if (!onEA) return false;
                var hasSBC = body.indexOf('SBC') >= 0;
                var hasHome = body.indexOf('Home') >= 0 || body.indexOf('主页') >= 0;
                var hasSquads = body.indexOf('Squads') >= 0;
                return hasSBC && (hasHome || hasSquads);
            } catch(e) {
                return false;
            }
        }()""")


# ── Registry ──
# Order matters: more specific states first, catch-all (Unknown) last.
ALL_PAGE_STATES = [
    Loading,
    LoginPage,
    EmailForm,
    PasswordForm,
    VerifyCode,
    FSULoading,
    DialogOverlay,    # Before LoggedIn — dismiss dialogs before declaring ready
    EnglishUI,        # Before LoggedIn — switch language if needed
    LoggedIn,
    Unknown,  # catch-all — must be last
]
