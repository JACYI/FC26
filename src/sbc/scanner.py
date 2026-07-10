# -*- coding: utf-8 -*-
"""
Scan SBC pages and parse requirements.
Uses EA view model API for reliable status checking (not text parsing).
"""
import re, json
from src.sbc.models import SBCRequirement, RequirementType


def parse_sbc_requirements(page):
    """
    Parse detailed requirements from the SBC squad builder page text.
    Call after navigating into an SBC set.
    Returns list of SBCRequirement.
    """
    text = page.inner_text("body")
    requirements = []

    patterns = [
        (r'最低(\d+)总评', RequirementType.MIN_OVR),
        (r'最低.*?(\d+)化学', RequirementType.MIN_CHEM),
        (r'至少(\d+)个联赛', RequirementType.MIN_LEAGUES),
        (r'最多(\d+)个联赛', RequirementType.EXACT_LEAGUES),
        (r'至少(\d+)个国籍', RequirementType.MIN_NATIONS),
        (r'最多(\d+)个国籍', RequirementType.EXACT_NATIONS),
        (r'最多(\d+)个同俱乐部', RequirementType.MAX_CLUB),
        (r'至少.*?(\d+)名.*?黄金', RequirementType.MIN_GOLD),
        (r'不超过(\d+)个稀有', RequirementType.MAX_RARITY),
        (r'首发.*?至少(\d+)名.*?稀有', RequirementType.MIN_RARITY),
    ]

    for pattern, req_type in patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            requirements.append(SBCRequirement(req_type, value))

    # Check for position restrictions
    for kw in ["守门员", "后卫", "中场", "前锋", "GK", "DEF", "MID", "FWD"]:
        if kw in text:
            requirements.append(SBCRequirement(RequirementType.POSITION_RESTRICTION, kw))
            break

    return requirements


def get_buttons_text(page):
    """Get all visible button texts as a list."""
    return page.evaluate("""function() {
        var b = document.querySelectorAll('button');
        return Array.from(b).map(function(x) {
            return (x.innerText || '').trim().substring(0, 50);
        }).filter(function(x) { return x; });
    }()""")
