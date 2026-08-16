# FSU C 脚本修改日志（fsu-mod.c.user.js）

> C 脚本 = B 脚本（jackyi.1）集大成者：合并 Fodder（A脚本）精华。
> 需求文档：优化0816.md

## 版本格式
- **v26.09-jacyi.1** — B 脚本基线（fsu-mod.jackyi.js，已归档 archive/v26.09-jacyi.1.user.js）
- **v26.10-jacyi.N** — C 脚本第 N 个功能点（每功能点：语法测试 + 单元测试 + 手动验证清单 + 独立 git commit）

---

## v26.10-jacyi.8 (2026-08-16)

> 智能填充单按钮 — 合并全部填充/完成按钮为一个「智能填充」：填充 + 自动提交一体，条件分流 + Futbin 模板优先 + 填充前菜单

### 背景

SBC 阵容页有 6 个填充/完成类按钮（一键填充(优先重复)、重复球员填充、阵容补全、SBC方案填充、一键完成、AUTO SOLVE），功能重叠且文案误导（"一键填充(优先重复)"实际是 jacyi.7 的引擎入口）。用户要求只保留一个「智能填充」：填充前弹选项菜单（吸收 fodder 风格，per-SBC 记忆），按条件分流（基本条件→本地算法；特殊条件→Futbin 模板优先→引擎兜底），成功后自动提交。

### 修改内容

#### 1. [C-06] 智能填充模块（events.smartFill，fill.runForCurrent 之后）
- `runForCurrent(controller)`：点击 → 弹填充选项菜单 → 分流 → 落阵 → `submitChallengeFlow` 自动提交
- 分流：`classifySbcMode`（基本集：品质/稀有度/TOTW/最低评分/**阵容总评(均分)** → `"basic"` 本地引擎快速填充；化学/俱乐部/联赛/国籍/精确评分/位置/未知 → `"complex"` 模板优先。均分归 basic：本地 ratingCombo 可直接求解，如"均分84+TOTW×1+11人"无需外部模板）
- 模板路径：`getTemplate({challenge, setInteractionState:noop}, type, sId)` 伪事件调用，以 `templatePlan` 长度对比判定成败（getTemplate 零改动）；失败自动引擎兜底 + `smartfill.template.fail` 提示
- 方案链接/ID 输入（正则复用原 fillSquadBtn）：UUID → type 3，纯数字 → type 2，直接模板跳过分流
- per-SBC 记忆：GM key `SBCFillOptions`（`challengeId#setId` → 规范化选项），菜单"记住此SBC选项"勾选才写
- 菜单选项：球员来源（未分配/队内仓库）、仅不可交易、优先重复（默认开）、仅普通卡、评分范围、价格范围、复杂SBC优先Futbin模板（默认开）、方案链接/ID、记住选项

#### 2. [C-05] 引擎扩展（fill.run opts，全可选缺省零变化）
- 池预过滤：复用 `filterCandidates`（评分/价格/普通卡/不可交易一次到位）
- `poolSource:"storage"`：池传 undefined → `events.getItemBy` 自动用 俱乐部+仓库（replaceData 空值语义 L841）
- `preferDuplicates`：getItemBy 返回稳定排序（重复球员在前），非过滤；storage 模式池规模判定跳过（不误报 fill.error.pool）
- `simplifyReqs` 提取（旧内联循环逐行等价），`fill.run` 复用

#### 3. [C-06] 纯函数层（//PURE:）
- `simplifyReqs` / `classifySbcMode`（分流判定）
- `normalizeFillOptions`（评分钳 40-99、价格 ≥0、min>max 交换、0/空=不限、布尔强转）/ `loadFillOptions` / `saveFillOptions`（store 不可变）
- `resolveSmartFillEnabled`（sbc_smartfill 显式优先；未定义默认开，存量旧开关兼容）

#### 4. 按钮合并（UTSBCSquadOverviewViewController / DetailPanel）
- 删除：fillSquadBtn（方案填充）、dupFillBtn（重复球员填充）、squadCmplBtn（阵容补全，含评分弹窗）、autoFillBtn 的 tipsType 段（无消费方）、quicklyBtn（一键完成）、solveBtn（AUTO SOLVE）
- 新增：`smartFillBtn`（文案"智能填充"，闸门 `resolveSmartFillEnabled`，任何 SBC 可用）→ exchangeElement 前
- 布局 mini 化条件改为 smartFillBtn 存在；批量按钮（每日一键清空/一键三连）改挂 quickOther 末尾
- hideLoader 模板恢复逻辑 fillSquadBtn → smartFillBtn（可选链防抖）
- **保留**：加入流程/流程管理（quickOther 栏）、快捷任务按钮、fastsbc 缓存自动写入（挑战列表一键三连/未分配 Fast 区数据源）、hasChemistry 计算（L6568/L7101/L11119 仍消费）

#### 5. 设置面板
- setfield sbc 列表：删 template/templatemode/dupfill/autofill/squadcmpl，加 smartfill
- solveBox（AUTO SOLVE 参数）→ 替换为「智能填充默认选项」区块（sbcFill_poolSource/minRating/maxRating/minPrice/maxPrice/preferDuplicates/untradeableOnly/commonsOnly/useTemplate，0=不限）
- solver 模块代码保留（`_pendingRs` 被 quickGreedy/fastSBC 读取，删不得）；filterCandidates 被智能填充复用

### 涉及文件

- `fsu-mod.c.user.js`
  - `[C-06]` 块（[C-05] 之后）— smartFill 模块 + 纯函数
  - `[C-05]` fill.run — opts 扩展 + simplifyReqs
  - 按钮区（15213-15480 附近）— 合并为 smartFillBtn
  - 显示区（15526-15566 附近）— 挂载/mini 化
  - quickOther 栏（3643 附近）— 删一键完成/AUTO SOLVE，批量按钮改挂
  - hideLoader（1125 附近）— 模板恢复逻辑
  - 设置面板（8156 附近）— sbcFill 区块；setfield L86
  - `info.localization` — smartfill.* + set.sbcFill.* 三语键（26 个）
- 新增测试：`test_smart_classify.js`（19）/ `test_smart_options.js`（26）
- 更新：`test_fill_flow.js`（19，新增 7 个 opts 用例）

### ⚠️ 待确认事项（手动验证清单）

1. 阵容页只出现一个「智能填充」按钮（原 6 个按钮消失）
2. 点击 → 弹填充选项菜单（选项与上次保存一致）→ 确认 → 填充 + 自动提交
3. 基本 SBC（均分84 + TOTW×1 + 11人 / 84+球员 + TOTW×1）→ 本地算法快速填充成功（不拉模板）
4. 复杂 SBC（联赛+国籍+化学）→ Futbin 模板优先；断网/无方案 → "template.fail" → 引擎兜底成功
5. 菜单记忆：改"仅不可交易"并记住 → 退出重进该 SBC 预载；进其他 SBC 不受影响
6. 方案链接/ID 粘贴 → 直接模板填充
7. 兼容：存量 `sbc_dupfill=true && sbc_autofill=false` 配置下按钮仍显示；设置面板只有"智能填充"一个开关
8. 回归：一键三连/一键清空、未分配 Fast 区、加入流程/流程管理、快捷任务按钮、ignoreBtn、bulkBuyBtn
9. 设置面板：智能填充默认选项区块生效（默认评分范围 0=不限）

---

## v26.10-jacyi.9 (2026-08-16)

> 额外优化1 — 开包引擎三修复：金币/组合包奖励自动兑换（照 fodder 实证 API）、停止按钮修复、进度文案重构 + 瓦片按钮精简

### 背景

需求文档「优化0816.md 额外优化1」：① 组合包开出金币/内层包奖励时无法自动兑换 → 物品无法完全分配、整批中断（停止按钮也失效）；② 全部出售进度提示"出售+12"文案不对；③ 组合包瓦片按钮太多，只留"批量开包 + 打开扩展包"。

**关键逆向**：抓取 fodder client.core.js 实证——EA 原生 `services.Item.redeem(item)` 是兑换 API；A 脚本对开包 items 按 `type === ItemType.MISC("misc")` 分入 redeem 桶，逐条调用 redeem（返回 `{success}`），失败仅日志不中断。金币入账/内层包进"我的包"由 EA 完成。

### 修改内容

#### 1. [C-01] 兑换（五去向）
- `classifyPackItems` 增加第 5 去向 `toRedeem`：判定链最前插 picks（`isPlayerPickItem()` → toUnassigned，本轮保守不处理）与 misc（`type === "misc"` → toRedeem，sellAll 下也不卖 misc）；**不变量升级五去向和 === items.length**；batchSeen 移到分流后（misc defId 不污染去重）
- `openOne` 新增兑换桶：逐条 `deps.redeem(item)`（=`services.Item.redeem`，observable/promise 双形态 + 方法缺失防御），成功记 storeLoc=4，失败记未分配不中断批
- **修复 moveClub 失败提前 return 丢记录**：toStorage/toSell/toRedeem 记录全落，返回 `{failed:true, moveFail:"club"}` 但批继续
- 未分配兜底对无法分类条目（无 type/非球员）console.warn 输出结构供实测反馈

#### 2. [C-01] 停止按钮修复
- `observeOnce` 60s 超时（`PACK_OBSERVE_TIMEOUT_MS`）+ observe 异常兜底（controller 切换不再永久挂起）→ 超时/异常**不重试**（防双开），物品留未分配区由下次批量前置检查兜住
- `openOne` 全流程取消检查点（入口/每次 openPack 后/重试 sleep 前后/各动作前）→ `{cancelled:true}`
- `sleep` 可中断（200ms 轮询令牌，取消提前返回）；主循环包间 sleep 消费取消

#### 3. [C-01] 进度文案重构
- `formatProgressText` 模板句式：`开包 3/10 ｜ 发送俱乐部 12 个 ｜ 放入SBC仓库 8 个 ｜ 出售物品 5 个（金币 3,200） ｜ 兑换 2 个 ｜ 未分配 1 个`（金币千分位，X=0 隐藏对应段）
- `buildPackSummary` 加 redeemCount；结果弹窗 popupm3 追加"兑换 %10 个"

#### 4. [C-09] 瓦片按钮精简 + 弹窗红色规则
- 瓦片删 sellAllBtn/sellDupBtn，只留「批量开包 + 打开扩展包」各 1/2 宽；注入闸门（isPlayers||tradable）不动
- 批量开包点击统一走确认弹窗（数量 + 模式三选 + `tradable` 参数）
- 弹窗红色规则三态：`danger = sellAll || (sellDup && !tradable)` → 全红 #c0392b；不可交易包选出售类时显示红色警示行（openpack.popup.untradable.warn）
- `info_sellall` 开关移除（setfield.info 删"sellall"，两级确认由弹窗模式选择取代）

### 涉及文件

- `fsu-mod.c.user.js`：[C-01] 引擎（L16387-16860 区域：常量/纯函数/_makeDeps/openOne/open 主循环）、瓦片按钮区（L9824-9920）、确认弹窗（L13829-13950）、i18n（L1595-1630）、setfield（L86）
- 更新：`test_classify_pack.js`（29，新增 10 个五去向用例）/ `test_pack_summary.js`（13，模板句式断言重写）
- 新增：`test_pack_flow.js`（10，openOne 流程：redeem 成功/失败/异常、moveClub 不丢记录、超时不重试、取消检查点、sellAll 下 misc 不误卖）

### ⚠️ 待确认事项（手动验证清单）

1. 开含金币奖励的组合包（普通模式）→ 进度条出现"兑换 1 个"，金币入账，同包球员正常分配
2. 开含内层包奖励的组合包 → 兑换后"我的包"出现内层包，批不中断
3. 全部出售模式开组合包 → 文案"出售物品 X 个（金币 xxxx）"+"兑换 X 个"，无"出售+12"
4. 停止按钮：开包挂起时点停止 → 60s 内中断（或立即）；汇总弹窗展示已开部分
5. 瓦片：仅"批量开包 + 打开扩展包"各半宽；弹窗模式三选正常
6. 弹窗红色规则：不可交易包选"出售重复/全部出售"变红 + 警示行；可交易包仅"全部出售"红
7. 三语言切换后新文案正确；设置页无"全部出售"开关残留
8. 若实测发现批量开包"莫名中断"：第一嫌疑是运行中 EA 触发了 hideLoader（其仍会置取消令牌，jacyi.1 有意设计）
9. 全量回归：`bash fc26_fsu_mod/pre-check.sh`（228 个测试）

### 已知边界（后续迭代）

- picks（球员选择卡）本轮留未分配（A 脚本走专门 confirmPlayerPickItemSelection 流程）
- 不可交易混合包瓦片不注入"批量开包"（[C-05] 安全闸门，可单独放开）
- misc 判定依赖 EA 字段形态（fodder 实证有效）；无法分类条目有结构诊断 warn，实测反馈即可修正

---

## v26.10-jacyi.7 (2026-08-16)

> AUTO SOLVE 2.0 — 通用 SBC 填充引擎：融合所有填充算法，按需求类型自动路由，任何 SBC 都能填充

### 背景

用户重新定位 AUTO SOLVE：应为"阵容补全/SBC方案填充"按钮的替代，融合所有相关算法，针对不同类型 SBC 选择不同算法，最终都能填充出符合需求的球员。调研确认 B 的硬边界：`oneFillCreationGF` 只认识 4 类需求（品质/稀有度/最低评分），联赛/国籍/俱乐部/精确评分/化学 SBC 无法一键填充；两个闸门（hasChemistry/oneFillCriteria）导致按钮不显示。

### 修改内容（5 步实施）

#### 1. [C-05] 纯函数层
- `parseRequirements`：需求 → groups/flags/summary；**关键突破**——getItemBy 的 default 分支支持任意直接字段匹配，CLUB_ID→`teamId`（expandTeamIds 同队扩展）、LEAGUE_ID→`leagueId`、NATION_ID→`nationId`、EXACT_OVR→`rating`、POSITION→`includePos` 全部可作 criteria，无需改检索核心；TEAM_RATING/CHEMISTRY 仅置 flags；未知需求透传不丢弃
- `routeAlgorithm`/`buildChain`：算法链路由（chem→extended→rating→basic 约束组先填，verifyFallback 恒末尾）+ 强制覆盖（legacy/fodder 旧行为零变化）
- `classifyFailure`：失败原因分类（pool→chem→rating→req→noanswer 优先级，partial 也算约束未满足）
- `expandTeamIds`/`chemScore`/`scoreCandidate`/`compareScore`/`capShortlist` 辅助纯函数

#### 2. 算法库 + 引擎控制流
- `fill.algorithms`：quickGreedy（现有 4 类，fodder 参数注入）/ reqAware（扩展类型）/ ratingCombo（needRatingsCount+getRatingPlayers）/ verifyFallback（受限回溯，候选 cap 200 + virtualMeets cap 2000）
- `fill.run` 主流程：parse → 路由 → 逐算法（排除链 NEdatabaseId + **excludeRatings exact 评分占用**）→ 终校验（EA meetsRequirements）→ 失败分类
- **测试暴露并修复 3 个真实缺陷**：① 路由顺序（quickGreedy 先填满导致扩展约束缺失 → 约束组先填）② excludeRatings 时序（取数前占用导致自己组被过滤 → 取完再占用）③ 算法 status 语义（组取不够即使填满也标 partial → shortfall 标记）
- `fill.runForCurrent`：按钮入口（填充 + 落阵保存 + 分类通知）

#### 3. chemFirst + 按钮升级
- `chemFirst` 算法：化学启发式排序（候选与已选球员同俱乐部×3/联赛×2/国家×1 加权，低评分次之；纯化学需求走全量候选）；终校验兜底
- **一键填充按钮升级**：移除闸门B（不依赖 oneFillCriteria，任何 SBC 创建）；移除闸门A（化学 SBC 也插入，chemFirst 处理）；点击 → `fill.runForCurrent`（auto 路由）；失败 setInteractionState(0) + 分类通知
- dupFill/squadCmpl 保留原闸门（不处理化学）；fillSquadBtn（方案）不动；布局 mini 化按"任一填充按钮存在"执行
- i18n：fill.done + fill.error.pool/chem/rating/req/noanswer 三语键

#### 4. AUTO SOLVE auto 模式
- `solve_algorithm` 默认 **auto**（存量 legacy/fodder 兼容），设置下拉加"自动路由（智能）"
- `events.submitChallengeFlow`：从 fastSBC 提交段提取（逐行等价：可提交检查/不可交易警告/提交/奖励弹窗/页面刷新/PIN），fastSBC 本体零改动
- `solver.algorithms.auto`：fill.run 引擎填充 → 落阵 → submitChallengeFlow；solveLoop 加 auto 分支
- **收益**：批量 AUTO SOLVE 不再依赖 fastsbc 缓存（未进过阵容页的 SBC 也能求解），能求解化学/俱乐部类 SBC

#### 5. 收尾
- VERSION、归档快照、完整记录

### 涉及文件

- `fsu-mod.c.user.js`
  - `[C-05]` 块（文件尾，[C-04] 后）— fill 引擎全套 + submitChallengeFlow
  - `oneFillCreationGF`（10526）— **零改动**（fastsbc 缓存兼容）
  - 按钮创建段（15257-15359）— 闸门B 移除 + 智能填充回调
  - 按钮插入段（15516-15550）— 闸门A 拆分 + 布局
  - `[C-03]` solver — normalizeSolveOptions/_loadOptions/algorithms.auto/solveLoop 分支
  - 设置面板（8166）— 算法下拉加 auto
  - `info.localization` — fill.* + set.solve.algorithm.auto 三语键
- 新增测试：`test_fill_parse.js`（23）/ `test_fill_route.js`（14）/ `test_fill_chain.js`（19）/ `test_fill_flow.js`（12，async 感知 mock 控制流）
- 更新：`test_solve_options.js`（algorithm auto 语义，16 用例）

### ⚠️ 待确认事项（手动验证清单）

1. **智能填充按钮**：SBC 详情页"一键填充"现在任何挑战都显示（含化学/俱乐部/联赛 SBC）
2. 纯评分 SBC（如 83+）→ 快速贪心填充成功
3. 俱乐部/联赛/国籍 SBC（如"至少 4 个曼城"）→ reqAware 正确筛选（约束组先填）
4. 化学 SBC → chemFirst 优先选同队/同联赛球员，失败给"化学约束无法满足"分类提示
5. 精确评分 SBC（EXACT_OVR）→ 恰好 N 人该评分，补人不重复选同分
6. 填不满 → 分类提示（未分配不足/约束无解/穷尽无解），按钮禁用可再次点击
7. **AUTO SOLVE 按钮**（auto 默认）：对未进过阵容页的 SBC 也能批量完成（不再报 fastsbc.error_1）
8. 设置切 legacy/fodder → 行为与旧版一致（回归）
9. 化学 SBC 详情页布局：智能填充按钮显示且布局不错位（mini 化正常）
10. 排除配置（屏蔽联赛/不可交易）在智能填充中生效（ignorePlayerToCriteria 复用）

> 开包进度提示去重 — 去掉居中"正在打开"重复文案，进度条改为屏幕居中浮层面板

### 修改内容

1. `packs.open` 移除两处 `changeLoadingText` 调用（打开前 + 每包前）——不再在居中 loading 遮罩显示"正在打开/开启进度"，消除与进度条的双重提示
2. 进度条（`packs._ensureBar`）从底部改为**屏幕居中**浮层面板：fixed + top/left 50% + translate(-50%,-50%)，半透明深色背景、圆角、阴影、最大宽 90vw 自动换行；停止按钮 + 统计文案（俱乐部/仓库/出售/未分配）保留

### 涉及文件

- `fsu-mod.c.user.js`：[C-01] `packs.open` / `packs._ensureBar`

### ⚠️ 待确认事项（手动验证清单）

1. 批量开包时屏幕中央显示进度面板（含停止按钮），无"正在打开"居中文字
2. 进度面板不遮挡包卡片操作区，结束 6 秒后淡出
3. 点击停止 → 当前包完成后停止，弹汇总

> 修复：可交易混合包（如白银组合包，contentType ≠ 'players'）不显示开包/全出售按钮

### 背景

白银组合包为**可交易混合包**（含球员+物品），`packInfo.isPlayers`（contentType === 'players'）为 false，导致整个 FSU 按钮区（批量打开/出售重复/全出售）未注入。需求文档明确"可交易的球员**或物品**"。

### 修改内容

1. **注入条件放宽**（商店按钮区）：`packInfo.isPlayers` → `(packInfo.isPlayers || packInfo.tradable)`——可交易包（纯球员/混合/物品包）都显示三按钮；不可交易混合包仍不注入
2. **引擎 isDiscardBs 方法缺失容错**（[C-01] `_makeDeps`）：非球员物品无 `isSpecial`/`isBronzeRating`/`isSilverRating` 方法，加 typeof 守卫 + try/catch，缺失时返回 false（不误卖、不抛错）
3. **非球员物品分类行为**：普通模式 → 移俱乐部（失败留未分配，引擎降级矩阵兜底）；sellAll 模式 → 全部 toSell（物品+球员出售换金币）
4. 文案：全出售按钮副标题改为"所有球员/物品立即出售换金币"

### 涉及文件

- `fsu-mod.c.user.js`
  - 商店按钮注入条件（9685 附近）
  - `[C-01] packs._makeDeps` — isDiscardBs 容错
  - `info.localization` — sellallbtn.subtext 文案更新
- 测试：`test_classify_pack.js` 新增 4 个混合包用例（物品不误卖/sellAll 收敛/物品重复去向/不落空）

### ⚠️ 待确认事项（手动验证清单）

1. 白银组合包（可交易）现在显示三个按钮（红色全出售/出售重复/批量打开）
2. 普通批量打开混合包 → 球员进俱乐部/仓库，物品进俱乐部，无报错中断
3. 全出售混合包 → 球员+物品全部出售，金币入账，汇总正确
4. 不可交易混合包仍不显示按钮（预期）

> 自定义流程编排 — 参考 A 脚本 routines：SBC 完成+开包循环，可排序可每日

### 修改内容

#### 1. routine 命名空间（[C-04] 块）
- 纯函数（`//PURE:`）：`normalizeRoutine`（校验/补默认/非法 packMode 回退）/ `routineIsExpired`（daily + expiresDaysHours 从 createdAt 起算，0/0 视为未设置不过期）/ `normalizeRoutineStore`（版本号 + 过期过滤）
- `routine.load/save`：持久化 GM key `fsu_routines`（带 v 版本号，结构可演进）；load 时清理过期流程
- `routine.run` 执行引擎：逐步骤"完成 SBC → 开包"循环，异常/失败跳过继续，汇总；完成复用 `events.fastSBC`（B 链路），开包复用 `packs.open`（[C-01] 引擎，继承稳定性）
- `routine.runAll`：执行全部启用且未过期的流程

#### 2. UI（参考 A 的 createRoutine/addSbc/editRoutine/deleteRoutine）
- SBC 详情 quickOther 容器新增"加入流程"（追加到默认流程）和"流程管理"按钮
- 流程管理弹窗：流程选择/新建/删除、步骤列表（packMode 选择：开包/出售重复/全部出售/不开包）、步骤上移/下移/删除、"立即执行"
- 每日模式与过期时间在数据模型层就绪（UI 开关后续可加）

### 涉及文件

- `fsu-mod.c.user.js`
  - `[C-04]` 块（文件尾）— routine 全套
  - SBC 详情按钮区（quickOther）— 加入流程/流程管理按钮
  - `info.localization` — 新增 15 个三语键（routine.*）
- 新增测试：`test_routine_model.js`（15 用例）

### ⚠️ 待确认事项（手动验证清单）

1. SBC 详情页出现"加入流程"和"流程管理"按钮
2. 点击"加入流程"→ 通知"已加入流程"，流程管理弹窗可见该步骤
3. 流程管理：新建流程、步骤上移/下移/删除、packMode 切换生效
4. "立即执行"→ 按步骤顺序"完成SBC→开包"循环，进度通知逐步骤显示
5. 某步骤 SBC 无法完成时跳过继续，汇总显示异常数
6. 开包模式"全部出售"联动 [C-02] 红色确认
7. 过期流程（daily + 超时）在 load 时被清理（重启页面后消失）

> AUTO SOLVE 双算法 — 吸收 A 脚本自动求解（参数化策略），用户可切换 B 旧算法 / A 风格新算法

### ⚠️ 关键事实（逆向结论）

**A 脚本的求解核心 `sz(x)` 是 fodder.gg 后端服务**（服务器求解，Gold 会员限制，本地无法复刻黑盒）。本功能复刻 A 的**协议与策略**：
- A 的求解输入协议（需求标准化 + 候选池 + 过滤参数 + 平台）
- A 的参数化策略（minRating/maxRating/minPrice/maxPrice/commonsOnly/untradeableOnly/storageOnly）
- 本地实现：参数化候选过滤 + 评分约束注入 B 检索（rs 覆盖）
- 未搬运 A 的 Gold 会员逻辑（糟粕丢弃）

### 修改内容

#### 1. solver 命名空间（[C-03] 块）
- 纯函数（`//PURE:`）：`normalizeSolveOptions`（参数校验/边界钳制/min>max 交换）/ `filterCandidates`（A 风格过滤，unitCoins 按价格/unitOvr 按评分排序）/ `filterUnfinishedChallenges`（复制 A 挑战过滤）/ `buildSolveSummary`
- `solver.algorithms.legacy`：B 旧算法 — 原样走 events.fastSBC 链路，行为零变化
- `solver.algorithms.fodder`：A 风格新算法 — 参数化候选池预判（不足则跳过记录原因）+ rs 评分约束注入
- `solver.solveLoop`：未完成挑战循环 → 按算法逐个求解 → 汇总（每挑战失败跳过继续）
- `solver.runForCurrent`：当前 SBC 一键入口

#### 2. 用户切换与参数（设置面板新增 AUTO SOLVE 区块）
- 新增渲染器 `set.addSelect`（下拉）/ `set.addNumber`（数字输入）
- 算法切换 `solve_algorithm`（默认 legacy — 新算法未验证不默认启用）
- 求解参数：次数/最低评分/最高评分/最低价格/最高价格（存 info.set.solve_*）
- SBC 详情"一键完成"旁新增 AUTO SOLVE 按钮（quickOther 容器）

#### 3. fastSBC 参数注入（最小侵入）
- 检索条件构造处加 rs 覆盖钩子：solver._pendingRs 存在时覆盖检索评分范围（solver 调用后 finally 清空）

### 涉及文件

- `fsu-mod.c.user.js`
  - `[C-03]` 块（文件尾）— solver 全套
  - `events.fastSBC`（10541 附近）— rs 参数注入钩子（2 行）
  - SBC 详情按钮区（3607 附近）— AUTO SOLVE 按钮
  - 设置面板（8099 附近）— AUTO SOLVE 设置区块
  - `set` 对象 — 新增 addSelect/addNumber 渲染器
  - `info.localization` — 新增 15 个三语键（set.solve.* / solve.*）
- 新增测试：`test_solver_core.js`（15 用例）/ `test_solve_options.js`（14 用例）

### ⚠️ 待确认事项（手动验证清单）

1. SBC 详情页出现 AUTO SOLVE 按钮（一键完成旁）
2. 默认 legacy 算法：点击 AUTO SOLVE → 按 B 原行为完成挑战
3. 设置切到"新算法（A风格）"→ 点击 → 参数化过滤生效（如 minRating=80 时 80 分以下卡不被选用）
4. 求解次数限制生效（设置次数=2 时只解 2 个挑战）
5. 挑战全部完成时提示"all-complete"，不误报
6. 参数越界钳制（minRating 输入 10 → 保存为 40）
7. A 风格算法在候选不足时提示跳过原因（如 maxRating=70 且 SBC 要求 83）

> 可交易包自动开启并全部出售 — 红色警示 + 两级确认防误点，批量模式三选

### 修改内容

#### 1. 商店第三个按钮 `.fsu-sellall`（仅可交易包）
- 文案"自动开启并全部出售"，**红色警示样式**（#c0392b）+ 布局 全出售/出售重复/批量打开 均分、打开扩展包占半
- 两级确认：点击 → 红色确认弹窗（"⚠️ 开包后所有球员/物品将立即出售换金币，不可恢复！"）→ 确认后执行
- 配置 `info_sellall`（设置面板"全部出售确认"，默认开）— 关闭则点击直接执行

#### 2. 确认弹窗模式三选
- 批量打开/出售重复按钮的确认弹窗增加模式选择：普通批量 / 出售重复 / 全部出售
- sellAll 模式红色高亮（防误点核心），OK 时透传 `sellAll` 参数到引擎

#### 3. 引擎整合（复用 [C-01]）
- `classifyPackItems` 决策表第一行 `sellAll → 全 toSell`（功能一已实现，本次由按钮通路触发）
- 出售链路沿用引擎降级矩阵：discard 失败 → fallback 转会名单
- 汇总弹窗 `popupm3` 展示出售数与金币合计

### 涉及文件

- `fsu-mod.c.user.js`
  - 商店按钮区（9685-9740）— 新增 sellAll 按钮
  - `events.openPacksConfirmPopup` — 模式三选 UI + sellAll 红色确认文案
  - `info.setfield.info` — 新增 "sellall" 开关
  - `info.localization` openpack.* — 新增 6 个三语键
- 测试：`test_classify_pack.js` 用例⑦（sellAll 收敛，16 用例）、`test_pack_summary.js` 新增 sellAll 汇总用例（9 用例）

### ⚠️ 待确认事项（手动验证清单）

1. 可交易包显示第三个红色按钮，布局不挤爆容器（不可交易包仍只有批量打开）
2. 点击红色按钮 → 红色确认弹窗（不可恢复文案），取消不执行
3. 确认后开包，所有球员立即出售，金币到账（商店金币数变化正确）
4. 批量弹窗模式三选：切到"全部出售"→ OK 后按 sellAll 执行；红色高亮明显
5. discard 失败场景 fallback 转会名单（可断网模拟部分失败）
6. 设置面板关闭"全部出售确认"后，红色按钮点击直接执行（无确认弹窗）

## v26.10-jacyi.1 (2026-08-16)

> 批量开包引擎重构 — 修复批量开包中断的 6 个根因，吸收 A 脚本（fodder）开包精华

### 修改内容

#### 1. 修复批量开包中断根因（6 个）
- **根因1 空仓库必中断**：`_.min([])` 返回 `Infinity`，重复球员评分 `>= Infinity` 恒 false 无法入仓库 → 数量核对失败整批中断。修复：空仓库时存储阈值归 0（`getStorageState`）
- **根因2 分类落空物品丢失**：俱乐部重复球员不满足出售条件且评分<仓库最低/仓库满时落入所有分支之外 → 核对失败硬中断。修复：新纯函数 `classifyPackItems` 四去向全覆盖（含 `onUnclassifiable` 三策略），**不变量：四去向和恒等于包内物品数，核对永不失败**
- **根因3 无 catch**：外层 try/finally 无 catch，任何异常放弃剩余包无提示。修复：单包降级矩阵——网络错误指数退避重试（1/2/4/8s 上限 30s，最多 3 次）、429 限流长退避、401/403 会话失效致命停止、move 失败留未分配继续、discard 失败 fallback 转会名单（沿用 B 逻辑）
- **根因4 汇总丢失**：`errorOccurred` 时不弹汇总。修复：`finally` 无条件弹结果弹窗（含未分配/失败统计），新增 `openpack.result.popupm3` 文案
- **根因5 取消耦合**：`hideLoader` 任何调用都静默取消批量（与其他流程互踩）。修复：令牌制 `packs._cancelToken`，hideLoader 只置令牌；引擎收尾用专用 `_finishLoader`
- **根因6 弹窗未接线**：数量选择弹窗已实现但按钮直接全量开。修复：两个商店按钮（批量打开/出售重复）均先弹数量确认弹窗，sellDup 模式透传

#### 2. 新增开包引擎（[C-01] 块）
- 命名空间 `packs`：`packs.open(options, deps)` 主循环 / `packs.openOne` 单包 / `packs._makeDeps` 生产依赖注入
- 纯函数（`//PURE:` 标记，复制进测试）：`classifyPackItems` / `buildPackSummary` / `formatProgressText` / `nextRetryDelay` / `isFatalError`
- 适配器 `events.openPacks` 覆盖旧实现，旧签名不变，调用点零改动

#### 3. 吸收 A 脚本精华
- **进度提示**（对应 A 的 openedProgress）：底部常驻进度条，文案 `开包 3/10 ｜ 俱乐部+12 ｜ 仓库+8 ｜ 出售+5(3200金币) ｜ 未分配+1`，附"停止"按钮
- **去向统计**（对应 A 的 openedRewardPacks）：俱乐部/仓库/出售/未分配实时计数
- **限流退避**（对应 A 的 rateLimited）：429 长退避 5/15/30s
- **仓库满策略**（对应 A 的 stoppedFull）：默认留未分配继续，可配置 discard/stop

#### 4. 结果弹窗全量展示
- `openPacksResultPopup` 加 `scrollable` 可选参数（默认 false，既有 3 处调用点行为不变）；新引擎调用传 true，列表 60vh 滚动，不再 `.slice(0, 20)` 截断

### 涉及文件

- `fsu-mod.c.user.js`
  - `events.hideLoader`（1143-1145 附近）— 取消令牌化
  - 商店包按钮（9685-9720）— 接线数量弹窗
  - `events.openPacksConfirmPopup` — 增加 sellDup 参数
  - `events.openPacksResultPopup` — scrollable 参数 + 滚动容器
  - `info.localization` openpack.* — 新增 9 个三语键
  - `[C-01]` 块（文件尾）— 开包引擎全套
- 新增测试：`test_classify_pack.js`（16 用例）/ `test_pack_summary.js`（8 用例）/ `test_pack_retry.js`（7 用例）

### ⚠️ 待确认事项（手动验证清单）

1. Tampermonkey 导入 `fsu-mod.c.user.js`，**禁用 `fsu-mod.jackyi.js`**（两者都改 EA 原型，双跑必互踩）
2. **空仓库账号**开含重复球员的包 → 批次不中断，重复球员正常进 SBC 仓库
3. 仓库满时开包 → 重复球员去未分配（默认策略），批次继续，汇总显示"未分配 N"
4. 开包中途断网 → 退避重试后继续，不整批放弃
5. 点击底部"停止"按钮 → 当前包完成后停止，弹汇总
6. 结果弹窗展示全部球员（60vh 滚动），含未分配/失败统计
7. "批量打开"按钮 → 数量选择弹窗 → 确认后按数量开包
8. 一键开包（出售重复）→ 弹窗文案为出售重复模式，确认后生效
