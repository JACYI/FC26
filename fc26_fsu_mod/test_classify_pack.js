/**
 * 批量开包引擎 — 分类纯函数 单元测试（v26.10-jacyi.1）
 *
 * 测试目标（边界矩阵）：
 * ① 空仓库（storageMinRating=0）重复球员 → toStorage（回归空仓库必中断 bug）
 * ② 仓库满（storageFree=0）重复 → toUnassigned（默认）/ toSell（discard策略）/ stop信号（stop策略）
 * ③ 可交易重复 + sellDup → toSell
 * ④ 不可交易铜/银非特殊 + discardBs → toSell
 * ⑤ 评分 < 仓库最低分重复 → 不落空（四去向和恒等，修复物品丢失）
 * ⑥ 包内重复（batchSeen）
 * ⑦ sellAll=true 全量 → toSell
 * ⑧ 普通新球员 → toClub
 * ⑨ 组合：sellDup + discardBs + 仓库满同时开启
 * 不变量：所有用例四去向长度之和 === items.length
 *
 * 运行：node fc26_fsu_mod/test_classify_pack.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-01]）=====
//PURE: 包内物品分类（核心决策，副作用全部经 ctx 注入）
// ctx: { sellDup, sellAll, discardBs, storageMinRating, storageFree,
//        inClub(defId)->bool, isDiscardBs(item)->bool, onUnclassifiable }
// onUnclassifiable: 'unassigned'（默认，留未分配）| 'discard' | 'stop'（整批停）
// 不变量：四去向长度之和 === items.length（物品永不丢失，数量核对恒成立）
function classifyPackItems(items, ctx) {
    const out = { toClub: [], toStorage: [], toSell: [], toUnassigned: [], stop: false };
    let storageFree = ctx.storageFree;
    const batchSeen = new Set();
    for (const item of items) {
        const defId = item.definitionId;
        const alreadyOwned = ctx.inClub(defId) || batchSeen.has(defId);
        batchSeen.add(defId);
        if (ctx.sellAll) {
            out.toSell.push(item);
        } else if (alreadyOwned) {
            if (ctx.sellDup && !(item.untradeableCount > 0)) {
                out.toSell.push(item);
            } else if (ctx.discardBs && ctx.isDiscardBs(item)) {
                out.toSell.push(item);
            } else if (item.rating >= ctx.storageMinRating && storageFree > 0) {
                out.toStorage.push(item);
                storageFree--;
            } else if (ctx.onUnclassifiable === 'discard') {
                out.toSell.push(item);
            } else if (ctx.onUnclassifiable === 'stop') {
                out.toUnassigned.push(item);
                out.stop = true;
            } else {
                out.toUnassigned.push(item);
            }
        } else if (ctx.discardBs && ctx.isDiscardBs(item)) {
            out.toSell.push(item);
        } else {
            out.toClub.push(item);
        }
    }
    return out;
}

// ===== Mock 设施 =====
let _seq = 0;
function makeItem(defId, rating, opts = {}) {
    _seq++;
    return {
        id: opts.id || `item-${_seq}`,
        definitionId: defId,
        rating: rating,
        untradeableCount: opts.untradeable ? 1 : 0,
        discardValue: opts.discardValue || 0,
        isSpecial: () => !!opts.special,
        isBronzeRating: () => rating <= 64,
        isSilverRating: () => rating >= 65 && rating <= 74
    };
}

// 默认 ctx 工厂
function makeCtx(overrides = {}) {
    const clubSet = overrides.clubSet || new Set();
    return Object.assign({
        sellDup: false,
        sellAll: false,
        discardBs: false,
        storageMinRating: 0,
        storageFree: 100,
        inClub: (defId) => clubSet.has(defId),
        isDiscardBs: (item) => item.untradeableCount > 0 && !item.isSpecial() && (item.isBronzeRating() || item.isSilverRating()),
        onUnclassifiable: 'unassigned'
    }, overrides);
}

function assertInvariant(out, items) {
    assert.strictEqual(out.toClub.length + out.toStorage.length + out.toSell.length + out.toUnassigned.length, items.length,
        `不变量破坏: 分类和 ${out.toClub.length + out.toStorage.length + out.toSell.length + out.toUnassigned.length} !== ${items.length}`);
}

// ===== 测试 =====
let passed = 0, failed = 0;
function test(name, fn) {
    try {
        fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}\n      ${e.message}`);
    }
}

console.log('\n批量开包分类 单元测试\n' + '='.repeat(40));

// --- ① 空仓库重复球员（回归空仓库必中断 bug）---
test('① 空仓库(threshold=0)+俱乐部重复 → toStorage', () => {
    const items = [makeItem('dup1', 80)];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), storageMinRating: 0 }));
    assert.strictEqual(out.toStorage.length, 1);
    assert.strictEqual(out.toClub.length, 0);
    assertInvariant(out, items);
});

// --- ② 仓库满三策略 ---
test('②a 仓库满+重复 → 默认 toUnassigned（不中断）', () => {
    const items = [makeItem('dup1', 80)];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), storageFree: 0, onUnclassifiable: 'unassigned' }));
    assert.strictEqual(out.toUnassigned.length, 1);
    assert.strictEqual(out.stop, false);
    assertInvariant(out, items);
});

test('②b 仓库满+重复 → discard 策略 toSell', () => {
    const items = [makeItem('dup1', 80)];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), storageFree: 0, onUnclassifiable: 'discard' }));
    assert.strictEqual(out.toSell.length, 1);
    assertInvariant(out, items);
});

test('②c 仓库满+重复 → stop 策略置 stop 信号', () => {
    const items = [makeItem('dup1', 80)];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), storageFree: 0, onUnclassifiable: 'stop' }));
    assert.strictEqual(out.stop, true);
    assert.strictEqual(out.toUnassigned.length, 1);
    assertInvariant(out, items);
});

// --- ③ 可交易重复 + sellDup ---
test('③ 可交易重复+sellDup → toSell', () => {
    const items = [makeItem('dup1', 82, { untradeable: false })];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), sellDup: true, storageMinRating: 70 }));
    assert.strictEqual(out.toSell.length, 1);
    assertInvariant(out, items);
});

test('③b 不可交易重复+sellDup → 不进 toSell（进仓库）', () => {
    const items = [makeItem('dup1', 82, { untradeable: true })];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), sellDup: true, storageMinRating: 70 }));
    assert.strictEqual(out.toSell.length, 0);
    assert.strictEqual(out.toStorage.length, 1);
    assertInvariant(out, items);
});

// --- ④ 不可交易铜银非特殊 + discardBs ---
test('④ 不可交易铜卡+discardBs → toSell', () => {
    const items = [makeItem('new1', 55, { untradeable: true })];
    const out = classifyPackItems(items, makeCtx({ discardBs: true }));
    assert.strictEqual(out.toSell.length, 1);
    assertInvariant(out, items);
});

test('④b 不可交易金卡+discardBs → 不进 toSell（进俱乐部）', () => {
    const items = [makeItem('new1', 80, { untradeable: true })];
    const out = classifyPackItems(items, makeCtx({ discardBs: true }));
    assert.strictEqual(out.toSell.length, 0);
    assert.strictEqual(out.toClub.length, 1);
    assertInvariant(out, items);
});

test('④c 特殊银卡+discardBs → 不进 toSell（保留）', () => {
    const items = [makeItem('new1', 68, { untradeable: true, special: true })];
    const out = classifyPackItems(items, makeCtx({ discardBs: true }));
    assert.strictEqual(out.toSell.length, 0);
    assert.strictEqual(out.toClub.length, 1);
    assertInvariant(out, items);
});

// --- ⑤ 评分 < 仓库最低分重复 → 不落空 ---
test('⑤ 重复评分低于仓库最低 → toUnassigned（不丢失物品）', () => {
    const items = [makeItem('dup1', 75)];
    const out = classifyPackItems(items, makeCtx({ clubSet: new Set(['dup1']), storageMinRating: 80, storageFree: 50 }));
    assert.strictEqual(out.toUnassigned.length, 1);
    assert.strictEqual(out.toStorage.length, 0);
    assertInvariant(out, items);
});

// --- ⑥ 包内重复 ---
test('⑥ 包内重复（同包两个同 defId）→ 第二个走已有分支进仓库', () => {
    const items = [makeItem('p1', 81), makeItem('p1', 81)];
    const out = classifyPackItems(items, makeCtx({ storageMinRating: 75, storageFree: 10 }));
    assert.strictEqual(out.toClub.length, 1, '第一个进俱乐部');
    assert.strictEqual(out.toStorage.length, 1, '第二个进仓库');
    assertInvariant(out, items);
});

test('⑥b 包内重复+sellDup（可交易）→ 第二个 toSell', () => {
    const items = [makeItem('p1', 81), makeItem('p1', 81, { untradeable: false })];
    const out = classifyPackItems(items, makeCtx({ sellDup: true, storageMinRating: 75, storageFree: 10 }));
    assert.strictEqual(out.toClub.length, 1);
    assert.strictEqual(out.toSell.length, 1);
    assertInvariant(out, items);
});

// --- ⑦ sellAll 全量 ---
test('⑦ sellAll=true → 全部 toSell（含不可交易/新球员）', () => {
    const items = [
        makeItem('dup1', 80, { untradeable: true }),
        makeItem('new1', 85),
        makeItem('new2', 60, { untradeable: true })
    ];
    const out = classifyPackItems(items, makeCtx({ sellAll: true, clubSet: new Set(['dup1']) }));
    assert.strictEqual(out.toSell.length, 3);
    assert.strictEqual(out.toClub.length + out.toStorage.length + out.toUnassigned.length, 0);
    assertInvariant(out, items);
});

// --- ⑧ 新球员 ---
test('⑧ 普通新球员 → toClub', () => {
    const items = [makeItem('new1', 84)];
    const out = classifyPackItems(items, makeCtx());
    assert.strictEqual(out.toClub.length, 1);
    assertInvariant(out, items);
});

// --- ⑨ 组合场景 ---
test('⑨ 组合：sellDup+discardBs+仓库满同开，物品不丢失', () => {
    const items = [
        makeItem('dup1', 82, { untradeable: false }),            // 可交易重复 → sell
        makeItem('dup2', 56, { untradeable: true }),             // 铜卡不可交易重复 → discardBs sell
        makeItem('dup3', 84, { untradeable: true }),             // 金卡不可交易重复+仓库满 → unassigned
        makeItem('new1', 83, { untradeable: false }),            // 新球员 → club
        makeItem('new1', 83, { untradeable: false }),            // 包内重复(可交易) → sell
        makeItem('new2', 66, { untradeable: true })              // 新银卡不可交易 → discardBs sell
    ];
    const out = classifyPackItems(items, makeCtx({
        clubSet: new Set(['dup1', 'dup2', 'dup3']),
        sellDup: true, discardBs: true, storageMinRating: 80, storageFree: 0
    }));
    assert.strictEqual(out.toSell.length, 4, 'dup1+dup2+包内dup+new2 出售');
    assert.strictEqual(out.toUnassigned.length, 1, 'dup3 留未分配');
    assert.strictEqual(out.toClub.length, 1, 'new1 进俱乐部');
    assertInvariant(out, items);
});

// --- ⑩ 边界：空包 ---
test('⑩ 空包 → 四去向全空', () => {
    const out = classifyPackItems([], makeCtx());
    assert.strictEqual(out.toClub.length + out.toStorage.length + out.toSell.length + out.toUnassigned.length, 0);
    assert.strictEqual(out.stop, false);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
