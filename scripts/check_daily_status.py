# -*- coding: utf-8 -*-
"""
Check daily SBC task status.
1. Connect → ensure logged in (PageMachine)
2. Navigate to SBC → Upgrades tab
3. Scan ALL upgrade SBCs status
4. Print report to UTF-8 file (avoids Windows GBK encoding issues)
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright
from src.page_machine import PageMachine
from src.page_states import LoggedIn
from src.utils import _js, click_sbc_nav, navigate_sbc_category

CDP_URL = "http://127.0.0.1:9222"
EMAIL = "3079479814@qq.com"
PASSWORD = "Yyh3079479814"
OUT_FILE = os.path.join(os.path.dirname(__file__), "..", "sbc_status_report.txt")

def log(msg):
    print(msg)
    sys.stdout.flush()

log("=" * 55)
log("FC26 Daily SBC Status Check")
log("=" * 55)

# ── Connect ──
log("[1/4] Connecting to Chrome...")
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(CDP_URL)

page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team" in pg.url:
            page = pg
            break
    if page: break

if not page:
    page = browser.contexts[0].new_page()
    page.goto("https://www.ea.com/ea-sports-fc/ultimate-team/web-app/",
              wait_until="domcontentloaded", timeout=60000)

# ── Login ──
log("[2/4] Ensuring logged in (PageMachine)...")
machine = PageMachine(page, email=EMAIL, password=PASSWORD, interactive=True)
result = machine.run(goal_state=LoggedIn)

if not result["success"]:
    log(f"[FAIL] Login failed: {result.get('error')}")
    p.stop()
    sys.exit(1)

log(f"[OK] Logged in ({result['cycles']} cycles)")

# ── Navigate SBC → Upgrades ──
log("[3/4] Navigating to SBC > Upgrades...")
click_sbc_nav(page)
time.sleep(3)

nav = navigate_sbc_category(page, cat_name="升级", cat_id=2)
log(f"  {nav}")
time.sleep(2)

# ── Scan ALL SBCs via VM API ──
log("[4/4] Scanning all SBC status...")
result = _js(page, """function() {
    try {
        var vm = getAppMain()._rootViewController.currentController
            .childViewControllers[5].currentController._viewmodel;
        var sets = vm.getSetsByCurrentCategory();
        var r = {};
        for (var i = 0; i < sets.length; i++) {
            try {
                var s = sets[i];
                r[s.name] = {
                    complete: s.isComplete(),
                    repeatsLeft: s.getRepeatsRemaining(),
                    timesCompleted: s.timesCompleted,
                    maxRepeats: s.repeats
                };
            } catch(e) {}
        }
        return JSON.stringify(r, null, 2);
    } catch(e) {
        return JSON.stringify({error: e.message});
    }
}()""")

# ── Write report to UTF-8 file ──
lines = []
lines.append("=" * 60)
lines.append("FC26 SBC Upgrades Status Report")
lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("=" * 60)
lines.append("")

try:
    data = json.loads(result) if isinstance(result, str) else result
except:
    data = {"error": str(result)[:200]}

if isinstance(data, dict) and "error" not in data:
    # Categorize
    available = []    # repeatsLeft > 0 OR (maxRepeats == 0 AND not complete)
    unlimited = []    # maxRepeats == 0, repeatsLeft == 0 (still doable)
    completed = []    # complete == True
    expired = []      # repeatsLeft == 0 AND maxRepeats > 0

    for name, info in sorted(data.items()):
        if not isinstance(info, dict):
            continue
        if info.get("complete"):
            completed.append((name, info))
        elif info.get("repeatsLeft", 0) > 0:
            available.append((name, info))
        elif info.get("maxRepeats", 0) == 0:
            unlimited.append((name, info))
        else:
            expired.append((name, info))

    lines.append(f"Total SBCs: {len(data)}")
    lines.append("")

    # ── Available (with repeats remaining) ──
    lines.append("─" * 60)
    lines.append(f"AVAILABLE (repeats remaining): {len(available)}")
    lines.append("─" * 60)
    for name, info in available:
        rl = info["repeatsLeft"]
        mr = info["maxRepeats"]
        tc = info["timesCompleted"]
        lines.append(f"  [DO] {name}")
        lines.append(f"       left: {rl}/{mr} | done: {tc}x")
    lines.append("")

    # ── Unlimited (no max, no repeats counter) ──
    lines.append("─" * 60)
    lines.append(f"UNLIMITED (always available): {len(unlimited)}")
    lines.append("─" * 60)
    for name, info in unlimited:
        tc = info["timesCompleted"]
        lines.append(f"  [UN] {name}")
        lines.append(f"       done: {tc}x")
    lines.append("")

    # ── Completed ──
    if completed:
        lines.append("─" * 60)
        lines.append(f"COMPLETED: {len(completed)}")
        lines.append("─" * 60)
        for name, info in completed:
            lines.append(f"  [OK] {name}")
        lines.append("")

    # ── Expired ──
    if expired:
        lines.append("─" * 60)
        lines.append(f"EXPIRED: {len(expired)}")
        lines.append("─" * 60)
        for name, info in expired:
            lines.append(f"  [--] {name}")
        lines.append("")

else:
    lines.append(f"ERROR: {data}")

lines.append("=" * 60)
lines.append("Browser kept open.")

report = "\n".join(lines)

# Write file
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(report + "\n")

# Also dump raw JSON for reference
raw_file = OUT_FILE.replace(".txt", "_raw.json")
with open(raw_file, "w", encoding="utf-8") as f:
    f.write(result + "\n" if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2) + "\n")

# Print summary to console (ASCII-safe)
log(f"\nReport written to: {OUT_FILE}")
log(f"Raw data: {raw_file}")
log(f"\nSummary:")
log(f"  Available (with repeats): {len(available)}")
log(f"  Unlimited:                {len(unlimited)}")
log(f"  Completed:                {len(completed)}")
log(f"  Expired:                  {len(expired)}")
for name, info in available:
    log(f"    [DO] {name}  ({info['repeatsLeft']}/{info['maxRepeats']})")

log(f"\n{'=' * 55}")
log("Browser kept open. Ctrl+C to exit.")
log(f"{'=' * 55}")

try:
    while browser.is_connected():
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    try: p.stop()
    except: pass
