# -*- coding: utf-8 -*-
"""Capture current SBC squad builder page state."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ea_structure")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(name, content):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved {name}")

def save_json(name, data):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {name}")

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
page = browser.contexts[0].pages[0]
page.wait_for_load_state("networkidle")
print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Save full page text
body = page.inner_text("body")
save("squad_builder_live.txt", body)

# Capture detailed DOM state
state = page.evaluate("""() => {
    var info = {};
    // FSU elements
    info.fsuCardsTotal = document.querySelectorAll('.fsu-cards').length;
    info.fsuRatingElements = document.querySelectorAll('.fsu-cards-rating').length;
    info.fsuPosElements = document.querySelectorAll('.fsu-cards-pos').length;
    info.fsuPriceElements = document.querySelectorAll('.fsu-PriceBar, .fsu-PriceRightBox').length;
    info.fsuExtraElements = document.querySelectorAll('.fsu-cards-attr, .fsu-player-other').length;

    // FSU rating samples
    var ratings = document.querySelectorAll('.fsu-cards-rating');
    info.ratingSamples = Array.from(ratings).slice(0, 11).map(function(r) {
        return {
            text: r.textContent,
            visible: r.offsetParent !== null,
            style: r.getAttribute('style') || '',
            parentClasses: r.parentElement ? r.parentElement.className.substring(0, 80) : '',
            clickListeners: typeof r.onclick !== 'undefined' ? (r.onclick !== null) : 'unknown'
        };
    });

    // FSU buttons
    var btns = Array.from(document.querySelectorAll('button'));
    info.visibleButtons = btns.filter(function(b) { return b.offsetParent !== null; }).map(function(b) {
        return { text: (b.innerText || '').trim().substring(0, 50), classes: b.className.substring(0, 60) };
    });

    // Check for FSU fill buttons
    info.fsuFillButtons = btns.filter(function(b) {
        var t = (b.innerText || '').trim();
        return t.indexOf('一键') >= 0 || t.indexOf('重复') >= 0 || t.indexOf('补全') >= 0 || t.indexOf('FSU') >= 0;
    }).map(function(b) {
        return { text: (b.innerText || '').trim().substring(0, 50), visible: b.offsetParent !== null };
    });

    // Submit button
    info.submitButton = btns.filter(function(b) {
        return (b.innerText || '').trim() === '提交' || (b.innerText || '').indexOf('Submit') >= 0;
    }).map(function(b) {
        return { text: (b.innerText || '').trim(), visible: b.offsetParent !== null, disabled: b.disabled };
    });

    // Squad slots
    info.squadSlots = document.querySelectorAll('.ut-squad-slot-view').length;
    info.bricks = document.querySelectorAll('[class*="brick"]').length;

    // Toggle switches (ignorepos, league, etc.)
    info.toggles = btns.filter(function(b) {
        return b.className.indexOf('toggle') >= 0 || b.getAttribute('aria-checked') !== null;
    }).map(function(b) {
        return { text: (b.innerText || '').trim().substring(0, 50), checked: b.getAttribute('aria-checked') };
    });

    return info;
}""")
save_json("squad_builder_dom.json", state)
print(f"\n=== Squad Builder State ===")
print(f"  FSU cards: {state['fsuCardsTotal']}, rating elements: {state['fsuRatingElements']}")
print(f"  FSU fill buttons: {len(state['fsuFillButtons'])}")
print(f"  Submit button: {state['submitButton']}")
print(f"  Toggles: {len(state['toggles'])}")

# Check if our mod-01 click handler is on the rating elements
rating_check = page.evaluate("""() => {
    var ratings = document.querySelectorAll('.fsu-cards-rating');
    if (ratings.length === 0) return 'no ratings found';
    var r = ratings[0];
    var info = {
        textContent: r.textContent,
        style: r.getAttribute('style'),
        cursor: r.style.cursor,
        hasClickListener: false,
    };
    // Try to check if there's an event listener (limited in JS)
    var clone = r.cloneNode(true);
    info.hasStyleCursor = clone.style.cursor === 'pointer';
    return info;
}""")
save_json("rating_click_check.json", rating_check)

# Check if we can access events.info.build
events_check = page.evaluate("""() => {
    try {
        if (typeof events !== 'undefined' && events.info) {
            return {
                build: events.info.build,
                hasIgnorePos: events.info.build ? events.info.build.ignorepos : undefined,
                hasSet: typeof events.info.set
            };
        }
        return 'events.info not accessible (closure scope)';
    } catch(e) {
        return 'error: ' + e.message;
    }
}""")
save_json("events_build.json", events_check)

# Capture one player card's full HTML for structure analysis
card_html = page.evaluate("""() => {
    var cards = document.querySelectorAll('.ut-squad-slot-view, .listFUTItem');
    for (var i = 0; i < cards.length; i++) {
        if (cards[i].offsetParent !== null) {
            return cards[i].outerHTML.substring(0, 4000);
        }
    }
    return 'no visible cards';
}""")
save("player_card_full.html", str(card_html))

# Check UTLargePlayerItemView for renderItem
large_view = page.evaluate("""() => {
    var info = {};
    if (typeof UTLargePlayerItemView !== 'undefined') {
        var proto = UTLargePlayerItemView.prototype;
        info.hasOwnRenderItem = proto.hasOwnProperty('renderItem');
        info.renderItemSource = proto.renderItem ? proto.renderItem.toString().substring(0, 300) : 'none';
        // Check if it inherits from UTPlayerItemView
        info.prototypeChain = [];
        var p = proto;
        while (p) {
            var name = p.constructor ? p.constructor.name : 'unknown';
            info.prototypeChain.push(name);
            p = Object.getPrototypeOf(p);
            if (info.prototypeChain.length > 5) break;
        }
    } else {
        info.error = 'UTLargePlayerItemView not found';
    }
    if (typeof UTSmallPlayerItemView !== 'undefined') {
        info.smallHasOwnRenderItem = UTSmallPlayerItemView.prototype.hasOwnProperty('renderItem');
    }
    return info;
}""")
save_json("large_player_view.json", large_view)

p.stop()
print(f"\nAll squad builder data saved to: {OUTPUT_DIR}")
