# -*- coding: utf-8 -*-
"""
SBC submission player validator.

Rules (from CLAUDE.md):
  - Bronze: no checks → always pass
  - Silver: if Silver Legend → reject
  - Gold: price > 10000 → reject; OVR > 83 → reject; evolving/evolved → reject
  - Other (Special/ICON/Hero etc.): always reject
"""


def validate_players(players):
    """
    Validate all players against submission rules.
    Returns dict: {valid: bool, results: [player_results], errors: [str]}
    """
    results = []
    errors = []
    all_valid = True

    for pl in players:
        if not pl.get("filled"):
            continue

        result = _validate_single(pl)
        results.append(result)
        if not result["valid"]:
            all_valid = False
            errors.append(f"  [{pl['slot']}] {result['reason']}")

    return {
        "valid": all_valid,
        "results": results,
        "errors": errors,
    }


def _validate_single(pl):
    """Validate a single player. Returns {valid, reason, checks}."""
    ovr = pl.get("ovr", 0)
    rarity = pl.get("rarity", "")
    price = pl.get("price", 0)
    tradeable = pl.get("tradeable", True)
    is_rare = pl.get("is_rare", False)
    is_special = pl.get("is_special", False)
    is_evolution = pl.get("is_evolution", False)
    slot = pl.get("slot", "?")
    position = pl.get("position", "")

    checks = []
    reason = ""

    # Determine tier from OVR (same logic as extraction)
    if ovr >= 40 and ovr <= 64:
        tier = "bronze"
    elif ovr >= 65 and ovr <= 74:
        tier = "silver"
    elif ovr >= 75:
        tier = "gold"
    else:
        tier = "other"

    # Rule: Other rarities → reject
    if tier not in ("bronze", "silver", "gold"):
        checks.append(("稀有度", f"OVR {ovr} 非青铜/白银/黄金范围", False))
        return {
            "valid": False,
            "slot": slot,
            "ovr": ovr,
            "position": position,
            "rarity": rarity,
            "reason": f"非标准稀有度 (OVR={ovr})",
            "checks": checks,
        }

    # Bronze: no checks
    if tier == "bronze":
        checks.append(("青铜", "无检查条件，自动通过", True))
        return {
            "valid": True,
            "slot": slot,
            "ovr": ovr,
            "position": position,
            "rarity": rarity,
            "reason": "",
            "checks": checks,
        }

    # Silver: check for Silver Legend (special card)
    if tier == "silver":
        if is_special or is_rare:
            # Silver Legend = special silver card (rareflag >= 2 or special type)
            checks.append(("白银传奇", f"白银{'稀有' if is_rare else '特殊'}球员，需要确认是否传奇", is_special))
            if is_special:
                return {
                    "valid": False,
                    "slot": slot,
                    "ovr": ovr,
                    "position": position,
                    "rarity": rarity,
                    "reason": "白银传奇/特殊球员，不能提交",
                    "checks": checks,
                }
            # Regular rare silver is OK
            checks.append(("白银稀有", "普通白银稀有，通过", True))
            return {
                "valid": True,
                "slot": slot,
                "ovr": ovr,
                "position": position,
                "rarity": rarity,
                "reason": "",
                "checks": checks,
            }
        checks.append(("白银普通", "普通白银，通过", True))
        return {
            "valid": True,
            "slot": slot,
            "ovr": ovr,
            "position": position,
            "rarity": rarity,
            "reason": "",
            "checks": checks,
        }

    # Gold: multiple checks
    if tier == "gold":
        # Check 1: Price > 10000
        if isinstance(price, str):
            try:
                price_val = int(price.replace(",", ""))
            except:
                price_val = 0
        else:
            price_val = price

        if price_val > 10000:
            checks.append(("身价", f"{price_val} > 10000", False))
            return {
                "valid": False,
                "slot": slot,
                "ovr": ovr,
                "position": position,
                "rarity": rarity,
                "reason": f"身价过高 ({price_val} > 10000)",
                "checks": checks,
            }
        checks.append(("身价", f"{price_val} <= 10000", True))

        # Check 2: OVR > 83
        if ovr > 83:
            checks.append(("OVR", f"{ovr} > 83", False))
            return {
                "valid": False,
                "slot": slot,
                "ovr": ovr,
                "position": position,
                "rarity": rarity,
                "reason": f"OVR过高 ({ovr} > 83)",
                "checks": checks,
            }
        checks.append(("OVR", f"{ovr} <= 83", True))

        # Check 3: Evolution status
        if is_evolution:
            checks.append(("进化", "进化中或已进化", False))
            return {
                "valid": False,
                "slot": slot,
                "ovr": ovr,
                "position": position,
                "rarity": rarity,
                "reason": "进化中/已进化的球员，不能提交",
                "checks": checks,
            }
        checks.append(("进化", "非进化球员", True))

        return {
            "valid": True,
            "slot": slot,
            "ovr": ovr,
            "position": position,
            "rarity": rarity,
            "reason": "",
            "checks": checks,
        }

    # Fallback
    return {
        "valid": False,
        "slot": slot,
        "ovr": ovr,
        "position": position,
        "rarity": rarity,
        "reason": f"未知稀有度 (tier={tier})",
        "checks": checks,
    }


def print_validation(result):
    """Print validation results to console."""
    if result["valid"]:
        print("  [OK] 所有球员检查通过")
    else:
        print("  [FAIL] 球员检查未通过:")
        for err in result["errors"]:
            print(f"     {err}")

    for r in result["results"]:
        status = "[OK]" if r["valid"] else "[FAIL]"
        print(f"  {status} [{r['slot']}] OVR {r['ovr']} {r['position']} | {r['rarity']}")
        for check in r["checks"]:
            ck = "PASS" if check[2] else "FAIL"
            print(f"       {ck} {check[0]}: {check[1]}")
