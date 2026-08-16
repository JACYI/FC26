/**
 * 通用填充引擎 — 需求解析 单元测试（v26.10-jacyi.7 Step1）
 *
 * 运行：node fc26_fsu_mod/test_fill_parse.js
 * 注意：被测函数从 fsu-mod.c.user.js 的 //PURE: 块复制，修改实现必须同步修改此处
 */

const assert = require('assert');

// ===== 待测函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
//PURE: 同俱乐部跨联赛链接扩展（teamLinks: {teamId: [linkedTeamIds]}，可缺省）
// 返回：单值返回标量，多值返回数组（criteria 数组 = OR 语义）
function expandTeamIds(teamId, teamLinks) {
    const ids = [parseInt(teamId, 10) || teamId];
    if (teamLinks && teamLinks[teamId]) {
        for (const t of teamLinks[teamId]) {
            if (ids.indexOf(t) === -1) ids.push(t);
        }
    }
    return ids.length === 1 ? ids[0] : ids;
}

//PURE: 需求 → {groups, flags, summary}
// reqs: [{key, value, count}]（key 为 SBCEligibilityKey 值；由调用方从 EA 需求对象转换）
// groups: [{t: criteria键值对, c: 数量}] —— 只含可检索需求
// flags: {basic, extended, chem, rating, exact, pos} —— 跨槽全局约束由算法层处理
// summary: 全量清单（含不可检索/未知项，不静默丢弃）
function parseRequirements(reqs, miss) {
    const groups = [];
    const flags = { basic: false, extended: false, chem: false, rating: false, exact: false, pos: false };
    const summary = [];
    const push = (t, c) => {
        const ex = groups.find((g) => {
            const k1 = Object.keys(g.t), k2 = Object.keys(t);
            return k1.length === k2.length && k1.every((k) => k2.indexOf(k) >= 0 && g.t[k] === t[k]);
        });
        if (ex) ex.c += c;
        else groups.push({ t: t, c: c });
    };
    for (const r of (reqs || [])) {
        const key = r.key, v = r.value, c = r.count || 1;
        const rec = { key: key, kind: "other", count: c };
        switch (key) {
            case "PLAYER_QUALITY":
            case "PLAYER_LEVEL":
                push({ rs: Math.max(0, (parseInt(v, 10) || 0) - 1) }, c);
                flags.basic = true; rec.kind = "basic"; break;
            case "PLAYER_RARITY":
                push({ rareflag: parseInt(v, 10) || 0 }, c);
                flags.basic = true; rec.kind = "basic"; break;
            case "PLAYER_RARITY_GROUP":
                // fv===4 用 gs；其余用 groups 直接匹配（实验性）
                if (v === 4) { push({ gs: 4 }, c); }
                else { push({ groups: v }, c); }
                flags.basic = true; rec.kind = "basic"; break;
            case "PLAYER_MIN_OVR":
                push({ GTrating: parseInt(v, 10) || 0 }, c);
                flags.basic = true; rec.kind = "basic"; break;
            case "CLUB_ID":
                push({ teamId: expandTeamIds(v, miss && miss.teamLinks) }, c);
                flags.extended = true; rec.kind = "extended"; break;
            case "LEAGUE_ID":
                push({ leagueId: parseInt(v, 10) || v }, c);
                flags.extended = true; rec.kind = "extended"; break;
            case "NATION_ID":
                push({ nationId: parseInt(v, 10) || v }, c);
                flags.extended = true; rec.kind = "extended"; break;
            case "PLAYER_EXACT_OVR":
                push({ rating: parseInt(v, 10) || 0 }, c);
                flags.extended = true; flags.exact = true; rec.kind = "extended"; break;
            case "PLAYER_POSITION":
                push({ includePos: v }, c);
                flags.extended = true; flags.pos = true; rec.kind = "extended"; break;
            case "TEAM_RATING":
                flags.rating = true; rec.kind = "rating"; break;
            case "CHEMISTRY_POINTS":
            case "ALL_PLAYERS_CHEMISTRY_POINTS":
                flags.chem = true; rec.kind = "chem"; break;
            default:
                rec.kind = "other"; break; // 未知需求透传，不静默丢弃
        }
        summary.push(rec);
    }
    return { groups: groups, flags: flags, summary: summary };
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

console.log('\n通用填充引擎需求解析 单元测试\n' + '='.repeat(40));

// --- 基础需求（B 原有 4 类）---
test('PLAYER_MIN_OVR → GTrating', () => {
    const r = parseRequirements([{ key: "PLAYER_MIN_OVR", value: 83, count: 11 }]);
    assert.deepStrictEqual(r.groups, [{ t: { GTrating: 83 }, c: 11 }]);
    assert.strictEqual(r.flags.basic, true);
    assert.strictEqual(r.flags.extended, false);
});

test('PLAYER_QUALITY → rs = value-1', () => {
    const r = parseRequirements([{ key: "PLAYER_QUALITY", value: 3, count: 5 }]);
    assert.deepStrictEqual(r.groups, [{ t: { rs: 2 }, c: 5 }]);
});

test('PLAYER_RARITY → rareflag', () => {
    const r = parseRequirements([{ key: "PLAYER_RARITY", value: 2, count: 4 }]);
    assert.deepStrictEqual(r.groups, [{ t: { rareflag: 2 }, c: 4 }]);
});

test('PLAYER_RARITY_GROUP fv=4 → gs；fv≠4 → groups', () => {
    const r4 = parseRequirements([{ key: "PLAYER_RARITY_GROUP", value: 4, count: 3 }]);
    assert.deepStrictEqual(r4.groups, [{ t: { gs: 4 }, c: 3 }]);
    const r3 = parseRequirements([{ key: "PLAYER_RARITY_GROUP", value: 3, count: 3 }]);
    assert.deepStrictEqual(r3.groups, [{ t: { groups: 3 }, c: 3 }]);
});

// --- 扩展需求（AUTO SOLVE 2.0 新增）---
test('CLUB_ID → teamId（单值标量）', () => {
    const r = parseRequirements([{ key: "CLUB_ID", value: 101, count: 2 }]);
    assert.deepStrictEqual(r.groups, [{ t: { teamId: 101 }, c: 2 }]);
    assert.strictEqual(r.flags.extended, true);
});

test('CLUB_ID + teamLinks → 多值数组（OR）', () => {
    const r = parseRequirements([{ key: "CLUB_ID", value: 101, count: 2 }], { teamLinks: { 101: [102, 103] } });
    assert.deepStrictEqual(r.groups, [{ t: { teamId: [101, 102, 103] }, c: 2 }]);
});

test('LEAGUE_ID → leagueId', () => {
    const r = parseRequirements([{ key: "LEAGUE_ID", value: 13, count: 6 }]);
    assert.deepStrictEqual(r.groups, [{ t: { leagueId: 13 }, c: 6 }]);
});

test('NATION_ID → nationId', () => {
    const r = parseRequirements([{ key: "NATION_ID", value: 44, count: 5 }]);
    assert.deepStrictEqual(r.groups, [{ t: { nationId: 44 }, c: 5 }]);
});

test('PLAYER_EXACT_OVR → rating + exact flag', () => {
    const r = parseRequirements([{ key: "PLAYER_EXACT_OVR", value: 85, count: 1 }]);
    assert.deepStrictEqual(r.groups, [{ t: { rating: 85 }, c: 1 }]);
    assert.strictEqual(r.flags.exact, true);
});

test('PLAYER_POSITION → includePos + pos flag', () => {
    const r = parseRequirements([{ key: "PLAYER_POSITION", value: "ST", count: 3 }]);
    assert.deepStrictEqual(r.groups, [{ t: { includePos: "ST" }, c: 3 }]);
    assert.strictEqual(r.flags.pos, true);
});

// --- 全局约束（不产生 criteria）---
test('TEAM_RATING → 仅 rating flag，无 groups', () => {
    const r = parseRequirements([{ key: "TEAM_RATING", value: 80, count: 1 }]);
    assert.strictEqual(r.flags.rating, true);
    assert.strictEqual(r.groups.length, 0);
});

test('CHEMISTRY_POINTS → 仅 chem flag', () => {
    const r = parseRequirements([{ key: "CHEMISTRY_POINTS", value: 25, count: 1 }]);
    assert.strictEqual(r.flags.chem, true);
    assert.strictEqual(r.groups.length, 0);
});

test('ALL_PLAYERS_CHEMISTRY_POINTS → chem flag', () => {
    const r = parseRequirements([{ key: "ALL_PLAYERS_CHEMISTRY_POINTS", value: 2, count: 1 }]);
    assert.strictEqual(r.flags.chem, true);
});

// --- 组合场景 ---
test('组合：chem + club + rating → flags 全置 + 可检索 groups', () => {
    const r = parseRequirements([
        { key: "CHEMISTRY_POINTS", value: 25, count: 1 },
        { key: "CLUB_ID", value: 101, count: 4 },
        { key: "TEAM_RATING", value: 83, count: 1 },
        { key: "PLAYER_MIN_OVR", value: 80, count: 11 }
    ]);
    assert.strictEqual(r.flags.chem, true);
    assert.strictEqual(r.flags.rating, true);
    assert.strictEqual(r.flags.extended, true);
    assert.strictEqual(r.flags.basic, true);
    assert.strictEqual(r.groups.length, 2, 'chem/rating 不产生 groups，只有 teamId + GTrating');
    assert.deepStrictEqual(r.summary.map(s => s.key), ["CHEMISTRY_POINTS", "CLUB_ID", "TEAM_RATING", "PLAYER_MIN_OVR"]);
});

test('组合：exact + league + position', () => {
    const r = parseRequirements([
        { key: "PLAYER_EXACT_OVR", value: 85, count: 2 },
        { key: "LEAGUE_ID", value: 13, count: 5 },
        { key: "PLAYER_POSITION", value: "GK", count: 1 }
    ]);
    assert.strictEqual(r.flags.exact, true);
    assert.strictEqual(r.flags.pos, true);
    assert.strictEqual(r.groups.length, 3);
});

// --- 边界 ---
test('空需求 → groups 空 + 全 flag false + quickGreedy 会兜底', () => {
    const r = parseRequirements([]);
    assert.strictEqual(r.groups.length, 0);
    assert.strictEqual(r.flags.basic && r.flags.extended && r.flags.chem && r.flags.rating, false);
});

test('未知需求 key → summary 透传不丢弃', () => {
    const r = parseRequirements([{ key: "MYSTERY_REQ", value: 1, count: 2 }]);
    assert.strictEqual(r.groups.length, 0);
    assert.strictEqual(r.summary.length, 1);
    assert.strictEqual(r.summary[0].kind, "other");
    assert.strictEqual(r.summary[0].count, 2);
});

test('count 归并：相同 criteria 合并数量', () => {
    const r = parseRequirements([
        { key: "PLAYER_MIN_OVR", value: 80, count: 6 },
        { key: "PLAYER_MIN_OVR", value: 80, count: 5 }
    ]);
    assert.strictEqual(r.groups.length, 1);
    assert.strictEqual(r.groups[0].c, 11);
});

test('count 缺省 → 1', () => {
    const r = parseRequirements([{ key: "PLAYER_MIN_OVR", value: 80 }]);
    assert.strictEqual(r.groups[0].c, 1);
});

test('null 输入容错', () => {
    const r = parseRequirements(null);
    assert.strictEqual(r.groups.length, 0);
    assert.strictEqual(r.summary.length, 0);
});

// --- expandTeamIds ---
test('expandTeamIds：无 teamLinks 返回标量', () => {
    assert.strictEqual(expandTeamIds(101), 101);
    assert.strictEqual(expandTeamIds(101, {}), 101);
});

test('expandTeamIds：有链接返回去重数组', () => {
    assert.deepStrictEqual(expandTeamIds(101, { 101: [102, 103, 102] }), [101, 102, 103]);
});

test('expandTeamIds：字符串 id 兼容', () => {
    assert.strictEqual(expandTeamIds("101"), 101);
});

// ===== 结果 =====
console.log('\n' + '='.repeat(40));
console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
if (failed > 0) process.exit(1);
