# -*- coding: utf-8 -*-
"""
Complete Bronze and Silver segments of Bronze/Silver/Gold Upgrade SBC.
Connects to Chrome → navigates to SBC → completes segments sequentially.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.login import connect, do_login, check_fsu, navigate_to_ea
from src.sbc.executor import SBCExecutor
from src.sbc.config import ensure_fsu_config
from src.utils import wait_for_page


def segment_name_from_text(page):
    """Detect the current segment name from the SBC squad builder page."""
    text = page.inner_text("body")
    for keyword in ["青铜", "Silver", "Bronze", "Gold", "黄金", "白银"]:
        if keyword in text:
            return keyword
    return "unknown"


def find_segment_links(page):
    """Find clickable segment links/buttons on the SBC segment selection page.
    Returns list of segment text labels found."""
    return page.evaluate("""function() {
        var links = document.querySelectorAll('a, button, [class*="segment"], [class*="challenge"]');
        var segments = [];
        var seen = new Set();
        for (var i = 0; i < links.length; i++) {
            var t = (links[i].innerText || '').trim();
            if (!t) continue;
            // Look for segment-like labels
            if ((t.indexOf('青铜') >= 0 || t.indexOf('白银') >= 0 || t.indexOf('黄金') >= 0 ||
                 t.indexOf('Bronze') >= 0 || t.indexOf('Silver') >= 0 || t.indexOf('Gold') >= 0) &&
                t.indexOf('SBC') < 0 && !seen.has(t)) {
                segments.push(t);
                seen.add(t);
            }
        }
        return segments;
    }()""")


def click_segment(page, segment_text):
    """Click on a specific segment by its text label."""
    try:
        locator = page.get_by_text(segment_text, exact=False).first
        locator.wait_for(state="visible", timeout=5000)
        locator.click(force=True)
        return True
    except Exception:
        pass
    # Fallback
    try:
        locator = page.locator(f"text={segment_text}").first
        locator.wait_for(state="visible", timeout=3000)
        locator.click(force=True)
        return True
    except Exception:
        return False


def is_squad_page(page):
    """Check if current page is a squad builder (has Submit button or FSU elements)."""
    body = page.inner_text("body")
    return "提交" in body or "Submit" in body or "一键填充" in body


def is_segment_list_page(page):
    """Check if current page shows the segment list (not yet in squad builder)."""
    body = page.inner_text("body")
    # If we see segment indicators but no Submit, we're on segment list
    has_segment = any(kw in body for kw in ["青铜", "白银", "黄金", "Bronze", "Silver", "Gold"])
    has_submit = "提交" in body or "Submit" in body
    return has_segment and not has_submit


def complete_sbc_segment(executor, segment_name):
    """Complete one SBC segment (fill → submit → claim)."""
    page = executor.page
    print(f"\n{'='*50}")
    print(f"SEGMENT: {segment_name}")
    print(f"{'='*50}")

    # Wait for squad page to load
    try:
        page.wait_for_function(
            'document.body.innerText.indexOf("提交") >= 0 || document.body.innerText.indexOf("Submit") >= 0',
            timeout=15000)
    except:
        pass
    wait_for_page(page, timeout=10)

    # Check if already completed
    body = page.inner_text("body")
    if "已领取" in body and "不可重复" in body:
        print(f"  Segment '{segment_name}' already completed (claimed)")
        return True

    # Configure FSU daily switches
    print("[FSU] Configuring daily switches...")
    ensure_fsu_config(page)

    # Try FSU auto-fill
    fsu_filled = executor.try_fsu_autofill()
    if not fsu_filled:
        fsu_filled = executor.try_fsu_dupfill()

    if not fsu_filled:
        print("  FSU fill unavailable, trying manual...")
        if not executor.fill_squad_manually(segment_name):
            print("  Manual build failed")
            return False

    # Check submit ready
    if not executor.is_submit_ready():
        print("  Submit button not enabled after fill")
        # Try to read what's wrong
        body = page.inner_text("body")
        print(f"  Page debug: {body[:200]}")
        return False

    # Submit
    if not executor.submit():
        print("  Submit failed")
        return False

    # Claim reward
    executor.claim_reward()

    print(f"  COMPLETED: {segment_name}")
    return True


def main():
    print("=" * 50)
    print("EA FC 26 - Bronze & Silver Daily SBC")
    print("=" * 50)

    # Step 1: Connect to Chrome
    print("\n[STEP 1] Connecting to Chrome...")
    p, browser, page = connect()
    if not page:
        print("  Failed to connect to Chrome")
        return

    # Step 2: Navigate to EA Web App
    print("\n[STEP 2] Navigating to EA Web App...")
    navigate_to_ea(page)

    # Step 3: Login if needed
    print("\n[STEP 3] Checking login state...")
    if not do_login(page):
        print("  Login failed, aborting")
        return

    # Step 4: Check FSU
    print("\n[STEP 4] Checking FSU plugin...")
    check_fsu(page)

    # Step 5: Navigate to SBC > Upgrades
    print("\n[STEP 5] Navigating to SBC > Upgrades...")
    executor = SBCExecutor(page)
    if not executor.navigate_to_sbc("Upgrades"):
        print("  Navigation failed")
        return

    # Step 6: Find and enter "Bronze/Silver/Gold Upgrade"
    print("\n[STEP 6] Finding Bronze/Silver/Gold Upgrade...")
    sbc_name = "Bronze/Silver/Gold Upgrade"

    # Try clicking the SBC
    from src.sbc.scanner import click_into_sbc
    if not click_into_sbc(page, sbc_name):
        # Try Chinese name
        sbc_name_cn = "青铜/白银/黄金升级"
        if not click_into_sbc(page, sbc_name_cn):
            print("  Could not find Bronze/Silver/Gold Upgrade SBC")
            # List what's available for debugging
            from src.sbc.scanner import scan_sbc_listing
            sbcs = scan_sbc_listing(page)
            print(f"  Available SBCs:")
            for s in sbcs[:10]:
                print(f"    - {s.name}")
            return

    wait_for_page(page, timeout=10)

    # Step 7: Determine current page and handle segments
    print("\n[STEP 7] Processing segments...")
    time.sleep(3)

    # Check if we're on a segment list page (multiple segments visible)
    body = page.inner_text("body")
    print(f"  Page title/snippet: {body[:150].strip()}")

    # The segments are visible - click Bronze/Silver one by one
    segments_to_do = ["Bronze", "Silver", "青铜", "白银"]
    segment_labels = find_segment_links(page)
    print(f"  Found segment labels: {segment_labels}")

    completed = 0
    # Try Bronze segment first
    for seg_name in ["Bronze", "青铜"]:
        if seg_name in body or any(seg_name in s for s in segment_labels):
            print(f"\n>>> Entering {seg_name} segment...")
            if click_segment(page, seg_name):
                time.sleep(3)
                if complete_sbc_segment(executor, seg_name):
                    completed += 1
                # Go back to segment list
                print("  Going back to segment list...")
                try:
                    page.locator("button:has-text('返回')").first.click(force=True, timeout=3000)
                except:
                    try:
                        page.locator("button:has-text('Back')").first.click(force=True, timeout=3000)
                    except:
                        pass
                wait_for_page(page, timeout=10)
                time.sleep(2)
            break

    # Then Silver segment
    for seg_name in ["Silver", "白银"]:
        if seg_name in page.inner_text("body") or any(seg_name in s for s in find_segment_links(page)):
            print(f"\n>>> Entering {seg_name} segment...")
            if click_segment(page, seg_name):
                time.sleep(3)
                if complete_sbc_segment(executor, seg_name):
                    completed += 1
            break

    # Summary
    print(f"\n{'='*50}")
    print(f"RESULTS: {completed}/2 segments completed")
    print(f"{'='*50}")

    if completed < 2:
        print("\nSome segments may be already completed or not found.")
        print("You can check manually in the Web App.")

    print("\nDone. Browser remains open.")
    try:
        while browser.is_connected():
            time.sleep(3)
    except:
        pass
    finally:
        try:
            p.stop()
        except:
            pass


if __name__ == "__main__":
    main()
