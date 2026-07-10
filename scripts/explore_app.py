"""Explore EA FC 26 Web App structure — read-only, no submissions."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.utils import connect, wait_for_page, get_page_state

p, browser, page = connect()
time.sleep(5)

def save_page(name):
    """Save page state for analysis."""
    text = page.inner_text("body")
    with open(f"explore_{name}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    page.screenshot(path=f"explore_{name}.png")
    print(f"  Saved explore_{name}.txt + .png")

def click_nav(label):
    """Click a nav button and wait."""
    print(f"\n[{label}] Clicking navigation...")
    try:
        page.locator(f"button:has-text('{label}')").first.click(timeout=5000)
    except:
        page.locator(f"a:has-text('{label}')").first.click(timeout=5000)
    time.sleep(4)
    wait_for_page(page, timeout=15)

print("=" * 50)
print("EA FC 26 Web App Exploration")
print("=" * 50)

state = get_page_state(page)
print(f"\n[Start] State: {state}")

click_nav("SBC")
save_page("sbc")

click_nav("Club")
save_page("club")

print("\n[Players] Looking at player list...")
text = page.inner_text("body")
for tag in ["Players", "球员"]:
    try:
        if tag in text:
            btn = page.locator(f"button:has-text('{tag}')").first
            if btn.is_visible(timeout=1000):
                btn.click()
                time.sleep(3)
                wait_for_page(page, timeout=10)
                save_page("players")
                break
    except:
        pass

click_nav("Transfers")
save_page("transfers")

print("\n" + "=" * 50)
print("Exploration complete - no SBCs submitted.")
print("=" * 50)

try:
    while browser.is_connected():
        time.sleep(3)
except:
    pass
