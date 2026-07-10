# -*- coding: utf-8 -*-
"""
每日青铜/白银/普通黄金 升级 SBC 自动化
输出写入文件 bsg_log.txt 避免 GBK 编码问题
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Log to file (avoid GBK terminal issues) ────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "bsg_log.txt")
def log(msg=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
    sys.stdout.flush()

# ── Daily SBC list ─────────────────────────────────────────
DAILY_SBCS = [
    "每日青铜升级",
    "每日白银升级",
    "每日普通黄金升级",
]


def click_sbc_group(page, sbc_name):
    """Click an SBC group card by name using get_by_text locator."""
    try:
        page.get_by_text(sbc_name, exact=False).first.click(force=True, timeout=8000)
        time.sleep(3)
        return True
    except:
        return False


def is_submit_visible(page):
    """Check if Submit button is on the page (squad builder)."""
    return page.evaluate("""function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].innerText || "";
            if ((t.indexOf("提交") >= 0 || t.indexOf("Submit") >= 0) && btns[i].offsetParent !== null) {
                return true;
            }
        }
        return false;
    }()""")


def is_segment_list(page):
    """Check if current page shows SBC segments (group detail)."""
    body = page.inner_text("body")
    return body.count("个 SBC") >= 1 and not is_submit_visible(page)


def wait_for_fsu(page, timeout=60):
    """Wait for FSU plugin to load."""
    log("[FSU] Waiting for plugin to load...")
    for i in range(timeout):
        text = page.inner_text("body")
        if "【FSU】" in text:
            log(f"  FSU loaded after {i}s")
            return True
        if "正在读取球员数据" in text:
            pass
        time.sleep(1)
    log("  FSU timeout, checking DOM...")
    return page.evaluate('document.querySelectorAll("[class*=fsu]").length') >= 2


def run_one_sbc(page, executor, sbc_name):
    """Complete one daily upgrade SBC. Returns True if successful."""
    log()
    log("=" * 50)
    log(f"  >>> {sbc_name}")
    log("=" * 50)

    # Click into SBC group
    log(f"[NAV] Clicking '{sbc_name}'...")
    if not click_sbc_group(page, sbc_name):
        log(f"  [X] Could not find '{sbc_name}' on page")
        return False
    from src.utils import wait_for_page
    wait_for_page(page, timeout=10)

    # Check if we landed on squad builder or segment listing
    if is_segment_list(page):
        log("  -> Segment list page, clicking first segment...")
        try:
            page.locator(".ut-sbc-set-tile-view").first.click(force=True, timeout=5000)
            time.sleep(3)
        except:
            log("  [X] Could not find segment to click")
            return False
        wait_for_page(page, timeout=10)

    if not is_submit_visible(page):
        log("  [X] Not on squad builder page")
        return False
    log("  [OK] Squad builder page")

    # Configure FSU
    executor.configure_fsu()

    # FSU auto-fill
    if executor.try_fsu_autofill():
        log("  [OK] FSU auto-fill done")
    elif executor.try_fsu_dupfill():
        log("  [OK] FSU duplicate fill done")
    else:
        log("  [X] No FSU button available")
        return False

    if not executor.is_submit_ready():
        log("  [X] Submit not ready after fill")
        return False

    # Verify squad before submit (BSG-specific rule: no expensive gold cards)
    ok, msg, players, problem_players = executor.verify_squad()
    if not ok:
        log(f"  [!] Squad has {len(problem_players)} problematic player(s):")
        for p in problem_players:
            log(f"      Slot {p.get('index')}: {p.get('name')} (OVR {p.get('ovr')})")
        log("  [REPLACE] Attempting to replace...")
        if executor.replace_players(problem_players):
            log("  [OK] Replacement done, re-verifying...")
            ok, msg, players, problem_players = executor.verify_squad()
        if not ok:
            log(f"  [X] Could not fix squad, skipping: {msg}")
            return False
    log("  [OK] Squad verified, proceeding...")

    if not executor.submit():
        log("  [X] Submit failed")
        return False

    executor.claim_reward()
    log(f"  [OK] {sbc_name} done!")

    # Navigate back to SBC > Upgrades for next SBC (Chinese UI)
    log("[NAV] Back to SBC > Upgrades...")
    try:
        page.locator("button").filter(has_text="SBC").first.click(force=True, timeout=5000)
        time.sleep(2)
    except:
        pass
    try:
        page.locator("button").filter(has_text="升级").first.click(force=True, timeout=5000)
        time.sleep(3)
    except:
        pass
    return True


def main():
    log("=" * 50)
    log("EA FC 26 - BSG Upgrade")
    log("=" * 50)

    from src.utils import connect

    log("\n[CONNECT] Connecting to Chrome...")
    p, browser, page = connect()
    time.sleep(2)

    from src.utils import get_page_state
    state = get_page_state(page)
    log(f"  State: {state}")
    if state == "login_page":
        log("  Login required - run scripts/login.py first")
        return

    wait_for_fsu(page)

    from src.sbc.executor import SBCExecutor
    executor = SBCExecutor(page)

    log("\n[NAV] SBC > Upgrades...")
    if not executor.navigate_to_sbc("升级"):
        log("  Navigation failed")
        return

    results = {}
    for sbc_name in DAILY_SBCS:
        ok = run_one_sbc(page, executor, sbc_name)
        results[sbc_name] = "OK" if ok else "FAIL"
        time.sleep(2)

    log()
    log("=" * 50)
    log("RESULTS")
    log("=" * 50)
    for name, status in results.items():
        log(f"  [{status}] {name}")

    ok_count = sum(1 for s in results.values() if s == "OK")
    log(f"\n{ok_count}/{len(results)} completed")
    log(f"\nFull log: {LOG_FILE}")

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
