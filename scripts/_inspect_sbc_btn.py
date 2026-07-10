# -*- coding: utf-8 -*-
"""Inspect SBC nav button DOM thoroughly."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

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

info = page.evaluate("""() => {
    var btns = document.querySelectorAll('button');
    var results = [];
    for (var i = 0; i < btns.length; i++) {
        var t = (btns[i].innerText || '').trim();
        if (t.indexOf('SBC') >= 0 && btns[i].offsetParent !== null) {
            var r = btns[i].getBoundingClientRect();
            var parent = btns[i].parentElement;
            var parentTag = parent ? parent.tagName : '?';
            var parentClass = parent ? (parent.className || '').substring(0, 80) : '?';
            results.push({
                index: i,
                text: t,
                tag: btns[i].tagName,
                id: btns[i].id,
                className: (btns[i].className || '').substring(0, 100),
                ariaLabel: btns[i].getAttribute('aria-label'),
                rect: {left: Math.round(r.left), top: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)},
                parentTag: parentTag,
                parentClass: parentClass,
                domPath: btns[i].tagName + (btns[i].id ? '#' + btns[i].id : '') + '.' + ((btns[i].className || '').replace(/ /g, '.').substring(0, 50))
            });
        }
    }

    // Also check all 'SBC' text in body
    var allText = [];
    var els = document.querySelectorAll('*');
    for (var i = 0; i < els.length; i++) {
        if (els[i].children.length === 0 && (els[i].innerText || '').trim() === 'SBC') {
            var r = els[i].getBoundingClientRect();
            if (r.width > 0 && r.height > 0) {
                allText.push({
                    tag: els[i].tagName,
                    id: els[i].id,
                    className: (els[i].className || '').substring(0, 60),
                    rect: {l: Math.round(r.left), t: Math.round(r.top)}
                });
            }
        }
    }
    return {buttons: results, textNodes: allText};
}""")

print("=== Buttons containing 'SBC' ===")
for b in info.get('buttons', []):
    print(f"  index={b['index']} text='{b['text']}' id='{b['id']}' class='{b['className']}'")
    print(f"    arialabel='{b.get('ariaLabel')}' parent={b['parentTag']}.{b['parentClass']}")
    print(f"    rect=({b['rect']['left']},{b['rect']['top']}) {b['rect']['w']}x{b['rect']['h']}")

print("\n=== Leaf text nodes 'SBC' ===")
for t in info.get('textNodes', []):
    print(f"  <{t['tag']}> id='{t['id']}' class='{t['className']}' pos=({t['rect']['l']},{t['rect']['t']})")

# Deep inspect the nav container
print("\n=== Nav sidebar structure ===")
nav_info = page.evaluate("""() => {
    // Try to find the left nav container
    var all = document.querySelectorAll('*');
    var nav = null;
    for (var i = 0; i < all.length; i++) {
        var t = (all[i].innerText || '').trim();
        if (t.indexOf('SBC') >= 0 && t.indexOf('Squad') < 0) {
            var r = all[i].getBoundingClientRect();
            // Left sidebar is roughly x < 150
            if (r.left < 150 && r.width > 30 && r.height > 20) {
                nav = all[i];
                break;
            }
        }
    }
    if (!nav) return 'no nav found';

    var walk = function(el, depth) {
        if (depth > 4) return '';
        var r = el.getBoundingClientRect();
        var parts = [];
        for (var child = el.firstElementChild; child; child = child.nextElementSibling) {
            var cr = child.getBoundingClientRect();
            if (cr.width === 0 || cr.height === 0) continue;
            var txt = (child.innerText || '').trim().substring(0, 20);
            parts.push({
                tag: child.tagName,
                id: child.id,
                cls: (child.className || '').substring(0, 40),
                text: txt,
                rect: {l: Math.round(cr.left), t: Math.round(cr.top), w: Math.round(cr.width), h: Math.round(cr.height)},
                children: walk(child, depth + 1)
            });
        }
        return parts;
    };
    return walk(nav, 0);
}""")
print(f"Nav structure: {json.dumps(nav_info, ensure_ascii=False, indent=2)}")