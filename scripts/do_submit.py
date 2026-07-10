# -*- coding: utf-8 -*-
"""Quick submit: click submit and claim reward on current squad builder page."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.utils import click_text, log, _js, get_page_text

def main():
    log("[SUBMIT] Connecting...")
    from src.login import connect as pw_connect
    p, browser, pw_page = pw_connect()
    if not pw_page:
        log("[FATAL] No page")
        return

    body = pw_page.inner_text("body")
    log(f"Body: {body[:300]}")

    if "提交" in body:
        log("[SUBMIT] Clicking 提交...")
        # Check if submit is enabled
        submit_enabled = pw_page.evaluate("""() => {
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t = btns[i].innerText || '';
                if ((t.indexOf('提交') >= 0 || t.indexOf('Submit') >= 0) && btns[i].offsetParent !== null)
                    return !btns[i].disabled;
            }
            return false;
        }""")
        if not submit_enabled:
            log("[SUBMIT] Submit is disabled, need to fill first")
            # Try FSU fill
            for btn in ["一键填充(优先重复)", "一键填充", "阵容补全"]:
                if btn in body:
                    log(f"[FSU] Clicking {btn}...")
                    pw_page.locator(f"button:has-text('{btn}')").first.click(force=True, timeout=5000)
                    time.sleep(5)
                    break

        # Try clicking submit
        if click_text(pw_page, "提交"):
            log("[SUBMIT] Submit clicked, waiting...")
            time.sleep(5)

            # After submit: handle FSU warning, reward, etc.
            body = pw_page.inner_text("body")
            log(f"Body after submit: {body[:300]}")

            # Claim reward
            for attempt in range(5):
                if "领取" in body:
                    log("[REWARD] Clicking 领取...")
                    click_text(pw_page, "领取")
                    time.sleep(3)
                    break
                if "确定" in body:
                    log("[CONFIRM] Clicking 确定...")
                    click_text(pw_page, "确定")
                    time.sleep(3)
                    break
                if "继续" in body:
                    log("[FSU WARNING] Clicking 继续...")
                    click_text(pw_page, "继续")
                    time.sleep(3)
                    break
                time.sleep(2)
                body = pw_page.inner_text("body")
        else:
            log("[SUBMIT] Submit button not found or not clickable")

    # Final state
    time.sleep(3)
    body = pw_page.inner_text("body")
    log(f"Final body: {body[:300]}")
    print("Done. Check log.")

if __name__ == "__main__":
    main()
