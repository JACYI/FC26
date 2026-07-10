# -*- coding: utf-8 -*-
"""Check daily SBC task status — read-only, no execution."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import connect, _js, click_sbc_nav, navigate_sbc_category, go_to_sbc_hub

p = connect()
page = p

# Check page state
body = _js(page, "document.body.innerText.substring(0, 500)") or ""
print(f"[STATE] Page body (first 500 chars):\n  {repr(body[:200])}")

if "Login" in body and "SBC" not in body:
    print("[STATE] → Login page — need to login first")
    p.stop()
    sys.exit(1)

# Navigate to SBC
print("\n[NAV] Clicking SBC nav...")
sbc_ok = click_sbc_nav(page)
print(f"  SBC nav: {'OK' if sbc_ok else 'FAILED'}")
time.sleep(4)

# Switch to Upgrades
print("[NAV] Switching to Upgrades tab...")
r = navigate_sbc_category(page, "升级", 2)
print(f"  Result: {json.dumps(r, ensure_ascii=False)}")
time.sleep(2)

# Scan ALL sets
print("\n[SCAN] Reading all SBC sets...")
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
        return JSON.stringify(r);
    } catch(e) {
        return JSON.stringify({error: e.message});
    }
}()""")

data = json.loads(result) if isinstance(result, str) else result

if "error" in data:
    print(f"[SCAN] Error: {data['error']}")
else:
    print(f"[SCAN] Found {len(data)} SBCs in Upgrades:\n")
    # Print nicely
    for name, info in sorted(data.items()):
        status = "DONE" if info["complete"] else "PENDING"
        repeats = f"{info['repeatsLeft']}/{info['maxRepeats']}" if info['maxRepeats'] else "∞"
        print(f"  [{status}] {name}")
        print(f"          repeats: {repeats} | completed: {info['timesCompleted']}x")

print("\n" + "=" * 50)
print("Browser stays open. Press Ctrl+C in terminal to close.")
print("=" * 50)

try:
    while p._loop and p._loop.is_running():
        time.sleep(10)
except (KeyboardInterrupt, SystemExit):
    pass
except:
    pass
finally:
    try: p.stop()
    except: pass
