# -*- coding: utf-8 -*-
"""
EA FC 26 Web App - Login Module

Handles Chrome launch, CDP connection, login flow with all edge cases:
  - Session valid (already logged in) → skip
  - Login page → email → password → 2FA verification
  - 2FA with SEND CODE → code from user → submit
  - FSU detection after login

Usage as CLI:
    python -m src.login                    # Launch Chrome + login
    python -m src.login --no-launch        # Connect to running Chrome only

Usage as module:
    from src.login import connect, do_login, check_fsu
    p, browser, page = connect()
    do_login(page)
    check_fsu(page)
"""
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

# ── Configuration ──────────────────────────────────────────────
EA_URL = "https://www.ea.com/ea-sports-fc/ultimate-team/web-app/"
CDP_URL = "http://127.0.0.1:9222"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_PROFILE = "Profile 1"

# ── Credentials (stored locally, not committed) ────────────────
EMAIL = "3079479814@qq.com"
PASSWORD = "Yyh3079479814"


# ── Helpers ────────────────────────────────────────────────────
def log(msg):
    print(msg)
    sys.stdout.flush()


def js_click(page, selector):
    """Click element via JavaScript — supports CSS selectors and text-based :has-text()."""
    if ":has-text(" in selector:
        # Playwright :has-text() pseudo-selector — not supported by querySelector
        # Parse: "button:has-text('Login')" → tag=button, text=Login
        import re
        m = re.match(r'(\w+)?:has-text\(\'([^\']+)\'\)', selector)
        tag = m.group(1) if m and m.group(1) else "*"
        text = m.group(2) if m else selector
        return page.evaluate("""(args) => {
            var els = document.querySelectorAll(args.tag);
            for (var i = 0; i < els.length; i++) {
                if ((els[i].innerText || "").indexOf(args.text) >= 0) {
                    els[i].click();
                    return true;
                }
            }
            return false;
        }""", {"tag": tag, "text": text})

    return page.evaluate("""(sel) => {
        var el = document.querySelector(sel);
        if (el) { el.click(); return true; }
        return false;
    }""", selector)


def _click_btn(page, text, timeout=5):
    """Click a button by its text using Playwright locator (handles :has-text natively)."""
    try:
        page.locator(f"button:has-text('{text}')").first.wait_for(state="visible", timeout=timeout * 1000)
        page.locator(f"button:has-text('{text}')").first.click(force=True, timeout=timeout * 1000)
        return True
    except Exception:
        return False


def wait_for_text(page, text, timeout=15):
    """Wait until text appears in page body, polling every 0.5s."""
    for _ in range(timeout * 2):
        if text in page.inner_text("body"):
            return True
        time.sleep(0.5)
    return False


# ── State Detection ───────────────────────────────────────────
def get_state(page):
    """Detect current EA Web App login/page state."""
    url = page.url
    body = page.inner_text("body")

    if "ultimate-team/web-app" in url:
        if "SBC" in body and ("Home" in body or "Squads" in body or "主页" in body):
            return "logged_in"
        if any(kw in body for kw in ["Login", "登录"]) and \
           any(kw in body for kw in ["Find out more", "浏览更多", "User Agreement", "用户协议"]):
            return "login_page"
        return "loading"

    if "signin.ea.com" in url:
        if page.locator("#twoFactorCode").is_visible(timeout=1000):
            return "verify_code"
        if page.locator("#password").is_visible(timeout=1000):
            return "password_form"
        if page.locator("#email").is_visible(timeout=1000):
            return "email_form"
        return "signin_unknown"

    if "ea.com" in url:
        return "other_ea_page"

    return "off_ea"


# ── Chrome / CDP ──────────────────────────────────────────────
def launch_chrome():
    """Launch Chrome with remote debugging port and Profile 1."""
    log("[CHROME] Launching Chrome (Profile 1, debug port 9222)...")
    subprocess.Popen([
        CHROME_PATH,
        "--remote-debugging-port=9222",
        "--profile-directory=" + CHROME_PROFILE,
    ])
    for i in range(30):
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2)
            log("  Chrome ready")
            return True
        except Exception:
            time.sleep(1)
    log("  FAILED to start Chrome")
    return False


def connect():
    """Connect to Chrome via CDP. Launch if needed. Returns (playwright, browser, page)."""
    try:
        import urllib.request
        urllib.request.urlopen(CDP_URL + "/json/version", timeout=2)
        log("[CONNECT] Connecting to existing Chrome...")
    except Exception:
        if "--no-launch" in sys.argv:
            log("[CONNECT] Chrome not running and --no-launch specified. Aborting.")
            return None, None, None
        log("[CONNECT] Chrome not running on 9222.")
        if not launch_chrome():
            return None, None, None

    p = sync_playwright().start()
    browser = p.chromium.connect_over_cdp(CDP_URL)
    page = _find_ea_page(browser)
    if not page:
        log("[CONNECT] No EA page found, opening new tab...")
        page = browser.contexts[0].new_page()
        page.goto(EA_URL, wait_until="domcontentloaded", timeout=60000)
    return p, browser, page


def _find_ea_page(browser):
    """Search all contexts and pages for one with EA Web App."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "ultimate-team/web-app" in pg.url:
                log(f"  Found EA page at {pg.url[:60]}...")
                return pg
    return None


# ── Navigation ────────────────────────────────────────────────
def navigate_to_ea(page):
    """Ensure we're on the EA Web App page."""
    if "ultimate-team/web-app" not in page.url:
        log("[NAV] Opening EA Web App...")
        try:
            page.goto(EA_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            log(f"  goto() aborted ({str(e)[:40]}), waiting for existing navigation...")
            time.sleep(10)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    # Auto-login animation can take 15-20s, use 30s timeout to be safe
    wait_for_text(page, "SBC", timeout=30)
    time.sleep(3)
    return page


# ── Login Flow ────────────────────────────────────────────────
def do_login(page):
    """
    Main login routine. Handles all states:
      1. Already logged in → return True
      2. Login page → click Login
      3. Email form → fill email → NEXT
      4. Password form → fill password → Sign In
      5. 2FA code → send code, ask user, submit
    """
    state = get_state(page)
    log(f"[STATE] {state}")

    if state == "logged_in":
        log("  Already logged in!")
        return True

    if state == "login_page":
        log("[LOGIN] Clicking Login button...")
        if not _click_btn(page, "Login"):
            _click_btn(page, "登录")
        time.sleep(5)
        return do_login(page)

    if state == "email_form":
        log("[LOGIN] Entering email...")
        page.locator("#email").fill(EMAIL)
        time.sleep(1)
        log("  Clicking NEXT...")
        js_click(page, "#logInBtn")
        time.sleep(3)
        return do_login(page)

    if state == "password_form":
        log("[LOGIN] Entering password...")
        page.locator("#password").fill(PASSWORD)
        time.sleep(1)
        log("  Clicking Sign In...")
        if not js_click(page, "#logInBtn"):
            if not _click_btn(page, "Sign"):
                if not _click_btn(page, "登录"):
                    page.keyboard.press("Enter")
        time.sleep(5)
        return do_login(page)

    if state == "verify_code":
        log("[2FA] Verification code required.")
        return handle_verification_code(page)

    if state == "loading":
        log("  Page loading (auto-login may be in progress)...")
        time.sleep(5)
        return do_login(page)

    log(f"  Unknown state, waiting 5s...")
    time.sleep(5)
    state = get_state(page)
    if state in ("email_form", "password_form", "verify_code", "login_page"):
        return do_login(page)
    log(f"  Still unknown after wait. URL: {page.url[:80]}")
    return False


def handle_verification_code(page):
    """Handle 2FA: send code → user provides → submit."""
    body = page.inner_text("body")

    if "SEND CODE" in body:
        log("  Sending verification code...")
        page.keyboard.press("Tab")
        time.sleep(0.3)
        page.keyboard.press("Tab")
        time.sleep(0.3)
        page.keyboard.press("Enter")
        time.sleep(3)
        log("  Code sent to email.")
        wait_for_text(page, "Enter your code", timeout=10)

    print("\n" + "=" * 50)
    print("  *** VERIFICATION CODE REQUIRED ***")
    print("  Check your email (30*****@qq.com) for the code,")
    print("  including spam/promotions folders.")
    print("  Enter the 6-digit code below when you have it.")
    print("=" * 50)
    code = prompt("Verification code: ")
    if not code:
        log("  No code provided, aborting verification.")
        return False

    page.locator("#twoFactorCode").fill(code)
    time.sleep(1)

    page.evaluate("""
        var cb = document.getElementById('trustThisDevice');
        if (cb && !cb.checked) { cb.checked = true; }
    """)
    log("  Trust this device: checked")

    log("  Submitting code...")
    js_click(page, "#btnSubmit")

    for i in range(20):
        time.sleep(3)
        if "ultimate-team/web-app" in page.url:
            log("  Login complete!")
            return True
        log(f"  Waiting for redirect... ({page.url[:60]})")

    return "ultimate-team/web-app" in page.url


def prompt(prompt_text, default=""):
    """Prompt user for input. Returns default if non-interactive."""
    try:
        if sys.stdin.isatty():
            return input(prompt_text).strip()
    except Exception:
        pass
    log(f"  (non-interactive, default='{default}')")
    return default


# ── FSU Detection ─────────────────────────────────────────────
def check_fsu(page):
    """Check if FSU plugin is loaded; offer refresh if not."""
    if _fsu_detected(page):
        log("[FSU] Plugin detected and ready.")
        return True

    log("[FSU] Plugin NOT detected yet.")
    print("\n  FSU (Tampermonkey userscript) not detected.")
    print("  A page refresh will trigger Tampermonkey to load it.")
    answer = prompt("  Refresh page to load FSU? [Y/n]: ").lower()

    if answer not in ("", "y", "yes"):
        log("[FSU] Skipping refresh.")
        return False

    log("[FSU] Refreshing page to load FSU...")
    page.reload()
    if not _wait_for_ea_app(page, timeout=60):
        log("  EA app did not finish loading within 60s.")
        return False

    log("  Waiting for FSU to initialize...")
    for i in range(30):
        if _fsu_detected(page):
            log(f"  FSU detected after refresh ({i + 1}s)!")
            return True
        time.sleep(2)

    log("[FSU] Still not detected after refresh + wait.")
    return False


def _fsu_detected(page):
    """Check multiple FSU indicators."""
    body = page.inner_text("body")
    if "【FSU】" in body:
        return True
    fsu_count = page.evaluate(
        "document.querySelectorAll('[class*=fsu]').length"
    )
    if fsu_count >= 2:
        return True
    if "正在读取球员数据" in body:
        return True
    return False


def _wait_for_ea_app(page, timeout=30):
    """Wait for the EA Web App to finish loading (animations + auto-login)."""
    log("  Waiting for EA app to load...")
    for i in range(timeout):
        url = page.url
        body = page.inner_text("body")
        if "ultimate-team/web-app" in url and "SBC" in body:
            return True
        time.sleep(1)
    return False


# ── Main ───────────────────────────────────────────────────────
def main():
    log("=" * 45)
    log("EA FC 26 Web App — Login")
    log("=" * 45)

    p, browser, page = connect()
    if not page:
        return

    navigate_to_ea(page)

    if do_login(page):
        check_fsu(page)
        log("\n[DONE] Browser is ready. Keeping it open...")
        try:
            while browser.is_connected():
                time.sleep(3)
        except KeyboardInterrupt:
            pass
    else:
        log("\n[FAIL] Login did not complete successfully.")

    try:
        p.stop()
    except Exception:
        pass


if __name__ == "__main__":
    main()
