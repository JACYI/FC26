/**
 * 通用填充引擎 — 失败分类 + 化学打分 单元测试（v26.10-jacyi.7 Step2）
 *
 * 运行：node fc26_fsu_mod/test_fill_chain.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
//PURE: 尝试记录 + 池规模 → 失败原因键（优先级 pool→chem→rating→req→noanswer）
// 判定条件用 status !== "ok"（partial 也视为该约束未被满足）
function classifyFailure(attempts, flags, poolSize, slotsNeeded) {
    if (poolSize < slotsNeeded) return "fill.error.pool";
    if (flags.chem && attempts.some((a) => a.name === "chemFirst" && a.status !== "ok")) return "fill.error.chem";
    if (flags.rating && attempts.some((a) => a.name === "ratingCombo" && a.status !== "ok")) return "fill.error.rating";
    if (flags.extended && attempts.some((a) => a.name === "reqAware" && a.status !== "ok")) return "fill.error.req";
    return "fill.error.noanswer";
}

//PURE: 候选短名单截取（评分升序后取前 n）
function capShortlist(list, n) {
    return list.slice(0, Math.max(0, n));
}

//PURE: 化学打分比较器（squadChem desc → playerChem desc → rating asc，对齐 getTemplate 化学择优）
function scoreCandidate(squadChem, playerChem, rating) {
    return { squadChem: squadChem, playerChem: playerChem, rating: rating };
}
function compareScore(a, b) {
    if (a.squadChem !== b.squadChem) return b.squadChem - a.squadChem;
    if (a.playerChem !== b.playerChem) return b.playerChem - a.playerChem;
    return (a.rating || 0) - (b.rating || 0);
}

const F = (o) => Object.assign({ basic: false, extended: false, chem: false, rating: false, exact: false, pos: false }, o);

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

console.log('\n填充引擎失败分类与打分 单元测试\n' + '='.repeat(40));

// --- classifyFailure 优先级 ---
test('池不足 → pool（最高优先级）', () => {
    assert.strictEqual(classifyFailure([{ name: "reqAware", status: "failed" }], F({ extended: true }), 5, 11), "fill.error.pool");
});

test('化学无解 → chem', () => {
    const attempts = [{ name: "chemFirst", status: "failed", reason: "chem-impossible" }, { name: "quickGreedy", status: "partial" }];
    assert.strictEqual(classifyFailure(attempts, F({ chem: true }), 100, 11), "fill.error.chem");
});

test('chemFirst partial（约束未满足）→ chem 分类', () => {
    const attempts = [{ name: "chemFirst", status: "partial" }, { name: "quickGreedy", status: "partial" }];
    assert.strictEqual(classifyFailure(attempts, F({ chem: true }), 100, 11), "fill.error.chem");
});

test('评分组合无解 → rating', () => {
    const attempts = [{ name: "ratingCombo", status: "failed", reason: "rating-insufficient" }];
    assert.strictEqual(classifyFailure(attempts, F({ rating: true }), 100, 11), "fill.error.rating");
});

test('扩展需求无解 → req', () => {
    const attempts = [{ name: "reqAware", status: "failed", reason: "no-candidates" }];
    assert.strictEqual(classifyFailure(attempts, F({ extended: true }), 100, 11), "fill.error.req");
});

test('全部失败且无特征 → noanswer', () => {
    const attempts = [{ name: "quickGreedy", status: "failed" }, { name: "verifyFallback", status: "failed", reason: "no-solution" }];
    assert.strictEqual(classifyFailure(attempts, F({}), 100, 11), "fill.error.noanswer");
});

test('优先级：pool 高于 chem（池不足时即使化学失败也报 pool）', () => {
    const attempts = [{ name: "chemFirst", status: "failed" }];
    assert.strictEqual(classifyFailure(attempts, F({ chem: true }), 3, 11), "fill.error.pool");
});

// --- capShortlist ---
test('cap 截取前 n 个', () => {
    const list = [1, 2, 3, 4, 5];
    assert.deepStrictEqual(capShortlist(list, 3), [1, 2, 3]);
});

test('cap 大于长度不截', () => {
    assert.deepStrictEqual(capShortlist([1, 2], 10), [1, 2]);
});

test('cap 0/负 → 空', () => {
    assert.deepStrictEqual(capShortlist([1, 2], 0), []);
    assert.deepStrictEqual(capShortlist([1, 2], -1), []);
});

// --- scoreCandidate / compareScore ---
test('打分：squadChem 高的优先', () => {
    const a = scoreCandidate(30, 3, 80), b = scoreCandidate(25, 3, 85);
    assert.ok(compareScore(a, b) < 0, 'a 应排前');
});

test('打分：squadChem 相同比 playerChem', () => {
    const a = scoreCandidate(30, 3, 80), b = scoreCandidate(30, 2, 85);
    assert.ok(compareScore(a, b) < 0);
});

test('打分：两者相同比评分（低分优先）', () => {
    const a = scoreCandidate(30, 3, 75), b = scoreCandidate(30, 3, 88);
    assert.ok(compareScore(a, b) < 0);
});

test('排序稳定性：整体按三键排序（squadChem 优先于 playerChem/rating）', () => {
    const list = [
        scoreCandidate(20, 2, 85),
        scoreCandidate(30, 3, 80),
        scoreCandidate(30, 3, 75),
        scoreCandidate(30, 1, 90)
    ];
    const sorted = list.slice().sort(compareScore);
    // (30,3,75) < (30,3,80) < (30,1,90) < (20,2,85)：squadChem=30 全部排在 squadChem=20 前
    assert.deepStrictEqual(sorted.map(s => s.rating), [75, 80, 90, 85]);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
