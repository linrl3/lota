from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_hero_durations
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


@tool
def hero_durations(
    hero: str,
    language: str = "english",
) -> str:
    """Get hero performance data across different match durations.

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing hero winrate at different match durations.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    data = fetch_json(
        endpoint_opendota_hero_durations(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No duration data found for {hero_name}."

    durations: List[dict] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        duration_bin = entry.get("duration_bin")
        games = entry.get("games_played", 0)
        wins = entry.get("wins", 0)
        if duration_bin is None or games < 1:
            continue
        winrate = (wins / games * 100.0) if games > 0 else 0.0
        durations.append({
            "duration_bin": duration_bin,
            "games": games,
            "wins": wins,
            "winrate": winrate,
        })

    durations.sort(key=lambda x: x["duration_bin"])

    if not durations:
        return f"No duration data found for {hero_name}."

    def format_duration_bin(seconds: int) -> str:
        minutes = seconds // 60
        return f"{minutes} min"

    lines: List[str] = [
        f"Match Duration Performance for {hero_name}",
        "(Winrate at different game lengths)",
        "",
        f"{'Duration':<15} {'Games':>10} {'Wins':>10} {'Winrate':>10}",
        "-" * 50,
    ]

    for d in durations:
        dur_display = format_duration_bin(d["duration_bin"])
        wr_display = f"{d['winrate']:.1f}%"
        lines.append(f"{dur_display:<15} {d['games']:>10} {d['wins']:>10} {wr_display:>10}")

    lines.append("")
    lines.append("Data from OpenDota public matches")

    return "\n".join(lines)
