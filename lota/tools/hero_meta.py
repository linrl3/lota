"""Hero meta statistics tool."""

from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_hero_stats
from lota.core.http import fetch_json


@tool
def hero_meta(
    top: int = 15,
    sort_by: str = "pro_pick",
) -> str:
    """Get hero meta statistics including pro pick/ban rates and public winrates.

    Args:
        top: Number of heroes to show (default: 15).
        sort_by: Sort criteria - 'pro_pick' (most picked in pro), 'pro_ban' (most banned in pro), 'pub_pick' (most picked in pubs), 'pub_winrate' (highest pub winrate) (default: 'pro_pick').

    Returns:
        A formatted table showing hero meta statistics.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_hero_stats(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch hero stats data."

    heroes = []
    for h in data:
        if not isinstance(h, dict):
            continue

        hero_name = h.get("localized_name", "Unknown")
        pro_pick = h.get("pro_pick", 0) or 0
        pro_win = h.get("pro_win", 0) or 0
        pro_ban = h.get("pro_ban", 0) or 0
        pub_pick = h.get("pub_pick", 0) or 0
        pub_win = h.get("pub_win", 0) or 0

        pro_winrate = (pro_win / pro_pick * 100.0) if pro_pick > 0 else 0.0
        pub_winrate = (pub_win / pub_pick * 100.0) if pub_pick > 0 else 0.0

        heroes.append({
            "name": hero_name,
            "pro_pick": pro_pick,
            "pro_win": pro_win,
            "pro_ban": pro_ban,
            "pro_winrate": pro_winrate,
            "pub_pick": pub_pick,
            "pub_win": pub_win,
            "pub_winrate": pub_winrate,
        })

    sort_key = sort_by.lower()
    if sort_key == "pro_ban":
        heroes.sort(key=lambda x: -x["pro_ban"])
        title = "Most Banned Heroes in Pro Scene"
    elif sort_key == "pub_pick":
        heroes.sort(key=lambda x: -x["pub_pick"])
        title = "Most Picked Heroes in Public Matches"
    elif sort_key in ("pub_winrate", "pub_wr", "winrate"):
        heroes = [h for h in heroes if h["pub_pick"] >= 10000]
        heroes.sort(key=lambda x: -x["pub_winrate"])
        title = "Highest Winrate Heroes in Public Matches"
    else:
        heroes.sort(key=lambda x: -x["pro_pick"])
        title = "Most Picked Heroes in Pro Scene"

    top_n = max(1, min(50, int(top)))
    heroes = heroes[:top_n]

    if not heroes:
        return "No hero data found."

    lines: List[str] = [
        title,
        "(from OpenDota)",
        "",
    ]

    if sort_key in ("pub_winrate", "pub_wr", "winrate"):
        lines.append(f"{'Rank':<5} {'Hero':<18} {'Pub Pick':>10} {'Pub WR':>8}")
        lines.append("-" * 45)
        for i, h in enumerate(heroes, 1):
            lines.append(f"{i:<5} {h['name']:<18} {h['pub_pick']:>10} {h['pub_winrate']:>7.1f}%")
    elif sort_key == "pub_pick":
        lines.append(f"{'Rank':<5} {'Hero':<18} {'Pub Pick':>10} {'Pub WR':>8}")
        lines.append("-" * 45)
        for i, h in enumerate(heroes, 1):
            lines.append(f"{i:<5} {h['name']:<18} {h['pub_pick']:>10} {h['pub_winrate']:>7.1f}%")
    else:
        lines.append(f"{'Rank':<5} {'Hero':<18} {'Pro Pick':>9} {'Pro Ban':>9} {'Pro WR':>8}")
        lines.append("-" * 55)
        for i, h in enumerate(heroes, 1):
            wr_str = f"{h['pro_winrate']:.1f}%" if h['pro_pick'] > 0 else "n/a"
            lines.append(f"{i:<5} {h['name']:<18} {h['pro_pick']:>9} {h['pro_ban']:>9} {wr_str:>8}")

    return "\n".join(lines)
