# -*- coding: utf-8 -*-
"""Test: Daily Bronze Upgrade - FSU config + fill + validate + submit + claim."""
from playwright.sync_api import sync_playwright
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.sbc.logger import log_submission, print_submission_summary
from src.sbc.validator import validate_players, print_validation
from src.sbc.config import ensure_fsu_config, open_fsu_config, close_fsu_config

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]


def log(msg):
    print(msg)
    with open("data/bronze_test.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def click_text(text, timeout=5):
    """Click an element by its text content using Playwright locator with force=True."""
    try:
        page.locator(f'text={text}').first.wait_for(state='attached', timeout=timeout * 1000)
        page.locator(f'text={text}').first.click(force=True, timeout=timeout * 1000)
        return True
    except Exception:
        return False


def wait_for_text(text, timeout=15):
    """Wait for text to appear in page body."""
    try:
        page.wait_for_function(
            f'document.body.innerText.indexOf("{text}") >= 0',
            timeout=timeout * 1000)
        return True
    except Exception:
        return False


log("=" * 50)
log("STEP 1: Navigate to SBC > Upgrades")

# Click SBC nav
page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True)
wait_for_text("全部", timeout=20)

# Click 升级 tab
click_text("升级", timeout=10)
wait_for_text("每日青铜升级", timeout=15)
time.sleep(2)

log("\nSTEP 2: Click 每日青铜升级")
time.sleep(1)
page.get_by_text("每日青铜升级", exact=False).first.click(force=True, timeout=10000)
wait_for_text("提交", timeout=15)
time.sleep(3)

log("\nSTEP 3: Configure FSU plugin settings")
if ensure_fsu_config(page):
    log("  [OK] FSU config applied (3 daily switches set)")
else:
    log("  [WARN] FSU config may be incomplete, continuing...")

time.sleep(2)

log("\nSTEP 4: Click 一键填充(优先重复)")
click_text("一键填充", timeout=5)
time.sleep(5)

# Wait for squad to be filled (Submit button should become enabled)
try:
    page.wait_for_function("""
        () => {
            const btns = document.querySelectorAll('button');
            for (let b of btns) {
                const t = (b.innerText || '').trim();
                if ((t === '提交' || t.indexOf('提交') >= 0) && !b.disabled) return true;
            }
            return false;
        }
    """, timeout=15000)
except Exception:
    log("  [WARN] Submit button did not enable within timeout")
time.sleep(2)

log("\nSTEP 5: Extract filled players")
# Save raw text for debugging
with open("data/bronze_after_fill.txt", "w", encoding="utf-8") as f:
    f.write(page.inner_text("body"))

players = page.evaluate("""
(() => {
    const results = [];
    const slotViews = document.querySelectorAll('.ut-squad-slot-view');

    for (let slot of slotViews) {
        const labelEl = slot.querySelector('.ut-squad-slot-pedestal-view .label');
        const slotPos = labelEl ? labelEl.innerText.trim() : '?';
        const playerCard = slot.querySelector('.ut-item-loaded');

        if (!playerCard) {
            results.push({slot: slotPos, filled: false});
            continue;
        }

        const cardCls = playerCard.className || '';
        const priceItem = playerCard.querySelector('.fsu-PriceBarItem');
        const priceType = priceItem ? priceItem.querySelector('.fsu-PriceType') : null;

        const ovrAttr = priceItem ? priceItem.getAttribute('data-rating') : null;
        const rareflag = priceItem ? priceItem.getAttribute('data-rareflag') : null;
        const fsuSource = priceType ? priceType.getAttribute('data-content') : null;
        const isUntradeable = priceItem ? priceItem.className.indexOf('untradeable') >= 0 : false;
        const priceEl = priceItem ? priceItem.querySelector('.fsu-PriceValue') : null;
        const price = priceEl ? priceEl.innerText.trim() : '';

        const overview = playerCard.querySelector('.playerOverview');
        const ratingEl = overview ? overview.querySelector('.rating') : null;
        const posEl = overview ? overview.querySelector('.position') : null;
        const ovr = ratingEl ? parseInt(ratingEl.innerText) : (ovrAttr ? parseInt(ovrAttr) : 0);
        const position = posEl ? posEl.innerText.trim() : '';

        const isRare = cardCls.indexOf('rare') >= 0 || rareflag === '1';
        const isCommon = cardCls.indexOf('common') >= 0;
        const isSpecial = !isCommon && !isRare;

        const statusOverlay = playerCard.querySelector('.ut-item-player-status');
        const statusCls = statusOverlay ? (statusOverlay.className || '') : '';
        const isEvolution = statusCls.indexOf('evo') >= 0 || statusCls.indexOf('Evo') >= 0;

        let tier = '';
        if (ovr >= 40 && ovr <= 64) tier = '青铜';
        else if (ovr >= 65 && ovr <= 74) tier = '白银';
        else if (ovr >= 75) tier = '黄金';
        let rarity = tier + (isRare ? '稀有' : '普通');
        if (isSpecial) rarity = tier + '特殊';

        const source = (fsuSource === 'sbc' || fsuSource === 'sbcredeem') ? 'SBC仓库' : '俱乐部';

        results.push({
            slot: slotPos,
            filled: true,
            ovr: ovr,
            position: position,
            rarity: rarity,
            source: source,
            tradeable: !isUntradeable,
            price: price,
            is_rare: isRare,
            is_special: isSpecial,
            is_evolution: isEvolution,
        });
    }

    return results;
})()
""")

# Get reward/cost info from page
body = page.inner_text("body")
lines = [l.strip() for l in body.split("\n") if l.strip()]
reward = ""
cost = 0
squad_value = 0
for i, line in enumerate(lines):
    if "高级青铜球员组合包" in line:
        reward = line.strip()
    if line == "预估造价" and i + 1 < len(lines):
        try:
            cost = int(lines[i + 1].replace(",", ""))
        except Exception:
            pass
    if line == "阵容价值" and i + 1 < len(lines):
        try:
            squad_value = int(lines[i + 1].replace(",", ""))
        except Exception:
            pass
if not reward:
    reward = "高级青铜球员组合包 (不可交易)"

log("\nSTEP 6: Validate players")
filled_players = [pl for pl in players if pl.get("filled")]
validation = validate_players(filled_players)
print_validation(validation)

log("\nSTEP 7: Log submission data")
entry = log_submission(
    sbc_name="每日青铜升级",
    players=players,
    reward=reward,
    cost=cost,
    squad_value=squad_value,
)
print_submission_summary(entry)

# Save structured player list
with open("data/bronze_player_list.txt", "w", encoding="utf-8") as f:
    f.write("每日青铜升级 - 填充球员列表\n")
    f.write("=" * 70 + "\n")
    f.write("{:<6} {:<5} {:<6} {:<16} {:<10} {:<8} {:<6} {:<6}\n".format(
        "槽位", "OVR", "位置", "稀有度", "来源", "身价", "可交易", "特殊"))
    f.write("-" * 65 + "\n")
    for pl in players:
        if pl.get("filled"):
            trad = "是" if pl.get("tradeable") else "否"
            spec = "是" if pl.get("is_special") else "否"
            f.write("{:<6} {:<5} {:<6} {:<16} {:<10} {:<8} {:<6} {:<6}\n".format(
                pl['slot'], pl['ovr'], pl['position'], pl['rarity'], pl['source'], pl['price'], trad, spec))
        else:
            f.write("{:<6} {:<5}\n".format(pl['slot'], "---"))
    f.write("\n验证结果: {}\n".format("通过" if validation['valid'] else "不通过"))

# Stop here if validation fails
if not validation['valid']:
    log("\n[ABORT] Validation failed — not submitting")
    print("\n  [ABORT] 验证不通过，不提交")
    p.stop()
    sys.exit(1)

log("\nSTEP 8: Submit")
print("\n  [SUBMIT] 点击提交...")
click_text("提交", timeout=5)

# Handle FSU precious player warning dialog
time.sleep(2)
try:
    warning = page.get_by_text("珍贵球员提示", exact=False)
    if warning.is_visible(timeout=3000):
        log("  FSU珍贵球员提示出现，点击继续")
        print("  [FSU] 珍贵球员提示，点击继续")
        page.get_by_text("继续", exact=False).first.click(force=True, timeout=5000)
        time.sleep(1)
        # Re-click Submit after dismissing warning
        click_text("提交", timeout=5)
except Exception:
    pass

# Wait for claim button (submission successful)
time.sleep(3)
claimed = False
try:
    claim_btn = page.get_by_text("领取奖励", exact=False).first
    if claim_btn.is_visible(timeout=5000):
        log("  [OK] Submission successful, claiming reward...")
        print("  [CLAIM] 领取奖励...")
        claim_btn.click(force=True, timeout=5000)
        time.sleep(2)
        claimed = True
except Exception:
    # Try other claim text variants
    for text in ["领取", "Claim", "点击领取"]:
        try:
            if click_text(text, timeout=2):
                log(f"  [OK] Claimed via '{text}'")
                print(f"  [CLAIM] 通过 '{text}' 领取")
                time.sleep(2)
                claimed = True
                break
        except Exception:
            pass

if claimed:
    log("\n[COMPLETE] 每日青铜升级 done!")
    print("\n  [COMPLETE] 每日青铜升级 完成!")
else:
    log("\n[WARN] Claim button not found — may need manual claiming")
    print("\n  [WARN] 未找到领取按钮，可能需要手动领取")

p.stop()
