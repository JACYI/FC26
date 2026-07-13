# FSU 脚本修改日志

## 版本格式
- **v26.09-original** — 原始版本，未修改
- **v26.09-mod-NN** — 第 NN 次修改

---

## v26.09-mod-01 (2026-06-29)

> 修复球员评分显示不准确问题

### 修改内容

#### 1. 球员卡评分自动刷新（renderItem）
- **问题**：FSU 在球员卡上叠加显示的评分（`p.rating`）在特殊卡（色卡/周黑/促销卡）上经常显示为基础评分，与实际不符。点击 EA 原生的评分弹出窗口后刷新元数据才能正确显示。
- **根因**：`p.rating` 在 PlayerMetaData 未加载时返回基础评分。特殊卡片的实际评分需要通过 `PlayerMetaData.updateItemPlayerMeta` 异步加载后才可用。
- **修改**：
  - 评分元素添加 `cursor: pointer`，表明可点击
  - 添加 `click` 事件监听：点击评分时触发 `PlayerMetaData.updateItemPlayerMeta`，加载完成后刷新评分
  - 添加自动加载逻辑：渲染时若元数据未加载（`metaRepo.has` 为 false），主动调用 `updateItemPlayerMeta`，加载完成后更新显示

#### 2. 开包动画评分加载（runAnimation）
- **问题**：开包动画中的球员卡评分同样不准确，且之前无法通过点击刷新
- **修改**：在 `e.generateItem(this.presentedItem)` 后，若当前项为球员类型，自动触发 `PlayerMetaData.updateItemPlayerMeta` 加载元数据

#### 3. Large/Small 球员卡元数据加载（新增）
- **问题**：`UTLargePlayerItemView` 和 `UTSmallPlayerItemView` 各自有独立的 `renderItem` 方法（不继承父类），FSU 对 `UTPlayerItemView.prototype.renderItem` 的覆盖不生效，导致这些卡片上既没有 FSU 叠加层，也无法通过元数据刷新评分。
- **根因**：通过页面抓取确认 `hasOwnRenderItem: true`，原型链为 `LargePlayerItemView → PlayerItemView → ItemView`
- **修改**：Hook Large/Small 的 `renderItem`，在原始渲染后检测元数据是否已加载，未加载时自动调用 `PlayerMetaData.updateItemPlayerMeta`

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `UTPlayerItemView.prototype.renderItem` — 评分显示 + 点击刷新 + 自动加载
  - `UTLargePlayerItemView.prototype.renderItem` — 元数据自动加载（新增）
  - `UTSmallPlayerItemView.prototype.renderItem` — 元数据自动加载（新增）
  - `UTPackAnimationViewController.prototype.runAnimation` — 开包动画元数据加载

### ⚠️ 待确认事项（后续版本跟进）

1. ~~**`UTLargePlayerItemView` / `UTSmallPlayerItemView` 单独 hook**~~ ✅ **v26.09-mod-01 补充已修复**
   - 已在 Large/Small 的 `renderItem` 中添加了元数据自动加载逻辑

2. **加载修改后的脚本到 Tampermonkey 测试**
   - 页面目前加载的是原始 baseline 脚本，不是 working/ 中的修改版本
   - 需将 `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js` 导入 Tampermonkey 才能验证所有修改效果
   - 需将 `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js` 导入 Tampermonkey 才能验证

---

## v26.09-mod-08 (2026-06-29)

> 记录每日SBC完成顺序 — 按时间排序显示在SBC计数弹窗中

### 修改内容

#### 1. `UTSBCService.prototype.submitChallenge` 记录每日SBC日志
- **问题**：用户想知道每天的SBC是按什么顺序完成的、各花了多少时间
- **修改**：每次SBC提交成功时，记录SBC名称 + 完成时间（HH:MM:SS）+ 时间戳到 `GM_setValue("SBCDailyLog")`
- **日志重置**：新的一天开始时自动清空前一天日志

#### 2. SBC计数弹窗增加完成顺序展示
- **修改**：点击顶栏"SBC计数：N"按钮的弹窗中，在原有提示下方增加"今日完成顺序："列表
- **显示格式**：`1. [09:15:30] 每日青铜升级`

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `UTSBCService.prototype.submitChallenge` — 新增每日日志记录
  - `SBCCount.createElement` — 弹窗增加完成顺序展示

---

## v26.09-mod-07 (2026-06-29)

> 球员加载优化 — 优先级分层加载 + 可配置页大小/延迟

### 修改内容

#### 1. 重写 `events.reloadPlayers`：评分分层加载
- **问题**：原来每次登录不分优先级，逐页加载全部 7458 个球员（38 页 × 2-3s），用户必须等全部加载完才能操作。
- **修改**：按 SBC 填充需求分两层加载：
  - **优先层（阻塞）**：40-60（低分青铜）、65-70（低分白银）、75-84（低分黄金）— SBC 填充主力
  - **后台层（不阻塞）**：61-64、71-74、85+（高分/特殊球员）— 不影响操作
- **效果**：优先层约 5-7 页即可加载完成，用户可开始操作，后台层静默加载。

#### 2. 新增配置项
- `players_page_size`（默认 500）：每页加载数量，可在设置中调整
- `players_page_delay`（默认 0.3）：页间延迟秒数

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `events.reloadPlayers` — 分层加载重写
  - `set.init` — 新增 players_page_size / players_page_delay 配置

---

## v26.09-mod-06 (2026-06-29)

> 修复快捷完成任务对每日青铜/白银/黄金升级及2×84+升级不生效

### 修改内容

#### 1. `oneFillCreationGF` 中 TEAM_RATING / CHEMISTRY 不再清空已有填充条件
- **问题**：每日青铜/白银/黄金升级等 SBC 虽然显示"黄金：最少5名球员"等简单条件，但 EA 内部同时包含 `TEAM_RATING`（阵容评分）要求。`oneFillCreationGF` 第10092行检测到 `TEAM_RATING` 时无条件 `gf = []`，导致填充条件被清空，快捷任务和"一键完成"按钮无法创建。
- **修改**：添加 `gf.length === 0` 前置判断——仅当没有其他填充条件时才清空 `gf`。已有球员条件（PLAYER_QUALITY/LEVEL/RARITY 等）时保留，阵容评分可基于球员自动计算。

#### 2. `PLAYER_MIN_OVR` 取消 `req.length === 1` 限制
- **问题**：2×84+ 升级等 SBC 有多个要求（PLAYER_MIN_OVR + TEAM_RATING），原代码 `if (req.length === 1)` 限制导致多条件时跳过，不会生成填充条件。
- **修改**：改为无条件加入 `GTrating` 条件。下游 `events.getItemBy` 会配合其他条件进行过滤。

#### 3. `info.base.fastsbc` 持久化到 GM storage
- **问题**：`info.base.fastsbc` 一直只存在内存中，页面刷新后丢失。`api.fut.to` 服务器挂了之后，数据来源只有用户手动访问 SBC 详情页触发的自动生成，但刷新页面后数据归零，需要重新访问每个 SBC 详情页。
- **修改**：
  - `events.init()` 启动时从 `GM_getValue("fastsbc")` 加载缓存数据
  - 服务端 `fastsbc` 数据加载成功时保存到 GM storage
  - 本地自动添加（`info.base.fastsbc[fastSbcName] = fastSbcNeedInfo`）时同步保存到 GM storage

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `events.oneFillCreationGF` — TEAM_RATING 清空加保护 + PLAYER_MIN_OVR 放宽
  - `events.init` — 启动时从 GM storage 加载 fastsbc 缓存
  - `events.init` 中 fastsbc API 处理 — 成功时保存、失败时从缓存加载
  - SBC 详情面板自动添加 — 本地生成 fastsbc 数据时同步保存到 GM storage

---

## v26.09-mod-05 (2026-06-29)

> 修复新SBC缺少社区推荐率数据 — 移除早期返回，数据缺失时优雅降级

### 修改内容

#### 1. `events.sbcInfoFill` 移除 `hasOwnProperty` 早期返回
- **问题**：新上架的 SBC 不在 `api.fut.to/26/sbc.json` 数据中（因为社区投票尚未生成），而 `sbcInfoFill` 第5146行 `if(!info.task.sbc.stat.hasOwnProperty(d)) return;` 导致整个函数提前退出，新 SBC 不显示任何额外信息（价格、推荐率、到期时间等）。
- **修改**：移除早期返回，改用可选链 `info.task.sbc.stat?.[d]`。
- **推荐率显示**：当 `s` 为 undefined 时，价格显示 0，推荐率显示 `--` 而非崩溃。

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `events.sbcInfoFill` — 移除早期返回+推荐率优雅降级
  - `events.init` 中 sbc.json 处理 — 成功时缓存到 GM storage，失败时读取缓存回退

---

## v26.09-mod-04 (2026-06-29)

> 修复登录后频繁提示"数据加载失败" — 防重入锁 + API 静默错误处理 + 带退避重试

### 修改内容

#### 1. `events.init()` 加防重入锁
- **问题**：`events.init()` 在页面加载和点击"重载数据"磁贴时被多次调用（第6868、6886行），导致多个请求同时发起，造成请求风暴和 EA 限流
- **修改**：添加 `events._initLock` 标志，init 执行期间锁定，执行完毕释放。重复调用直接跳过。

#### 2. 外部 API 请求加 `onerror` 静默处理
- **问题**：`events.init()` 中 13 个 `GM_xmlhttpRequest` 调用到 `api.fut.to`，其中只有主请求有 `onerror` 处理。其余 12 个（meta/pack/sbc/ggrating/evolutions/inpacks/other/fgconfig/playermeta/lowprice）在 API 不可达时静默失败，下游代码使用空数据继续运行。
- **修改**：给全部 12 个嵌套 API 请求添加 `onerror` → `console.warn` 静默记录，不干扰用户。

#### 3. `events.reloadPlayers()` 带退避重试
- **问题**：`services.Club.search()` 在登录后短时间内多次调用时被 EA 限流，失败后直接弹出"球员数据加载失败"通知。
- **修改**：重写错误处理，连续失败时带退避重试（2s→4s→6s），3 次失败后才弹出错误通知。成功时重置计数器。

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `events.init` — 防重入锁 + API onerror
  - `events.reloadPlayers` — 带退避重试机制

---

## v26.09-mod-03 (2026-06-29)

> 修复"满足需求球员"按钮不稳定 — 移除 `meetsRequirements()` 门控条件

### 修改内容

#### 1. 移除 `controller.challenge.meetsRequirements()` 门控
- **问题**："满足需求球员"按钮有时显示有时不显示。原因是按钮被 `controller.challenge.meetsRequirements()` 条件门控，只有当前阵容**已经满足所有 SBC 要求**时才显示。
- **根因**：当阵容评分不足、化学不够时，按钮直接隐藏。用户最需要替换球员的时候反而看不到这个按钮。
- **修改**：移除 `meetsRequirements()` 条件，按钮始终显示。`SBCSetMeetsPlayers` 内部已经通过虚拟挑战逐一检查候选球员（`newChallenge.meetsRequirements()`），不满足要求的不会展示，无候选球员时显示错误提示。

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `UTSquadBuilderViewController` — 移除"满足需求球员"按钮的 `meetsRequirements()` 门控

---

## v26.09-mod-02 (2026-06-29)

> 修复一键填充位置匹配优化 — ignorepos 开关对所有填充路径一致生效

### 修改内容

#### 1. 移除 `playerListFillSquad` 中 `type==2` 的快捷跳过条件
- **问题**：`type==2`（一键填充、阵容补全使用的类型）直接跳过位置判断，导致即使关闭了"忽略位置"开关，一键填充也不会匹配位置
- **根因**：`playerListFillSquad` 第8317行条件 `info.build.ignorepos || e == -1 || type == 2` 中，`type==2` 无条件跳过位置检查
- **修改**：移除 `type == 2`，让一键填充和阵容补全都受到 `info.build.ignorepos` 开关控制

### 涉及文件

- `working/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
  - `events.playerListFillSquad` — 去掉 `type==2` 快捷条件

---

## v26.09-original (2026-06-26)

> 原始脚本，尚未修改。

- 来源：`/【FSU】EAFC FUT WEB 增强器-26.09.user.js`
- 作者：Futcd_kcka
- 描述：EA FC 26 FUT Web App 全功能增强插件
