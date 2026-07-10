# -*- coding: utf-8 -*-
"""Scan club players and filter by criteria."""
import json
import os
import re
import time
from src.sbc.models import Player, PlayerRarity

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "players.json")


def scan_players(page, use_cache=True):
    """
    Scan Club > Players and extract all visible player cards.
    Returns list of Player objects.
    """
    if use_cache and os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Player(**p) for p in data]

    players = _extract_players_from_page(page)

    # Save cache
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump([p.__dict__ for p in players], f, ensure_ascii=False, indent=2)

    return players


def _extract_players_from_page(page):
    """Parse player cards from the Club > Players page."""
    text = page.inner_text("body")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    players = []

    # Player card pattern:
    # OVR | Position | Name
    # PAC SHO PAS DRI DEF PHY  (outfield)
    # or DIV HAN KIC REF SPD POS (goalkeeper)
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line looks like an OVR number
        if re.match(r'^\d{2}$', line) and i + 1 < len(lines):
            ovr = int(line)
            position = lines[i + 1] if i + 1 < len(lines) else ""

            if position in Player.ALL and i + 2 < len(lines):
                name = lines[i + 2]

                # Check if next lines are stats (PAC SHO PAS ... or DIV HAN ...)
                if i + 3 < len(lines):
                    stat_line = lines[i + 3]
                    if stat_line in ("PAC", "DIV"):
                        # Found a player card
                        rarity = _guess_rarity(ovr, position, name)
                        player = Player(
                            database_id=len(players),
                            name=name,
                            ovr=ovr,
                            position=position,
                            nation="",
                            league="",
                            club="",
                            rarity=rarity,
                            tradeable=True,
                        )
                        players.append(player)
                        i += 7  # skip stat lines
                        continue
        i += 1

    return players


def _guess_rarity(ovr, position, name):
    """Guess player rarity from card data."""
    # Without actual Rarity field from the DOM, fall back to OVR-based guess
    return PlayerRarity.GOLD_COMMON  # placeholder


def navigate_to_club_players(page):
    """Navigate to Club > Players view."""
    page.locator("button:has-text('Club')").first.click(timeout=5000)
    time.sleep(2)

    # Try clicking "Players" / "球员" button
    text = page.inner_text("body")
    for label in ["Players", "球员"]:
        if label in text:
            try:
                page.evaluate('''function(label) {
                    var all = document.querySelectorAll('button, [role="button"]');
                    for (var i = 0; i < all.length; i++) {
                        if ((all[i].innerText || "").indexOf(label) >= 0) {
                            all[i].click(); return true;
                        }
                    }
                    return false;
                }''', label)
                time.sleep(3)
                return True
            except:
                pass
    return False


def filter_players(players, min_ovr=0, max_ovr=99, position=None,
                   rarity=None, league=None, nation=None, exclude_ids=None):
    """Filter player list by criteria."""
    result = players
    if min_ovr:
        result = [p for p in result if p.ovr >= min_ovr]
    if max_ovr < 99:
        result = [p for p in result if p.ovr <= max_ovr]
    if position:
        result = [p for p in result if p.position == position]
    if rarity:
        result = [p for p in result if p.rarity == rarity]
    if league:
        result = [p for p in result if p.league == league]
    if nation:
        result = [p for p in result if p.nation == nation]
    if exclude_ids:
        exclude_set = set(exclude_ids)
        result = [p for p in result if p.database_id not in exclude_set]
    return result
