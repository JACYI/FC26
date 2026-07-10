# -*- coding: utf-8 -*-
"""Data models for SBC automation."""


class PlayerRarity:
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD_COMMON = "gold_common"
    GOLD_RARE = "gold_rare"
    SPECIAL = "special"
    ICON = "icon"
    HERO = "hero"


class RequirementType:
    MIN_OVR = "min_ovr"
    EXACT_OVR = "exact_ovr"
    MIN_CHEM = "min_chem"
    EXACT_RARITY = "exact_rarity"
    MIN_RARITY = "min_rarity"
    MIN_LEAGUES = "min_leagues"
    EXACT_LEAGUES = "exact_leagues"
    MIN_NATIONS = "min_nations"
    EXACT_NATIONS = "exact_nations"
    MAX_CLUB = "max_club"
    MIN_CLUB = "min_club"
    POSITION_RESTRICTION = "position_restriction"
    MIN_GOLD = "min_gold"
    MAX_RARITY = "max_rarity"  # e.g. "Max 4 Rare"
    SPECIAL_COUNT = "special_count"


class Position:
    GK = "GK"
    CB = "CB"
    LB = "LB"
    RB = "RB"
    LWB = "LWB"
    RWB = "RWB"
    CDM = "CDM"
    CM = "CM"
    CAM = "CAM"
    LM = "LM"
    RM = "RM"
    LW = "LW"
    RW = "RW"
    CF = "CF"
    ST = "ST"

    ALL_OUTFIELD = [CB, LB, RB, LWB, RWB, CDM, CM, CAM, LM, RM, LW, RW, CF, ST]
    ALL = [GK] + ALL_OUTFIELD


class Player:
    """A player card in the club."""

    def __init__(self, database_id, name, ovr, position, nation, league, club,
                 rarity, tradeable=True, price=0, duplicate_id=None):
        self.database_id = database_id
        self.name = name
        self.ovr = ovr
        self.position = position
        self.nation = nation
        self.league = league
        self.club = club
        self.rarity = rarity
        self.tradeable = tradeable
        self.price = price
        self.duplicate_id = duplicate_id

    def __repr__(self):
        return f"[{self.ovr}] {self.name} ({self.position}, {self.league})"


class SBCRequirement:
    """A single requirement for an SBC segment."""

    def __init__(self, req_type, value, operator="gte"):
        self.req_type = req_type
        self.value = value
        self.operator = operator  # gte, lte, eq, exact

    def __repr__(self):
        return f"{self.req_type} {self.operator} {self.value}"


class SBCSegment:
    """One segment of an SBC group (one squad to submit)."""

    def __init__(self, segment_id, name, requirements=None, is_completed=False):
        self.segment_id = segment_id
        self.name = name
        self.requirements = requirements or []
        self.is_completed = is_completed

    def __repr__(self):
        return f"Segment {self.segment_id}: {len(self.requirements)} reqs, {'done' if self.is_completed else 'pending'}"


class SBC:
    """An SBC challenge group (may contain multiple segments)."""

    def __init__(self, name, tab="All", segments=None, is_repeatable=False,
                 max_repeats=1, expires_in="", progress="0/1"):
        self.name = name
        self.tab = tab
        self.segments = segments or []
        self.is_repeatable = is_repeatable
        self.max_repeats = max_repeats
        self.expires_in = expires_in
        self.progress = progress

    @property
    def is_completed(self):
        return all(s.is_completed for s in self.segments)

    @property
    def total_segments(self):
        return len(self.segments)

    @property
    def completed_segments(self):
        return sum(1 for s in self.segments if s.is_completed)

    def __repr__(self):
        status = "DONE" if self.is_completed else f"{self.completed_segments}/{self.total_segments}"
        return f"[{status}] {self.name} ({self.tab})"


def guess_rarity_from_ovr(ovr):
    """Guess player rarity from OVR."""
    if ovr <= 64:
        return PlayerRarity.BRONZE
    elif ovr <= 74:
        return PlayerRarity.SILVER
    else:
        return PlayerRarity.GOLD_COMMON
