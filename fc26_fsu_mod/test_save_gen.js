/**
 * saveSquad 代际计数器 单元测试（_fsuSaveGen）
 *
 * 测试目标：
 * 1. 首次调用 _fsuSaveGen 从 1 开始
 * 2. 多次调用逐次递增（1→2→3）
 * 3. 同一 challenge 快速连续调用，只有最新代际的回调通过守卫
 * 4. 最早代际的回调被守卫拦截
 * 5. 不同 challenge 对象计数器隔离
 * 6. 新旧对象交替：新对象计数器重置为 1
 *
 * 模拟 saveSquad 的核心逻辑：
 *   c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
 *   const thisGen = c._fsuSaveGen;
 *   await asyncTask(); // 模拟 saveChallenge + loadChallengeData
 *   if (c._fsuSaveGen !== thisGen) return; // 守卫
 *   apply(); // 应用阵容
 *
 * 运行：node fc26_fsu_mod/test_save_gen.js
 */

const assert = require('assert');

// ===== 模拟异步任务：延迟后执行回调 =====
// 模拟 services.SBC.saveChallenge().observe() + loadChallengeData().observe()
function simulateAsyncTask(c, thisGen, ms, onComplete) {
    return new Promise(resolve => {
        setTimeout(() => {
            // 模拟 loadChallengeData 回调
            if (c._fsuSaveGen !== thisGen) {
                resolve('SKIPPED');
                return;
            }
            onComplete();
            resolve('APPLIED');
        }, ms);
    });
}

// ===== 模拟 saveSquad 的核心逻辑 =====
async function mockSaveSquad(c, delayMs, applyFn) {
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
    const thisGen = c._fsuSaveGen;
    // 模拟 await saveChallenge + loadChallengeData
    return await simulateAsyncTask(c, thisGen, delayMs, applyFn);
}

// ===== 测试 =====
let passed = 0, failed = 0;
const asyncTests = [];

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

function testAsync(name, fn) {
    asyncTests.push(
        (async () => {
            try {
                await fn();
                passed++;
                console.log(`  ✓ ${name}`);
            } catch (e) {
                failed++;
                console.log(`  ✗ ${name}\n      ${e.message}`);
            }
        })()
    );
}

function printResults() {
    console.log('\n' + '='.repeat(40));
    console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
}

console.log('\nsaveSquad 代际计数器 单元测试\n' + '='.repeat(40));

// --- 1. 基本递增 ---
test('首次调用初始化为 1', () => {
    const c = {};
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
    assert.strictEqual(c._fsuSaveGen, 1);
});

test('第二次调用递增为 2', () => {
    const c = {};
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
    assert.strictEqual(c._fsuSaveGen, 2);
});

test('连续三次调用值正确', () => {
    const c = {};
    for (let i = 1; i <= 3; i++) {
        c._fsuSaveGen = (c._fsuSaveGen || 0) + 1;
        assert.strictEqual(c._fsuSaveGen, i);
    }
});

// --- 2. 守卫拦截 ---
testAsync('单次调用正常通过守卫', async () => {
    const c = {};
    let applied = false;
    const result = await mockSaveSquad(c, 10, () => { applied = true; });
    assert.strictEqual(result, 'APPLIED');
    assert.strictEqual(applied, true);
});

testAsync('同一对象快速再调用，旧回调被跳过', async () => {
    const c = {};
    let applyCount = 0;

    // 发起两拨调用，延迟不同：第一次慢(50ms)，第二次快(5ms)
    const p1 = mockSaveSquad(c, 50, () => { applyCount++; }); // gen=1, 50ms后回来
    // 在 p1 完成前发起第二次
    const p2 = mockSaveSquad(c, 5, () => { applyCount++; });  // gen=2, 5ms后先回来

    const r1 = await p1; // 50ms后回来，此时 _fsuSaveGen=2 !== thisGen(1)
    const r2 = await p2; // 5ms后回来，此时 _fsuSaveGen=2 === thisGen(2)

    assert.strictEqual(r1, 'SKIPPED');
    assert.strictEqual(r2, 'APPLIED');
    assert.strictEqual(applyCount, 1, '只有第二次填充被应用');
});

testAsync('三次快速调用，仅最后一次通过守卫', async () => {
    const c = {};
    let applyCount = 0;

    const p1 = mockSaveSquad(c, 50, () => { applyCount++; }); // gen=1
    const p2 = mockSaveSquad(c, 30, () => { applyCount++; }); // gen=2
    const p3 = mockSaveSquad(c, 10, () => { applyCount++; }); // gen=3

    const r1 = await p1;
    const r2 = await p2;
    const r3 = await p3;

    assert.strictEqual(r1, 'SKIPPED');
    assert.strictEqual(r2, 'SKIPPED');
    assert.strictEqual(r3, 'APPLIED');
    assert.strictEqual(applyCount, 1, '只有第三次填充被应用');
});

// --- 3. 按序完成也正确 ---
testAsync('依次调用（前一个完成后再调下一个），全部通过', async () => {
    const c = {};
    let applyCount = 0;

    // 第一次完成后才调第二次
    const r1 = await mockSaveSquad(c, 5, () => { applyCount++; });
    const r2 = await mockSaveSquad(c, 5, () => { applyCount++; });
    const r3 = await mockSaveSquad(c, 5, () => { applyCount++; });

    assert.strictEqual(r1, 'APPLIED');
    assert.strictEqual(r2, 'APPLIED');
    assert.strictEqual(r3, 'APPLIED');
    assert.strictEqual(applyCount, 3);
});

// --- 4. 对象隔离 ---
testAsync('不同 challenge 对象计数器互不干扰', async () => {
    const c1 = {}, c2 = {};
    let applyC1 = 0, applyC2 = 0;

    // 两个对象交替调用
    const p1 = mockSaveSquad(c1, 30, () => { applyC1++; });
    const p2 = mockSaveSquad(c2, 10, () => { applyC2++; });
    const p3 = mockSaveSquad(c1, 20, () => { applyC1++; });

    const r1 = await p1; // c1 gen=1, 30ms, 此时 c1._fsuSaveGen=2 (被p3递增)
    const r2 = await p2; // c2 gen=1, 10ms, 此时 c2._fsuSaveGen=1
    const r3 = await p3; // c1 gen=2, 20ms, 此时 c1._fsuSaveGen=2 === thisGen

    assert.strictEqual(r1, 'SKIPPED', 'c1的gen=1被跳过');
    assert.strictEqual(r2, 'APPLIED', 'c2的gen=1正常通过');
    assert.strictEqual(r3, 'APPLIED', 'c1的gen=2正常通过');
    assert.strictEqual(applyC1, 1);
    assert.strictEqual(applyC2, 1);
});

// --- 5. 新对象计数器归零 ---
testAsync('新 challenge 对象计数器从 1 开始', async () => {
    // 模拟 SBC 提交后挑战被重置为新的 challenge 对象
    const oldC = {};
    oldC._fsuSaveGen = (oldC._fsuSaveGen || 0) + 1; // =1
    oldC._fsuSaveGen = (oldC._fsuSaveGen || 0) + 1; // =2

    const newC = {}; // 全新对象，相当 SBCSetEntity.getChallenge() 返回新的
    assert.strictEqual((newC._fsuSaveGen || 0) + 1, 1);
});

// --- 6. 边界：对象没有 _fsuSaveGen 属性 ---
test('无属性的对象从 0 开始', () => {
    const c = {};
    const gen = (c._fsuSaveGen || 0) + 1;
    assert.strictEqual(gen, 1);
    c._fsuSaveGen = gen;
    assert.strictEqual(c._fsuSaveGen, 1);
});

// --- 7. 验证替换后的 real code 逻辑 ---
test('代际守卫表达式等价验证', () => {
    // 模拟最新调用场景
    const c = {};
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1; // gen=1
    const thisGen1 = c._fsuSaveGen;
    assert.strictEqual(c._fsuSaveGen === thisGen1, true); // 最新，通过

    // 模拟旧回调场景（再次调用后）
    c._fsuSaveGen = (c._fsuSaveGen || 0) + 1; // gen=2
    assert.strictEqual(c._fsuSaveGen === thisGen1, false); // 陈旧，拒绝
});

// ===== 结果（等所有异步测试完成） =====
(async () => {
    await Promise.all(asyncTests);
    printResults();
    process.exit(failed > 0 ? 1 : 0);
})();
