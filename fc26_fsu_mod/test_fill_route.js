/**
 * 通用填充引擎 — 算法路由 单元测试（v26.10-jacyi.7 Step1）
 *
 * 运行：node fc26_fsu_mod/test_fill_route.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
//PURE: 需求 flags → 算法链（全局算法在前，槽填充在后，校验兜底恒在末尾）
function routeAlgorithm(flags) {
    const chain = [];
    if (flags.chem) chain.push("chemFirst");
    if (flags.rating) chain.push("ratingCombo");
    if (flags.extended) chain.push("reqAware");
    if (flags.basic || (!flags.extended && !flags.chem && !flags.rating)) chain.push("quickGreedy");
    chain.push("verifyFallback");
    return chain;
}

//PURE: 算法链构建（forced: "legacy"|"fodder" → 旧行为零变化；"auto"/null → 自动路由）
function buildChain(flags, forced) {
    if (forced === "legacy" || forced === "fodder") {
        return ["quickGreedy", "verifyFallback"];
    }
    return routeAlgorithm(flags);
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

console.log('\n通用填充引擎算法路由 单元测试\n' + '='.repeat(40));

// --- routeAlgorithm 矩阵 ---
test('仅基础需求（min ovr）→ [quickGreedy, verifyFallback]', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ basic: true })), ["quickGreedy", "verifyFallback"]);
});

test('无任何需求 → [quickGreedy, verifyFallback]', () => {
    assert.deepStrictEqual(routeAlgorithm(F({})), ["quickGreedy", "verifyFallback"]);
});

test('有化学 → chemFirst 在链首（chemFirst 自身填槽，无需 quickGreedy）', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ chem: true })), ["chemFirst", "verifyFallback"]);
});

test('有评分组合需求 → ratingCombo 在链首（自身填槽）', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ rating: true })), ["ratingCombo", "verifyFallback"]);
});

test('扩展需求（俱乐部）→ reqAware 加入', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ extended: true })), ["reqAware", "verifyFallback"]);
});

test('chem + club + rating → [chemFirst, ratingCombo, reqAware, verifyFallback]', () => {
    assert.deepStrictEqual(
        routeAlgorithm(F({ chem: true, rating: true, extended: true })),
        ["chemFirst", "ratingCombo", "reqAware", "verifyFallback"]
    );
});

test('chem + basic → [chemFirst, quickGreedy, verifyFallback]', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ chem: true, basic: true })), ["chemFirst", "quickGreedy", "verifyFallback"]);
});

test('rating + extended → [ratingCombo, reqAware, verifyFallback]', () => {
    assert.deepStrictEqual(routeAlgorithm(F({ rating: true, extended: true })), ["ratingCombo", "reqAware", "verifyFallback"]);
});

test('verifyFallback 恒在末尾（全 flag）', () => {
    const chain = routeAlgorithm(F({ basic: true, extended: true, chem: true, rating: true }));
    assert.strictEqual(chain[chain.length - 1], "verifyFallback");
    assert.strictEqual(new Set(chain).size, chain.length, "链无重复");
});

test('exact/pos flag 不影响链形（归 extended）', () => {
    const a = routeAlgorithm(F({ extended: true, exact: true, pos: true }));
    const b = routeAlgorithm(F({ extended: true }));
    assert.deepStrictEqual(a, b);
});

// --- buildChain ---
test('forced=legacy → 旧行为链（零变化）', () => {
    assert.deepStrictEqual(buildChain(F({ chem: true, rating: true, extended: true }), "legacy"), ["quickGreedy", "verifyFallback"]);
});

test('forced=fodder → 同 legacy 链', () => {
    assert.deepStrictEqual(buildChain(F({ extended: true }), "fodder"), ["quickGreedy", "verifyFallback"]);
});

test('forced=auto → 自动路由', () => {
    assert.deepStrictEqual(buildChain(F({ chem: true }), "auto"), ["chemFirst", "verifyFallback"]);
});

test('forced=null/undefined → 自动路由', () => {
    assert.deepStrictEqual(buildChain(F({ extended: true }), null), ["reqAware", "verifyFallback"]);
    assert.deepStrictEqual(buildChain(F({}), undefined), ["quickGreedy", "verifyFallback"]);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
