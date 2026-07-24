# -*- coding: utf-8 -*-
"""Diagnose: what's on the page, and why SBC view model is null."""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def log(msg):
    print(msg)
    sys.stdout.flush()

from src.login import connect, navigate_to_ea, do_login, check_fsu
from src.utils import _js

p, browser, page = connect()
if not page:
    log("Connect failed")
    sys.exit(1)

if "ultimate-team" not in page.url:
    navigate_to_ea(page)

do_login(page)
check_fsu(page)

log("\n=== PAGE STATE (before SBC nav) ===")
log(f"URL: {page.url[:80]}")

# Body text snippet
body = page.inner_text("body")[:1000]
log(f"Body(500): {body[:500]}")

# Check nav buttons
nav_check = _js(page, """function() {
    var btns = document.querySelectorAll('button');
    var results = [];
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if (t && t.length < 30 && btns[i].offsetParent !== null) {
            results.push(t);
        }
    }
    return results;
}()""")
log(f"Visible buttons: {nav_check}")

# Check childViewControllers
vc_check = _js(page, """function() {
    try {
        var app = getAppMain();
        if (!app) return 'getAppMain() null';
        var root = app._rootViewController;
        if (!root) return '_rootViewController null';
        var cc = root.currentController;
        if (!cc) return 'currentController null';
        var cvc = cc.childViewControllers;
        if (!cvc) return 'childViewControllers null';
        var names = [];
        for (var i = 0; i < cvc.length; i++) {
            try {
                var vc = cvc[i];
                var name = vc.__proto__.constructor.name || '?';
                names.push(i + ':' + name);
            } catch(e) {
                names.push(i + ':ERR:' + str(e));
            }
        }
        return names.join(', ');
    } catch(e) {
        return 'ERROR: ' + e.message;
    }
}()""")
log(f"View controllers: {vc_check}")

# Try clicking SBC nav via JS
log("\n=== CLICKING SBC NAV ===")
clicked = _js(page, """function() {
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if (t === 'SBC' && btns[i].offsetParent !== null) {
            btns[i].scrollIntoView({block: 'center'});
            btns[i].click();
            return 'clicked_js';
        }
    }
    return 'SBC_button_not_found';
}()""")
log(f"JS click result: {clicked}")
import time; time.sleep(5)

log("\n=== PAGE STATE (after SBC nav) ===")
body2 = page.inner_text("body")[:500]
log(f"Body(500): {body2}")

# Check VCs again
vc2 = _js(page, """function() {
    try {
        var app = getAppMain();
        var cc = app._rootViewController.currentController;
        var cvc = cc.childViewControllers;
        var names = [];
        for (var i = 0; i < cvc.length; i++) {
            try {
                var vc = cvc[i];
                var ctrl = vc.currentController;
                var ctrlName = ctrl ? (ctrl.__proto__.constructor.name || '?') : 'null';
                names.push(i + ':' + (vc.__proto__.constructor.name || '?') + '/' + ctrlName);
            } catch(e) {
                names.push(i + ':ERR');
            }
        }
        return names.join(', ');
    } catch(e) {
        return 'ERROR: ' + e.message;
    }
}()""")
log(f"View controllers: {vc2}")

# Try accessing SBC viewmodel
sbc_vm = _js(page, """function() {
    try {
        var app = getAppMain();
        var vc = app._rootViewController.currentController.childViewControllers[5];
        if (!vc) return 'vc[5] null';
        var cc = vc.currentController;
        if (!cc) return 'vc[5].currentController null';
        var vm = cc._viewmodel;
        if (!vm) return 'vc[5].currentController._viewmodel null';
        try {
            var cats = vm.getCategories();
            return 'OK, categories: ' + (cats ? cats.length : 0);
        } catch(e) {
            return 'vm.getCategories error: ' + e.message;
        }
    } catch(e) {
        return 'ERROR: ' + e.message;
    }
}()""")
log(f"SBC viewmodel: {sbc_vm}")

log("\nDone. Browser stays open.")
try:
    while browser.is_connected():
        time.sleep(3)
except:
    pass
try:
    p.stop()
except:
    pass
