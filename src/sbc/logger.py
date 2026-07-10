# -*- coding: utf-8 -*-
"""Structured SBC submission logger."""
import os
import json
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "log", "sbc_submit")
HIGH_VALUE_THRESHOLD = 1000  # coins - flag players above this


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _today_path():
    """Get today's log file path (JSONL format)."""
    _ensure_dir()
    return os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")


def parse_price(price_str):
    """Parse price string like '2,900' or '200' to int."""
    try:
        return int(price_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def check_high_value(players, threshold=HIGH_VALUE_THRESHOLD):
    """
    Check if any tradeable player has price above threshold.
    Returns list of flagged players.
    """
    flagged = []
    for pl in players:
        if not pl.get("filled"):
            continue
        price = parse_price(pl.get("price", "0"))
        if price > threshold and pl.get("tradeable", True):
            flagged.append({
                "slot": pl.get("slot", "?"),
                "ovr": pl.get("ovr", 0),
                "position": pl.get("position", ""),
                "price": price,
                "rarity": pl.get("rarity", ""),
            })
    return flagged


def log_submission(sbc_name, players, reward="", cost=0, squad_value=0):
    """
    Log an SBC submission to today's log file.
    Returns the log entry dict.
    """
    now = datetime.now()
    entry = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "sbc_name": sbc_name,
        "players": [
            {
                "slot": pl.get("slot", "?"),
                "ovr": pl.get("ovr", 0),
                "position": pl.get("position", ""),
                "rarity": pl.get("rarity", ""),
                "source": pl.get("source", ""),
                "price": parse_price(pl.get("price", "0")),
                "tradeable": pl.get("tradeable", True),
            }
            for pl in players if pl.get("filled")
        ],
        "reward": reward,
        "cost": cost,
        "squad_value": squad_value,
    }

    # Check high-value alerts
    flagged = check_high_value(players)
    entry["high_value_alerts"] = flagged
    entry["has_alert"] = len(flagged) > 0

    # Append to daily JSONL file
    filepath = _today_path()
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def print_submission_summary(entry):
    """Print a human-readable submission summary."""
    print(f"\n{'='*60}")
    print(f"  提交记录 - {entry['sbc_name']}")
    print(f"  时间: {entry['timestamp']}")
    print(f"{'='*60}")
    print(f"  {'槽位':<6} {'OVR':<5} {'位置':<6} {'稀有度':<16} {'来源':<10} {'身价':<8} {'可交易':<6}")
    print(f"  {'-'*55}")
    for pl in entry["players"]:
        trad = "是" if pl["tradeable"] else "否"
        print(f"  {pl['slot']:<6} {pl['ovr']:<5} {pl['position']:<6} {pl['rarity']:<16} {pl['source']:<10} {pl['price']:<8} {trad:<6}")
    print(f"  {'-'*55}")
    print(f"  阵容价值: {entry['squad_value']}")
    print(f"  预估造价: {entry['cost']}")
    print(f"  奖励: {entry['reward']}")
    if entry["has_alert"]:
        print(f"  [WARN] 以下球员身价过高!")
        for flagged in entry["high_value_alerts"]:
            print(f"    - {flagged['slot']} OVR {flagged['ovr']} 身价 {flagged['price']}")
    print(f"{'='*60}\n")
