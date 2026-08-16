/**
 * 自定义流程编排 — 数据模型 单元测试（v26.10-jacyi.4）
 *
 * 运行：node fc26_fsu_mod/test_routine_model.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-04]）=====
//PURE: 流程数据规范化（校验 + 补默认，id 由创建方生成）
function normalizeRoutine(raw) {
    const r = raw || {};
    return {
        id: typeof r.id === "string" ? r.id : "",
        name: r.name || "未命名流程",
        enabled: r.enabled !== false,
        daily: !!r.daily,
        expiresDaysHours: r.expiresDaysHours && typeof r.expiresDaysHours === "object" ? {
            d: Math.max(0, parseInt(r.expiresDaysHours.d, 10) || 0),
            h: Math.max(0, parseInt(r.expiresDaysHours.h, 10) || 0)
        } : null,
        createdAt: typeof r.createdAt === "number" ? r.createdAt : null,
        steps: Array.isArray(r.steps) ? r.steps
            .map((s) => ({
                sbcId: s.sbcId || null,
                challengeId: s.challengeId || null,
                sbcName: s.sbcName || "",
                packId: s.packId || null,
                packMode: ["open", "sellDup", "sellAll", "skip"].indexOf(s.packMode) >= 0 ? s.packMode : "open"
            }))
            .filter((s) => s.sbcId) : []
    };
}

//PURE: 流程是否过期（daily 模式 + expiresDaysHours 从 createdAt 起算；0/0 视为未设置，不过期）
function routineIsExpired(r, now) {
    if (!r || !r.daily || !r.expiresDaysHours || !r.createdAt) return false;
    const ms = (r.expiresDaysHours.d || 0) * 86400000 + (r.expiresDaysHours.h || 0) * 3600000;
    if (ms <= 0) return false;
    return now - r.createdAt > ms;
}

//PURE: 规范化整个存储结构（v 版本号 + 过期过滤）
function normalizeRoutineStore(raw, now) {
    if (!raw || typeof raw !== "object" || !Array.isArray(raw.routines)) return { v: 1, routines: [] };
    return {
        v: 1,
        routines: raw.routines.map(normalizeRoutine).filter((r) => !routineIsExpired(r, now))
    };
}

// ===== Mock GM Storage =====
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

// load/save 封装（复制自 C，mock GM）
function routineLoad(now) {
    try {
        return normalizeRoutineStore(JSON.parse(GM_getValue("fsu_routines", "null")), now || Date.now());
    } catch (e) {
        return { v: 1, routines: [] };
    }
}
function routineSave(list) {
    GM_setValue("fsu_routines", JSON.stringify({ v: 1, routines: list.map(normalizeRoutine) }));
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

console.log('\n自定义流程数据模型 单元测试\n' + '='.repeat(40));

// --- normalizeRoutine ---
test('规范化：补默认值（空对象）', () => {
    const r = normalizeRoutine({});
    assert.strictEqual(r.name, "未命名流程");
    assert.strictEqual(r.enabled, true);
    assert.strictEqual(r.daily, false);
    assert.strictEqual(r.expiresDaysHours, null);
    assert.deepStrictEqual(r.steps, []);
});

test('规范化：id 保留字符串', () => {
    assert.strictEqual(normalizeRoutine({ id: "rt-1" }).id, "rt-1");
    assert.strictEqual(normalizeRoutine({ id: 42 }).id, "");
});

test('规范化：enabled=false 保留', () => {
    assert.strictEqual(normalizeRoutine({ enabled: false }).enabled, false);
});

test('规范化：步骤补默认 + 过滤无 sbcId 步骤', () => {
    const r = normalizeRoutine({ steps: [{ sbcId: "s1", challengeId: "c1", packMode: "sellAll" }, { packMode: "skip" }, { sbcId: "s2" }] });
    assert.strictEqual(r.steps.length, 2);
    assert.strictEqual(r.steps[0].packMode, "sellAll");
    assert.strictEqual(r.steps[1].packMode, "open", "缺省 packMode 补 open");
    assert.strictEqual(r.steps[1].sbcName, "");
});

test('规范化：非法 packMode 回退 open', () => {
    const r = normalizeRoutine({ steps: [{ sbcId: "s1", packMode: "hack" }] });
    assert.strictEqual(r.steps[0].packMode, "open");
});

test('规范化：expiresDaysHours 钳制非负', () => {
    const r = normalizeRoutine({ expiresDaysHours: { d: -3, h: 48 } });
    assert.strictEqual(r.expiresDaysHours.d, 0);
    assert.strictEqual(r.expiresDaysHours.h, 48);
});

// --- routineIsExpired ---
test('过期：非 daily 永不过期', () => {
    const r = { daily: false, expiresDaysHours: { d: 0, h: 1 }, createdAt: 1000 };
    assert.strictEqual(routineIsExpired(r, 999999999), false);
});

test('过期：daily + 0/0 → 永不过期', () => {
    const r = { daily: true, expiresDaysHours: { d: 0, h: 0 }, createdAt: 1000 };
    assert.strictEqual(routineIsExpired(r, 999999999), false);
});

test('过期：1 天后过期边界', () => {
    const r = { daily: true, expiresDaysHours: { d: 1, h: 0 }, createdAt: 1000 };
    assert.strictEqual(routineIsExpired(r, 1000 + 86400000), false, "刚好 1 天不过期");
    assert.strictEqual(routineIsExpired(r, 1000 + 86400000 + 1), true, "超过 1 天过期");
});

test('过期：缺 createdAt 永不过期', () => {
    const r = { daily: true, expiresDaysHours: { d: 1, h: 0 }, createdAt: null };
    assert.strictEqual(routineIsExpired(r, 999999999), false);
});

// --- normalizeRoutineStore + load/save ---
test('存储：损坏 JSON 容错 → 空结构', () => {
    _fakeStorage['fsu_routines'] = '{{{bad json';
    const store = routineLoad(1000);
    assert.deepStrictEqual(store, { v: 1, routines: [] });
});

test('存储：空/非法结构 → 空结构', () => {
    assert.deepStrictEqual(routineLoad(1000), { v: 1, routines: [] });
    GM_setValue("fsu_routines", JSON.stringify({ foo: 1 }));
    assert.deepStrictEqual(routineLoad(1000), { v: 1, routines: [] });
});

test('存储：save → load 往返保持步骤顺序', () => {
    resetStorage();
    const list = [{
        id: "rt-1", name: "A", steps: [
            { sbcId: "s1", challengeId: "c1", sbcName: "青铜", packMode: "open" },
            { sbcId: "s2", challengeId: "c2", sbcName: "黄金", packMode: "sellAll" }
        ]
    }];
    routineSave(list);
    const store = routineLoad(1000);
    assert.strictEqual(store.routines.length, 1);
    assert.strictEqual(store.routines[0].steps.length, 2);
    assert.strictEqual(store.routines[0].steps[0].sbcName, "青铜");
    assert.strictEqual(store.routines[0].steps[1].packMode, "sellAll");
});

test('存储：load 时清理过期流程（daily 超时）', () => {
    resetStorage();
    const now = 1000000000000;
    routineSave([
        { id: "r1", name: "过期", daily: true, expiresDaysHours: { d: 1, h: 0 }, createdAt: now - 90000000, steps: [{ sbcId: "s1" }] },
        { id: "r2", name: "不过期", daily: true, expiresDaysHours: { d: 1, h: 0 }, createdAt: now - 1000, steps: [{ sbcId: "s2" }] },
        { id: "r3", name: "非daily", daily: false, createdAt: now - 99999999, steps: [{ sbcId: "s3" }] }
    ]);
    const store = routineLoad(now);
    assert.deepStrictEqual(store.routines.map(r => r.id), ["r2", "r3"]);
});

test('存储：多流程互不干扰', () => {
    resetStorage();
    routineSave([
        { id: "a", name: "A", steps: [{ sbcId: "s1" }] },
        { id: "b", name: "B", steps: [{ sbcId: "s2" }, { sbcId: "s3" }] }
    ]);
    const store = routineLoad(1000);
    assert.strictEqual(store.routines.length, 2);
    assert.strictEqual(store.routines[1].steps.length, 2);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
