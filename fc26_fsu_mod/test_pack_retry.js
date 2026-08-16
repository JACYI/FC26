/**
 * 批量开包引擎 — 重试退避 + 致命错误判定 单元测试（v26.10-jacyi.1）
 *
 * 运行：node fc26_fsu_mod/test_pack_retry.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-01]）=====
//PURE: 重试退避：指数增长，上限 30s
function nextRetryDelay(attempt, baseMs) {
    return Math.min(baseMs * Math.pow(2, attempt), 30000);
}

//PURE: 致命错误码（会话失效等，不重试；兼容字符串/数字错误码）
function isFatalError(code, fatalCodes) {
    return (fatalCodes || [401, 403]).some(c => String(c) === String(code));
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

console.log('\n开包重试退避 单元测试\n' + '='.repeat(40));

// --- nextRetryDelay ---
test('退避序列：1s/2s/4s/8s（基数1000）', () => {
    assert.strictEqual(nextRetryDelay(0, 1000), 1000);
    assert.strictEqual(nextRetryDelay(1, 1000), 2000);
    assert.strictEqual(nextRetryDelay(2, 1000), 4000);
    assert.strictEqual(nextRetryDelay(3, 1000), 8000);
});

test('退避封顶：30s 上限（第5次起截断）', () => {
    assert.strictEqual(nextRetryDelay(5, 1000), 30000);
    assert.strictEqual(nextRetryDelay(10, 1000), 30000);
    assert.strictEqual(nextRetryDelay(100, 1000), 30000);
});

test('退避基数 5000（限流长退避）', () => {
    assert.strictEqual(nextRetryDelay(0, 5000), 5000);
    assert.strictEqual(nextRetryDelay(1, 5000), 10000);
    assert.strictEqual(nextRetryDelay(2, 5000), 20000);
    assert.strictEqual(nextRetryDelay(3, 5000), 30000);
});

// --- isFatalError ---
test('401/403 判定为致命（默认集合）', () => {
    assert.strictEqual(isFatalError(401), true);
    assert.strictEqual(isFatalError(403), true);
});

test('429/500/网络错误非致命（可重试）', () => {
    assert.strictEqual(isFatalError(429), false);
    assert.strictEqual(isFatalError(500), false);
    assert.strictEqual(isFatalError(undefined), false);
    assert.strictEqual(isFatalError(null), false);
});

test('自定义致命集合生效', () => {
    assert.strictEqual(isFatalError(500, [500, 502]), true);
    assert.strictEqual(isFatalError(401, [500, 502]), false);
});

test('字符串错误码兼容', () => {
    assert.strictEqual(isFatalError("401"), true);
    assert.strictEqual(isFatalError("429"), false);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
