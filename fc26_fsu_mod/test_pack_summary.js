/**
 * 批量开包引擎 — 汇总统计 + 进度文案 单元测试（v26.10-jacyi.1）
 *
 * 运行：node fc26_fsu_mod/test_pack_summary.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-01]）=====
//PURE: 汇总统计（storeLoc: 1=俱乐部 2=仓库 3=出售 0=未分配）
function buildPackSummary(records) {
    return records.reduce((acc, e) => {
        if (e.storeLoc === 1) acc.clubCount++;
        else if (e.storeLoc === 2) acc.storageCount++;
        else if (e.storeLoc === 3) { acc.sellCount++; acc.sellCoins += e.discardValue || 0; }
        else if (e.storeLoc === 0) acc.unassignedCount++;
        if (e.isSpecial && e.isSpecial()) acc.specialCount++;
        if (e.rating > acc.playerMaxRating) acc.playerMaxRating = e.rating;
        if ((e.packCount || 0) > acc.packCount) acc.packCount = e.packCount;
        return acc;
    }, { clubCount: 0, storageCount: 0, sellCount: 0, sellCoins: 0, specialCount: 0, packCount: 0, playerMaxRating: 0, unassignedCount: 0 });
}

//PURE: 底部进度条文案（A 的 openedProgress + openedRewardPacks 合并形态）
function formatProgressText(stats, total, texts) {
    const parts = [];
    if (texts.prefix) parts.push(texts.prefix.replace("{done}", stats.done).replace("{total}", total));
    if (stats.clubCount > 0) parts.push(texts.club + "+" + stats.clubCount);
    if (stats.storageCount > 0) parts.push(texts.storage + "+" + stats.storageCount);
    if (stats.sellCount > 0) parts.push(texts.sell + "+" + stats.sellCount + "(" + stats.sellCoins + texts.coin + ")");
    if (stats.unassignedCount > 0) parts.push(texts.unassigned + "+" + stats.unassignedCount);
    return parts.join(" ｜ ");
}

// ===== Mock 设施 =====
let _seq = 0;
function makeRecord(storeLoc, rating, opts = {}) {
    _seq++;
    return {
        id: `r-${_seq}`,
        definitionId: `d-${_seq}`,
        storeLoc: storeLoc,
        rating: rating,
        discardValue: opts.discardValue || 0,
        packCount: opts.packCount || 1,
        isSpecial: () => !!opts.special
    };
}

const TEXTS = {
    prefix: "开包 {done}/{total}",
    club: "俱乐部",
    storage: "仓库",
    sell: "出售",
    coin: "金币",
    unassigned: "未分配"
};

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

console.log('\n开包汇总与进度文案 单元测试\n' + '='.repeat(40));

// --- buildPackSummary ---
test('汇总：俱乐部/仓库/出售/未分配/特殊/最高分/包数', () => {
    const records = [
        makeRecord(1, 80),
        makeRecord(1, 82, { special: true }),
        makeRecord(2, 79),
        makeRecord(3, 75, { discardValue: 500 }),
        makeRecord(3, 74, { discardValue: 300 }),
        makeRecord(0, 70)
    ];
    const s = buildPackSummary(records);
    assert.strictEqual(s.clubCount, 2);
    assert.strictEqual(s.storageCount, 1);
    assert.strictEqual(s.sellCount, 2);
    assert.strictEqual(s.sellCoins, 800);
    assert.strictEqual(s.unassignedCount, 1);
    assert.strictEqual(s.specialCount, 1);
    assert.strictEqual(s.playerMaxRating, 82);
    assert.strictEqual(s.packCount, 1);
});

test('汇总：packCount 取最大包号', () => {
    const records = [makeRecord(1, 80, { packCount: 3 }), makeRecord(1, 81, { packCount: 5 })];
    assert.strictEqual(buildPackSummary(records).packCount, 5);
});

test('汇总：空记录 → 全 0', () => {
    const s = buildPackSummary([]);
    assert.strictEqual(s.clubCount + s.storageCount + s.sellCount + s.unassignedCount + s.specialCount + s.playerMaxRating, 0);
});

test('汇总：sellCoins 累加含 0 值容错', () => {
    const records = [makeRecord(3, 80), makeRecord(3, 81, { discardValue: 600 })];
    assert.strictEqual(buildPackSummary(records).sellCoins, 600);
});

test('汇总：sellAll 模式全量出售（storeLoc=3）收敛统计', () => {
    const records = [
        makeRecord(3, 82, { discardValue: 2000, special: true }),
        makeRecord(3, 60, { discardValue: 100 }),
        makeRecord(3, 75, { discardValue: 400 })
    ];
    const s = buildPackSummary(records);
    assert.strictEqual(s.sellCount, 3);
    assert.strictEqual(s.sellCoins, 2500);
    assert.strictEqual(s.clubCount + s.storageCount + s.unassignedCount, 0);
    assert.strictEqual(s.specialCount, 1);
    assert.strictEqual(s.playerMaxRating, 82);
});

// --- formatProgressText ---
test('进度文案：全去向展示', () => {
    const text = formatProgressText(
        { done: 3, clubCount: 12, storageCount: 8, sellCount: 5, sellCoins: 3200, unassignedCount: 1 },
        10, TEXTS
    );
    assert.strictEqual(text, "开包 3/10 ｜ 俱乐部+12 ｜ 仓库+8 ｜ 出售+5(3200金币) ｜ 未分配+1");
});

test('进度文案：零值去向不展示', () => {
    const text = formatProgressText(
        { done: 1, clubCount: 11, storageCount: 0, sellCount: 0, sellCoins: 0, unassignedCount: 0 },
        5, TEXTS
    );
    assert.strictEqual(text, "开包 1/5 ｜ 俱乐部+11");
});

test('进度文案：空记录只显示前缀', () => {
    const text = formatProgressText(
        { done: 0, clubCount: 0, storageCount: 0, sellCount: 0, sellCoins: 0, unassignedCount: 0 },
        10, TEXTS
    );
    assert.strictEqual(text, "开包 0/10");
});

test('进度文案：prefix 为空则从去向开始', () => {
    const text = formatProgressText(
        { done: 2, clubCount: 3, storageCount: 0, sellCount: 0, sellCoins: 0, unassignedCount: 0 },
        10, Object.assign({}, TEXTS, { prefix: null })
    );
    assert.strictEqual(text, "俱乐部+3");
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
