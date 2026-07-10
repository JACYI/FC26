# -*- coding: utf-8 -*-
"""Extract filled player data from club items and static data."""
from playwright.sync_api import sync_playwright
import time
import json

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]

page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True)
try:
    page.wait_for_function('document.body.innerText.indexOf("全部") >= 0', timeout=20000)
except:
    page.locator("button.ut-tab-bar-item.icon-sbc").click(force=True)
    time.sleep(8)
page.locator("text=升级").first.click(force=True)
try:
    page.wait_for_function('document.body.innerText.indexOf("每日青铜升级") >= 0', timeout=15000)
except:
    pass
time.sleep(2)
page.get_by_text("每日青铜升级", exact=False).first.click(force=True)
time.sleep(5)
try:
    page.get_by_text("一键填充(优先重复)", exact=False).first.click(force=True)
except:
    page.locator("button:has-text('一键填充')").first.click(force=True)
time.sleep(5)

data = page.evaluate("""
(() => {
    const results = {};

    const repo = window.services.Item.itemDao.itemRepo;

    // 1. Get club items - extract all items with key fields
    if (repo.club && repo.club.items) {
        const items = repo.club.items;
        results.clubItemCount = items.length;

        // Get key fields from first few items to understand structure
        if (items.length > 0) {
            const allKeys = new Set();
            for (let item of items.slice(0, 50)) {
                for (let k of Object.keys(item)) {
                    allKeys.add(k);
                }
            }
            results.clubItemAllKeys = Array.from(allKeys);

            // Sample items (first 3)
            results.clubItemSamples = [];
            for (let i = 0; i < Math.min(3, items.length); i++) {
                const item = items[i];
                const sample = {};
                for (let k of Array.from(allKeys)) {
                    const v = item[k];
                    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
                        sample[k] = v;
                    } else if (v === null || v === undefined) {
                        sample[k] = null;
                    } else if (Array.isArray(v)) {
                        sample[k] = '[arr:' + v.length + ']';
                    } else if (typeof v === 'object') {
                        const subKeys = Object.keys(v).slice(0, 5);
                        sample[k] = '{' + subKeys.join(',') + '}';
                    }
                }
                results.clubItemSamples.push(sample);
            }

            // Find items with rating 53 (our bronze card) to get rareflag
            const bronzeItems = items.filter(function(it) { return it.rating === 53; });
            results.bronzeItemsCount = bronzeItems.length;
            if (bronzeItems.length > 0) {
                results.bronzeItemSample = {};
                for (let k of Array.from(allKeys)) {
                    const v = bronzeItems[0][k];
                    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
                        results.bronzeItemSample[k] = v;
                    } else if (v === null || v === undefined) {
                        results.bronzeItemSample[k] = null;
                    } else if (Array.isArray(v)) {
                        results.bronzeItemSample[k] = '[arr:' + v.length + ']';
                    } else if (typeof v === 'object') {
                        const subKeys = Object.keys(v).slice(0, 5);
                        results.bronzeItemSample[k] = '{' + subKeys.join(',') + '}';
                    }
                }
            }
        }
    }

    // 2. Get static data for player names
    if (repo.staticData && repo.staticData._collection) {
        const coll = repo.staticData._collection;
        results.staticDataType = typeof coll;
        if (typeof coll === 'object') {
            const keys = Object.keys(coll);
            results.staticDataKeysCount = keys.length;
            results.staticDataFirstKeys = keys.slice(0, 5);
            // Get a sample
            if (keys.length > 0) {
                const firstKey = keys[0];
                const val = coll[firstKey];
                if (typeof val === 'object') {
                    results.staticDataSample = {};
                    for (let k of Object.keys(val).slice(0, 15)) {
                        const v = val[k];
                        if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
                            results.staticDataSample[k] = v;
                        }
                    }
                }
            }
        }
    }

    // 3. Get SBC storage items
    if (repo.storage && repo.storage._collection) {
        const coll = repo.storage._collection;
        if (typeof coll === 'object') {
            const keys = Object.keys(coll);
            results.storageKeysCount = keys.length;
            results.storageFirstKeys = keys.slice(0, 3);
        }
    }

    // 4. NEW: Also check SBC service for current challenge squad data
    const SBC = window.services && window.services.SBC;
    if (SBC) {
        // Check sbcDAO for current challenge data
        if (SBC.sbcDAO) {
            results.sbcDaoKeys = Object.keys(SBC.sbcDAO).slice(0, 15);
        }
        // Check repository
        if (SBC.repository) {
            results.sbcRepositoryKeys = Object.keys(SBC.repository).slice(0, 10);
        }
        // Check itemRepository (FSU-related?)
        if (SBC.itemRepository) {
            results.sbcItemRepoKeys = Object.keys(SBC.itemRepository).slice(0, 10);
        }
    }

    // 5. NEW: Check squad repo for individual squads
    if (window.services.Squad && window.services.Squad.squadDao && window.services.Squad.squadDao.squadRepo) {
        const sqRepo = window.services.Squad.squadDao.squadRepo;
        if (sqRepo.squads) {
            const squads = sqRepo.squads;
            results.squadsType = typeof squads;
            if (typeof squads === 'object' && !Array.isArray(squads)) {
                const squadKeys = Object.keys(squads).slice(0, 10);
                results.squadKeys = squadKeys;
                // Get a squad sample
                if (squadKeys.length > 0) {
                    const sampleSquad = squads[squadKeys[0]];
                    if (sampleSquad) {
                        results.squadSample = {};
                        for (let k of Object.keys(sampleSquad).slice(0, 15)) {
                            const v = sampleSquad[k];
                            if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
                                results.squadSample[k] = v;
                            } else if (Array.isArray(v)) {
                                results.squadSample[k] = '[arr:' + v.length + ']';
                            } else if (typeof v === 'object') {
                                results.squadSample[k] = Object.keys(v).slice(0, 5).join(',');
                            }
                        }
                    }
                }
            }
        }
    }

    return results;
})()
""")

print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
with open("data/bronze_item_service4.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

p.stop()
