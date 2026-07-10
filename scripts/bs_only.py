# -*- coding: utf-8 -*-
"""Bronze & Silver daily only - skip gold."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

LOG_FILE = os.path.join(os.path.dirname(__file__), "bsg_log.txt")
def log(msg=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
    sys.stdout.flush()

from src.utils import connect, wait_for_page
from src.sbc.executor import SBCExecutor

log("=" * 50)
log("Bronze & Silver Only")
log("=" * 50)

p, browser, page = connect()
time.sleep(2)

state = page.inner_text("body")
if "登录" in state and "Login" in state:
    log("Login required - run scripts/login.py first")
    exit()

# Wait for FSU
for i in range(60):
    if "【FSU】" in page.inner_text("body"):
        log(f"  FSU loaded after {i}s")
        break
    time.sleep(1)

executor = SBCExecutor(page)

# Navigate to SBC > Upgrades
if not executor.navigate_to_sbc("升级"):
    log("Navigation failed")
    exit()

# Do bronze then silver
for sbc_name in ["每日青铜升级", "每日白银升级"]:
    log(f"\n>>> {sbc_name}")

    # Click into SBC
    try:
        page.get_by_text(sbc_name, exact=False).first.click(force=True, timeout=8000)
        time.sleep(3)
    except:
        log(f"  Could not find '{sbc_name}'")
        continue

    wait_for_page(page, timeout=10)

    # Check if segment list page
    has_submit = page.evaluate("""function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].innerText || "";
            if ((t.indexOf("提交") >= 0 || t.indexOf("Submit") >= 0) && btns[i].offsetParent !== null)
                return true;
        }
        return false;
    }()""")

    if not has_submit and "个 SBC" in page.inner_text("body"):
        log("  Segment list, clicking first...")
        try:
            page.locator(".ut-sbc-set-tile-view").first.click(force=True, timeout=5000)
            time.sleep(3)
        except:
            log("  No segment tile found")
            continue
        wait_for_page(page, timeout=10)

    # Configure FSU
    executor.configure_fsu()

    # FSU fill
    if executor.try_fsu_autofill():
        log("  FSU auto-fill OK")
    elif executor.try_fsu_dupfill():
        log("  FSU dup-fill OK")
    else:
        log("  No FSU button")
        continue

    if not executor.is_submit_ready():
        log("  Submit not ready")
        continue

    # Submit
    ok, msg, players, problem_players = executor.verify_squad()
    if not ok:
        log(f"  Squad issue: {msg}, replacing...")
        executor.replace_players(problem_players)

    if executor.submit():
        log("  Submit OK")
        executor.claim_reward()
        log(f"  [OK] {sbc_name} done!")
    else:
        log(f"  [FAIL] {sbc_name}")

    # Back to SBC > Upgrades
    try:
        page.locator("button").filter(has_text="SBC").first.click(force=True, timeout=5000)
        time.sleep(2)
    except: pass
    try:
        page.locator("button").filter(has_text="升级").first.click(force=True, timeout=5000)
        time.sleep(3)
    except: pass

log("\nDone! Gold was SKIPPED.")
try:
    while browser.is_connected(): time.sleep(3)
except: pass
try: p.stop()
except: pass
