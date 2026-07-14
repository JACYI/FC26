# -*- coding: utf-8 -*-
"""Explore SBC requirements - see what rareflags/special cards are required."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.login import connect, navigate_to_ea, do_login, check_fsu, wait_for_text

p, browser, page = connect()
if not page:
    print("Failed to connect")
    sys.exit(1)

navigate_to_ea(page)
do_login(page)
check_fsu(page)

def save_page(name):
    text = page.inner_text("body")
    path = f"explore_{name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Saved {path}")

def click_tab(label):
    print(f"\n[{label}] Clicking tab...")
    try:
        page.locator(f"button:has-text('{label}')").first.click(timeout=5000)
    except:
        try:
            page.locator(f"a:has-text('{label}')").first.click(timeout=5000)
        except:
            print(f"  Cannot click tab: {label}")
            return False
    time.sleep(3)
    return True

# Go to SBC
print("\n[Nav] Going to SBC...")
page.locator("button:has-text('SBC')").first.click(timeout=5000)
time.sleep(3)

body = page.inner_text("body")
print(f"\n=== PAGE BODY (first 3000 chars) ===")
print(body[:3000])

# Check Upgrades tab
if "Upgrades" in body or "升级" in body:
    click_tab("Upgrades" if "Upgrades" in body else "升级")
    time.sleep(3)
    save_page("sbc_upgrades")

    # Now try to click into each SBC set to see requirements
    # Read the upgrades page to find SBC names
    body2 = page.inner_text("body")
    print(f"\n=== UPGRADES PAGE (first 2000 chars) ===")
    print(body2[:2000])

# Also check Players tab
if "Players" in body or "球员" in body:
    click_tab("Players" if "Players" in body else "球员")
    time.sleep(3)
    save_page("sbc_players")

# Check All tab for all available SBCs
if "All" in body or "全部" in body:
    click_tab("All" if "All" in body else "全部")
    time.sleep(3)
    save_page("sbc_all")

# Try clicking into specific SBC groups to see challenge requirements
# First, let's look for common SBC names
print("\n\n=== Trying to click into SBC groups ===")
sbc_groups_to_try = [
    "Premium Mixed Leagues Upgrade",
    "Mixed Leagues Upgrade",
    "Daily Rare Gold Upgrade",
    "TOTS Crafting Upgrade",
    "85-87 Upgrade",
    "14x 83+ Upgrade",
    "Premium PL League Upgrade",
    "82+ PL/BWSL Player Pick",
    "83+ Upgrade",
    "Bronze/Silver/Gold Upgrade",
]

for sbc_name in sbc_groups_to_try:
    if sbc_name in page.inner_text("body"):
        print(f"\n[{sbc_name}] Clicking...")
        try:
            page.locator(f"text='{sbc_name}'").first.click(timeout=3000)
            time.sleep(4)
            save_page(f"sbc_detail_{sbc_name[:20].replace('/', '_')}")

            # Read requirements from the page
            detail = page.inner_text("body")
            # Look for requirement-related keywords
            for kw in ["TOTW", "TOTS", "赛季最佳", "周黑", "周最佳", "rare", "Rare", "稀有", "特殊", "1名", "至少"]:
                if kw in detail:
                    idx = detail.find(kw)
                    print(f"  Found '{kw}' at pos {idx}: ...{detail[max(0,idx-30):idx+80]}...")

            # Go back
            try:
                page.locator("button:has-text('Back')").first.click(timeout=3000)
            except:
                try:
                    page.locator("button:has-text('返回')").first.click(timeout=3000)
                except:
                    page.go_back()
            time.sleep(3)
        except Exception as e:
            print(f"  Error: {e}")

print("\n\n[DONE] Exploration complete. Browser left open.")
input("Press Enter to exit...")
p.stop()
