# -*- coding: utf-8 -*-
"""Find and click the correct tile parent element."""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.login import connect, navigate_to_ea

p, browser, page = connect()
page.set_viewport_size({"width": 1280, "height": 900})
time.sleep(1)
navigate_to_ea(page)
page.locator("button.ut-tab-bar-item.icon-sbc").first.click(force=True, timeout=5000)
time.sleep(4)
page.evaluate("""function() {
    var btns = document.querySelectorAll('button.ea-filter-bar-item-view');
    for (var i = 0; i < btns.length; i++) {
        if ((btns[i].innerText || '').indexOf('升级') >= 0) btns[i].click();
    }
}()""")
time.sleep(4)

# Find TOTS 制作升级 tile and its clickable parent
info = page.evaluate("""function() {
    var target = 'TOTS 制作升级';
    var all = document.querySelectorAll('[class*="tile"], [class*="Tile"]');
    for (var i = 0; i < all.length; i++) {
        var t = all[i].innerText || '';
        if (t.indexOf(target) >= 0) {
            var cr = all[i].getBoundingClientRect();
            // Get parent chain to find which element has React handlers
            var chain = [];
            var el = all[i];
            while (el && el.tagName !== 'BODY') {
                var hasHandler = el.onclick || el.getAttribute('onclick') || el.getAttribute('__reactProps');
                chain.push({
                    tag: el.tagName,
                    class: (el.className || '').substring(0, 60),
                    hasHandler: !!hasHandler,
                    w: Math.round(el.getBoundingClientRect().width),
                    h: Math.round(el.getBoundingClientRect().height)
                });
                el = el.parentElement;
            }
            return {
                tileTag: all[i].tagName,
                tileClass: (all[i].className || '').substring(0, 80),
                rect: {x: Math.round(cr.x), y: Math.round(cr.y), w: Math.round(cr.width), h: Math.round(cr.height)},
                parentChain: chain
            };
        }
    }
    return 'not found';
}()""")
print("Tile info:")
print(json.dumps(info, indent=2, ensure_ascii=False, default=str))

# If we found the tile, try clicking the outermost container that has React props
if isinstance(info, dict):
    chain = info.get('parentChain', [])
    # Find the tile parent (ut-sbc-set-tile-view)
    for el in reversed(chain):
        if 'tile' in el['class'].lower() and el['w'] > 400:
            print(f"\nFound parent tile: {el['tag']} .{el['class']}")

    # Get the full tile container
    tile_container = page.evaluate("""function() {
        var target = 'TOTS 制作升级';
        var tiles = document.querySelectorAll('.ut-sbc-set-tile-view');
        for (var i = 0; i < tiles.length; i++) {
            if ((tiles[i].innerText || '').indexOf(target) >= 0) {
                var cr = tiles[i].getBoundingClientRect();
                return {
                    cx: Math.round(cr.left + cr.width/2),
                    cy: Math.round(cr.top + cr.height/2),
                    w: Math.round(cr.width),
                    h: Math.round(cr.height),
                    visible: cr.width > 0
                };
            }
        }
        return null;
    }()""")
    print(f"Tile container center: {tile_container}")

    if tile_container:
        # Click via mouse coordinates instead of Playwright
        print("Clicking tile container via mouse.coords...")
        page.mouse.click(tile_container['cx'], tile_container['cy'])
        time.sleep(4)
        body = page.inner_text("body")
        print(f"After click: body={len(body)} chars")
        print(f"  提交={'提交' in body}, 一键填充={'一键填充' in body}")

        if '提交' not in body:
            # Try Playwright force click on tile container
            print("\nTrying Playwright force click on tile container...")
            tile = page.locator('.ut-sbc-set-tile-view').filter(has_text='TOTS 制作升级').first
            bbox = tile.bounding_box()
            print(f"  bbox: {bbox}")
            if bbox:
                tile.click(force=True, timeout=5000)
                time.sleep(4)
                body = page.inner_text("body")
                print(f"After: body={len(body)} chars")
                print(f"  提交={'提交' in body}")
                with open("_after_squad.txt", "w", encoding="utf-8") as f:
                    f.write(body)
