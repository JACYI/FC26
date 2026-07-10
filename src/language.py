# -*- coding: utf-8 -*-
"""
EA FC 26 Web App - Language Management

Functions for setting and switching the Web App language between Chinese and English.

Usage as CLI:
    python -m src.language set              # Set to Simplified Chinese
    python -m src.language switch English    # Switch to English
    python -m src.language switch "Simplified Chinese"  # Switch to Chinese

Usage as module:
    from src.language import set_language, switch_language
    set_language(page)
    switch_language(page, "English")
"""
import sys
import time

from src.utils import connect, wait_for_page, get_page_state


def set_language(page):
    """Set Web App language to Simplified Chinese."""
    print("[1] Checking current page state...")
    state = get_page_state(page)
    print(f"    State: {state}")

    body = page.inner_text("body")
    if "简体中文" in body:
        print('[2] Language options visible, clicking Simplified Chinese...')
        page.locator("text=简体中文").first.click()
        time.sleep(3)
        wait_for_page(page, timeout=15)
        print("[3] Language set to Chinese!")
        return True

    print("[2] Navigating to Settings...")
    if state == "login_page":
        print("   Need to login first")
        return False

    _click_settings(page)

    print("[3] Clicking Select Language...")
    page.locator("button:has-text('Select Language')").first.click()
    time.sleep(2)
    wait_for_page(page, timeout=10)

    print("[4] Looking for Simplified Chinese...")
    body = page.inner_text("body")
    if "简体中文" in body:
        page.locator("text=简体中文").first.click()
        time.sleep(3)
        wait_for_page(page, timeout=15)
        print("[5] Language set to Chinese!")
        return True

    for text in ["中文", "Chinese"]:
        if text in body:
            page.locator(f"text={text}").first.click()
            time.sleep(3)
            print(f"[5] Clicked '{text}', waiting for page refresh...")
            wait_for_page(page, timeout=15)
            return True

    print("[5] Could not find Chinese option")
    page.screenshot(path="lang_fail.png")
    return False


def switch_language(page, target_lang):
    """
    Switch Web App language to target_lang.
    Works whether current UI is in Chinese or English.
    target_lang: e.g. 'English' or 'Simplified Chinese'
    """
    body = page.inner_text("body")

    if target_lang in body:
        print(f"  Language options visible, clicking '{target_lang}'...")
        page.locator(f"text={target_lang}").first.click()
        time.sleep(3)
        wait_for_page(page, timeout=15)
        return True

    print("  Looking for Settings button...")
    _click_settings(page)

    body = page.inner_text("body")
    print("  Looking for Select Language button...")
    for label in ["Select Language", "选择语言", "Language Select"]:
        btn = page.locator(f"button:has-text('{label}')").first
        try:
            if btn.is_visible(timeout=1000):
                print(f"  Clicking '{label}'...")
                btn.click()
                time.sleep(2)
                break
        except:
            continue
    else:
        print("  Select Language not found")
        page.screenshot(path="no_lang_btn.png")
        return False

    body = page.inner_text("body")
    if target_lang in body:
        print(f"  Clicking '{target_lang}'...")
        page.locator(f"text={target_lang}").first.click()
        time.sleep(3)
        wait_for_page(page, timeout=15)
        return True

    print(f"  '{target_lang}' not found in language list")
    page.screenshot(path="lang_not_found.png")
    return False


def _click_settings(page):
    """Find and click the Settings button (works in Chinese or English)."""
    for label in ["Settings", "设置"]:
        btn = page.locator(f"button:has-text('{label}')").first
        try:
            if btn.is_visible(timeout=1000):
                print(f"  Clicking '{label}'...")
                btn.click()
                time.sleep(2)
                return
        except:
            continue
    print("  Settings button not found, navigating...")
    page.goto("https://www.ea.com/ea-sports-fc/ultimate-team/web-app/")
    wait_for_page(page)


def _main_set():
    """CLI: set language to Chinese."""
    p, browser, page = connect()
    try:
        print("=" * 40)
        print("EA FC 26 - Set Language to Chinese")
        print("=" * 40)

        from src.utils import ensure_logged_in
        if not ensure_logged_in(page):
            print("Need to login first.")
            return

        success = set_language(page)
        if success:
            page.screenshot(path="language_set.png")
            print("Language set successfully!")
        else:
            print("Failed to set language")

        print("\nBrowser remains open. Press Ctrl+C to exit.")
        while browser.is_connected():
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
        page.screenshot(path="lang_error.png")
    finally:
        try:
            p.stop()
        except:
            pass


def _main_switch():
    """CLI: switch language to target (e.g. English, Simplified Chinese)."""
    target = sys.argv[2] if len(sys.argv) > 2 else "English"

    p, browser, page = connect()
    try:
        print("=" * 40)
        print(f"EA FC 26 - Switch Language to '{target}'")
        print("=" * 40)

        success = switch_language(page, target)
        if success:
            page.screenshot(path=f"lang_{target[:4]}.png")
            print(f"Switched to '{target}'!")
        else:
            print(f"Failed to switch to '{target}'")

        print("\nBrowser remains open. Press Ctrl+C to exit.")
        while browser.is_connected():
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            p.stop()
        except:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.language [set|switch <lang>]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "set":
        _main_set()
    elif command == "switch":
        _main_switch()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
