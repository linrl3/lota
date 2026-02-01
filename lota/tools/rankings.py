"""Hero rankings tool."""

from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_rankings
from lota.core.filters import rank_tier_to_str
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


@tool
def hero_rankings(
    hero: str,
    top: int = 20,
    language: str = "english",
) -> str:
    """Get top players for a specific hero.

    Args:
        hero: Hero name to look up (e.g., 'Invoker', 'Anti-Mage').
        top: Number of top players to show (default: 20, max: 100).
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing top players for the hero.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    data = fetch_json(
        endpoint_opendota_rankings(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"No ranking data found for {hero_name}."

    rankings = data.get("rankings", [])
    if not rankings:
        return f"No ranking data found for {hero_name}."

    top_n = max(1, min(50, int(top)))
    rankings = rankings[:top_n]

    lines: List[str] = [
        f"Top {hero_name} Players",
        "(from OpenDota rankings)",
        "",
        f"{'Rank':<5} {'Player':<22} {'Score':>10} {'Medal':>6}",
        "-" * 48,
    ]

    for i, r in enumerate(rankings, 1):
        name = (r.get("personaname") or r.get("name") or "Unknown")[:22]
        score = r.get("score", 0)
        rank_tier = r.get("rank_tier")
        medal = rank_tier_to_str(rank_tier)
        lines.append(f"{i:<5} {name:<22} {score:>10.1f} {medal:>6}")

    return "\n".join(lines)
