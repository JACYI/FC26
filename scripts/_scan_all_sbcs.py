# -*- coding: utf-8 -*-
"""Scan all SBC categories and sets to find real names."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout = open(1, 'w', encoding='utf-8', closefd=False)

from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = None
for ctx in browser.contexts:
    for pg in ctx.pages:
        if "ultimate-team" in pg.url:
            page = pg
            break
    if page:
        break

from src.utils import _js

def get_all_sets():
    return _js(page, """function() {
        try {
            var vm = getAppMain()._rootViewController.currentController
                .childViewControllers[5].currentController._viewmodel;
            var cats = vm.getCategories();
            var result = {};
            for (var ci = 0; ci < cats.length; ci++) {
                try {
                    vm.setCategoryById(cats[ci].id);
                    var sets = vm.getSetsByCurrentCategory();
                    result[cats[ci].name] = [];
                    for (var si = 0; si < sets.length; si++) {
                        var s = sets[si];
                        result[cats[ci].name].push({
                            name: s.name,
                            complete: s.isComplete ? s.isComplete() : '?',
                            repeatsLeft: s.getRepeatsRemaining ? s.getRepeatsRemaining() : '?',
                            timesCompleted: s.timesCompleted || 0,
                            maxRepeats: s.repeats || 0
                        });
                    }
                } catch(e) {
                    result[cats[ci].name] = 'ERROR: ' + e.message;
                }
            }
            return result;
        } catch(e) {
            return {'error': e.message};
        }
    }()""")

# Navigate to SBC first
from src.utils import click_sbc_nav
click_sbc_nav(page)
time.sleep(5)

info = get_all_sets()
print(json.dumps(info, ensure_ascii=False, indent=2))

p.stop()
