/**
 * AUTO SOLVE — 参数规范化 单元测试（v26.10-jacyi.3）
 *
 * 运行：node fc26_fsu_mod/test_solve_options.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-03]）=====
//PURE: 求解参数规范化（默认值 + 边界钳制）
function normalizeSolveOptions(raw, defaults) {
    const d = defaults || {};
    const o = Object.assign({}, d, raw || {});
    o.count = Math.max(1, Math.min(20, parseInt(o.count, 10) || d.count || 1));
    o.minRating = o.minRating == null ? (d.minRating != null ? d.minRating : null) : Math.max(40, Math.min(99, parseInt(o.minRating, 10) || 40));
    o.maxRating = o.maxRating == null ? (d.maxRating != null ? d.maxRating : null) : Math.max(40, Math.min(99, parseInt(o.maxRating, 10) || 99));
    if (o.minRating != null && o.maxRating != null && o.minRating > o.maxRating) {
        const t = o.minRating; o.minRating = o.maxRating; o.maxRating = t;
    }
    o.minPrice = o.minPrice == null ? null : Math.max(0, parseInt(o.minPrice, 10) || 0);
    o.maxPrice = o.maxPrice == null ? null : Math.max(0, parseInt(o.maxPrice, 10) || 0);
    o.algorithm = o.algorithm === 'fodder' ? 'fodder' : 'legacy';
    o.commonsOnly = !!o.commonsOnly;
    o.untradeableOnly = !!o.untradeableOnly;
    o.storageOnly = !!o.storageOnly;
    return o;
}

const DEFAULTS = { count: 1, algorithm: "legacy", minRating: null, maxRating: null, minPrice: null, maxPrice: null, commonsOnly: false, untradeableOnly: false, storageOnly: false };

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

console.log('\nAUTO SOLVE 参数规范化 单元测试\n' + '='.repeat(40));

// --- count ---
test('count 缺省 → 默认 1', () => {
    assert.strictEqual(normalizeSolveOptions({}, DEFAULTS).count, 1);
});
test('count 0/负值/非法 → 1', () => {
    assert.strictEqual(normalizeSolveOptions({ count: 0 }, DEFAULTS).count, 1);
    assert.strictEqual(normalizeSolveOptions({ count: -5 }, DEFAULTS).count, 1);
    assert.strictEqual(normalizeSolveOptions({ count: "abc" }, DEFAULTS).count, 1);
});
test('count 上限钳制 20', () => {
    assert.strictEqual(normalizeSolveOptions({ count: 999 }, DEFAULTS).count, 20);
});
test('count 字符串数字解析', () => {
    assert.strictEqual(normalizeSolveOptions({ count: "7" }, DEFAULTS).count, 7);
});

// --- rating 范围 ---
test('minRating 低于下限钳制到 40', () => {
    assert.strictEqual(normalizeSolveOptions({ minRating: 10 }, DEFAULTS).minRating, 40);
});
test('maxRating 高于上限钳制到 99', () => {
    assert.strictEqual(normalizeSolveOptions({ maxRating: 120 }, DEFAULTS).maxRating, 99);
});
test('min>max 自动交换', () => {
    const o = normalizeSolveOptions({ minRating: 90, maxRating: 80 }, DEFAULTS);
    assert.strictEqual(o.minRating, 80);
    assert.strictEqual(o.maxRating, 90);
});
test('null 值保持 null（不设限制）', () => {
    const o = normalizeSolveOptions({}, DEFAULTS);
    assert.strictEqual(o.minRating, null);
    assert.strictEqual(o.maxRating, null);
});

// --- price ---
test('价格负数钳制到 0', () => {
    assert.strictEqual(normalizeSolveOptions({ minPrice: -100 }, DEFAULTS).minPrice, 0);
});
test('价格 null 保持 null', () => {
    assert.strictEqual(normalizeSolveOptions({}, DEFAULTS).maxPrice, null);
});

// --- algorithm ---
test('algorithm 非法值回退 legacy', () => {
    assert.strictEqual(normalizeSolveOptions({ algorithm: "hack" }, DEFAULTS).algorithm, "legacy");
});
test('algorithm=fodder 保留', () => {
    assert.strictEqual(normalizeSolveOptions({ algorithm: "fodder" }, DEFAULTS).algorithm, "fodder");
});
test('algorithm 缺省 → legacy（新算法未验证前不默认启用）', () => {
    assert.strictEqual(normalizeSolveOptions({}, DEFAULTS).algorithm, "legacy");
});

// --- 布尔开关 ---
test('布尔开关强制布尔化', () => {
    const o = normalizeSolveOptions({ commonsOnly: 1, untradeableOnly: "yes", storageOnly: 0 }, DEFAULTS);
    assert.strictEqual(o.commonsOnly, true);
    assert.strictEqual(o.untradeableOnly, true);
    assert.strictEqual(o.storageOnly, false);
});

// --- 默认值合并 ---
test('自定义默认值生效', () => {
    const o = normalizeSolveOptions({ count: 5 }, { count: 3, algorithm: "fodder", minRating: 80 });
    assert.strictEqual(o.count, 5);
    assert.strictEqual(o.algorithm, "fodder");
    assert.strictEqual(o.minRating, 80);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
