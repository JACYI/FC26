# FSU C 脚本修改日志（fsu-mod.c.user.js）

> C 脚本 = B 脚本（jackyi.1）集大成者：合并 Fodder（A脚本）精华。
> 需求文档：优化0816.md

## 版本格式
- **v26.09-jacyi.1** — B 脚本基线（fsu-mod.jackyi.js，已归档 archive/v26.09-jacyi.1.user.js）
- **v26.10-jacyi.N** — C 脚本第 N 个功能点（每功能点：语法测试 + 单元测试 + 手动验证清单 + 独立 git commit）

---

## v26.10-jacyi.2 (2026-08-16)

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
