/**
 * 提交评分缓存 单元测试
 *
 * 测试目标：
 * 1. 缓存写入格式 {v, ts}
 * 2. 读取兼容旧格式（纯字符串）
 * 3. LRU淘汰：超过30条删最旧10条
 * 4. 同一SBC重复提交覆盖旧值，不新增
 * 5. 自定义key（setId + challengeId）隔离
 *
 * 运行：node fc26_fsu_mod/test_submit_cache.js
 */

const assert = require('assert');

// ===== 模拟 GM Storage =====
let _fakeStorage = {};

function GM_getValue(key, def) {
    const v = _fakeStorage[key];
    return v !== undefined ? JSON.parse(v) : def;
}

function GM_setValue(key, val) {
    _fakeStorage[key] = JSON.stringify(val);
}

function resetStorage() {
    _fakeStorage = {};
}

// ===== 待测函数：写入缓存（带LRU淘汰）=====
function saveLastRatings(setId, challengeId, ratingsStr) {
    const key = `${setId}#${challengeId}`;
    let cache = GM_getValue("SBCLastRatings", {});
    cache[key] = { v: ratingsStr, ts: Date.now() };
    const keys = Object.keys(cache);
    if (keys.length > 30) {
        keys.sort((a, b) => (cache[a].ts || 0) - (cache[b].ts || 0));
        keys.slice(0, 10).forEach(k => delete cache[k]);
    }
    GM_setValue("SBCLastRatings", cache);
}

// ===== 待测函数：读取缓存 =====
function loadLastRatings(setId, challengeId) {
    try {
        const cache = GM_getValue("SBCLastRatings", {});
        const entry = cache[`${setId}#${challengeId}`];
        if (entry) return entry.v || entry; // 兼容旧格式
    } catch(e) {}
    return null;
}

// ===== 测试 =====
let passed = 0, failed = 0;

function test(name, fn) {
    try {
        resetStorage();
        fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}\n      ${e.message}`);
    }
}

console.log('\n提交评分缓存 单元测试\n' + '='.repeat(40));

// --- 1. 基本写入读取 ---
test('写入并读取缓存', () => {
    saveLastRatings('set1', 'ch1', '91,89,88,87,86,85,84,83,82,81,80');
    const val = loadLastRatings('set1', 'ch1');
    assert.strictEqual(val, '91,89,88,87,86,85,84,83,82,81,80');
});

// --- 2. key隔离 ---
test('不同SBC的key隔离', () => {
    saveLastRatings('setA', 'ch1', '83,82,82,81,81,80,80,79,79,78,78');
    saveLastRatings('setB', 'ch2', '75,75,74,74,73,73,72,72,71,71,70');
    assert.strictEqual(loadLastRatings('setA', 'ch1'), '83,82,82,81,81,80,80,79,79,78,78');
    assert.strictEqual(loadLastRatings('setB', 'ch2'), '75,75,74,74,73,73,72,72,71,71,70');
    assert.strictEqual(loadLastRatings('setA', 'nonexist'), null);
});

// --- 3. 覆盖旧值 ---
test('同一SBC重复提交覆盖', () => {
    saveLastRatings('s1', 'c1', '88,87,86,85,84,83,82,81,80,79,78');
    saveLastRatings('s1', 'c1', '91,90,89,88,87,86,85,84,83,82,81');
    const cache = GM_getValue("SBCLastRatings", {});
    assert.strictEqual(Object.keys(cache).length, 1);
    assert.strictEqual(loadLastRatings('s1', 'c1'), '91,90,89,88,87,86,85,84,83,82,81');
});

// --- 4. LRU淘汰 ---
test('超过30条删最旧10条', () => {
    for (let i = 0; i < 31; i++) {
        saveLastRatings(`set${i}`, 'ch', `85,85,84,84,83,83,82,82,81,81,80`);
    }
    const cache = GM_getValue("SBCLastRatings", {});
    assert.ok(Object.keys(cache).length <= 30, `应有≤30条，实际${Object.keys(cache).length}条`);
    assert.strictEqual(loadLastRatings('set0', 'ch'), null, 'set0应该被淘汰');
    assert.strictEqual(loadLastRatings('set9', 'ch'), null, 'set9应该被淘汰');
    assert.ok(loadLastRatings('set10', 'ch') !== null, 'set10应该保留');
    assert.ok(loadLastRatings('set30', 'ch') !== null, 'set30应该保留');
});

// --- 5. 刚好30条不淘汰 ---
test('30条不触发淘汰', () => {
    for (let i = 0; i < 30; i++) {
        saveLastRatings(`s${i}`, 'ch', '80,80,80,80,80,80,80,80,80,80,80');
    }
    assert.strictEqual(Object.keys(GM_getValue("SBCLastRatings", {})).length, 30);
});

// --- 6. 兼容旧格式 ---
test('读取兼容旧格式', () => {
    GM_setValue("SBCLastRatings", { "old#key": "83,82,82,81,81,80,80,79,79,78,78" });
    assert.strictEqual(loadLastRatings('old', 'key'), '83,82,82,81,81,80,80,79,79,78,78');
});

// --- 7. 空缓存 ---
test('空缓存返回null', () => {
    resetStorage();
    assert.strictEqual(loadLastRatings('any', 'any'), null);
});

// --- 8. 缓存损坏容错 ---
test('损坏的JSON返回null', () => {
    _fakeStorage['SBCLastRatings'] = '{{{invalid json';
    assert.strictEqual(loadLastRatings('any', 'any'), null);
});

// --- 9. 大量并发SBC场景 ---
test('50条 → 保留30条', () => {
    for (let i = 0; i < 50; i++) {
        saveLastRatings(`mass${i}`, 'ch', '81,81,80,80,79,79,78,78,77,77,76');
    }
    const cache = GM_getValue("SBCLastRatings", {});
    assert.strictEqual(Object.keys(cache).length, 30);
});

// --- 10. 模拟真实场景 ---
test('真实场景：两个不同的升级SBC', () => {
    saveLastRatings('set_premium_mixed', 'ch_mixed', '83,83,82,82,81,81,80,80,79,79,78');
    saveLastRatings('set_daily_gold', 'ch_gold', '84,83,82,81,80,79,78,77,76,75,75');
    assert.strictEqual(loadLastRatings('set_premium_mixed', 'ch_mixed'), '83,83,82,82,81,81,80,80,79,79,78');
    assert.strictEqual(loadLastRatings('set_daily_gold', 'ch_gold'), '84,83,82,81,80,79,78,77,76,75,75');
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
