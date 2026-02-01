"""Live matches tool."""

from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_live
from lota.core.http import fetch_json
from lota.core.utils import format_duration


@tool
def live_matches(
    limit: int = 10,
) -> str:
    """Get currently live high-ranked Dota 2 matches from OpenDota.

    Args:
        limit: Number of live matches to show (default: 10, max: 30).

    Returns:
        A formatted list of live matches with players, heroes, and game state.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(30, int(limit)))

    data = fetch_json(
        endpoint_opendota_live(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch live matches data."

    matches = data[:limit_n]

    if not matches:
        return "No live matches currently available."

    lines: List[str] = [
        "Live High-Ranked Matches",
        "(from OpenDota)",
        "",
    ]

    for m in matches:
        if not isinstance(m, dict):
            continue

        match_id = m.get("match_id", 0)
        radiant_score = m.get("radiant_score", 0)
        dire_score = m.get("dire_score", 0)
        game_time = m.get("game_time", 0)
        average_mmr = m.get("average_mmr") or "N/A"
        spectators = m.get("spectators", 0)

        lines.append(f"Match {match_id}")
        lines.append(f"  Score: Radiant {radiant_score} - {dire_score} Dire")
        lines.append(f"  Game Time: {format_duration(game_time)} | Avg MMR: {average_mmr} | Spectators: {spectators}")

        players = m.get("players", [])
        if players:
            radiant_players = [p for p in players if p.get("team") == 0 or p.get("is_radiant")]
            dire_players = [p for p in players if p.get("team") == 1 or not p.get("is_radiant")]

            if radiant_players:
                radiant_names = [p.get("name") or p.get("personaname") or "Unknown" for p in radiant_players[:5]]
                lines.append(f"  Radiant: {', '.join(radiant_names)}")

            if dire_players:
                dire_names = [p.get("name") or p.get("personaname") or "Unknown" for p in dire_players[:5]]
                lines.append(f"  Dire: {', '.join(dire_names)}")

        lines.append("")

    return "\n".join(lines)
