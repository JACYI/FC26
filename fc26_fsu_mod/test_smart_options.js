/**
 * 智能填充 — 选项模型 单元测试（v26.10-jacyi.8）
 *
 * 测试 normalizeFillOptions（规范化）/ loadFillOptions / saveFillOptions（per-SBC 存取）/ resolveSmartFillEnabled（旧开关兼容）
 * 注意：测试只复制 //PURE: 纯函数
 *
 * 运行：node fc26_fsu_mod/test_smart_options.js
 */

const assert = require('assert');

// ===== 待测纯函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
function normalizeFillOptions(raw, defaults) {
    const d = Object.assign({
        poolSource: "unassigned", untradeableOnly: false, preferDuplicates: true,
        commonsOnly: false, useTemplate: true,
        minRating: null, maxRating: null, minPrice: null, maxPrice: null
    }, defaults || {});
    const r = raw || {};
    const num = (v, fb) => {
        if (v === undefined || v === null || v === "") return fb;
        const n = parseInt(v, 10);
        if (isNaN(n) || n <= 0) return null; // 0/非法 = 不限
        return n;
    };
    const o = {
        poolSource: (r.poolSource === "storage" || (!r.poolSource && d.poolSource === "storage")) ? "storage" : "unassigned",
        untradeableOnly: r.untradeableOnly !== undefined ? !!r.untradeableOnly : !!d.untradeableOnly,
        preferDuplicates: r.preferDuplicates !== undefined ? !!r.preferDuplicates : !!d.preferDuplicates,
        commonsOnly: r.commonsOnly !== undefined ? !!r.commonsOnly : !!d.commonsOnly,
        useTemplate: r.useTemplate !== undefined ? !!r.useTemplate : !!d.useTemplate,
        minRating: num(r.minRating, d.minRating),
        maxRating: num(r.maxRating, d.maxRating),
        minPrice: num(r.minPrice, d.minPrice),
        maxPrice: num(r.maxPrice, d.maxPrice)
    };
    if (o.minRating != null) o.minRating = Math.max(40, Math.min(99, o.minRating));
    if (o.maxRating != null) o.maxRating = Math.max(40, Math.min(99, o.maxRating));
    if (o.minPrice != null) o.minPrice = Math.max(0, o.minPrice);
    if (o.maxPrice != null) o.maxPrice = Math.max(0, o.maxPrice);
    if (o.minRating != null && o.maxRating != null && o.minRating > o.maxRating) { const t = o.minRating; o.minRating = o.maxRating; o.maxRating = t; }
    if (o.minPrice != null && o.maxPrice != null && o.minPrice > o.maxPrice) { const t = o.minPrice; o.minPrice = o.maxPrice; o.maxPrice = t; }
    return o;
}

function loadFillOptions(key, store, defaults) {
    const s = store || {};
    return normalizeFillOptions(key && s[key] ? s[key] : null, defaults);
}

function saveFillOptions(store, key, opts) {
    if (!key) return store || {};
    const s = Object.assign({}, store || {});
    s[key] = normalizeFillOptions(opts, null);
    return s;
}

function resolveSmartFillEnabled(set) {
    const s = set || {};
    if (s.sbc_smartfill === false) return false;
    if (s.sbc_smartfill === true) return true;
    // 存量兼容：任一旧填充开关开启过即视为启用；全无也默认开（新用户开箱即用）
    return true;
}

const DEFAULTS = {
    poolSource: "unassigned", untradeableOnly: false, preferDuplicates: true,
    commonsOnly: false, useTemplate: true,
    minRating: null, maxRating: null, minPrice: null, maxPrice: null
};

let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("  ✓ " + name); }
    catch (e) { failed++; console.error("  ✗ " + name + " — " + e.message); }
}

console.log("🧪 normalizeFillOptions — 选项规范化");
test("空输入 → 默认值全量补齐（preferDuplicates/useTemplate 默认开）", () => {
    const o = normalizeFillOptions(null, DEFAULTS);
    assert.deepStrictEqual(o, DEFAULTS);
});
test("评分越界钳制+交换：minRating 130→99、maxRating 10→40（钳制后 min>max 自动交换为 40/99）", () => {
    const o = normalizeFillOptions({ minRating: 130, maxRating: 10 }, DEFAULTS);
    assert.strictEqual(o.minRating, 40);
    assert.strictEqual(o.maxRating, 99);
});
test("min>max 自动交换（minRating 90/maxRating 70 → 70/90）", () => {
    const o = normalizeFillOptions({ minRating: 90, maxRating: 70 }, DEFAULTS);
    assert.strictEqual(o.minRating, 70);
    assert.strictEqual(o.maxRating, 90);
});
test("价格 min>max 自动交换", () => {
    const o = normalizeFillOptions({ minPrice: 900, maxPrice: 300 }, DEFAULTS);
    assert.strictEqual(o.minPrice, 300);
    assert.strictEqual(o.maxPrice, 900);
});
test("价格 0/空 → null（不限）", () => {
    const o = normalizeFillOptions({ minPrice: 0, maxPrice: "" }, DEFAULTS);
    assert.strictEqual(o.minPrice, null);
    assert.strictEqual(o.maxPrice, null);
});
test("价格 0 不钳制负值", () => {
    const o = normalizeFillOptions({ minPrice: -500 }, DEFAULTS);
    assert.strictEqual(o.minPrice, null); // 负值视为非法 → 不限
});
test("布尔强转（字符串 'false' → true 注意语义：存在即真）", () => {
    const o = normalizeFillOptions({ untradeableOnly: "yes" }, DEFAULTS);
    assert.strictEqual(o.untradeableOnly, true);
});
test("显式 false 覆盖默认 true", () => {
    const o = normalizeFillOptions({ preferDuplicates: false, useTemplate: false }, DEFAULTS);
    assert.strictEqual(o.preferDuplicates, false);
    assert.strictEqual(o.useTemplate, false);
});
test("缺省回退 defaults（raw 未提供字段用全局默认）", () => {
    const o = normalizeFillOptions({ minRating: 85 }, Object.assign({}, DEFAULTS, { maxRating: 90 }));
    assert.strictEqual(o.minRating, 85);
    assert.strictEqual(o.maxRating, 90);
});
test("poolSource 非法值 → unassigned", () => {
    const o = normalizeFillOptions({ poolSource: "weird" }, DEFAULTS);
    assert.strictEqual(o.poolSource, "unassigned");
});
test("poolSource storage 保留", () => {
    const o = normalizeFillOptions({ poolSource: "storage" }, DEFAULTS);
    assert.strictEqual(o.poolSource, "storage");
});
test("默认 poolSource storage（defaults 携带）", () => {
    const o = normalizeFillOptions(null, Object.assign({}, DEFAULTS, { poolSource: "storage" }));
    assert.strictEqual(o.poolSource, "storage");
});
test("评分 0 → null（不限）", () => {
    const o = normalizeFillOptions({ minRating: 0 }, DEFAULTS);
    assert.strictEqual(o.minRating, null);
});
test("脏字段被过滤（未知键不进结果）", () => {
    const o = normalizeFillOptions({ hacker: 1, templateRef: "x" }, DEFAULTS);
    assert.strictEqual(o.hacker, undefined);
    assert.strictEqual(o.templateRef, undefined);
});

console.log("🧪 loadFillOptions / saveFillOptions — per-SBC 存取");
test("缺 key → 回退 defaults", () => {
    const store = { "c1#s1": { minRating: 85 } };
    const o = loadFillOptions("c2#s2", store, DEFAULTS);
    assert.strictEqual(o.minRating, null);
    assert.strictEqual(o.preferDuplicates, true);
});
test("命中 key → 规范化副本", () => {
    const store = { "c1#s1": { minRating: 999, poolSource: "storage" } };
    const o = loadFillOptions("c1#s1", store, DEFAULTS);
    assert.strictEqual(o.minRating, 99);
    assert.strictEqual(o.poolSource, "storage");
});
test("save → load 往返一致", () => {
    let store = {};
    store = saveFillOptions(store, "c9#s9", { minRating: 84, maxRating: 88, preferDuplicates: false, untradeableOnly: true });
    const o = loadFillOptions("c9#s9", store, DEFAULTS);
    assert.strictEqual(o.minRating, 84);
    assert.strictEqual(o.maxRating, 88);
    assert.strictEqual(o.preferDuplicates, false);
    assert.strictEqual(o.untradeableOnly, true);
});
test("store 不可变（原对象不被修改）", () => {
    const before = JSON.stringify({ "c1#s1": { minRating: 85 } });
    const store = JSON.parse(before);
    saveFillOptions(store, "c2#s2", { minRating: 80 });
    assert.strictEqual(JSON.stringify(store), before);
});
test("多 SBC 互不覆盖", () => {
    let store = {};
    store = saveFillOptions(store, "a#1", { minRating: 80 });
    store = saveFillOptions(store, "b#2", { minRating: 90 });
    assert.strictEqual(loadFillOptions("a#1", store, DEFAULTS).minRating, 80);
    assert.strictEqual(loadFillOptions("b#2", store, DEFAULTS).minRating, 90);
});
test("空 key 不写入", () => {
    const store = { "c1#s1": { minRating: 85 } };
    const out = saveFillOptions(store, "", { minRating: 80 });
    assert.deepStrictEqual(out, store);
});
test("store 缺省（null/undefined）→ 正常创建", () => {
    const store = saveFillOptions(null, "c1#s1", { minRating: 80 });
    assert.strictEqual(store["c1#s1"].minRating, 80);
});

console.log("🧪 resolveSmartFillEnabled — 旧开关兼容");
test("sbc_smartfill 显式 true → true", () => {
    assert.strictEqual(resolveSmartFillEnabled({ sbc_smartfill: true }), true);
});
test("sbc_smartfill 显式 false → false（用户关闭）", () => {
    assert.strictEqual(resolveSmartFillEnabled({ sbc_smartfill: false }), false);
    assert.strictEqual(resolveSmartFillEnabled({ sbc_smartfill: false, sbc_autofill: true }), false);
});
test("未定义 + 任一旧键 true → true（存量兼容）", () => {
    assert.strictEqual(resolveSmartFillEnabled({ sbc_dupfill: true }), true);
    assert.strictEqual(resolveSmartFillEnabled({ sbc_squadcmpl: true, sbc_autofill: false }), true);
    assert.strictEqual(resolveSmartFillEnabled({ sbc_template: true }), true);
});
test("未定义 + 全部旧键 false → true（默认开）", () => {
    assert.strictEqual(resolveSmartFillEnabled({ sbc_autofill: false, sbc_dupfill: false, sbc_squadcmpl: false, sbc_template: false }), true);
});
test("空对象/空输入 → true", () => {
    assert.strictEqual(resolveSmartFillEnabled({}), true);
    assert.strictEqual(resolveSmartFillEnabled(null), true);
    assert.strictEqual(resolveSmartFillEnabled(undefined), true);
});

console.log("");
console.log(`✅ test_smart_options.js — ${passed} 通过, ${failed} 失败`);
process.exit(failed ? 1 : 0);
