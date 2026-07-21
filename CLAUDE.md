# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FC26 SBC Daily Task Automation — Automate browser-based completion of Squad Building Challenges (SBCs) in EA Sports FC 26 Ultimate Team.

## What is FC26?

EA Sports FC 26 (FC26) is a football/soccer video game. Its **Ultimate Team (FUT)** mode lets players collect player cards and build squads. FC 26 was released on **September 26, 2025**, with a new chemistry system (max 33 team chemistry, 0–3 per player, positional adjacency no longer required).

## What are SBCs?

**Squad Building Challenges (SBCs)** are puzzle-style objectives where you submit squads meeting specific requirements in exchange for rewards (packs, coins, special player cards). Submissions are permanent — submitted players are removed from the club.

### SBC Types

| Type | Description |
|------|-------------|
| **Foundations** | Beginner-friendly, always available. Teaches basic mechanics. |
| **Upgrade SBCs** | Often repeatable. Exchange squads for packs (e.g., Premium Mixed Leagues Upgrade). |
| **Player SBCs** | Time-limited. Submit multiple squads to earn a specific untradeable player. |
| **Live SBCs** | Timed challenges tied to promos/events. |
| **Marquee Matchups** | Weekly, tied to real-world fixtures. Usually 4 segments with escalating difficulty. |
| **League SBCs** | Submit squads from specific leagues for league-specific rewards. |

### Common SBC Requirements

| Requirement | Examples |
|-------------|----------|
| **Squad Rating (OVR)** | Min 68, 74, 77, 80, 82, 83, 85, 87 |
| **Chemistry** | Min 10, 14, 18, 20, 22, 25, 26, 30 |
| **Leagues** | Exactly N leagues, Min N leagues, specific leagues |
| **Nationalities** | Exactly N nations, Min N nations, specific nations |
| **Clubs** | Max N from same club, at least 1 player from specific club |
| **Rarity** | Min N Rare, Exactly N Bronze/Silver/Gold, Min N Gold |
| **Player Quality** | Min N Gold, Exactly Bronze, etc. |
| **Special Cards** | Min N Rares, Min N Specials, TOTW, ICON, etc. |
| **Position Restrictions** | At least 1 player from specific position groups |

### Squad Rating Calculation

Not a simple average — uses a weighted formula:
1. Sum all 11 player ratings
2. Calculate average (do not round)
3. For every player above the average, sum the excess (player_rating - average)
4. Add total excess to original sum
5. Round to nearest whole number, divide by 11
6. **Round down** for final rating

**Rule of thumb (2-3-6 rule):** For an N-rated squad: 2 players at N+1, 3 players at N, 6 players at N-1.

### FC26 Chemistry System

- **Max team chemistry: 33** (each player 0–3)
- **Positional adjacency NOT required** — players link anywhere on the pitch
- Players must be in their correct position to earn chemistry

**Chemistry thresholds:**
| Players sharing condition | Points |
|---------------------------|--------|
| 2 same club / same nation | 1 |
| 3 same league | 1 |
| 4 same club | 2 |
| 5 same nation / same league | 2 |
| 7 same club | 3 |
| 8 same nation / same league | 3 |

**Special cards chemistry:**
- **ICON**: Always 3 chem (preferred position). Counts as +2 to nation thresholds, +1 to all leagues.
- **Hero**: Always 3 chem (preferred position). Counts as +1 to nation, +2 to league thresholds.
- **Manager**: +1 chem to players sharing nationality or league (capped at 1).

### 球员稀有度分类

SBC 按稀有度筛选球员，而非按场上属性。以下是 SBC 相关的稀有度层级：

| 稀有度 | OVR 范围 | SBC 中的应用 |
|--------|----------|-------------|
| **Bronze**（铜卡） | 40–64 | 用于要求 "Exactly Bronze" 的 SBC |
| **Silver**（银卡） | 65–74 | 用于要求 "Exactly Silver" 的 SBC |
| **Gold Common**（金卡普通） | 75–99 | 最常见的 SBC 填充材料 |
| **Gold Rare**（金卡稀有） | 75–99 | 高评分 SBC（83+）的主要材料 |
| **Special**（特殊卡） | 不定 | IF/TOTW/TOTS/TOTY/促销卡等，可替代 Rare |
| **ICON**（传奇） | 85–99 | 固定 3 化学，可做跨联赛/国籍的桥梁 |
| **Hero**（英雄） | 不定 | 类似 ICON，固定 3 化学 |

### SBC 关注的球员属性

SBC 任务**只关注以下字段**，球员的场上属性（速度、射门等）不参与任何 SBC 判定：

| 字段 | 说明 | SBC 中的作用 |
|------|------|-------------|
| **OVR（总评）** | 0–99 的整数评分 | 满足最低评分要求、计算阵容平均评分 |
| **国籍（Nation）** | 球员所属国家 | 满足国籍数量限制或指定国籍 |
| **联赛（League）** | 球员所属联赛 | 满足联赛数量限制或指定联赛 |
| **俱乐部（Club）** | 球员所属俱乐部 | 满足俱乐部数量限制或指定俱乐部 |
| **稀有度（Rarity）** | Bronze / Silver / Gold / Rare / Special / ICON / Hero | 满足最低稀有度或卡类型要求 |
| **位置（Position）** | GK / CB / LB / RB / CM / CAM / LW / RW / ST 等 | 部分 SBC 限制特定位置球员数量 |
| **价格（Price）** | 市场购买价格 | 用于评估 SBC 性价比和选择最便宜的方案 |

### SBC 提交前球员检查规则

在提交 SBC 前，必须对阵容中的每一名球员按以下规则检查，**只要一项不满足就不能提交**，需要替换该球员：

| 稀有度 | 检查条件 | 结果 |
|--------|----------|------|
| **青铜 (Bronze)** | 无检查条件 | 始终通过 |
| **白银 (Silver)** | 是否白银传奇球员？ | 如是 → ❌ 不能提交 |
| **黄金 (Gold)** | ① 身价 > 10,000 金币？ | 如是 -> 不能提交 |
| | ② OVR > 83？ | 如是 -> 不能提交 |
| | ③ 进化中或已进化的球员？ | 如是 -> 不能提交 |
| **其他 (Special/ICON/Hero 等)** | 任何情况 | 不能提交 |

### FSU 插件配置规则 (硬性规定)

**每日任务必须开启的开关（仅此三个，其余开关无论什么任务都不得修改）：**

| 开关 | 状态 | 说明 |
|------|------|------|
| 仅限不可交易球员 | ON | 只使用不可交易的球员填充 |
| 排除指定联赛球员(5) | ON | 排除特定联赛的球员 |
| 优先使用球员仓库球员 | ON | 优先使用仓库球员 |

**重要：任何其他开关（排除进化球员、可使用特殊球员等）都必须保持当前状态，永远不能更改。**

## EA FC 26 Web App Structure

The Web App at `https://www.ea.com/ea-sports-fc/ultimate-team/web-app/` is a **Single Page Application (SPA)**. URL does not change when navigating sections.

### Navigation

Left sidebar buttons: **Home**, **Squads**, **Transfers**, **Store**, **Club**, **SBC**, **Evolutions**, **Settings**

### SBC Page

Accessible by clicking the **SBC** button in the left nav. Sub-tabs at top:
- **All** — all available SBCs
- **Favourites** — user's starred SBCs
- **Players** — player-specific SBCs (time-limited, untradeable players)
- **Upgrades** — repeatable upgrade SBCs (e.g., TOTS upgrades)
- **Challenges** — challenge-based SBCs  
- **Icons** — Icon player SBCs
- **Foundations** — permanent beginner SBCs

Each SBC card shows: name, progress (e.g., 0/2 SBCs), group reward, expiry time, and repeatability.

### Login Flow

1. Open EA Web App → loading animation (~10s) → Login page
2. Click **Login** button → redirects to `signin.ea.com`
3. Fill `#email` → click `#logInBtn` (NEXT) → fill `#password` → click Sign In
4. If first login on device → email verification code required
5. Session persists in Chrome profile via cookies

### Login 状态机（首选方案）

**任何涉及登录、页面状态检测的操作，优先使用 `src/page_machine.py` + `src/page_states.py`，不要自己写 ad-hoc 的状态检测和登录脚本。**

核心文件：
- `src/page_states.py` — 9 种页面状态定义，每种包含 `detect(page)` 静态方法，通过 URL + DOM 判断状态
- `src/page_machine.py` — OODA 状态机（Observe→Orient→Decide→Act→Verify），轮询检测状态变化，无盲等

使用方式：
```python
from src.page_machine import PageMachine

machine = PageMachine(page)
result = machine.run(goal_state="LOGGED_IN")
if result["state"] == "LOGGED_IN":
    # 已登录，继续后续操作
```

状态机覆盖的场景：
- 缓存登录（页面刷新后自动登录）、首次登录、密码/2FA 输入
- FSU 加载等待（"正在读取球员数据"）
- 登录后弹窗关闭（"了解了"/"知道了"/"Got it" 等）
- 英文界面自动切换简体中文
- 所有等待采用轮询检测（无 blind sleep >2s），超时自动恢复

## SBC Automation Architecture (Planned)

### Module Structure

```
src/
├── utils.py                  # CDP connection, state detection, nav helpers
└── sbc/
    ├── models.py             # Data models: SBC, Requirement, Player, SquadSlot
    ├── scanner.py            # Scan SBC page → parse requirements → list available SBCs
    ├── club.py               # Scan Club > Players → filter by OVR/position/league/nation/rarity
    ├── builder.py            # Squad building algorithm (constraint satisfaction)
    └── executor.py           # State-aware flow orchestration
```

### Core Execution Flow (executor.py)

Every step must follow the **state-aware pattern**:
1. **Check** current page state
2. **Recover** if state mismatch (navigate to known good state)
3. **Act** perform the intended action
4. **Verify** action succeeded

```
① enter_sbc(sbc)        → navigate to SBC → click into specific SBC group
② parse_requirements()  → read text: "Min OVR 83, Min Chem 25, Max 3 leagues..."
③ scan_club()           → Club > Players → filter usable players
④ build_squad()         → find 11 players meeting all constraints
⑤ fill_slots(players)   → click each slot → search → select player
⑥ verify_requirements() → check all conditions met → Submit button is clickable
⑦ submit()              → click Submit → confirm
⑧ claim_reward()        → click claim button → collect pack
⑨ collect_pack()        → Store > Packs > open or leave for later
```

### Key Data Models

```
Player:
  - name, ovr, position, nation, league, club
  - rarity (Bronze/Silver/Gold Common/Gold Rare/Special/ICON/Hero)
  - tradeable (bool), price (int)

SBC:
  - name, group_name, tab (Upgrades/Players/Foundations/...)
  - segments: [SBCSegment]
  - is_repeatable, max_repeats, expires_in

SBCSegment:
  - requirements: [SBCRequirement]
  - is_completed (bool)

SBCRequirement:
  - type (MIN_OVR, MIN_CHEM, EXACT_RARITY, MIN_RARITY, MIN_LEAGUES,
           EXACT_LEAGUES, MIN_NATIONS, EXACT_NATIONS, MAX_CLUB,
           MIN_PLAYERS_FROM_CLUB, POSITION_RESTRICTION, etc.)
  - value, operator
```

### Squad Building Strategy

1. Filter player pool by hard constraints (rarity, min OVR, league/nation)
2. Sort by OVR ascending (prefer cheapest cards)
3. Use **2-3-6 rule** as starting point for OVR targets
4. Assign positions, then backfill chemistry via nation/league/club matches
5. Verify all requirements; adjust if any fail
6. Priority: use lowest-rated tradeable cards first, save high-rated untradeables

### Page Refresh / Auto-Login Flow

When the page refreshes (including after language change):
1. **Logo animation** appears (~several seconds) — different animation for Chinese vs English
2. **Two possible outcomes**:
   - **Session valid** → auto-login → loading animation → app ready
   - **Session expired** → login page appears (need to run login flow)
3. Animation takes ~15-20s total. Always wait with `wait_for_page(page, timeout=30)` before checking state.

### Club Page Structure

From Club nav: sections are **Players**, **Consumables**, **Managers**, **SBC Storage**, **Stadium**, **Leaderboards**.
- **Players**: 4908 items in this account. Card format per row:
  ```
  OVR | Position | Name
  PAC SHO PAS DRI DEF PHY   (outfield)
  DIV HAN KIC REF SPD POS   (goalkeeper)
  ```
- Has **Search** bar at top and **Next** pagination button.
- Player detail panel (right side): Player Bio, Apply Consumable, Compare Price, Quick Sell.
- Filter/sort controls available (Position, Rarity, Nation, League, etc.)

### Transfers Page
- Transfer List, Transfer Targets, Selling/Sold counts.
- **Search the Transfer Market** entry point.

### SBC Page (observed April 30, 2026)

Currently available SBC groups on the **Upgrades** tab:
| SBC | Progress | Repeat | Expires |
|-----|----------|--------|---------|
| 1 of 3 82+ PL/BWSL Player Pick | 0/1 | Yes | 1d 9h |
| Premium PL League Upgrade | 0/1 | Yes | 1d 9h |
| Daily Rare Gold Upgrade | 0/1 | x5 | 28d |
| Mixed Leagues Upgrade | **3/4** | Yes | 28d |
| Premium Mixed Leagues Upgrade | 0/4 | Yes | 28d |
| Bronze/Silver/Gold Upgrade | 0/1 | Yes | Permanent |
| 14x 83+ Upgrade | 0/1 | x3 | 15d |
| 85-87 Upgrade | 0/1 | x5 | 28d |
| TOTS Crafting Upgrade | 0/1 | Yes | 29d |

Player SBCs active: Locatelli, Ederson, Mbeumo+Casemiro, Schweinsteiger (ICON), Beckham (ICON), Batistuta (ICON), etc.

**Completed** SBCs (noted): Marquee Matchups ✓, Son (11/11), Reus (9/9), Intro SBCs (all done).

### Technical Quirks & Known Issues

- **CDP connection unstable**: `page.screenshot()` frequently times out (30s). Prefer saving `page.inner_text("body")` to files for debugging.
- **Nav buttons hidden by panels**: When a detail panel is open (e.g., player detail), left nav buttons are behind the overlay. Use JS click to bypass:
  ```python
  page.eval_on_selector('text=SBC', 'el => el.closest("button") ? el.closest("button").click() : el.click()')
  ```
- **Windows GBK encoding**: Chinese characters and special chars (✓) can't print in terminal. Write to UTF-8 files instead.
- **Reliable operations**: `page.inner_text("body")` always works. `click()` with timeout often fails on nav elements. `eval_on_selector` for clicking is more reliable.

### File Structure

```
FC26/
├── CLAUDE.md            # Project documentation
├── index.js             # File index (like a skill registry)
├── data/                # Cached data (players.json, etc.)
├── src/
│   ├── utils.py         # CDP connection, state detection, navigation, fill_input()
│   ├── page_states.py   # 9 page state detectors (Loading→LoginPage→...→LoggedIn)
│   ├── page_machine.py  # OODA state machine: poll → detect → act → verify
│   └── sbc/
│       ├── models.py    # Data models: Player, SBC, Requirement
│       ├── scanner.py   # Scan SBC listing + parse requirements
│       ├── club.py      # Club player scanner + filter
│       ├── builder.py   # Squad building algorithm (FSU fallback)
│       └── executor.py  # State-aware flow: check→recover→act→verify
└── scripts/
    ├── login.py         # Launch Chrome + login flow
    ├── set_language.py  # Set language to Chinese
    ├── switch_lang.py   # Toggle language: python scripts/switch_lang.py English
    ├── explore_app.py   # Read-only page exploration
    ├── explore_sbc_tabs.py # Read-only SBC sub-tab exploration
    └── daily_sbc.py     # Main entry: run all repeatable SBCs daily
```

**Run from project root**: `python scripts/<name>.py`

### Current Account Info

- **Nickname**: AIXZ666
- **Coins**: 171,549
- **Founded**: Est. Nov 2025
- **Platform**: PC (crossplay enabled)
- **Active Squad**: 4-3-2-1 (manager: guan2), rating 92, chemistry 32/33

## Code Modification Rules

### 每次修改必须验证语法

**修改 JS 文件时，每次修改前后都必须执行语法检查：**

```bash
node --check fc26_fsu_mod/【FSU】EAFC FUT WEB 增强器-26.09.yyh.js
```

规则：
1. **修改前**：先检查原始文件语法是否通过（`OK` 或无输出），确认基线
2. **每次编辑后**：立即运行语法检查，确保修改不引入语法错误
3. **多个无关区域的修改**：分批提交，每批修改后验证语法，缩小问题范围
4. **错误处理**：如果 `node --check` 报错，先排查当前修改——不要继续在同一个文件上做更多修改，直到错误修复

**不遵守此规则的后果**：这次花了大几个小时追一个 `}` 不匹配，就是因为修改后没有即时验证，累积了4个区域的问题导致错误位置漂移，排查极为困难。

### 提交前验证流程

仓库配置了 **pre-commit hook**（`.git/hooks/pre-commit`），在 `git commit` 前自动执行：

| 步骤 | 动作 | 失败处理 |
|------|------|---------|
| 1 | `node --check` 语法检查 | 阻止提交 |
| 2 | `node test_submit_cache.js` 单元测试（如有变更） | 阻止提交 |

**手动运行验证：**
```bash
bash fc26_fsu_mod/pre-check.sh
```

**单元测试文件：** `fc26_fsu_mod/test_submit_cache.js`
- 使用 Node.js `assert`，不依赖第三方框架
- 运行：`node fc26_fsu_mod/test_submit_cache.js`
- 新增功能必须补充对应测试用例

## Reference Websites

- https://www.futbin.com/ — Player prices, SBC solutions, market data
- https://www.fut.gg/ — Player database, SBC guides, chemistry analysis
- https://www.fifplay.com/fc-26-sbc-guide/ — SBC guide for beginners
- https://fifauteam.com/fc-26-squad-rating-guide/ — Squad rating calculation details
- https://help.ea.com/ — EA official help for SBC rules
