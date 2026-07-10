# -*- coding: utf-8 -*-
"""
1. 检测当前页面状态
2. 如在登录页 → 执行登录（邮箱→密码→2FA）
3. 跳转到 SBC Upgrades
4. 扫描所有 SBC 状态
5. 保持浏览器打开
"""
import sys, os, json, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
EA_URL = "https://www.ea.com/ea-sports-fc/ultimate-team/web-app/"
EMAIL = "3079479814@qq.com"
PASSWORD = "Yyh3079479814"

log = lambda msg: print(msg) or sys.stdout.flush()

def js_click(page, selector):
    if ":has-text(" in selector:
        m = re.match(r'(\w+)?:has-text\(\'([^\']+)\'\)', selector)
        tag, text = (m.group(1) or "*", m.group(2)) if m else ("*", selector)
        return page.evaluate("""(args) => {
            var els = document.querySelectorAll(args.tag);
            for (var i = 0; i < els.length; i++)
                if ((els[i].innerText || "").indexOf(args.text) >= 0)
                    { els[i].click(); return true; }
            return false;
        }""", {"tag": tag, "text": text})
    return page.evaluate("(sel) => { var el = document.querySelector(sel); if(el){el.click();return true} return false; }", selector)

def get_state(page):
    """
    检测当前页面状态，返回:
      'logged_in'    → EA App 主界面（有 SBC/Home等）
      'login_page'   → EA 登录页（有"登录"/Login + 协议）
      'email_form'   → signin.ea.com 邮箱输入
      'password_form' → signin.ea.com 密码输入
      'verify_code'  → 2FA 验证码输入
      'loading'      → 加载中
    """
    url = page.url
    body = page.inner_text("body")

    # 1. 已登录：主界面包含 SBC 或 主页/Squads
    if "ultimate-team/web-app" in url and ("SBC" in body or ("Home" in body and "Squads" in body)):
        return "logged_in"

    # 2. EA 登录页：有登录按钮和协议
    if "ultimate-team/web-app" in url:
        if ("登录" in body or "Login" in body):
            return "login_page"
        return "loading"

    # 3. signin.ea.com 子页面
    if "signin.ea.com" in url:
        if page.locator("#twoFactorCode").is_visible(timeout=500):
            return "verify_code"
        if page.locator("#password").is_visible(timeout=500):
            return "password_form"
        if page.locator("#email").is_visible(timeout=500):
            return "email_form"
        return "signin_unknown"

    # 4. 其他
    return "loading"


# ═══════════════════════════════════════════
# 连接
# ═══════════════════════════════════════════
try:
    import urllib.request
    urllib.request.urlopen(CDP_URL + "/json/version", timeout=2)
    log("[OK] Chrome running on 9222")
except:
    log("[ERR] Chrome not running on 9222")
    sys.exit(1)

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(CDP_URL)

page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team" in pg.url:
            page = pg
            log(f"[OK] Found EA tab")
            break
    if page: break

if not page:
    log("[NAV] No EA tab, creating...")
    page = browser.contexts[0].new_page()
    page.goto(EA_URL, wait_until="domcontentloaded", timeout=60000)

# ═══════════════════════════════════════════
# 状态检测 + 登录
# ═══════════════════════════════════════════
log(f"\n=== 状态检测 ===")
for _ in range(20):
    state = get_state(page)
    log(f"  {state}")
    if state == "logged_in":
        break
    if state == "login_page":
        log("[ACTION] 点击登录...")
        js_click(page, "button:has-text('登录')")
        time.sleep(5)
        continue
    if state == "email_form":
        log("[ACTION] 输入邮箱...")
        page.locator("#email").fill(EMAIL)
        js_click(page, "#logInBtn")
        time.sleep(3)
        continue
    if state == "password_form":
        log("[ACTION] 输入密码...")
        page.locator("#password").fill(PASSWORD)
        if not js_click(page, "#logInBtn"):
            page.keyboard.press("Enter")
        time.sleep(5)
        continue
    if state == "verify_code":
        log("[2FA] 需要验证码")
        body = page.inner_text("body")
        if "SEND CODE" in body:
            log("  发送验证码...")
            page.keyboard.press("Tab")
            time.sleep(0.3)
            page.keyboard.press("Tab")
            time.sleep(0.3)
            page.keyboard.press("Enter")
            time.sleep(3)
        code = input("  验证码（查邮件）: ").strip()
        if not code:
            log("  未输入，退出")
            p.stop(); sys.exit(1)
        page.locator("#twoFactorCode").fill(code)
        page.evaluate("() => { var cb = document.getElementById('trustThisDevice'); if(cb && !cb.checked) cb.checked = true; }")
        js_click(page, "#btnSubmit")
        time.sleep(20)
        continue
    # loading → 等
    time.sleep(2)
else:
    log("[ERR] 页面状态未能转为 logged_in")
    log(f"  最终 URL: {page.url}")
    log(f"  最终 Body: {page.inner_text('body')[:200]}")
    p.stop(); sys.exit(1)

log(f"[OK] 已登录")

# ═══════════════════════════════════════════
# 导航到 SBC → Upgrades
# ═══════════════════════════════════════════
log(f"\n=== SBC ===")
js_click(page, "button:has-text('SBC')")
time.sleep(4)

log(f"\n=== Upgrades ===")
js_click(page, "button:has-text('Upgrades')")
time.sleep(3)

# ═══════════════════════════════════════════
# 扫描状态
# ═══════════════════════════════════════════
log(f"\n=== 扫描 SBC ===")
result = page.evaluate("""(function() {
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
        return r;
    } catch(e) {
        return {error: e.message};
    }
})()""")

log("")
log("=" * 55)
log("SBC Upgrades 状态")
log("=" * 55)
if isinstance(result, dict) and "error" not in result:
    log(f"共 {len(result)} 个 SBC\n")
    for name, info in sorted(result.items()):
        done = info.get("complete", False)
        icon = "✅" if done else "⬜"
        rl = info.get('repeatsLeft', 0)
        mr = info.get('maxRepeats', 0)
        repeats = f"{rl}/{mr}" if mr else "∞"
        status = "已完成" if done else "待完成"
        log(f"  {icon} {name}")
        log(f"     {status} | 剩余: {repeats} | 已做: {info.get('timesCompleted', 0)}x")
else:
    log(f"[ERR] {result}")

log("\n" + "=" * 55)
log("浏览器保持打开")
log("=" * 55)

try:
    while browser.is_connected():
        time.sleep(3)
except:
    pass
finally:
    try: p.stop()
    except: pass
