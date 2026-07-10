# -*- coding: utf-8 -*-
"""
Shared utility functions for EA FC 26 Web App automation.

Connection: raw WebSocket CDP (cdp_shell.py).
Click API: click_text(text) — one-liner like Playwright locator.click().
EA API: page_evaluate(js) — like Playwright page.evaluate().
"""
import sys, os, json, time, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.cdp_shell import connect as cdp_connect

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "scripts", "bsg_cdp_log.txt")


# ── Connection ─────────────────────────────────────────────────────────

def connect():
    """Connect to EA page via raw WebSocket CDP. Returns CDPPage."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    page = loop.run_until_complete(cdp_connect())
    page._loop = loop
    return page


def _js(page, expression):
    """Run JS and return result. Supports both Playwright and raw CDP pages."""
    # Playwright page (sync API) — has evaluate()
    if hasattr(page, 'evaluate'):
        try:
            expr = expression.strip()
            if expr.startswith("function"):
                expr = "(" + expr + ")"
            return page.evaluate(expr)
        except Exception as e:
            return f"JS_ERROR: {e}"
    # Raw CDP page
    return page._loop.run_until_complete(page.js(expression))


def _click(page, x, y):
    """Click at coordinates. Supports both Playwright and raw CDP pages."""
    if hasattr(page, 'mouse'):
        page.mouse.click(x, y)
        return
    # Raw CDP
    loop = page._loop
    loop.run_until_complete(page.send_faf('Input.dispatchMouseEvent',
        {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1}))
    loop.run_until_complete(asyncio.sleep(0.05))
    loop.run_until_complete(page.send_faf('Input.dispatchMouseEvent',
        {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1}))


# ── Click helpers (CDP mouse, but one-liner API) ─────────────────────

def fill_input(page, selector, value, timeout=5):
    """
    Fill an input field by selector. Multiple fallback strategies for React compatibility.

    Strategies (tried in order):
    1. Playwright locator.fill() — simulates real keystrokes via CDP Input.insertText
    2. CDP Input.insertText — raw CDP, works with any framework
    3. Native value setter — bypasses React synthetic event system
    4. Direct el.value + dispatchEvent — last resort

    After each attempt, verifies the field value matches. Returns True on success.
    """
    # Playwright path — locator.fill() is most reliable
    if hasattr(page, 'locator'):
        try:
            loc = page.locator(selector)
            loc.wait_for(state="visible", timeout=timeout * 1000)
            loc.fill(value)
            # Verify
            actual = loc.input_value()
            if actual == value:
                return True
        except Exception:
            pass

        # Playwright fallback: focus + type (if fill didn't work)
        try:
            loc = page.locator(selector)
            loc.wait_for(state="visible", timeout=1000)
            loc.click()
            time.sleep(0.2)
            loc.fill("")  # clear
            loc.type(value, delay=30)
            actual = loc.input_value()
            if actual == value:
                return True
        except Exception:
            pass

    # Raw CDP path — try multiple JS strategies
    for strategy in range(4):
        if strategy == 0:
            # Strategy 1: CDP Input.insertText (most reliable for React)
            focused = _js(page, f"""function() {{
                var el = document.querySelector('{selector}');
                if (!el || el.offsetParent === null) return 'not_found';
                el.focus();
                el.select();
                return 'focused';
            }}()""")
            if focused == 'focused' and hasattr(page, 'send_faf'):
                # Clear then insert
                import asyncio
                loop = page._loop if hasattr(page, '_loop') else None
                if loop:
                    loop.run_until_complete(page.send_faf('Input.insertText', {'text': value}))
                    time.sleep(0.3)
                    actual = _js(page, f"document.querySelector('{selector}').value")
                    if actual == value:
                        return True

        elif strategy == 1:
            # Strategy 2: Native value setter (React-compatible)
            actual = _js(page, f"""function() {{
                var el = document.querySelector('{selector}');
                if (!el || el.offsetParent === null) return null;
                el.focus();
                el.select();
                var nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(el, '{value}');
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return el.value;
            }}()""")
            if actual == value:
                return True

        elif strategy == 2:
            # Strategy 3: click + keyboard events
            pos = _js(page, f"""function() {{
                var el = document.querySelector('{selector}');
                if (!el || el.offsetParent === null) return null;
                el.focus();
                el.select();
                var r = el.getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }}()""")
            if pos and len(pos) == 2:
                _click(page, pos[0], pos[1])
                time.sleep(0.2)
                _js(page, f"""function() {{
                    var el = document.querySelector('{selector}');
                    if (el) el.value = '';
                }}()""")
                for ch in value:
                    _js(page, f"""function() {{
                        var el = document.querySelector('{selector}');
                        if (!el) return;
                        el.value += '{ch}';
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}()""")
                    time.sleep(0.05)
                actual = _js(page, f"document.querySelector('{selector}').value")
                if actual == value:
                    return True

        else:
            # Strategy 4: raw set value + dispatch (last resort)
            actual = _js(page, f"""function() {{
                var el = document.querySelector('{selector}');
                if (!el || el.offsetParent === null) return null;
                el.focus();
                el.value = '{value}';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return el.value;
            }}()""")
            if actual == value:
                return True

    log(f"  [fill_input] All strategies failed for '{selector}'")
    return False


def click_text(page, text, timeout=5):
    """Find visible element containing text and click.
    For Playwright pages, uses locator click (more reliable).
    For raw CDP pages, falls back to coordinate-based mouse click.
    Returns True if clicked, False if not found."""
    # Playwright path — use locator
    if hasattr(page, 'locator'):
        # Try button first (most common click target)
        try:
            page.locator(f"button:has-text('{text}')").first.wait_for(state="visible", timeout=timeout * 1000)
            page.locator(f"button:has-text('{text}')").first.click(force=True, timeout=timeout * 1000)
            return True
        except Exception:
            pass
        # Fallback: other clickable elements
        try:
            locator = page.locator(f"a:has-text('{text}'), span:has-text('{text}'), div:has-text('{text}'), label:has-text('{text}')")
            locator.first.wait_for(state="visible", timeout=timeout * 1000)
            locator.first.click(force=True, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    # Raw CDP path — coordinate-based
    pos = _js(page, f"""function() {{
        var els = document.querySelectorAll('button, a, span, div, label');
        for (var i = 0; i < els.length; i++) {{
            if ((els[i].innerText || '').indexOf('{text}') >= 0 && els[i].offsetParent !== null) {{
                els[i].scrollIntoView({{block: 'center'}});
                var r = els[i].getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }}
        }}
        return null;
    }}()""")
    if pos and len(pos) == 2:
        _click(page, pos[0], pos[1])
        return True
    return False


def click_nav_by_text(page, text):
    """Click a nav sidebar button by text, using coordinate-based mouse click.

    Uses evaluate() to find the exact button position, then mouse.click() to dispatch
    a real OS-level event. More reliable than locator.click() in this SPA which
    can miss due to viewport offset calculations.
    """
    pos = _js(page, f"""function() {{
        var nav = document.querySelector('nav.ut-tab-bar');
        if (!nav) return null;
        var btns = nav.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {{
            if (btns[i].offsetParent === null) continue;
            var t = (btns[i].innerText || '').trim();
            if (t === '{text}') {{
                btns[i].scrollIntoView({{block: 'center'}});
                var r = btns[i].getBoundingClientRect();
                return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
            }}
        }}
        return null;
    }}()""")
    if pos and len(pos) == 2:
        _click(page, pos[0], pos[1])
        return True
    return False


def click_sbc_nav(page):
    """Click SBC button in left nav bar. Uses coordinate-based click for reliability."""
    return click_nav_by_text(page, "SBC")


# ── EA Navigation API Helpers (page_evaluate) ────────────────────────

def page_evaluate(page, js_func):
    """Execute JavaScript in page context and return result.
    Like Playwright's page.evaluate()."""
    return _js(page, js_func)


def navigate_sbc_category(page, cat_name="升级", cat_id=2):
    """Switch SBC tab category via view model API."""
    return _js(page, f"""function() {{
        try {{
            var vm = getAppMain()._rootViewController.currentController
                .childViewControllers[5].currentController._viewmodel;
            var cats = vm.getCategories();
            for (var i = 0; i < cats.length; i++) {{
                if (cats[i].name === '{cat_name}' || cats[i].id === {cat_id}) {{
                    vm.setCategoryById(cats[i].id);
                    return JSON.stringify({{ok: true, name: cats[i].name}});
                }}
            }}
            return JSON.stringify({{error: 'category not found'}});
        }} catch(e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}()""")


def get_set_statuses(page, targets=None):
    """Get status of SBC sets. Returns dict keyed by set name.
    Args:
        targets: list of SBC set names to check (default: bronze/silver)
    """
    if targets is None:
        targets = ['每日青铜升级', '每日白银升级']
    targets_json = json.dumps(targets, ensure_ascii=False)

    result = _js(page, f"""function() {{
    var r = {{}};
    try {{
        var vm = getAppMain()._rootViewController.currentController
            .childViewControllers[5].currentController._viewmodel;
        var sets = vm.getSetsByCurrentCategory();
        var targets = {targets_json};
        targets.forEach(function(name) {{
            for (var i = 0; i < sets.length; i++) {{
                try {{
                    if (sets[i].name === name) {{
                        r[name] = {{
                            complete: sets[i].isComplete(),
                            repeatsLeft: sets[i].getRepeatsRemaining(),
                            timesCompleted: sets[i].timesCompleted,
                            maxRepeats: sets[i].repeats
                        }};
                    }}
                }} catch(e) {{}}
            }}
        }});
        return JSON.stringify(r);
    }} catch(e) {{
        return JSON.stringify({{error: e.message}});
    }}
}}()""")
    if result and isinstance(result, str) and result != "null":
        return json.loads(result)
    return result if isinstance(result, dict) else {}


def trigger_challenge_loading(page, set_name):
    """Trigger async challenge loading for an SBC set from the hub page.
    Must be called while on the SBC hub/listing page (not after VC push).
    Call wait_for_challenge_load() after to wait for completion.
    Returns dict with target info or error."""
    result = _js(page, f"""function() {{
        try {{
            var hub = getAppMain()._rootViewController.currentController
                .childViewControllers[5].currentController;
            var vm = hub._viewmodel;
            var sets = vm.getSetsByCurrentCategory();
            var target = null;
            for (var i = 0; i < sets.length; i++) {{
                try {{
                    if ((sets[i].name || '') === '{set_name}') {{
                        target = sets[i];
                        break;
                    }}
                }} catch(e) {{}}
            }}
            if (!target) return JSON.stringify({{error: 'set not found: {set_name}'}});

            // Start async challenge loading — same pattern as FSU goToSBC
            services.SBC.requestChallengesForSet(target).observe(target, function(e, t) {{
                e.unobserve(target);
            }});

            return JSON.stringify({{
                ok: true,
                name: target.name,
                repeatsLeft: target.getRepeatsRemaining()
            }});
        }} catch(e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}()""")
    if result and isinstance(result, str) and result != "null":
        return json.loads(result)
    return result if isinstance(result, dict) else {"error": "no result"}


def is_challenge_loaded(page, set_name):
    """Check if challenges are loaded for a set on the hub page.
    Returns True when the set entity has loaded challenges."""
    return _js(page, f"""function() {{
        try {{
            var sets = services.SBC.repository.getSets();
            for (var i = 0; i < sets.length; i++) {{
                if ((sets[i].name || '') === '{set_name}') {{
                    var ch = sets[i].getChallenges();
                    return ch && ch.length > 0;
                }}
            }}
        }} catch(e) {{}}
        return false;
    }}()""")


def push_sbc_set(page, set_name):
    """Load challenges for a set, then navigate into it via VC push.

    Two-phase approach:
    1. Trigger async challenge loading from hub page
    2. Poll until challenges are loaded
    3. Push VC with initWithSBCSet (which now has data)
    """
    # Phase 1: trigger async loading
    result = trigger_challenge_loading(page, set_name)
    if not result.get("ok"):
        return result

    # Phase 2: poll until loaded
    for i in range(30):
        if is_challenge_loaded(page, set_name):
            log(f"  [push_sbc_set] Challenges loaded after {i+1}s")
            break
        time.sleep(1)
    else:
        log(f"  [push_sbc_set] Warning: challenges did not load within 30s, pushing VC anyway")

    # Phase 3: push VC (now with loaded challenges)
    nav_result = _js(page, f"""function() {{
        try {{
            var hub = getAppMain()._rootViewController.currentController
                .childViewControllers[5].currentController;
            var sets = services.SBC.repository.getSets();
            var target = null;
            for (var i = 0; i < sets.length; i++) {{
                try {{
                    if ((sets[i].name || '') === '{set_name}') {{
                        target = sets[i];
                        break;
                    }}
                }} catch(e) {{}}
            }}
            if (!target) return JSON.stringify({{error: 'set not found: {set_name}'}});

            var navCtrl = hub.getNavigationController();
            var splitVC = new UTSBCGroupChallengeSplitViewController();
            splitVC.initWithSBCSet(target);
            navCtrl.pushViewController(splitVC);

            return JSON.stringify({{
                ok: true,
                name: target.name,
                repeatsLeft: target.getRepeatsRemaining()
            }});
        }} catch(e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}()""")
    if nav_result and isinstance(nav_result, str) and nav_result != "null":
        return json.loads(nav_result)
    return nav_result if isinstance(nav_result, dict) else {"error": "no result"}


def open_sbc_squad_builder(page, set_name):
    """Load challenges for a set and push directly to squad builder VC.

    Skips the challenge list view (SET_DETAIL) entirely.
    Needed for hidden/single-segment SBCs like TOTS Crafting Upgrade
    where the challenge rows are not interactive DOM elements.

    Flow:
    1. requestChallengesForSet(target) — trigger async load
    2. Poll until challenges appear in repository
    3. services.SBC.loadChallenge(challenge) — load full challenge data
    4. Push UTSBCSquadSplitViewController.initWithSBCSet(target, challengeId)
    """
    # Phase 1: trigger async loading
    result = trigger_challenge_loading(page, set_name)
    if not result.get("ok"):
        return result

    # Phase 2: poll until loaded
    for i in range(30):
        if is_challenge_loaded(page, set_name):
            log(f"  [open_sbc_squad_builder] Challenges loaded after {i+1}s")
            break
        time.sleep(1)
    else:
        log(f"  [open_sbc_squad_builder] Warning: challenges not loaded within 30s")

    # Phase 3: load challenge + push squad builder VC (via Promise to wait for async callback)
    nav_result = _js(page, f"""function() {{
        try {{
            var hub = getAppMain()._rootViewController.currentController
                .childViewControllers[5].currentController;
            var sets = services.SBC.repository.getSets();
            var target = null;
            for (var i = 0; i < sets.length; i++) {{
                try {{
                    if ((sets[i].name || '') === '{set_name}') {{
                        target = sets[i];
                        break;
                    }}
                }} catch(e) {{}}
            }}
            if (!target) return JSON.stringify({{error: 'set not found: {set_name}'}});

            var challenges = target.getChallenges();
            if (!challenges || challenges.length === 0)
                return JSON.stringify({{error: 'no challenges loaded for ' + target.name}});

            var challenge = challenges[0];

            // Return a Promise so Runtime.evaluate(awaitPromise=true) waits for the callback
            return new Promise(function(resolve) {{
                services.SBC.loadChallenge(challenge).observe(target, function(ee, tt) {{
                    ee.unobserve(target);
                    if (tt.success) {{
                        var navCtrl = hub.getNavigationController();
                        var splitVC = new UTSBCSquadSplitViewController();
                        splitVC.initWithSBCSet(target, challenge.id);
                        navCtrl.pushViewController(splitVC);
                        // Wait briefly for VC push to render
                        setTimeout(function() {{
                            resolve(JSON.stringify({{
                                ok: true,
                                name: target.name,
                                challengeId: challenge.id
                            }}));
                        }}, 2000);
                    }} else {{
                        resolve(JSON.stringify({{error: 'loadChallenge failed'}}));
                    }}
                }});
            }});
        }} catch(e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}()""")

    if nav_result and isinstance(nav_result, str) and nav_result != "null":
        result = json.loads(nav_result)
    else:
        result = nav_result if isinstance(nav_result, dict) else {"error": "no result"}

    if result.get("ok"):
        # Wait for FSU to initialize: FSU needs to detect the squad builder DOM
        # and load player data before its fill buttons work
        log("  [open_sbc_squad_builder] Waiting for FSU initialization...")
        for i in range(20):
            body = _js(page, "document.body.innerText.substring(0, 200)") or ""
            has_fsu_btn = "一键填充" in body
            has_loading = "正在读取球员数据" in body
            if has_fsu_btn and not has_loading:
                log(f"  [open_sbc_squad_builder] FSU ready after {i+1}s")
                break
            if i % 5 == 0:
                log(f"  [open_sbc_squad_builder] FSU status: loading={'yes' if has_loading else 'no'} btn={'yes' if has_fsu_btn else 'no'}")
            time.sleep(1)
        else:
            log(f"  [open_sbc_squad_builder] FSU wait ended, body={body[:100]}")
    return result


# ── State check helpers ──────────────────────────────────────────────

def go_to_sbc_hub(page):
    """Reset SBC navigation to the hub/listing page.
    Pops all pushed view controllers to return to the SBC hub.
    Returns True if successful."""
    result = _js(page, """function() {
        try {
            var app = getAppMain();
            if (!app) return false;
            var tabBar = app._rootViewController.currentController;
            if (!tabBar || !tabBar.childViewControllers) return false;
            var sbcCtrl = tabBar.childViewControllers[5];
            if (!sbcCtrl) return false;
            var ctrl = sbcCtrl.currentController;
            if (!ctrl) return false;
            var nav = ctrl.getNavigationController ? ctrl.getNavigationController() : null;
            if (nav && nav.popToRootViewController) {
                nav.popToRootViewController(true);
                return true;
            }
            return false;
        } catch(e) {
            return false;
        }
    }()""")
    return result is True


def is_submit_ready(page):
    """Check if Submit button is enabled. Returns 'enabled', 'disabled', or 'not_found'."""
    return _js(page, r"""function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].innerText || '';
            if ((t.indexOf('提交') >= 0 || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null) {
                return btns[i].disabled ? 'disabled' : 'enabled';
            }
        }
        return 'not_found';
    }()""")


def get_page_text(page):
    """Get page body text."""
    return _js(page, "document.body.innerText") or ""


def get_visible_buttons(page):
    """Get list of visible button texts."""
    return _js(page, """function() {
        var b = document.querySelectorAll('button');
        return Array.from(b).map(function(x) {
            return (x.innerText || '').trim().substring(0, 50);
        }).filter(function(x) { return x; });
    }()""")


# ── Logging ────────────────────────────────────────────────────────────

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
