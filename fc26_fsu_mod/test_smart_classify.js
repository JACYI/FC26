/**
 * 智能填充 — 条件分流/需求简化 单元测试（v26.10-jacyi.8）
 *
 * 测试 classifySbcMode（basic→本地算法 / complex→Futbin模板优先）与 simplifyReqs（EA 需求对象简化）
 * 注意：测试只复制 //PURE: 纯函数；simplifyReqs 的 console.warn 在 Node 下无副作用
 *
 * 运行：node fc26_fsu_mod/test_smart_classify.js
 */

const assert = require('assert');

// ===== 待测纯函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
function simplifyReqs(ers) {
    const reqs = [];
    try {
        for (const er of (ers || [])) {
            reqs.push({
                key: er.getFirstKey ? er.getFirstKey() : er.key,
                value: er.getValue ? er.getValue() : er.value,
                count: er.getCount ? er.getCount() : 1
            });
        }
    } catch (e) { console.warn("[C-05] 需求解析异常", e); }
    return reqs;
}

function classifySbcMode(reqs) {
    const BASIC = new Set([
        "PLAYER_QUALITY", "PLAYER_LEVEL", "PLAYER_RARITY", "PLAYER_RARITY_GROUP", "PLAYER_MIN_OVR",
        "TEAM_RATING"
    ]);
    if (!reqs || !reqs.length) return "complex"; // 空需求保守走模板优先
    return reqs.every((r) => BASIC.has(r.key)) ? "basic" : "complex";
}

// ===== 测试辅助：mock EA 需求对象 =====
const mkReq = (key, value, count) => ({
    getFirstKey: () => key,
    getValue: () => value,
    getCount: () => count
});

let passed = 0, failed = 0;
function test(name, fn) {
    try { fn(); passed++; console.log("  ✓ " + name); }
    catch (e) { failed++; console.error("  ✗ " + name + " — " + e.message); }
}

console.log("🧪 classifySbcMode — 条件分流判定");
test("纯基础混合（品质+TOTW稀有度+最低评分）→ basic", () => {
    const reqs = [
        { key: "PLAYER_QUALITY", value: 2, count: 11 },
        { key: "PLAYER_RARITY", value: 1, count: 1 },
        { key: "PLAYER_MIN_OVR", value: 84, count: 11 }
    ];
    assert.strictEqual(classifySbcMode(reqs), "basic");
});
test("基础+稀有度组混合 → basic", () => {
    const reqs = [
        { key: "PLAYER_LEVEL", value: 1, count: 11 },
        { key: "PLAYER_RARITY_GROUP", value: 4, count: 4 }
    ];
    assert.strictEqual(classifySbcMode(reqs), "basic");
});
test("空数组 → complex（保守走模板优先）", () => {
    assert.strictEqual(classifySbcMode([]), "complex");
    assert.strictEqual(classifySbcMode(null), "complex");
    assert.strictEqual(classifySbcMode(undefined), "complex");
});
test("CLUB_ID 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "CLUB_ID", value: 1, count: 4 }]), "complex");
});
test("LEAGUE_ID 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "LEAGUE_ID", value: 1, count: 4 }]), "complex");
});
test("NATION_ID 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "NATION_ID", value: 1, count: 5 }]), "complex");
});
test("PLAYER_EXACT_OVR 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "PLAYER_EXACT_OVR", value: 83, count: 2 }]), "complex");
});
test("PLAYER_POSITION 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "PLAYER_POSITION", value: "GK", count: 1 }]), "complex");
});
test("TEAM_RATING（阵容总评/均分）单独 → basic（本地 ratingCombo 可解）", () => {
    assert.strictEqual(classifySbcMode([{ key: "TEAM_RATING", value: 84, count: 1 }]), "basic");
});
test("用户场景：均分84 + TOTW至少1名 + 11人 → basic（本地快速填充）", () => {
    const reqs = [
        { key: "TEAM_RATING", value: 84, count: 1 },
        { key: "PLAYER_RARITY", value: 1, count: 1 },
        { key: "PLAYER_MIN_OVR", value: 80, count: 11 }
    ];
    assert.strictEqual(classifySbcMode(reqs), "basic");
});
test("用户场景：均分84 + TOTW + 最低评分 → basic（无特殊条件）", () => {
    const reqs = [
        { key: "TEAM_RATING", value: 84, count: 1 },
        { key: "PLAYER_RARITY", value: 1, count: 1 },
        { key: "PLAYER_MIN_OVR", value: 82, count: 11 },
        { key: "PLAYER_QUALITY", value: 2, count: 11 }
    ];
    assert.strictEqual(classifySbcMode(reqs), "basic");
});
test("CHEMISTRY_POINTS 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "CHEMISTRY_POINTS", value: 25, count: 1 }]), "complex");
});
test("ALL_PLAYERS_CHEMISTRY_POINTS 单独 → complex", () => {
    assert.strictEqual(classifySbcMode([{ key: "ALL_PLAYERS_CHEMISTRY_POINTS", value: 3, count: 1 }]), "complex");
});
test("未知键 → complex（保守）", () => {
    assert.strictEqual(classifySbcMode([{ key: "MYSTERY_REQ", value: 1, count: 1 }]), "complex");
});
test("基础+特殊混合 → complex", () => {
    const reqs = [
        { key: "PLAYER_QUALITY", value: 2, count: 11 },
        { key: "LEAGUE_ID", value: 13, count: 4 }
    ];
    assert.strictEqual(classifySbcMode(reqs), "complex");
});
test("空对象需求项（无 key）→ complex", () => {
    assert.strictEqual(classifySbcMode([{}]), "complex");
});

console.log("🧪 simplifyReqs — EA 需求对象简化");
test("mock EA 对象 → 正确三元组", () => {
    const ers = [mkReq("PLAYER_QUALITY", 2, 11), mkReq("TEAM_RATING", 84, 1)];
    const reqs = simplifyReqs(ers);
    assert.deepStrictEqual(reqs, [
        { key: "PLAYER_QUALITY", value: 2, count: 11 },
        { key: "TEAM_RATING", value: 84, count: 1 }
    ]);
});
test("纯对象（无 get 方法）→ 透传 key/value，count 默认 1", () => {
    const reqs = simplifyReqs([{ key: "PLAYER_MIN_OVR", value: 83 }]);
    assert.deepStrictEqual(reqs, [{ key: "PLAYER_MIN_OVR", value: 83, count: 1 }]);
});
test("空数组/空输入 → []", () => {
    assert.deepStrictEqual(simplifyReqs([]), []);
    assert.deepStrictEqual(simplifyReqs(null), []);
    assert.deepStrictEqual(simplifyReqs(undefined), []);
});
test("异常对象（getFirstKey 抛错）→ 不抛出，返回已收集部分", () => {
    const bad = { getFirstKey: () => { throw new Error("boom"); } };
    const reqs = simplifyReqs([mkReq("PLAYER_QUALITY", 2, 11), bad]);
    assert.strictEqual(reqs.length, 1);
    assert.strictEqual(reqs[0].key, "PLAYER_QUALITY");
});
test("simplifyReqs 产物可直接喂 classifySbcMode（链路）", () => {
    const ers = [mkReq("PLAYER_QUALITY", 2, 11), mkReq("PLAYER_RARITY", 1, 1)];
    assert.strictEqual(classifySbcMode(simplifyReqs(ers)), "basic");
    const ers2 = [mkReq("PLAYER_QUALITY", 2, 11), mkReq("CHEMISTRY_POINTS", 25, 1)];
    assert.strictEqual(classifySbcMode(simplifyReqs(ers2)), "complex");
});

console.log("");
console.log(`✅ test_smart_classify.js — ${passed} 通过, ${failed} 失败`);
process.exit(failed ? 1 : 0);
