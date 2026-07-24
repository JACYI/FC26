# -*- coding: utf-8 -*-
"""Complete Bronze/Silver SBC via direct VC push navigation."""
import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.cdp_shell import connect

LOG_FILE = os.path.join(os.path.dirname(__file__), "bsg_cdp_log.txt")

async def mouse_click(page, x, y):
    await page.send_faf('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    await asyncio.sleep(0.05)
    await page.send_faf('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

async def find_btn_pos(page, text, exact=False):
    """Find button containing (or matching) text."""
    if exact:
        return await page.js(f"""function() {{
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {{
                if ((btns[i].innerText || '').trim() === '{text}' && btns[i].offsetParent !== null) {{
                    btns[i].scrollIntoView({{block: 'center'}});
                    var r = btns[i].getBoundingClientRect();
                    return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
                }}
            }}
            return null;
        }}()""")
    return await page.js(f"""function() {{
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {{
            if ((btns[i].innerText || '').indexOf('{text}') >= 0 && btns[i].offsetParent !== null) {{
                btns[i].scrollIntoView({{block: 'center'}});
                var r = btns[i].getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }}
        }}
        return null;
    }}()""")

async def navigate_to_set(page, set_name):
    """Navigate to an SBC set detail page by direct VC push."""
    return await page.js(f"""function() {{
        try {{
            var main = getAppMain();
            var hub = main._rootViewController.currentController.childViewControllers[5].currentController;
            var vm = hub._viewmodel;
            vm.setCategoryById(2);
            var sets = vm.getSetsByCurrentCategory();

            var targetSet = null;
            for (var i = 0; i < sets.length; i++) {{
                try {{
                    if ((sets[i].name || '') === '{set_name}') {{
                        targetSet = sets[i];
                        break;
                    }}
                }} catch(e) {{}}
            }}

            if (!targetSet) return JSON.stringify({{error: 'set not found'}});

            var navCtrl = hub.getNavigationController();
            var splitVC = new UTSBCGroupChallengeSplitViewController();
            splitVC.initWithSBCSet(targetSet);
            navCtrl.pushViewController(splitVC);
            return JSON.stringify({{ok: true, name: targetSet.name, complete: targetSet.isComplete(), repeats: targetSet.getRepeatsRemaining()}});
        }} catch(e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}()""")

async def navigate_sbc_upgrades(page):
    """Navigate back to SBC > 升级 listing."""
    await mouse_click(page, 48, 277)
    await asyncio.sleep(3)
    # Switch to 升级 via API
    await page.js("""function() {
        var vm = getAppMain()._rootViewController.currentController.childViewControllers[5].currentController._viewmodel;
        vm.setCategoryById(2);
    }()""")
    await asyncio.sleep(2)

async def run_sbc(page, sbc_name):
    """Complete one daily SBC."""
    log(f"\n>>> {sbc_name}")

    # Navigate via VC push
    nav = await navigate_to_set(page, sbc_name)
    log(f"  Nav: {nav}")
    await asyncio.sleep(5)

    body = await page.get_body_text() or ""

    # Check what page we're on
    if "提交" in body:
        log("  [OK] Squad builder ready")
    elif "开始挑战" in body:
        log("  -> Challenge detail page, clicking 开始挑战...")
        start_pos = await find_btn_pos(page, "开始挑战")
        if start_pos:
            await mouse_click(page, start_pos[0], start_pos[1])
            await asyncio.sleep(5)
            body = await page.get_body_text() or ""
            if "提交" not in body:
                # Maybe the challenge was already started - look for 前往挑战
                go_pos = await find_btn_pos(page, "前往挑战")
                if go_pos:
                    await mouse_click(page, go_pos[0], go_pos[1])
                    await asyncio.sleep(5)
                    body = await page.get_body_text() or ""
        else:
            log("  [X] 开始挑战 not found")
            return False
    elif "前往挑战" in body:
        log("  -> Challenge page with 前往挑战")
        go_pos = await find_btn_pos(page, "前往挑战")
        if go_pos:
            await mouse_click(page, go_pos[0], go_pos[1])
            await asyncio.sleep(5)
            body = await page.get_body_text() or ""
        else:
            log("  [X] 前往挑战 not found")
            return False

    if "提交" not in (await page.get_body_text() or ""):
        log("  [X] Not on squad builder")
        return False
    log("  [OK] Squad builder ready")

    # FSU fill: 一键填充
    fill_pos = await find_btn_pos(page, "一键填充")
    if not fill_pos:
        fill_pos = await find_btn_pos(page, "阵容补全")
    if fill_pos:
        log(f"  FSU fill at ({fill_pos[0]},{fill_pos[1]})")
        await mouse_click(page, fill_pos[0], fill_pos[1])
        await asyncio.sleep(5)
        log("  [OK] FSU fill done")
    else:
        log("  [X] No FSU fill button")
        return False

    # Check submit
    submit_ready = await page.js(r"""function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].innerText || '';
            if ((t.indexOf('提交') >= 0 || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                return btns[i].disabled ? 'disabled' : 'enabled';
            }
        }
        return 'not_found';
    }()""")
    log(f"  Submit: {submit_ready}")
    if submit_ready != "enabled":
        log("  [X] Submit not ready")
        return False

    # Click Submit
    sub_pos = await find_btn_pos(page, "提交")
    if sub_pos:
        await mouse_click(page, sub_pos[0], sub_pos[1])
        await asyncio.sleep(4)
        log("  Submit clicked")
    else:
        log("  [X] Submit not found")
        return False

    # Handle FSU warning
    cont_pos = await find_btn_pos(page, "继续")
    if cont_pos:
        log("  FSU warning, clicking 继续...")
        await mouse_click(page, cont_pos[0], cont_pos[1])
        await asyncio.sleep(3)

    # Claim
    claim_pos = await find_btn_pos(page, "领取")
    if claim_pos:
        await mouse_click(page, claim_pos[0], claim_pos[1])
        await asyncio.sleep(3)
        log(f"  [OK] {sbc_name} done!")
        return True
    else:
        log("  [!] No claim button (might be auto-claimed)")
        return True

async def main():
    log("\n" + "=" * 60)
    log("FULL SBC VIA VC PUSH")
    log("=" * 60)

    page = await connect()
    log("[CONNECT] Connected")

    # First, get set status
    log("\n--- Check daily set status ---")
    status = await page.js("""function() {
        var r = {};
        try {
            var main = getAppMain();
            var hub = main._rootViewController.currentController.childViewControllers[5].currentController;
            var vm = hub._viewmodel;
            vm.setCategoryById(2);
            var sets = vm.getSetsByCurrentCategory();

            for (var i = 0; i < sets.length; i++) {
                try {
                    var name = sets[i].name || '';
                    if (name.indexOf('每日青铜升级') >= 0) {
                        r.bronze = {idx: i, name: name, complete: sets[i].isComplete(), repeats: sets[i].getRepeatsRemaining(), timesDone: sets[i].timesCompleted, maxRepeats: sets[i].repeats};
                    }
                    if (name.indexOf('每日白银升级') >= 0) {
                        r.silver = {idx: i, name: name, complete: sets[i].isComplete(), repeats: sets[i].getRepeatsRemaining(), timesDone: sets[i].timesCompleted, maxRepeats: sets[i].repeats};
                    }
                } catch(e) {}
            }
            return JSON.stringify(r);
        } catch(e) {
            r.error = e.message;
            return JSON.stringify(r);
        }
    }()""")
    log(f"Status: {status}")

    # Navigate to SBC
    await mouse_click(page, 48, 277)
    await asyncio.sleep(4)

    # Run for both sets
    for sbc_name in ["每日青铜升级", "每日白银升级"]:
        ok = await run_sbc(page, sbc_name)
        log(f"  Result: {'OK' if ok else 'FAIL'}")

        # If we navigated away, go back to SBC hub
        log("  Back to SBC...")
        await mouse_click(page, 48, 277)
        await asyncio.sleep(3)
        # Also try clicking back button if on detail page
        back_btn = await find_btn_pos(page, "back") or await find_btn_pos(page, "返回")
        if back_btn:
            await mouse_click(page, back_btn[0], back_btn[1])
            await asyncio.sleep(3)

    log(f"\n{'='*60}")
    log("DONE!")
    log(f"{'='*60}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
