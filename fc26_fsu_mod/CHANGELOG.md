# FSU C 脚本修改日志（fsu-mod.c.user.js）

> C 脚本 = B 脚本（jackyi.1）集大成者：合并 Fodder（A脚本）精华。
> 需求文档：优化0816.md

## 版本格式
- **v26.09-jacyi.1** — B 脚本基线（fsu-mod.jackyi.js，已归档 archive/v26.09-jacyi.1.user.js）
- **v26.10-jacyi.N** — C 脚本第 N 个功能点（每功能点：语法测试 + 单元测试 + 手动验证清单 + 独立 git commit）

---

## v26.10-jacyi.4 (2026-08-16)

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
