# -*- coding: utf-8 -*-
"""Simple CDP client using raw WebSocket — bypass Playwright/Selenium compatibility issues."""
import asyncio, json, websockets, time, sys, os, urllib.request

LOG_FILE = os.path.join(os.path.dirname(__file__), "cdp_shell_log.txt")
def log(msg=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


class CDPPage:
    """Minimal CDP client attached to one page target."""

    def __init__(self, ws, session_id):
        self.ws = ws
        self.sid = session_id
        self._msg_id = 100

    async def send(self, method, params=None):
        self._msg_id += 1
        msg = {"id": self._msg_id, "sessionId": self.sid, "method": method}
        if params:
            msg["params"] = params
        await self.ws.send(json.dumps(msg))
        return self._msg_id

    async def send_faf(self, method, params=None):
        """Fire-and-forget with response consumption."""
        mid = await self.send(method, params)
        while True:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=15)
            data = json.loads(raw)
            if data.get("id") == mid:
                return data.get("result")

    async def recv(self, timeout=15):
        while True:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            data = json.loads(raw)
            if "id" in data and data["id"] >= 100:
                return data

    async def js(self, expression, timeout=15):
        expr = expression.strip()
        if expr.startswith("function"):
            expr = "(" + expr + ")"
        await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        resp = await self.recv(timeout)
        if resp is None:
            return None
        result = resp.get("result", {})
        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            return f"JS_ERROR: {exc.get('text', '')} | {exc.get('exception', {}).get('description', '')}"
        return result.get("result", {}).get("value")

    async def wait_ms(self, ms):
        await self.js(f"new Promise(r => setTimeout(r, {ms}))")

    async def get_body_text(self):
        return await self.js("document.body.innerText", timeout=15)

    async def get_buttons(self):
        raw = await self.js("""function() {
            var b = document.querySelectorAll('button');
            return Array.from(b).map(function(x) {
                return (x.innerText || '').trim().substring(0, 50);
            }).filter(function(x) { return x; });
        }()""", timeout=10)
        return raw if isinstance(raw, list) else []

    async def click_by_js(self, selector):
        return await self.js(f"""function() {{
            var el = document.querySelector('{selector}');
            if (!el) return 'NOT_FOUND';
            el.scrollIntoView();
            el.click();
            return 'OK';
        }}()""", timeout=10)

    async def click_by_mouse(self, selector):
        """Click element by getting its position and using CDP Input.dispatchMouseEvent."""
        pos = await self.js(f"""function() {{
            var el = document.querySelector('{selector}');
            if (!el) return null;
            el.scrollIntoView();
            var r = el.getBoundingClientRect();
            return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
        }}()""")
        if not pos or len(pos) < 2:
            return "NOT_FOUND"
        x, y = pos[0], pos[1]
        await self.send_faf('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        await self.send_faf('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        return f"OK ({x},{y})"

    async def click_text(self, text):
        """Find visible element containing text and click via mouse."""
        pos = await self.js(f"""function() {{
            var els = document.querySelectorAll('button, a, span, div, label');
            for (var i = 0; i < els.length; i++) {{
                if ((els[i].innerText || '').indexOf('{text}') >= 0 && els[i].offsetParent !== null) {{
                    els[i].scrollIntoView();
                    var r = els[i].getBoundingClientRect();
                    return [Math.round(r.left + r.width/2), Math.round(r.top + r.height/2)];
                }}
            }}
            return null;
        }}()""")
        if not pos or len(pos) < 2:
            return "NOT_FOUND"
        x, y = pos[0], pos[1]
        await self.send_faf('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        await self.send_faf('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        return f"OK ({x},{y})"


async def connect():
    # Get WebSocket URL dynamically (UUID changes on Chrome restart)
    info = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version").read().decode())
    uri = info.get("webSocketDebuggerUrl")
    if not uri:
        raise Exception("No webSocketDebuggerUrl found")
    ws = await websockets.connect(uri, max_size=2**20)
    await ws.send(json.dumps({"id": 0, "method": "Target.getTargets"}))
    raw = await asyncio.wait_for(ws.recv(), timeout=10)
    targets = json.loads(raw).get("result", {}).get("targetInfos", [])
    tid = None
    for t in targets:
        if "ultimate-team" in t.get("url", ""):
            tid = t["targetId"]
            break
    if not tid:
        await ws.close()
        raise Exception("EA page not found")
    await ws.send(json.dumps({
        "id": 1, "method": "Target.attachToTarget",
        "params": {"targetId": tid, "flatten": True}
    }))
    r1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    r2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    event = r1 if "method" in r1 else r2
    sid = event.get("params", {}).get("sessionId", "")
    return CDPPage(ws, sid)
