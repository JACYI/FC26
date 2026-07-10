# -*- coding: utf-8 -*-
"""Squad building algorithm — constraint-based filler for when FSU fails."""
import itertools
import math
from src.sbc.models import Position, RequirementType, PlayerRarity


# Standard formations: position list (11 slots)
# Index order: GK, CB, CB, CB/LB, RB, CDM/CM, CM, CM, LW, RW/RM, ST
# Values are slot->preferred positions priority list
FORMATION_433 = [
    [Position.GK],
    [Position.CB], [Position.CB],
    [Position.LB], [Position.RB],
    [Position.CDM, Position.CM], [Position.CM],
    [Position.CAM, Position.CM],
    [Position.LW], [Position.RW],
    [Position.ST],
]

FORMATION_442 = [
    [Position.GK],
    [Position.CB], [Position.CB],
    [Position.LB], [Position.RB],
    [Position.CM], [Position.CM],
    [Position.LM, Position.LW], [Position.RM, Position.RW],
    [Position.ST], [Position.ST],
]

FORMATION_4231 = [
    [Position.GK],
    [Position.CB], [Position.CB],
    [Position.LB], [Position.RB],
    [Position.CDM], [Position.CDM],
    [Position.CAM], [Position.CAM], [Position.CAM],
    [Position.ST],
]

FORMATION_5212 = [
    [Position.GK],
    [Position.CB], [Position.CB], [Position.CB],
    [Position.LWB, Position.LB], [Position.RWB, Position.RB],
    [Position.CM], [Position.CM], [Position.CAM],
    [Position.ST], [Position.ST],
]

# Default formation
DEFAULT_FORMATION = FORMATION_433


def calculate_squad_rating(players):
    """
    Calculate squad rating using the weighted formula.
    Returns integer rating.
    """
    if not players or len(players) != 11:
        return 0

    ratings = [p.ovr for p in players]
    total = sum(ratings)
    avg = total / 11.0

    excess = sum(max(0, r - avg) for r in ratings)
    adjusted = (total + excess) / 11.0

    return math.floor(adjusted)


def calculate_chemistry(players):
    """
    Calculate chemistry for a squad.
    FC26 chemistry: max 33, players link anywhere on pitch.
    Returns chemistry score (0-33).
    """
    if not players or len(players) != 11:
        return 0

    total_chem = 0
    for player in players:
        chem = 3  # base chemistry for correct position

        # ICON: always 3 chem
        if player.rarity == "icon":
            chem = 3
        # Hero: always 3 chem
        elif player.rarity == "hero":
            chem = 3
        else:
            # Check links with teammates
            same_club_count = sum(1 for p in players if p.club == player.club and p.database_id != player.database_id)
            same_nation_count = sum(1 for p in players if p.nation == player.nation and p.database_id != player.database_id)
            same_league_count = sum(1 for p in players if p.league == player.league and p.database_id != player.database_id)

            if same_club_count >= 6:
                chem = 3
            elif same_club_count >= 3:
                chem = 2
            elif same_club_count >= 1:
                chem = 1
            elif same_nation_count >= 7:
                chem = 3
            elif same_nation_count >= 4:
                chem = 2
            elif same_nation_count >= 1:
                chem = 1
            elif same_league_count >= 7:
                chem = 3
            elif same_league_count >= 4:
                chem = 2
            elif same_league_count >= 2:
                chem = 1
            else:
                chem = 0

        total_chem += chem

    return min(total_chem, 33)


def check_requirements(players, requirements):
    """
    Check if a squad meets all requirements.
    Returns (passed: bool, details: str).
    """
    squad_rating = calculate_squad_rating(players)

    for req in requirements:
        if req.req_type == RequirementType.MIN_OVR:
            if squad_rating < req.value:
                return False, f"Squad rating {squad_rating} < {req.value}"

        elif req.req_type == RequirementType.MIN_CHEM:
            chem = calculate_chemistry(players)
            if chem < req.value:
                return False, f"Chemistry {chem} < {req.value}"

        elif req.req_type == RequirementType.MIN_LEAGUES:
            leagues = set(p.league for p in players if p.league)
            if len(leagues) < req.value:
                return False, f"Leagues {len(leagues)} < {req.value}"

        elif req.req_type == RequirementType.EXACT_LEAGUES:
            leagues = set(p.league for p in players if p.league)
            if len(leagues) != req.value:
                return False, f"Leagues {len(leagues)} != {req.value}"

        elif req.req_type == RequirementType.MIN_NATIONS:
            nations = set(p.nation for p in players if p.nation)
            if len(nations) < req.value:
                return False, f"Nations {len(nations)} < {req.value}"

        elif req.req_type == RequirementType.EXACT_NATIONS:
            nations = set(p.nation for p in players if p.nation)
            if len(nations) != req.value:
                return False, f"Nations {len(nations)} != {req.value}"

        elif req.req_type == RequirementType.MAX_CLUB:
            from collections import Counter
            clubs = Counter(p.club for p in players if p.club)
            if clubs and max(clubs.values()) > req.value:
                return False, f"More than {req.value} from same club"

        elif req.req_type == RequirementType.MIN_GOLD:
            gold_count = sum(1 for p in players if p.ovr >= 75)
            if gold_count < req.value:
                return False, f"Gold players {gold_count} < {req.value}"

    return True, "OK"


def build_squad(players, requirements, formation=None, max_ovr=83,
                excluded_rarities=None):
    """
    Build a squad meeting all requirements from available players.
    Uses greedy approach: 2-3-6 rule for OVR, then adjust for other constraints.

    Args:
        players: list of Player objects
        requirements: list of SBCRequirement
        formation: list of position lists (default: 4-3-3)
        max_ovr: maximum OVR allowed (default 83, per daily upgrade rules)
        excluded_rarities: set of rarities to exclude (default: special/icon/hero)

    Returns:
        list of 11 Player objects, or None if impossible
    """
    if excluded_rarities is None:
        excluded_rarities = {PlayerRarity.SPECIAL, PlayerRarity.ICON, PlayerRarity.HERO}
    formation = formation or DEFAULT_FORMATION
    min_ovr = _get_requirement_value(requirements, RequirementType.MIN_OVR)
    min_chem = _get_requirement_value(requirements, RequirementType.MIN_CHEM)

    # Always filter out special/high-OVR cards before requirement-based filtering
    players = [p for p in players if p.ovr <= max_ovr and p.rarity not in excluded_rarities]

    # Filter players
    usable = _filter_for_requirements(players, requirements)

    if len(usable) < 11:
        return None

    # Sort by OVR ascending (prefer cheap cards)
    usable.sort(key=lambda p: p.ovr)

    # 2-3-6 rule: for target rating N,
    # 2 players at N+1, 3 players at N, 6 players at N-1
    if min_ovr:
        target = min_ovr
        high = target + 1
        mid = target
        low = target - 1

        # Try to find players matching 2-3-6 distribution
        high_pool = [p for p in usable if p.ovr >= high]
        mid_pool = [p for p in usable if mid <= p.ovr < high]
        low_pool = [p for p in usable if low <= p.ovr < mid]

        squad = []
        # Take 2 high
        for p in high_pool[:2]:
            squad.append(p)
            usable.remove(p)
        # Take 3 mid
        for p in mid_pool[:3]:
            squad.append(p)
            usable.remove(p)
        # Take 6 low
        for p in low_pool[:6]:
            squad.append(p)
            usable.remove(p)

        if len(squad) < 11:
            # Fill remaining from usable
            for p in usable[:11 - len(squad)]:
                squad.append(p)
    else:
        # No OVR requirement, just pick lowest 11
        squad = usable[:11]

    # Verify
    passed, msg = check_requirements(squad, requirements)
    if not passed:
        # Try adjusting: swap out low players for higher ones
        squad = _adjust_squad(squad, usable, requirements)

    passed, msg = check_requirements(squad, requirements)
    if not passed:
        return None

    return squad


def _get_requirement_value(requirements, req_type):
    """Get numeric value for a requirement type, or None."""
    for req in requirements:
        if req.req_type == req_type:
            return req.value
    return None


def _filter_for_requirements(players, requirements):
    """Filter players based on hard constraints."""
    result = list(players)

    for req in requirements:
        if req.req_type == RequirementType.EXACT_RARITY:
            result = [p for p in result if p.rarity == req.value]
        elif req.req_type == RequirementType.MIN_RARITY:
            rarity_order = {"bronze": 0, "silver": 1, "gold_common": 2,
                            "gold_rare": 3, "special": 4, "hero": 5, "icon": 6}
            min_level = rarity_order.get(req.value, 0)
            result = [p for p in result if rarity_order.get(p.rarity, 0) >= min_level]

    return result


def _adjust_squad(squad, remaining_pool, requirements):
    """Try to improve squad by swapping low players for higher ones."""
    best = list(squad)
    best_rating = calculate_squad_rating(best)

    for i in range(len(squad)):
        for candidate in remaining_pool:
            test = list(best)
            test[i] = candidate
            passed, _ = check_requirements(test, requirements)
            rating = calculate_squad_rating(test)
            if passed and rating >= best_rating:
                best = test
                best_rating = rating
                if candidate in remaining_pool:
                    remaining_pool.remove(candidate)
                break

    return best
