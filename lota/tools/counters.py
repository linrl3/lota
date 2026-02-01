"""Hero counters/matchups tool."""

from __future__ import annotations

from typing import Dict, List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_hero_matchups, endpoint_opendota_heroes
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


def _load_opendota_hero_map(cache: Cache, timeout: int, user_agent: str) -> Dict[int, str]:
    """Load hero_id -> name mapping from OpenDota API."""
    data = fetch_json(
        endpoint_opendota_heroes(),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
    )
    if not data or not isinstance(data, list):
        return {}
    return {int(h.get("id", 0)): h.get("localized_name", f"Hero#{h.get('id')}") for h in data if h.get("id")}


@tool
def hero_counters(
    hero: str,
    top: int = 10,
    show: str = "counters",
    language: str = "english",
) -> str:
    """Find hero counters or good matchups based on OpenDota public match data.

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        top: Number of results to show (default: 10).
        show: What to show - 'counters' (heroes that beat this hero), 'good' (heroes this hero beats), or 'all' (default: 'counters').
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing hero matchups with winrate data.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    opendota_hero_map = _load_opendota_hero_map(cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)

    data = fetch_json(
        endpoint_opendota_hero_matchups(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No matchup data found for {hero_name}."

    matchups = []
    for m in data:
        if not isinstance(m, dict):
            continue
        enemy_id = m.get("hero_id")
        games = m.get("games_played", 0)
        wins = m.get("wins", 0)
        if games < 10:
            continue
        winrate = (wins / games * 100.0) if games > 0 else 50.0
        enemy_name = opendota_hero_map.get(enemy_id, f"Hero#{enemy_id}")
        matchups.append({
            "hero_id": enemy_id,
            "hero_name": enemy_name,
            "games": games,
            "wins": wins,
            "winrate": winrate,
        })

    show_type = show.lower()
    if show_type in ("counters", "counter", "bad"):
        matchups.sort(key=lambda x: x["winrate"])
        title = f"Heroes that counter {hero_name}"
        subtitle = "(lowest winrate when playing against)"
    elif show_type in ("good", "beats", "strong"):
        matchups.sort(key=lambda x: -x["winrate"])
        title = f"Heroes that {hero_name} beats"
        subtitle = "(highest winrate when playing against)"
    else:
        matchups.sort(key=lambda x: x["winrate"])
        title = f"All matchups for {hero_name}"
        subtitle = "(sorted by winrate)"

    top_n = max(1, min(50, int(top)))
    matchups = matchups[:top_n]

    if not matchups:
        return f"No matchup data found for {hero_name}."

    lines: List[str] = [
        title,
        subtitle,
        "",
        f"{'Rank':<5} {'Enemy Hero':<20} {'Games':>8} {'Winrate':>10}",
        "-" * 48,
    ]

    for i, m in enumerate(matchups, 1):
        wr_display = f"{m['winrate']:.1f}%"
        lines.append(f"{i:<5} {m['hero_name']:<20} {m['games']:>8} {wr_display:>10}")

    lines.append("")
    lines.append("Data from OpenDota public matches")

    return "\n".join(lines)
