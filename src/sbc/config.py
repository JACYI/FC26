# -*- coding: utf-8 -*-
"""
FSU plugin config panel management.

The FSU config panel is opened via the "排除球员配置" button on the SBC squad page.
Only 3 switches may be touched for daily tasks; all others must retain their current state.

Daily switches (must be ON):
  1. 仅限不可交易球员
  2. 排除指定联赛球员(5)
  3. 优先使用球员仓库球员
"""
import time


def open_fsu_config(page, retries=3):
    """Click the '排除球员配置' button and wait for the config dialog."""
    for attempt in range(retries):
        try:
            btn = page.get_by_text("排除球员配置", exact=False).first
            btn.wait_for(state="attached", timeout=5000)
            btn.click(force=True, timeout=5000)
            time.sleep(2)
            # Verify dialog opened
            count = page.evaluate(
                "document.querySelectorAll('.ut-toggle-cell-view--label').length")
            if count > 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def close_fsu_config(page, retries=3):
    """Close the FSU config dialog via the '关闭' button."""
    for attempt in range(retries):
        try:
            btn = page.get_by_text("关闭", exact=False).first
            btn.wait_for(state="attached", timeout=5000)
            btn.click(force=True, timeout=5000)
            time.sleep(1.5)
            return True
        except Exception:
            pass
        # Fallback: press Escape
        page.keyboard.press("Escape")
        time.sleep(1)
        count = page.evaluate(
            "document.querySelectorAll('.ut-toggle-cell-view--label').length")
        if count == 0:
            return True
    return False


def toggle_switch(page, label_text, expect_on=True):
    """
    Toggle an FSU switch by its label text to the desired state.
    Returns True if already in desired state or successfully toggled.
    Uses page.evaluate to find labels by exact text match (bypasses Playwright selector issues).
    """
    result = page.evaluate("""
        (args) => {
            const labelText = args.labelText;
            const turnOn = args.expectOn;
            const els = document.querySelectorAll('.ut-toggle-cell-view--label');
            for (let el of els) {
                if ((el.innerText || '').trim() === labelText) {
                    const cell = el.closest('.ut-toggle-cell-view');
                    if (!cell) return {found: false, reason: 'no parent cell'};
                    const toggle = cell.querySelector('.ut-toggle-control');
                    if (!toggle) return {found: false, reason: 'no toggle control'};
                    const isOn = toggle.classList.contains('toggled');
                    if (isOn === turnOn) return {found: true, skipped: true, isOn: isOn};
                    el.click();
                    return {found: true, toggled: true, was: isOn, now: !isOn};
                }
            }
            return {found: false, reason: 'label not found: ' + labelText};
        }
    """, {"labelText": label_text, "expectOn": expect_on})

    if result.get("skipped"):
        return True
    if result.get("toggled"):
        time.sleep(0.5)
        return True
    return False


# Hard rule: only these 3 switches for daily tasks
DAILY_SWITCHES = [
    ("仅限不可交易球员", True),
    ("排除指定联赛球员(5)", True),
    ("优先使用球员仓库球员", True),
]


def ensure_daily_switches(page):
    """
    Ensure the 3 daily switches are in their required state.
    Never touches any other switches.
    Returns list of results for reporting.
    """
    results = []
    for label, expect_on in DAILY_SWITCHES:
        ok = toggle_switch(page, label, expect_on=expect_on)
        results.append({"label": label, "ok": ok, "target_state": "ON" if expect_on else "OFF"})
    return results


def ensure_fsu_config(page):
    """
    Full FSU config routine: open → set daily switches → close.
    Returns True if all steps succeeded.
    """
    if not open_fsu_config(page):
        return False

    results = ensure_daily_switches(page)
    all_ok = all(r["ok"] for r in results)

    if not close_fsu_config(page):
        return False

    return all_ok
