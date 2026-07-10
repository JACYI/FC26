# -*- coding: utf-8 -*-
"""Quick bronze + silver, skip gold. Uses step-by-step direct control."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

LOG_FILE = os.path.join(os.path.dirname(__file__), "bsg_log.txt")
def log(msg=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
    sys.stdout.flush()

from src.login import connect
from src.utils import wait_for_page
from src.sbc.executor import SBCExecutor
from src.sbc.config import ensure_fsu_config

p, browser, page = connect()
time.sleep(2)
log("=== BS Only Quick ===")

# Ensure on EA and SBC > Upgrades
from src.utils import get_page_state
state = get_page_state(page)
log(f"State: {state}")

executor = SBCExecutor(page)

# Navigate
if state != "sbc":
    executor.navigate_to_sbc("升级")
    time.sleep(3)

log("[OK] On SBC Upgrades")

for sbc_name in ["每日青铜升级", "每日白银升级"]:
    log(f"\n>>> {sbc_name}")

    # Scroll to find the SBC tile and click it by JS
    found = page.evaluate("""function(name) {
        var els = document.querySelectorAll('[class*="sbc"], [class*="SBC"], [class*="tile"], [class*="Tile"], a, button');
        for (var i = 0; i < els.length; i++) {
            var t = (els[i].innerText || '');
            if (t.indexOf(name) >= 0) {
                els[i].scrollIntoView({block: 'center'});
                setTimeout(function() { els[i].click(); }, 200);
                return true;
            }
        }
        return false;
    }""", sbc_name)
    log(f"  Clicked via JS: {found}")
    time.sleep(4)

    wait_for_page(page, timeout=10)

    # Check page
    body = page.inner_text("body")
    log(f"  Has 提交: {'提交' in body}, Has 一键填充: {'一键填充' in body}")

    # If segment list, click first segment
    if "个 SBC" in body and "提交" not in body:
        log("  Segment list page")
        seg_clicked = page.evaluate("""function() {
            var tiles = document.querySelectorAll('.ut-sbc-set-tile-view, [class*="set-tile"]');
            if (tiles.length > 0) {
                tiles[0].scrollIntoView({block: 'center'});
                tiles[0].click();
                return true;
            }
            return false;
        }()""")
        log(f"  Segment clicked: {seg_clicked}")
        time.sleep(3)
        wait_for_page(page, timeout=10)

    if "提交" not in page.inner_text("body"):
        log("  [X] Still not on squad builder")
        # Back to upgrades
        page.evaluate("""function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if (t.indexOf('SBC') >= 0) { btns[i].click(); return; }
            }
        }()""")
        time.sleep(2)
        page.locator("button").filter(has_text="升级").first.click(force=True, timeout=5000)
        time.sleep(3)
        continue

    log("  [OK] Squad builder ready")

    # FSU config
    ensure_fsu_config(page)

    # FSU fill
    filled = executor.try_fsu_autofill()
    if not filled:
        filled = executor.try_fsu_dupfill()

    if not filled:
        log("  [X] FSU fill failed")
        # Back to upgrades
        page.evaluate("""function() {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if (t.indexOf('SBC') >= 0) { btns[i].click(); return; }
            }
        }()""")
        time.sleep(2)
        page.locator("button").filter(has_text="升级").first.click(force=True, timeout=5000)
        time.sleep(3)
        continue

    log("  [OK] FSU filled")

    if not executor.is_submit_ready():
        log("  [X] Submit not ready")
        continue

    ok, msg, players, problem_players = executor.verify_squad()
    if not ok:
        log(f"  Squad issue: {msg}")
        executor.replace_players(problem_players)

    if executor.submit():
        log("  [OK] Submit done")
        executor.claim_reward()
        log(f"  [OK] {sbc_name} complete!")
    else:
        log(f"  [FAIL] {sbc_name} submit failed")

    # Back to SBC > Upgrades
    page.evaluate("""function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].innerText || '';
            if (t.indexOf('SBC') >= 0) { btns[i].click(); return; }
        }
    }()""")
    time.sleep(2)
    page.locator("button").filter(has_text="升级").first.click(force=True, timeout=5000)
    time.sleep(3)

log("\n[DONE] Gold SKIPPED. Only bronze + silver done.")
try:
    while browser.is_connected(): time.sleep(3)
except: pass
try: p.stop()
except: pass
