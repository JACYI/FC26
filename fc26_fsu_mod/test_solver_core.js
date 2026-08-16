/**
 * AUTO SOLVE — 候选过滤 + 挑战筛选 + 循环统计 单元测试（v26.10-jacyi.3）
 *
 * 运行：node fc26_fsu_mod/test_solver_core.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-03]）=====
//PURE: A 风格候选过滤（unitCoins: 按价格升序优先；unitOvr: 按评分升序优先）
function filterCandidates(items, options, helpers) {
    helpers = helpers || {};
    const isSpecial = helpers.isSpecial || ((it) => !!(it.isSpecial && it.isSpecial()));
    const isUntradeable = helpers.isUntradeable || ((it) => it.untradeableCount > 0);
    const filtered = items.filter((it) => {
        const rating = it.rating || 0;
        if (options.minRating != null && rating < options.minRating) return false;
        if (options.maxRating != null && rating > options.maxRating) return false;
        if (options.minPrice != null && (it.price || 0) < options.minPrice) return false;
        if (options.maxPrice != null && (it.price || 0) > options.maxPrice) return false;
        if (options.commonsOnly && isSpecial(it)) return false;
        if (options.untradeableOnly && !isUntradeable(it)) return false;
        return true;
    });
    const unit = options.unitCoins ? (it) => it.price || 0 : (it) => it.rating || 0;
    return filtered.sort((a, b) => unit(a) - unit(b));
}

//PURE: 未完成挑战筛选（复制自 A 的挑战过滤逻辑）
function filterUnfinishedChallenges(challenges) {
    return challenges.filter((c) => {
        try {
            return !(c.status === "COMPLETED" || (c.isComplete && c.isComplete()));
        } catch (e) { return true; }
    });
}

//PURE: 求解循环统计
function buildSolveSummary(results) {
    return results.reduce((acc, r) => {
        if (r.solved) acc.solved++;
        else acc.skipped++;
        return acc;
    }, { solved: 0, skipped: 0 });
}

// ===== Mock 设施 =====
let _seq = 0;
function makePlayer(rating, opts = {}) {
    _seq++;
    return {
        id: `p-${_seq}`,
        rating: rating,
        price: opts.price || 0,
        untradeableCount: opts.untradeable ? 1 : 0,
        isSpecial: () => !!opts.special
    };
}
function makeChallenge(id, status, isComplete) {
    return { id: id, name: `ch-${id}`, status: status || "ACTIVE", isComplete: isComplete || (() => false) };
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

console.log('\nAUTO SOLVE 核心 单元测试\n' + '='.repeat(40));

// --- filterCandidates ---
test('minRating/maxRating 边界过滤', () => {
    const pool = [makePlayer(80), makePlayer(83), makePlayer(87), makePlayer(90)];
    const out = filterCandidates(pool, { minRating: 83, maxRating: 87 });
    assert.deepStrictEqual(out.map(p => p.rating), [83, 87]);
});

test('minPrice/maxPrice 过滤', () => {
    const pool = [makePlayer(80, { price: 500 }), makePlayer(83, { price: 2000 }), makePlayer(87, { price: 8000 })];
    const out = filterCandidates(pool, { minPrice: 1000, maxPrice: 5000 });
    assert.deepStrictEqual(out.map(p => p.rating), [83]);
});

test('commonsOnly 排除特殊卡', () => {
    const pool = [makePlayer(80), makePlayer(83, { special: true }), makePlayer(85)];
    const out = filterCandidates(pool, { commonsOnly: true });
    assert.deepStrictEqual(out.map(p => p.rating), [80, 85]);
});

test('untradeableOnly 只留不可交易', () => {
    const pool = [makePlayer(80, { untradeable: true }), makePlayer(83), makePlayer(85, { untradeable: true })];
    const out = filterCandidates(pool, { untradeableOnly: true });
    assert.deepStrictEqual(out.map(p => p.rating), [80, 85]);
});

test('组合过滤：minRating+commonsOnly+untradeableOnly', () => {
    const pool = [
        makePlayer(75, { untradeable: true }),
        makePlayer(82, { untradeable: true }),
        makePlayer(86, { untradeable: true, special: true }),
        makePlayer(90)
    ];
    const out = filterCandidates(pool, { minRating: 80, commonsOnly: true, untradeableOnly: true });
    assert.deepStrictEqual(out.map(p => p.rating), [82]);
});

test('unitOvr 默认按评分升序', () => {
    const pool = [makePlayer(90), makePlayer(75), makePlayer(83)];
    const out = filterCandidates(pool, {});
    assert.deepStrictEqual(out.map(p => p.rating), [75, 83, 90]);
});

test('unitCoins 按价格升序', () => {
    const pool = [makePlayer(80, { price: 8000 }), makePlayer(83, { price: 500 }), makePlayer(87, { price: 2000 })];
    const out = filterCandidates(pool, { unitCoins: true });
    assert.deepStrictEqual(out.map(p => p.rating), [83, 87, 80]);
});

test('无过滤条件返回全池（排序）', () => {
    const pool = [makePlayer(80), makePlayer(75)];
    assert.strictEqual(filterCandidates(pool, {}).length, 2);
});

test('自定义 helpers 生效（isSpecial 注入）', () => {
    const pool = [{ id: 1, rating: 85, isSpecial: () => true }];
    const out = filterCandidates(pool, { commonsOnly: true }, { isSpecial: (it) => true });
    assert.strictEqual(out.length, 0);
});

// --- filterUnfinishedChallenges ---
test('过滤已完成挑战（status=COMPLETED）', () => {
    const list = [
        makeChallenge(1, "COMPLETED"),
        makeChallenge(2, "ACTIVE"),
        makeChallenge(3, "ACTIVE", () => true)
    ];
    const out = filterUnfinishedChallenges(list);
    assert.deepStrictEqual(out.map(c => c.id), [2]);
});

test('isComplete 抛异常时保留挑战', () => {
    const bad = { id: 9, status: "ACTIVE", isComplete: () => { throw new Error("boom"); } };
    const out = filterUnfinishedChallenges([bad, makeChallenge(2)]);
    assert.strictEqual(out.length, 2);
});

test('空列表返回空', () => {
    assert.strictEqual(filterUnfinishedChallenges([]).length, 0);
});

// --- buildSolveSummary ---
test('统计：成功/跳过', () => {
    const s = buildSolveSummary([
        { solved: true }, { solved: true }, { solved: false }, { solved: false }, { solved: false }
    ]);
    assert.strictEqual(s.solved, 2);
    assert.strictEqual(s.skipped, 3);
});

test('统计：空结果', () => {
    const s = buildSolveSummary([]);
    assert.strictEqual(s.solved + s.skipped, 0);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
