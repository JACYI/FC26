# -*- coding: utf-8 -*-
"""
连接到浏览器 -> 读取 SBC 具体要求 -> 确定 rareflag 值

目标：点击"84+ TOTW 升级"、"英超 TOTS 升级"等 SBC，
读取具体要求中关于特殊球员的描述，判断正确的 rareflag。
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

# 连接
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(CDP_URL)
page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team/web-app" in pg.url:
            page = pg
            break
    if page:
        break

if not page:
    page = browser.contexts[0].pages[0]

print(f"Current URL: {page.url}")

def save_page(name):
    text = page.inner_text("body")
    path = os.path.join(os.path.dirname(__file__), "..", "data", f"sbc_reqs_{name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Saved {path}")

def find_btn(text):
    """Find element with given text"""
    try:
        return page.locator(f"button:has-text('{text}')").first
    except:
        return None

def click_text(text, timeout=3000):
    """Click an element by its visible text"""
    try:
        btn = page.locator(f"button:has-text('{text}')").first
        if btn.is_visible(timeout=1000):
            btn.click(force=True, timeout=timeout)
            time.sleep(3)
            return True
    except:
        pass
    try:
        el = page.locator(f"text='{text}'").first
        if el.is_visible(timeout=1000):
            el.click(force=True, timeout=timeout)
            time.sleep(3)
            return True
    except:
        pass
    try:
        page.evaluate(f"""
            var els = document.querySelectorAll('*');
            for(var i=0; i<els.length; i++) {{
                if((els[i].innerText||'').trim() == '{text}') {{
                    els[i].click();
                    return true;
                }}
            }}
            return false;
        """)
        time.sleep(3)
        return True
    except:
        return False

# ---- 开始探索 ----
# 先看看当前页面
print("\n=== CURRENT PAGE ===")
body = page.inner_text("body")
save_page("current")

# 检查是否有"84+ TOTW 升级"
target_sbcs = [
    "84+ TOTW",
    "TOTS",
    "赛季最佳",
    "86+ TOTW",
    "每周最佳",
    "TOTW",
]

print("\n=== 点击SBC组 ===")
# 先点击到 Upgrades 或 升级 标签
if "Upgrades" in body or "升级" in body:
    tab_name = "Upgrades" if "Upgrades" in body else "升级"
    print(f"Clicking tab: {tab_name}")
    try:
        page.locator(f"button:has-text('{tab_name}')").first.click(force=True, timeout=3000)
        time.sleep(3)
        save_page("upgrades_tab")
    except Exception as e:
        print(f"  Error clicking tab: {e}")

# 尝试点击 84+ TOTW 升级
body = page.inner_text("body")
if "84+ TOTW" in body or "84+TOTW" in body:
    print(f"\n=== Clicking '84+ TOTW 升级' ===")
    try:
        page.locator("text='84+ TOTW 升级'").first.click(force=True, timeout=3000)
        time.sleep(4)
        save_page("84plus_totw_detail")

        # 读取详细要求
        detail = page.inner_text("body")
        # 找关键词
        for kw in ["TOTW", "稀有", "稀有度", "每周", "周黑", "要求", "需求", "条件"]:
            if kw in detail:
                idx = detail.find(kw)
                print(f"  Found '{kw}' at pos {idx}: ...{detail[max(0,idx-30):idx+80]}...")

        # 读取完整页面看具体要求描述
        print("\n=== 84+ TOTW detail body (relevant parts) ===")
        lines = detail.split('\n')
        for i, line in enumerate(lines):
            for kw in ["TOTW", "稀有", "稀有度", "特殊", "tif", "min", "level", "rare", "化学", "OVR", "总评", "要求", "条件", "1名", "球员"]:
                if kw.lower() in line.lower():
                    ctx_lines = lines[max(0,i-1):i+3]
                    for cl in ctx_lines:
                        print(f"    {cl.strip()}")
                    break

        # Go back
        try:
            page.locator("button:has-text('Back')").first.click(force=True, timeout=2000)
        except:
            page.locator("button:has-text('返回')").first.click(force=True, timeout=2000)
        time.sleep(3)
    except Exception as e:
        print(f"  Error: {e}")

# 尝试找到其他需要特殊球员的SBC
body = page.inner_text("body")
for target in ["TOTS 升级", "Crafting Upgrade", "Premium Mixed", "82+ PL", "85-87 Upgrade", "磨砺升级"]:
    if target in body:
        print(f"\n=== Found: {target} ===")
        # Find surrounding context
        idx = body.find(target)
        print(f"  Context: ...{body[max(0,idx-40):idx+len(target)+60]}...")

print("\n\n=== 尝试读取 FSU 缓存数据中的 rareflag 定义 ===")

# 尝试通过浏览器控制台读取 FSU / FUT 内部数据
print("\n--- Try 1: repositories.Rarity ---")
try:
    rarity_data = page.evaluate("""() => {
        try {
            if (typeof repositories !== 'undefined' && repositories.Rarity) {
                return JSON.stringify(repositories.Rarity);
            }
            return 'NOT_FOUND';
        } catch(e) { return 'ERROR: ' + e.message; }
    }""")
    print(f"  Result: {rarity_data[:2000] if len(rarity_data) > 2000 else rarity_data}")
except Exception as e:
    print(f"  Error: {e}")

print("\n--- Try 2: repositories.Item.rarityMap ---")
try:
    rarity_map = page.evaluate("""() => {
        try {
            if (typeof repositories !== 'undefined') {
                // Try various paths
                if (repositories.Item && repositories.Item.rarityMap) return JSON.stringify(Array.from(repositories.Item.rarityMap.entries()));
                if (repositories.Item && repositories.Item._rarityMap) return JSON.stringify(Array.from(repositories.Item._rarityMap.entries()));
                if (repositories.Item && repositories.Item._rarity) return JSON.stringify(repositories.Item._rarity);
            }
            return 'NOT_FOUND';
        } catch(e) { return 'ERROR: ' + e.message; }
    }""")
    print(f"  Result: {rarity_map[:2000]}")
except Exception as e:
    print(f"  Error: {e}")

print("\n--- Try 3: look at a specific TOTS card's rareflag ---")
try:
    # Try to get a sample TOTW/TOTS card rareflag from club data
    tots_info = page.evaluate("""() => {
        try {
            if (typeof repositories !== 'undefined' && repositories.Item && repositories.Item.GetItems) {
                var items = repositories.Item.GetItems();
                // Find a TOTS card - look for levelId or rareflag patterns
                var tots_card = null;
                var totw_card = null;
                for (var i = 0; i < (items.length || 0); i++) {
                    var item = items[i];
                    if (!item) continue;
                    // TOTS typically has high rating and specific rareflag
                    if (item.rareflag === 53 && !tots_card) tots_card = item;
                    if (item.rareflag === 1 && !totw_card) totw_card = item;
                    if (tots_card && totw_card) break;
                }
                var result = {};
                if (tots_card) {
                    result.tots = {rareflag: tots_card.rareflag, rating: tots_card.rating, name: tots_card.name || tots_card.lastName || '?'};
                }
                if (totw_card) {
                    result.totw = {rareflag: totw_card.rareflag, rating: totw_card.rating, name: totw_card.name || totw_card.lastName || '?'};
                }
                return JSON.stringify(result);
            }
            return 'NO_ACCESS';
        } catch(e) { return 'ERROR: ' + e.message; }
    }""")
    print(f"  Result: {tots_info}")
except Exception as e:
    print(f"  Error: {e}")

print("\n--- Try 4: Check if SBC segment requirements have rareflag/levelId ---")
try:
    req_info = page.evaluate("""() => {
        try {
            if (typeof services !== 'undefined' && services.Item && services.Item.GetSBC) {
                var sbc = services.Item.GetSBC();
                return JSON.stringify({found: true, sbc: sbc});
            }
            // Try alternative paths
            if (typeof UTSBCService !== 'undefined') {
                return 'UTSBCService found';
            }
            return 'NOT_FOUND';
        } catch(e) { return 'ERROR: ' + e.message; }
    }""")
    print(f"  Result: {req_info[:2000]}")
except Exception as e:
    print(f"  Error: {e}")

print("\n\n=== DONE ===")
input("Press Enter to exit...")
