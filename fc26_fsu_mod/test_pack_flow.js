/**
 * 批量开包引擎 — 单包流程 openOne 单元测试（v26.10-jacyi.9）
 *
 * 覆盖：misc 兑换（redeem 成功/失败/异常）、moveClub 失败不丢记录（回归修复）、
 *       超时不重试（防双开）、取消检查点、sellAll 下 misc 不误卖
 * 注意：openOne 从 fsu-mod.c.user.js [C-01] 复制（revenue 块引用在 Node 下 undefined 但被 try/catch 包住）
 *
 * 运行：node fc26_fsu_mod/test_pack_flow.js
 */

const assert = require('assert');

// ===== 待测纯函数副本（//PURE: 复制自 fsu-mod.c.user.js [C-01]）=====
function nextRetryDelay(attempt, baseMs) {
    return Math.min(baseMs * Math.pow(2, attempt), 30000);
}

function isFatalError(code, fatalCodes) {
    return (fatalCodes || [401, 403]).some(c => String(c) === String(code));
}

function classifyPackItems(items, ctx) {
    const out = { toClub: [], toStorage: [], toSell: [], toRedeem: [], toUnassigned: [], stop: false };
    let storageFree = ctx.storageFree;
    const batchSeen = new Set();
    for (const item of items) {
        if (ctx.isPick && ctx.isPick(item)) { out.toUnassigned.push(item); continue; }
        if (ctx.isRedeemable && ctx.isRedeemable(item)) { out.toRedeem.push(item); continue; }
        const defId = item.definitionId;
        const alreadyOwned = ctx.inClub(defId) || batchSeen.has(defId);
        batchSeen.add(defId);
        if (ctx.sellAll) {
            out.toSell.push(item);
        } else if (alreadyOwned) {
            if (ctx.sellDup && !(item.untradeableCount > 0)) {
                out.toSell.push(item);
            } else if (ctx.discardBs && ctx.isDiscardBs(item)) {
                out.toSell.push(item);
            } else if (item.rating >= ctx.storageMinRating && storageFree > 0) {
                out.toStorage.push(item);
                storageFree--;
            } else if (ctx.onUnclassifiable === 'discard') {
                out.toSell.push(item);
            } else if (ctx.onUnclassifiable === 'stop') {
                out.toUnassigned.push(item);
                out.stop = true;
            } else {
                out.toUnassigned.push(item);
            }
        } else if (ctx.discardBs && ctx.isDiscardBs(item)) {
            out.toSell.push(item);
        } else {
            out.toClub.push(item);
        }
    }
    return out;
}

// ===== openOne 副本（复制自 fsu-mod.c.user.js，deps 注入）=====
async function openOne(pack, index, options, deps, records) {
    if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
    const maxRetries = options.maxRetries || 3;
    let openResult = null;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            openResult = await deps.openPack(pack);
            if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
            if (openResult.success) break;
            const code = (openResult.error && openResult.error.code) || openResult.status;
            if (isFatalError(code)) return { fatal: true, code: code };
            if (code === "timeout" || code === "cancelled" || code === "observe-error") return { failed: true, reason: code };
            if (attempt < maxRetries) {
                if (await deps.sleep(nextRetryDelay(attempt, 1000))) return { cancelled: true };
            }
        } catch (e) {
            console.warn("[C-01] pack.open 异常", e);
            if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
            if (attempt < maxRetries) {
                if (await deps.sleep(nextRetryDelay(attempt, 1000))) return { cancelled: true };
            }
            else return { failed: true };
        }
    }
    if (!openResult || !openResult.success) return { failed: true };

    // revenue 上报（Node 下引用 undefined 但被 try/catch 包住）
    try {
        if (pack instanceof UTStoreItemPackEntity && pack && pack.isMyPack) services.User.getUser().decrementNumUnopenedPacks();
        const logData = {
            [RevenueAnalytics.Key.CURRENCY]: GameCurrency.COINS,
            [RevenueAnalytics.Key.TYPE]: pack.dealType || "unknown",
            [RevenueAnalytics.Key.ID]: (pack.id || "").toString() || "unknown"
        };
        const sdk = unsafeWindow && unsafeWindow.services && unsafeWindow.services.revenueSDK;
        if (sdk && sdk.initialized && typeof sdk.logEvent === "function") sdk.logEvent(RevenueAnalytics.Event.STORE_PACK_PURCHASED, logData);
    } catch (e) {}

    const items = openResult.response.items;
    const storage = deps.getStorageState();
    const ctx = {
        sellDup: !!options.sellDup,
        sellAll: !!options.sellAll,
        discardBs: !!(options.discardBs),
        storageMinRating: storage.minRating,
        storageFree: storage.free,
        inClub: deps.getInClub,
        isDiscardBs: deps.isDiscardBs,
        isPick: deps.isPick,
        isRedeemable: deps.isRedeemable,
        onUnclassifiable: options.overfillMode || "unassigned"
    };
    const out = classifyPackItems(items, ctx);
    if (out.stop) {
        return { failed: true, stop: true };
    }

    const pushRecords = (list, storeLoc) => {
        for (const it of list) {
            const copy = Object.assign({}, it);
            copy.storeLoc = storeLoc;
            copy.packCount = index + 1;
            records.push(copy);
        }
    };

    let moveClubFailed = false;
    if (out.toClub.length > 0) {
        if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
        try {
            const r = await deps.moveClub(out.toClub);
            if (r.success) {
                pushRecords(out.toClub, 1);
            } else {
                console.warn("[C-01] moveClub 失败，物品留未分配", r);
                pushRecords(out.toClub, 0);
                moveClubFailed = true;
            }
        } catch (e) {
            console.warn("[C-01] moveClub 异常，物品留未分配", e);
            pushRecords(out.toClub, 0);
            moveClubFailed = true;
        }
    }

    if (out.toStorage.length > 0) {
        if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
        try {
            const r = await deps.moveStorage(out.toStorage);
            if (r.success) {
                pushRecords(out.toStorage, 2);
            } else {
                console.warn("[C-01] moveStorage 失败，物品留未分配", r);
                pushRecords(out.toStorage, 0);
            }
        } catch (e) {
            console.warn("[C-01] moveStorage 异常，物品留未分配", e);
            pushRecords(out.toStorage, 0);
        }
    }

    if (out.toSell.length > 0) {
        if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
        try {
            const r = await deps.discard(out.toSell);
            if (r.success) {
                pushRecords(out.toSell, 3);
            } else {
                console.warn("[C-01] discard 失败，fallback 转会名单", r);
                const fb = await deps.moveTransfer(out.toSell);
                if (fb.success) pushRecords(out.toSell, 3);
                else { console.warn("[C-01] fallback 转会也失败", fb); pushRecords(out.toSell, 0); }
            }
        } catch (e) {
            console.warn("[C-01] discard 异常，fallback 转会名单", e);
            try {
                const fb = await deps.moveTransfer(out.toSell);
                if (fb.success) pushRecords(out.toSell, 3);
                else pushRecords(out.toSell, 0);
            } catch (e2) { pushRecords(out.toSell, 0); }
        }
    }

    if (out.toRedeem.length > 0) {
        for (const item of out.toRedeem) {
            if (deps.isCancelled && deps.isCancelled()) return { cancelled: true };
            try {
                const d = await deps.redeem(item);
                if (d && d.success) pushRecords([item], 4);
                else {
                    console.warn("[C-01] redeem 未成功，留未分配", { id: item.id, type: item.type });
                    pushRecords([item], 0);
                }
            } catch (e) {
                console.warn("[C-01] redeem 异常，留未分配", e);
                pushRecords([item], 0);
            }
        }
    }

    for (const it of out.toUnassigned) {
        if (typeof it.type === "undefined" && typeof it.isPlayer !== "function") {
            console.warn("[C-01] 无法分类条目，输出结构", {
                id: it.id, definitionId: it.definitionId, assetId: it.assetId,
                itemState: it.itemState, keys: Object.keys(it).slice(0, 40)
            });
        }
    }
    pushRecords(out.toUnassigned, 0);

    return { opened: true, failed: moveClubFailed, moveFail: moveClubFailed ? "club" : null };
}

// ===== Mock 设施 =====
let _seq = 0;
function makeItem(defId, rating, opts = {}) {
    _seq++;
    return {
        id: opts.id || `item-${_seq}`,
        definitionId: defId,
        rating: rating,
        type: opts.type,
        untradeableCount: opts.untradeable ? 1 : 0,
        discardValue: opts.discardValue || 0,
        isSpecial: () => !!opts.special,
        isBronzeRating: () => rating <= 64,
        isSilverRating: () => rating >= 65 && rating <= 74
    };
}

function makeDeps(overrides = {}) {
    const calls = { openPack: 0, redeem: 0, moveClub: 0, moveStorage: 0, discard: 0, moveTransfer: 0 };
    const received = { discard: [], redeem: [] };
    const deps = Object.assign({
        isCancelled: () => false,
        openPack: async () => { calls.openPack++; return { success: true, response: { items: [] } }; },
        sleep: async () => false,
        getStorageState: () => ({ minRating: 0, free: 100 }),
        getInClub: () => false,
        isDiscardBs: () => false,
        isPick: () => false,
        isRedeemable: (it) => it.type === "misc",
        moveClub: async () => { calls.moveClub++; return { success: true }; },
        moveStorage: async () => { calls.moveStorage++; return { success: true }; },
        discard: async (items) => { calls.discard++; received.discard.push(items); return { success: true }; },
        moveTransfer: async () => { calls.moveTransfer++; return { success: true }; },
        redeem: async (item) => { calls.redeem++; received.redeem.push(item); return { success: true }; }
    }, overrides);
    deps._calls = calls;
    deps._received = received;
    return deps;
}

// ===== 测试（async 感知）=====
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
    console.log('\n批量开包引擎 单包流程 单元测试\n' + '='.repeat(40));

    // F1: misc 兑换成功
    await test('F1 openPack 成功 + misc 1 条 → redeem 恰 1 次、storeLoc=4', async () => {
        const records = [];
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [makeItem('coins', 0, { type: "misc" })] } })
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, records);
        assert.strictEqual(r.opened, true);
        assert.strictEqual(deps._calls.redeem, 1);
        assert.strictEqual(records.length, 1);
        assert.strictEqual(records[0].storeLoc, 4);
    });

    // F2: redeem 失败 → 未分配，批继续
    await test('F2 redeem 返回 {success:false} → storeLoc=0、批不中断', async () => {
        const records = [];
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [makeItem('coins', 0, { type: "misc" })] } }),
            redeem: async () => ({ success: false })
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, records);
        assert.strictEqual(r.opened, true, 'redeem 失败不中断批');
        assert.strictEqual(records[0].storeLoc, 0);
    });

    // F3: redeem 抛异常 → 未分配，批继续
    await test('F3 redeem 抛异常 → storeLoc=0、批不中断', async () => {
        const records = [];
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [makeItem('coins', 0, { type: "misc" })] } }),
            redeem: async () => { throw new Error("redeem boom"); }
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, records);
        assert.strictEqual(r.opened, true);
        assert.strictEqual(records[0].storeLoc, 0);
    });

    // F4: moveClub 失败不提前 return（记录全落）
    await test('F4 moveClub 失败 → toStorage/toRedeem 记录仍落（回归修复）', async () => {
        const records = [];
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [
                makeItem('new1', 84),                                    // → toClub（失败）
                makeItem('dup1', 82),                                    // → toStorage
                makeItem('coins', 0, { type: "misc" })                   // → toRedeem
            ] } }),
            getInClub: (defId) => defId === 'dup1',
            moveClub: async () => ({ success: false })
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, records);
        assert.strictEqual(r.opened, true, '不再提前 return');
        assert.strictEqual(r.failed, true);
        assert.strictEqual(r.moveFail, "club");
        assert.strictEqual(records.length, 3, '三去向记录全落');
        assert.strictEqual(records.find(x => x.definitionId === 'new1').storeLoc, 0, 'club 失败记未分配');
        assert.strictEqual(records.find(x => x.definitionId === 'dup1').storeLoc, 2, 'storage 记录保留');
        assert.strictEqual(records.find(x => x.type === "misc").storeLoc, 4, 'redeem 记录保留');
    });

    // F5: 超时不重试
    await test('F5 openPack 超时 → 不重试（调用=1）、{failed:true}', async () => {
        let n = 0;
        const deps = makeDeps({
            openPack: async () => { n++; return { success: false, error: { code: "timeout" } }; }
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, []);
        assert.strictEqual(n, 1, '超时不重试（防双开）');
        assert.strictEqual(r.failed, true);
        assert.strictEqual(r.reason, "timeout");
    });

    // F6: 入口取消 → 零动作
    await test('F6 入口 isCancelled → {cancelled:true}、零 deps 动作', async () => {
        const deps = makeDeps({ isCancelled: () => true });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, []);
        assert.strictEqual(r.cancelled, true);
        assert.strictEqual(deps._calls.openPack + deps._calls.redeem + deps._calls.moveClub, 0);
    });

    // F7: 失败-失败-成功
    await test('F7 失败-失败-成功 → openPack 调用=3、{opened:true}', async () => {
        let n = 0;
        const deps = makeDeps({
            openPack: async () => {
                n++;
                if (n < 3) return { success: false, error: { code: 500 } };
                return { success: true, response: { items: [] } };
            }
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, []);
        assert.strictEqual(n, 3);
        assert.strictEqual(r.opened, true);
    });

    // F8: sellAll + misc → discard 只收球员、redeem 收 misc
    await test('F8 sellAll 模式：discard 只收到球员，misc 走 redeem（不卖金币）', async () => {
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [
                makeItem('p1', 84),
                makeItem('coins', 0, { type: "misc" }),
                makeItem('p2', 80)
            ] } })
        });
        const r = await openOne({ id: 'p1' }, 0, { sellAll: true }, deps, []);
        assert.strictEqual(r.opened, true);
        assert.strictEqual(deps._calls.discard, 1);
        assert.strictEqual(deps._received.discard[0].length, 2, 'discard 只收球员');
        assert.strictEqual(deps._calls.redeem, 1);
        assert.strictEqual(deps._received.redeem[0].type, "misc");
    });

    // F9: moveClub 失败 + redeem 成功 → 双记录
    await test('F9 moveClub 失败 + redeem 成功 → club(0) 与 redeem(4) 同时落', async () => {
        const records = [];
        const deps = makeDeps({
            openPack: async () => ({ success: true, response: { items: [
                makeItem('new1', 84),
                makeItem('coins', 0, { type: "misc" })
            ] } }),
            moveClub: async () => ({ success: false })
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, records);
        assert.strictEqual(r.opened, true);
        assert.strictEqual(r.failed, true);
        assert.strictEqual(records.filter(x => x.storeLoc === 0).length, 1, 'club 失败记未分配');
        assert.strictEqual(records.filter(x => x.storeLoc === 4).length, 1, 'redeem 成功记已兑换');
    });

    // F10: 打开中途取消（moveClub 前检查点）
    await test('F10 openPack 后取消 → {cancelled:true}、零分配动作', async () => {
        let cancelled = false;
        const deps = makeDeps({
            isCancelled: () => cancelled,
            openPack: async () => { cancelled = true; return { success: true, response: { items: [makeItem('new1', 84)] } }; }
        });
        const r = await openOne({ id: 'p1' }, 0, {}, deps, []);
        assert.strictEqual(r.cancelled, true);
        assert.strictEqual(deps._calls.moveClub, 0, '取消后不执行分配');
    });

    // ===== 结果 =====
    console.log('\n' + '='.repeat(40));
    console.log(`结果: ${passed} 通过, ${failed} 失败, ${passed + failed} 总计`);
    if (failed > 0) process.exit(1);
})().catch((e) => { console.error(e); process.exit(1); });
