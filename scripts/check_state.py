# -*- coding: utf-8 -*-
"""Quick state check using CDP shell — fixed string escaping."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.cdp_shell import connect, log

JS_NAV = r"""function() {
    var btns = document.querySelectorAll('.ut-tab-bar-item');
    var r = [];
    for (var i = 0; i < btns.length; i++) {
        r.push((btns[i].innerText || '').trim().replace(/\n/g,'|'));
    }
    return JSON.stringify(r);
}()"""

JS_BUTTONS = r"""function() {
    var b = document.querySelectorAll('button');
    var r = [];
    for (var i = 0; i < b.length; i++) {
        var t = (b[i].innerText || '').trim().substring(0, 50);
        if (t) r.push(t.replace(/\n/g,'|'));
    }
    return JSON.stringify(r);
}()"""

JS_STATUS = r"""function() {
    var t = document.body.innerText;
    return JSON.stringify({
        hasFSU: t.indexOf('FSU') >= 0,
        hasQuickComplete: t.indexOf('一键完成') >= 0,
        hasQuickFill: t.indexOf('一键填充') >= 0,
        hasUpgrade: t.indexOf('升级') >= 0,
        hasSubmit: t.indexOf('提交') >= 0
    });
}()"""

async def main():
    log("=== State Check ===")
    page = await connect()

    text = await page.get_body_text()
    log(f"Body length: {len(text)}")

    raw = await page.js(JS_NAV)
    log(f"Nav buttons: {raw}")

    raw2 = await page.js(JS_BUTTONS)
    log(f"Buttons: {raw2[:1000] if isinstance(raw2, str) else 'NOT_STRING'}")

    raw3 = await page.js(JS_STATUS)
    log(f"Status: {raw3}")

    log("=== Done ===")

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
