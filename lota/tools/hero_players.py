from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_hero_players
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


@tool
def hero_players(
    hero: str,
    top: int = 20,
    language: str = "english",
) -> str:
    """Get players who play this hero the most.

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        top: Number of players to show (default: 20).
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing top players for this hero.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    data = fetch_json(
        endpoint_opendota_hero_players(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No player data found for {hero_name}."

    top_n = max(1, min(100, int(top)))

    players: List[dict] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        account_id = entry.get("account_id")
        games = entry.get("games_played", 0)
        wins = entry.get("wins", 0)
        if not account_id or games < 1:
            continue
        winrate = (wins / games * 100.0) if games > 0 else 0.0
        players.append({
            "account_id": account_id,
            "games": games,
            "wins": wins,
            "winrate": winrate,
        })

    players.sort(key=lambda x: -x["games"])
    players = players[:top_n]

    if not players:
        return f"No player data found for {hero_name}."

    lines: List[str] = [
        f"Top Players for {hero_name}",
        "(Players with most games on this hero)",
        "",
        f"{'Rank':<5} {'Account ID':<15} {'Games':>8} {'Wins':>8} {'Winrate':>10}",
        "-" * 52,
    ]

    for i, p in enumerate(players, 1):
        wr_display = f"{p['winrate']:.1f}%"
        lines.append(f"{i:<5} {p['account_id']:<15} {p['games']:>8} {p['wins']:>8} {wr_display:>10}")

    lines.append("")
    lines.append("Data from OpenDota public matches")

    return "\n".join(lines)
