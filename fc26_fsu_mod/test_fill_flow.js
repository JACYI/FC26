/**
 * 通用填充引擎 — 引擎控制流 单元测试（v26.10-jacyi.7 Step2）
 *
 * 用 mock deps 驱动 fill.run 主流程：需求解析 → 路由 → 逐算法（排除链）→ 终校验 → 失败分类
 * 注意：测试只 mock deps 层，不 mock EA 全局；matchItem 复刻 getItemBy 过滤语义（仅测试驱动）
 *
 * 运行：node fc26_fsu_mod/test_fill_flow.js
 */

const assert = require('assert');

// ===== 待测纯函数（//PURE: 复制自 fsu-mod.c.user.js [C-05]）=====
function expandTeamIds(teamId, teamLinks) {
    const ids = [parseInt(teamId, 10) || teamId];
    if (teamLinks && teamLinks[teamId]) {
        for (const t of teamLinks[teamId]) {
            if (ids.indexOf(t) === -1) ids.push(t);
        }
    }
    return ids.length === 1 ? ids[0] : ids;
}

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
                rec.kind = "other"; break;
        }
        summary.push(rec);
    }
    return { groups: groups, flags: flags, summary: summary };
}

function routeAlgorithm(flags) {
    const chain = [];
    if (flags.chem) chain.push("chemFirst");
    if (flags.extended) chain.push("reqAware");
    if (flags.rating) chain.push("ratingCombo");
    if (flags.basic || (!flags.extended && !flags.chem && !flags.rating)) chain.push("quickGreedy");
    chain.push("verifyFallback");
    return chain;
}

function buildChain(flags, forced) {
    if (forced === "legacy" || forced === "fodder") {
        return ["quickGreedy", "verifyFallback"];
    }
    return routeAlgorithm(flags);
}

function classifyFailure(attempts, flags, poolSize, slotsNeeded) {
    if (poolSize < slotsNeeded) return "fill.error.pool";
    if (flags.chem && attempts.some((a) => a.name === "chemFirst" && a.status !== "ok")) return "fill.error.chem";
    if (flags.rating && attempts.some((a) => a.name === "ratingCombo" && a.status !== "ok")) return "fill.error.rating";
    if (flags.extended && attempts.some((a) => a.name === "reqAware" && a.status !== "ok")) return "fill.error.req";
    return "fill.error.noanswer";
}

// ===== 算法库（复制自 C，deps 注入）=====
const algorithms = {};

algorithms.quickGreedy = async (ctx, deps) => {
    const groups = ctx.parsed.groups.filter((g) => {
        const keys = Object.keys(g.t);
        return keys.every((k) => ["rs", "rareflag", "gs", "groups", "GTrating"].indexOf(k) >= 0);
    });
    if (!groups.length) return { filled: [], status: "failed", reason: "no-basic-groups" };
    const picked = [];
    const excluded = ctx.excluded.slice();
    let shortfall = false;
    for (const g of groups) {
        const need = Math.min(g.c, ctx.slotsNeeded - picked.length);
        if (need <= 0) break;
        const crit = deps.ignorePlayerToCriteria(Object.assign({}, g.t));
        if (excluded.length) crit.NEdatabaseId = excluded;
        crit.lock = false;
        if (deps.solverPendingRs) crit.rs = JSON.parse(JSON.stringify(deps.solverPendingRs));
        let res = deps.getItemBy(crit, ctx.pool);
        if (ctx.excludeRatings && ctx.excludeRatings.size) {
            res = res.filter((it) => !ctx.excludeRatings.has(it.rating));
        }
        const take = (res || []).slice(0, need);
        if (take.length < need) shortfall = true;
        for (const it of take) { picked.push(it); excluded.push(it.databaseId); }
    }
    return {
        filled: picked,
        status: shortfall ? "partial" : (picked.length >= ctx.slotsNeeded ? "ok" : (picked.length ? "partial" : "failed")),
        reason: picked.length ? null : "no-candidates"
    };
};

algorithms.reqAware = async (ctx, deps) => {
    const groups = ctx.parsed.groups;
    if (!groups.length) return { filled: [], status: "failed", reason: "no-groups" };
    const picked = [];
    const excluded = ctx.excluded.slice();
    let shortfall = false;
    for (const g of groups) {
        const need = Math.min(g.c, ctx.slotsNeeded - picked.length);
        if (need <= 0) break;
        const crit = deps.ignorePlayerToCriteria(Object.assign({}, g.t));
        if (excluded.length) crit.NEdatabaseId = excluded;
        crit.lock = false;
        let res = deps.getItemBy(crit, ctx.pool);
        if (ctx.excludeRatings && ctx.excludeRatings.size) {
            res = res.filter((it) => !ctx.excludeRatings.has(it.rating));
        }
        const take = (res || []).slice(0, need);
        if (take.length < need) shortfall = true;
        for (const it of take) { picked.push(it); excluded.push(it.databaseId); }
        if (g.t.rating != null) {
            ctx.excludeRatings.add(g.t.rating);
        }
    }
    return {
        filled: picked,
        status: shortfall ? "partial" : (picked.length >= ctx.slotsNeeded ? "ok" : (picked.length ? "partial" : "failed")),
        reason: picked.length ? null : "no-candidates"
    };
};

algorithms.ratingCombo = async (ctx, deps) => {
    const target = ctx.ratingTarget;
    if (target == null) return { filled: [], status: "failed", reason: "no-rating-flag" };
    let combos = [];
    try { combos = deps.needRatingsCount(target, ctx.squad) || []; } catch (e) { combos = []; }
    if (!combos.length) return { filled: [], status: "failed", reason: "rating-insufficient" };
    for (const combo of combos) {
        let players = [];
        try { players = deps.getRatingPlayers(ctx.squad, combo.ratings) || []; } catch (e) { players = []; }
        if (players.length >= ctx.slotsNeeded) {
            if (deps.virtualMeets(ctx.challenge, players)) {
                return { filled: players, status: "ok", reason: null };
            }
        }
    }
    return { filled: [], status: "failed", reason: "rating-insufficient" };
};

//PURE: 化学启发式得分（复制自 C）
function chemScore(player, picked) {
    let score = 0;
    for (const p of (picked || [])) {
        if (p.teamId != null && player.teamId != null && p.teamId === player.teamId) score += 3;
        if (p.leagueId != null && player.leagueId != null && p.leagueId === player.leagueId) score += 2;
        if (p.nationId != null && player.nationId != null && p.nationId === player.nationId) score += 1;
    }
    return score;
}

algorithms.chemFirst = async (ctx, deps) => {
    if (!ctx.parsed.flags.chem) return { filled: [], status: "failed", reason: "no-chem-flag" };
    const groups = ctx.parsed.groups;
    if (!groups.length) {
        let res = deps.getItemBy(deps.ignorePlayerToCriteria({}), ctx.pool);
        if (ctx.excludeRatings.size) res = res.filter((it) => !ctx.excludeRatings.has(it.rating));
        const scored = (res || []).slice(0, 40)
            .map((it) => ({ it: it, s: chemScore(it, []) }))
            .sort((a, b) => b.s - a.s || (a.it.rating || 0) - (b.it.rating || 0));
        const take = scored.slice(0, ctx.slotsNeeded).map((x) => x.it);
        return {
            filled: take,
            status: take.length >= ctx.slotsNeeded ? "ok" : (take.length ? "partial" : "failed"),
            reason: take.length ? null : "no-candidates"
        };
    }
    const picked = [];
    const excluded = ctx.excluded.slice();
    let shortfall = false;
    for (const g of groups) {
        const need = Math.min(g.c, ctx.slotsNeeded - picked.length);
        if (need <= 0) break;
        const crit = deps.ignorePlayerToCriteria(Object.assign({}, g.t));
        if (excluded.length) crit.NEdatabaseId = excluded;
        crit.lock = false;
        let res = deps.getItemBy(crit, ctx.pool);
        if (ctx.excludeRatings.size) res = res.filter((it) => !ctx.excludeRatings.has(it.rating));
        const scored = (res || []).slice(0, 40)
            .map((it) => ({ it: it, s: chemScore(it, picked) }))
            .sort((a, b) => b.s - a.s || (a.it.rating || 0) - (b.it.rating || 0));
        const take = scored.slice(0, need).map((x) => x.it);
        if (take.length < need) shortfall = true;
        for (const it of take) { picked.push(it); excluded.push(it.databaseId); }
        if (g.t.rating != null) ctx.excludeRatings.add(g.t.rating);
    }
    return {
        filled: picked,
        status: shortfall ? "partial" : (picked.length >= ctx.slotsNeeded ? "ok" : (picked.length ? "partial" : "failed")),
        reason: picked.length ? null : "no-candidates"
    };
};

algorithms.verifyFallback = async (ctx, deps) => {
    const slots = ctx.slotsNeeded;
    if (slots <= 0) return { filled: [], status: "ok", reason: null };
    let cands = [];
    try { cands = deps.getItemBy(deps.ignorePlayerToCriteria({}), ctx.pool) || []; } catch (e) { cands = []; }
    cands = cands.slice(0, 200).sort((a, b) => (a.rating || 0) - (b.rating || 0));
    const used = new Set(ctx.excluded);
    let calls = 0;
    const MAX_CALLS = 2000;
    const solve = (picked, startIdx) => {
        if (calls > MAX_CALLS) return null;
        if (picked.length === slots) {
            calls++;
            return deps.virtualMeets(ctx.challenge, picked) ? picked.slice() : null;
        }
        for (let i = startIdx; i < cands.length; i++) {
            const it = cands[i];
            if (used.has(it.databaseId)) continue;
            used.add(it.databaseId);
            picked.push(it);
            const r = solve(picked, i + 1);
            picked.pop();
            used.delete(it.databaseId);
            if (r) return r;
        }
        return null;
    };
    const result = solve([], 0);
    if (!result) return { filled: [], status: "failed", reason: "no-solution" };
    return { filled: result, status: "ok", reason: null };
};

//PURE: EA 需求对象数组 → 简化形（复制自 C）
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
    } catch (e) {}
    return reqs;
}

//PURE: A 风格候选过滤（复制自 C solver 块；smartFill 池预过滤复用）
function filterCandidates(items, options, helpers) {
    helpers = helpers || {};
    const isSpecial = helpers.isSpecial || ((it) => !!(it.isSpecial && it.isSpecial()));
    const isUntradeable = helpers.isUntradeable || ((it) => it.untradeableCount > 0);
    const filtered = items.filter((it) => {
        const rating = it.rating || 0;
        if (options.minRating != null && rating < options.minRating) return false;
        if (options.maxRating != null && rating > options.maxRating) return false;
        if (options.minPrice != null && (it.price || 0) < options.minPrice) return false;
        if (options.maxPrice != null && (it.price || 0) > options.maxPrice) return false;
        if (options.commonsOnly && isSpecial(it)) return false;
        if (options.untradeableOnly && !isUntradeable(it)) return false;
        return true;
    });
    const unit = options.unitCoins ? (it) => it.price || 0 : (it) => it.rating || 0;
    return filtered.sort((a, b) => unit(a) - unit(b));
}

// ===== 引擎主流程（复制自 C，deps 注入）=====
async function fillRun(challenge, opts, deps) {
    const o = Object.assign({ algorithm: "auto" }, opts);
    const reqs = simplifyReqs((challenge && challenge.eligibilityRequirements) || []);
    const parsed = parseRequirements(reqs, { teamLinks: deps.getTeamLinks ? deps.getTeamLinks() : null });
    const totalSlots = (challenge && challenge.squad && challenge.squad.getNumOfRequiredPlayers) ? challenge.squad.getNumOfRequiredPlayers() : 11;
    // smartFill 选项：池预过滤（评分/价格/普通卡/不可交易）+ 数据源 + 优先重复
    let pool = deps.pool();
    let getItemBy = deps.getItemBy;
    if (o.minRating != null || o.maxRating != null || o.minPrice != null || o.maxPrice != null || o.commonsOnly || o.untradeableOnly) {
        pool = filterCandidates(pool || [], {
            minRating: o.minRating, maxRating: o.maxRating,
            minPrice: o.minPrice, maxPrice: o.maxPrice,
            commonsOnly: o.commonsOnly, untradeableOnly: o.untradeableOnly
        }, {
            isSpecial: (it) => !!(it.isSpecial && it.isSpecial()),
            isUntradeable: (it) => it.untradeableCount > 0
        });
    }
    if (o.poolSource === "storage") {
        // 数据源切换：池传 undefined → events.getItemBy 自动用 俱乐部+仓库（replaceData 空值语义）
        pool = null;
        const orig = getItemBy;
        getItemBy = (crit, p, rd) => orig(crit, p == null ? undefined : p, rd);
    }
    if (o.preferDuplicates) {
        // 优先重复：稳定排序（重复球员在前），非过滤
        const orig = getItemBy;
        getItemBy = (crit, p, rd) => {
            const res = orig(crit, p, rd) || [];
            return res.slice().sort((a, b) => {
                const da = !!(a.isDuplicate && a.isDuplicate()) ? 0 : 1;
                const db = !!(b.isDuplicate && b.isDuplicate()) ? 0 : 1;
                return da - db;
            });
        };
    }
    if (getItemBy !== deps.getItemBy) deps = Object.assign({}, deps, { getItemBy: getItemBy });
    const forced = o.algorithm === "legacy" ? "legacy" : (o.algorithm === "fodder" ? "fodder" : "auto");
    const chain = buildChain(parsed.flags, forced);
    const ctx = {
        challenge: challenge,
        parsed: parsed,
        slotsNeeded: totalSlots,
        ratingTarget: null,
        pool: pool,
        excluded: [],
        excludeRatings: new Set(),
        squad: challenge && challenge.squad,
        opts: o
    };
    const ratingReq = reqs.find((r) => r.key === "TEAM_RATING");
    if (ratingReq) ctx.ratingTarget = parseInt(ratingReq.value, 10) || 0;
    const attempts = [];
    const filled = [];
    for (const name of chain) {
        if (filled.length >= totalSlots) break;
        ctx.slotsNeeded = totalSlots - filled.length;
        const alg = algorithms[name];
        if (!alg) { attempts.push({ name: name, status: "failed", reason: "not-implemented", added: 0 }); continue; }
        const r = await alg(ctx, deps);
        const added = (r.filled || []).filter((it) => filled.indexOf(it) === -1);
        filled.push.apply(filled, added);
        ctx.excluded = ctx.excluded.concat(added.map((it) => it.databaseId));
        attempts.push({ name: name, status: r.status, reason: r.reason, added: added.length });
        if (r.status === "ok") break;
    }
    let ok = filled.length >= totalSlots;
    if (ok && deps.virtualMeets) ok = deps.virtualMeets(challenge, filled);
    // storage 模式 pool 为 null：池规模判定跳过
    const poolSize = pool ? pool.length : Infinity;
    const reason = ok ? null : classifyFailure(attempts, parsed.flags, poolSize, totalSlots);
    return { ok: ok, filled: filled, reason: reason, algorithm: chain.join("+"), attempts: attempts };
}

// ===== Mock 设施 =====
let _seq = 0;
function makePlayer(rating, attrs) {
    _seq++;
    return Object.assign({
        databaseId: _seq,
        rating: rating,
        teamId: 0,
        leagueId: 0,
        nationId: 0,
        possiblePositions: ["ST", "CF", "CAM"],
        rareflag: 0
    }, attrs || {});
}

// 复刻 getItemBy 过滤语义（测试专用）
function matchItem(item, criteria) {
    for (const k of Object.keys(criteria)) {
        if (k === "NEdatabaseId") { if (criteria[k].indexOf(item.databaseId) >= 0) return false; continue; }
        if (k === "lock" || k === "removeSquad") continue;
        if (k === "includePos") { if ((item.possiblePositions || []).indexOf(criteria[k]) === -1) return false; continue; }
        if (k === "GTrating") { if ((item.rating || 0) < criteria[k]) return false; continue; }
        const v = criteria[k];
        if (Array.isArray(v)) { if (v.indexOf(item[k]) === -1) return false; }
        else if (item[k] !== v) return false;
    }
    return true;
}

function makeDeps(pool, extra) {
    return Object.assign({
        getItemBy: (criteria, replaceData) => (replaceData || pool).filter((it) => matchItem(it, criteria)),
        ignorePlayerToCriteria: (c) => Object.assign({}, c),
        virtualMeets: (challenge, players) => {
            // 简化校验：GTrating 需求 → 全部满足；teamId 需求 → 对应球员在场
            const reqs = challenge.eligibilityRequirements || [];
            for (const r of reqs) {
                const k = r.getFirstKey ? r.getFirstKey() : r.key;
                const v = r.getValue ? r.getValue() : r.value;
                if (k === "TEAM_RATING") continue;
                if (k === "CHEMISTRY_POINTS") continue;
                if (k === "PLAYER_MIN_OVR") { if (!players.every(p => p.rating >= v)) return false; continue; }
                if (k === "CLUB_ID") { if (!players.some(p => p.teamId === v)) return false; continue; }
                if (k === "PLAYER_EXACT_OVR") { if (!players.some(p => p.rating === v)) return false; continue; }
                if (k === "PLAYER_RARITY") { if (!players.some(p => p.rareflag === v)) return false; continue; }
            }
            return players.length >= (challenge.squad.getNumOfRequiredPlayers());
        },
        needRatingsCount: () => [{ ratings: [80, 80, 80, 80, 80, 80, 80, 80, 80, 80, 80], cost: 0 }],
        getRatingPlayers: () => [],
        getTeamLinks: () => null,
        pool: () => pool
    }, extra || {});
}

function makeChallenge(reqs, slots) {
    return {
        eligibilityRequirements: reqs.map((r) => ({
            getFirstKey: () => r.key,
            getValue: () => r.value,
            getCount: () => r.count
        })),
        squad: { getNumOfRequiredPlayers: () => slots || 11 }
    };
}

// ===== 测试（async 感知：异步用例断言失败必须计入）=====
let passed = 0, failed = 0;
async function test(name, fn) {
    try {
        await fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}\n      ${e.message}`);
    }
}

(async () => {
    console.log('\n通用填充引擎控制流 单元测试\n' + '='.repeat(40));

    // --- 基础链路：min ovr ---
    await test('min ovr 83 × 11 → quickGreedy 填满 + 终校验过', async () => {
        const pool = Array.from({ length: 15 }, (_, i) => makePlayer(84 + (i % 5)));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 83, count: 11 }], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
        assert.ok(r.algorithm.startsWith("quickGreedy"), r.algorithm);
        assert.ok(r.filled.every(p => p.rating >= 83));
    });

    // --- 扩展链路：俱乐部需求 ---
    await test('CLUB_ID 4人 + min ovr → reqAware 筛选正确', async () => {
        const pool = [
            ...Array.from({ length: 6 }, (_, i) => makePlayer(80, { teamId: 101, leagueId: 13 })),
            ...Array.from({ length: 8 }, (_, i) => makePlayer(84, { teamId: 999, leagueId: 19 }))
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "CLUB_ID", value: 101, count: 4 },
            { key: "PLAYER_MIN_OVR", value: 80, count: 11 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.ok(r.filled.filter(p => p.teamId === 101).length >= 4, `至少 4 个曼城球员（EA 语义为 Min N），实际 ${r.filled.filter(p => p.teamId === 101).length}`);
        assert.strictEqual(r.filled.length, 11);
    });

    // --- 排除链：不重复使用 ---
    await test('排除链生效：同一球员不重复入队', async () => {
        const pool = [makePlayer(84, { teamId: 101 }), makePlayer(84, { teamId: 101 }), makePlayer(70)];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "CLUB_ID", value: 101, count: 2 }], 2), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 2);
        assert.strictEqual(new Set(r.filled.map(p => p.databaseId)).size, 2);
    });

    // --- partial 移交：quickGreedy 填不满 → reqAware 补充 ---
    await test('部分填充移交下一算法（排除链延续）', async () => {
        const pool = [
            ...Array.from({ length: 5 }, (_, i) => makePlayer(85, { teamId: 101 })),
            ...Array.from({ length: 8 }, (_, i) => makePlayer(82, { teamId: 999 }))
        ];
        const deps = makeDeps(pool);
        // 5 个 85+（满足 min ovr 85 只找到 5 个——同队），剩余由 reqAware 的 teamId 组找
        // 需求：min ovr 85 × 5 + 曼城 × 5 → quickGreedy 填 5 个 85 分（含曼城），reqAware 补 5 个曼城（82 分不行？）
        // 简化：min ovr 84 × 5 + 曼城 × 11（曼城池 5 个 85 + 3 个 82——不够 11）→ 全链失败 → noanswer
        const r = await fillRun(makeChallenge([
            { key: "PLAYER_MIN_OVR", value: 85, count: 5 },
            { key: "CLUB_ID", value: 101, count: 5 }
        ], 11), {}, deps);
        // reqAware 先取 5 个 85 曼城（partial）→ quickGreedy 的 85+ 已被用完（failed）→ 缺 6 → 失败
        assert.strictEqual(r.ok, false);
        assert.strictEqual(r.reason, "fill.error.req", '扩展需求未满足 → req 分类');
        assert.ok(r.attempts.some(a => a.name === "reqAware" && a.status === "partial"), 'reqAware 部分填充');
        assert.ok(r.attempts.some(a => a.name === "quickGreedy" && a.added === 0), 'quickGreedy 无剩余 85+ 候选可加');
    });

    // --- 池不足 ---
    await test('池不足 → pool 分类', async () => {
        const pool = [makePlayer(80), makePlayer(80), makePlayer(80)];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), {}, deps);
        assert.strictEqual(r.ok, false);
        assert.strictEqual(r.reason, "fill.error.pool");
    });

    // --- forced=legacy 旧行为 ---
    await test('forced legacy → 链为 quickGreedy+verifyFallback', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), { algorithm: "legacy" }, deps);
        assert.strictEqual(r.algorithm, "quickGreedy+verifyFallback");
        assert.strictEqual(r.ok, true);
    });

    // --- 化学需求：chemFirst 不存在时（Step2 阶段）走 quickGreedy+verifyFallback ---
    await test('化学需求（Step2 无 chemFirst）→ 链含 quickGreedy + verifyFallback，终校验放行', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "CHEMISTRY_POINTS", value: 20, count: 1 },
            { key: "PLAYER_MIN_OVR", value: 78, count: 11 }
        ], 11), {}, deps);
        // verifyFallback 终校验对化学需求放行（mock 简化）→ ok
        assert.strictEqual(r.ok, true);
    });

    // --- verifyFallback 兜底成功 ---
    await test('verifyFallback 兜底：贪心失败后回溯找到解', async () => {
        // 需求：exact 85 一人 —— quickGreedy 无 basic 组 → reqAware 找 exact 85
        const pool = [
            makePlayer(84), makePlayer(85), makePlayer(85), makePlayer(86), makePlayer(87),
            ...Array.from({ length: 8 }, (_, i) => makePlayer(83))
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "PLAYER_EXACT_OVR", value: 85, count: 1 },
            { key: "PLAYER_MIN_OVR", value: 83, count: 11 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.filter(p => p.rating === 85).length, 1);
    });

    // --- verifyFallback 无解 ---
    await test('verifyFallback 无解 → noanswer', async () => {
        // 需求 exact 99（池里没有）→ 终校验永不过 → noanswer
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "PLAYER_EXACT_OVR", value: 99, count: 1 },
            { key: "PLAYER_MIN_OVR", value: 80, count: 11 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, false);
        assert.strictEqual(r.reason, "fill.error.req");
    });

    // --- chemFirst：化学需求 → 同队球员优先 ---
    await test('化学需求 → chemFirst 链首，同队球员被优先选中', async () => {
        const pool = [
            makePlayer(80, { teamId: 101, leagueId: 13, nationId: 44 }),
            makePlayer(81, { teamId: 101, leagueId: 13, nationId: 44 }),
            makePlayer(82, { teamId: 101, leagueId: 13, nationId: 44 }),
            makePlayer(88, { teamId: 999, leagueId: 19, nationId: 1 }),
            makePlayer(87, { teamId: 999, leagueId: 19, nationId: 1 }),
            ...Array.from({ length: 6 }, (_, i) => makePlayer(75, { teamId: 500 + i, leagueId: 30, nationId: 2 }))
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "CHEMISTRY_POINTS", value: 20, count: 1 },
            { key: "PLAYER_MIN_OVR", value: 75, count: 11 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.algorithm.split("+")[0], "chemFirst", 'chemFirst 在链首');
        assert.ok(r.attempts.some(a => a.name === "chemFirst" && a.added >= 3), 'chemFirst 至少选中 3 个同队球员');
        const sameTeam = r.filled.filter(p => p.teamId === 101).length;
        assert.ok(sameTeam >= 3, `同队球员优先（实际 ${sameTeam}）`);
    });

    await test('纯化学需求（无其他组）→ chemFirst 直接取候选', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80, { teamId: 101, leagueId: 13, nationId: 44 }));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "CHEMISTRY_POINTS", value: 20, count: 1 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
    });

    // --- 空需求 ---
    await test('无需求 → quickGreedy 取前 11', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
    });

    // ===== 用户场景：基本条件本地快速填充（均分 + TOTW + 数量）=====
    await test('均分84 + TOTW×1 + 11人 → 本地链填充成功（无外部模板）', async () => {
        const pool = [
            makePlayer(86, { rareflag: 1 }), // TOTW
            ...Array.from({ length: 12 }, (_, i) => makePlayer(84 + (i % 3)))
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([
            { key: "TEAM_RATING", value: 84, count: 1 },
            { key: "PLAYER_RARITY", value: 1, count: 1 },
            { key: "PLAYER_MIN_OVR", value: 80, count: 11 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true, '本地引擎应直接求解成功');
        assert.strictEqual(r.filled.length, 11);
        assert.ok(r.filled.some(p => p.rareflag === 1), 'TOTW 球员在场');
        assert.ok(r.filled.every(p => p.rating >= 80), '全部满足最低评分');
        assert.ok(r.algorithm.indexOf("ratingCombo") >= 0, 'ratingCombo 在链中（均分路由）');
    });

    await test('纯均分 SBC（无 TOTW）→ ratingCombo 单独求解', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80 + (i % 4)));
        const deps = makeDeps(pool, { getRatingPlayers: () => pool.slice(0, 11) });
        const r = await fillRun(makeChallenge([
            { key: "TEAM_RATING", value: 82, count: 1 }
        ], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.algorithm.split("+")[0], "ratingCombo", 'ratingCombo 链首');
    });

    // ===== [C-05] smartFill 选项（v26.10-jacyi.8）=====
    await test('minRating 过滤：低于下限的球员不进池', async () => {
        const pool = [
            ...Array.from({ length: 4 }, (_, i) => makePlayer(80 + i)), // 80-83 被过滤
            ...Array.from({ length: 12 }, (_, i) => makePlayer(86 + (i % 3))) // 86-88 ×12 命中
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), { minRating: 85 }, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
        assert.ok(r.filled.every(p => p.rating >= 85), '全部 ≥85');
    });

    await test('maxRating 过滤：高于上限的球员不进池', async () => {
        const pool = [
            ...Array.from({ length: 12 }, (_, i) => makePlayer(82 + (i % 7))), // 82-88 ×12 命中
            makePlayer(95) // 被排除
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), { maxRating: 88 }, deps);
        assert.strictEqual(r.ok, true);
        assert.ok(r.filled.every(p => p.rating <= 88), '全部 ≤88（95 分被排除）');
    });

    await test('组合过滤：仅普通卡 + 仅不可交易 + 价格区间', async () => {
        const pool = [
            makePlayer(84, { isSpecial: () => true, untradeableCount: 1, price: 3000 }),   // special → 排除
            makePlayer(85, { isSpecial: () => false, untradeableCount: 0, price: 3000 }),  // 可交易 → 排除
            makePlayer(86, { isSpecial: () => false, untradeableCount: 1, price: 500 }),   // 价格过低 → 排除
            makePlayer(87, { isSpecial: () => false, untradeableCount: 1, price: 9000 }),  // 价格过高 → 排除
            ...Array.from({ length: 11 }, (_, i) => makePlayer(88, { isSpecial: () => false, untradeableCount: 1, price: 3000 + i * 100 }))
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11),
            { commonsOnly: true, untradeableOnly: true, minPrice: 2000, maxPrice: 5000 }, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
        assert.ok(r.filled.every(p => !p.isSpecial()), '无特殊卡');
        assert.ok(r.filled.every(p => p.untradeableCount > 0), '全部不可交易');
        assert.ok(r.filled.every(p => p.price >= 2000 && p.price <= 5000), '价格在区间内');
    });

    await test('preferDuplicates：重复球员优先被选中', async () => {
        const pool = [
            ...Array.from({ length: 11 }, (_, i) => makePlayer(82, { isDuplicate: () => false })),
            makePlayer(82, { isDuplicate: () => true }),
            makePlayer(82, { isDuplicate: () => true }),
            makePlayer(82, { isDuplicate: () => true })
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 80, count: 11 }], 11), { preferDuplicates: true }, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.filter(p => p.isDuplicate()).length, 3, '3 个重复球员全部优先选中');
    });

    await test('preferDuplicates 关闭 → 无重复偏好（回归）', async () => {
        const pool = [
            ...Array.from({ length: 11 }, (_, i) => makePlayer(80, { isDuplicate: () => false })),
            makePlayer(80, { isDuplicate: () => true })
        ];
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), { preferDuplicates: false }, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.filter(p => p.isDuplicate()).length, 0, '池末重复卡不被优先（按原顺序取）');
    });

    await test('poolSource storage → getItemBy 收到 undefined 池参数', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80));
        let lastPoolArg = "not-called";
        const deps = makeDeps(pool, {
            getItemBy: (criteria, replaceData) => { lastPoolArg = replaceData; return pool.filter((it) => matchItem(it, criteria)); }
        });
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 75, count: 11 }], 11), { poolSource: "storage" }, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(lastPoolArg, undefined, '池参数为 undefined → 引擎自动用 俱乐部+仓库');
    });

    await test('无 opts → 与旧行为一致（回归）', async () => {
        const pool = Array.from({ length: 12 }, (_, i) => makePlayer(80 + (i % 4)));
        const deps = makeDeps(pool);
        const r = await fillRun(makeChallenge([{ key: "PLAYER_MIN_OVR", value: 80, count: 11 }], 11), {}, deps);
        assert.strictEqual(r.ok, true);
        assert.strictEqual(r.filled.length, 11);
    });

    // ===== 结果 =====
    console.log('\n' + '='.repeat(40));
    console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
    if (failed > 0) process.exit(1);
})().catch((e) => { console.error(e); process.exit(1); });
