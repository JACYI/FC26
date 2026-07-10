"""Explore SBC sub-tabs and Club players — read-only."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.utils import connect, wait_for_page

p, browser, page = connect()
time.sleep(5)

def save_page(name):
    text = page.inner_text("body")
    with open(f"explore_{name}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    page.screenshot(path=f"explore_{name}.png")
    print(f"  Saved explore_{name}")

def click_tab(label):
    """Click a sub-tab."""
    print(f"\n[{label}] Clicking tab...")
    try:
        page.locator(f"button:has-text('{label}')").first.click(timeout=5000)
    except:
        page.locator(f"a:has-text('{label}')").first.click(timeout=5000)
    time.sleep(3)
    wait_for_page(page, timeout=10)

print("[Nav] Going to SBC...")
page.locator("button:has-text('SBC')").first.click(timeout=5000)
time.sleep(3)
wait_for_page(page, timeout=10)

body = page.inner_text("body")
tabs = ["Upgrades", "Players", "Challenges", "Icons", "Foundations", "Favourites"]
available = [t for t in tabs if t in body]
print(f"Available tabs: {available}")

if "Upgrades" in available:
    click_tab("Upgrades")
    save_page("sbc_upgrades")

if "Foundations" in available:
    click_tab("Foundations")
    save_page("sbc_foundations")

print("\n[Nav] Going to Club > Players...")
page.locator("button:has-text('Club')").first.click(timeout=5000)
time.sleep(3)
wait_for_page(page, timeout=10)

body = page.inner_text("body")
if "Players" in body:
    page.locator("button:has-text('Players')").first.click(timeout=5000)
    time.sleep(3)
    wait_for_page(page, timeout=10)
    save_page("club_players")

    print("\n[Players] Checking player list structure...")
    text = page.inner_text("body")
    lines = text.split("\n")
    print(f"  Total lines: {len(lines)}")

print("\nDone - read only, no submissions.")
try:
    while browser.is_connected():
        time.sleep(3)
except:
    pass
