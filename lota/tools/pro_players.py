from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_pro_players,
    endpoint_opendota_top_players,
)
from lota.core.http import fetch_json


@tool
def pro_players(
    limit: int = 20,
) -> str:
    """Get a list of professional Dota 2 players from OpenDota.

    Args:
        limit: Number of players to show (default: 20, max: 50).

    Returns:
        A formatted list of professional players with their names, teams, and countries.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(50, int(limit)))

    data = fetch_json(
        endpoint_opendota_pro_players(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch pro players data."

    players = []
    for p in data:
        if not isinstance(p, dict):
            continue
        name = p.get("name") or p.get("personaname") or "Unknown"
        team_name = p.get("team_name") or "No Team"
        country_code = p.get("country_code") or "N/A"
        account_id = p.get("account_id", 0)

        players.append({
            "name": name,
            "team": team_name,
            "country": country_code,
            "account_id": account_id,
        })

    players = players[:limit_n]

    if not players:
        return "No professional players found."

    lines: List[str] = [
        "Professional Dota 2 Players",
        "(from OpenDota)",
        "",
    ]

    for p in players:
        lines.append(f"**{p['name']}** - {p['team']} ({p['country']})")
        lines.append(f"  Account ID: {p['account_id']}")
        lines.append("")

    return "\n".join(lines)


@tool
def top_players(
    limit: int = 20,
    turbo: Optional[bool] = None,
) -> str:
    """Get a list of top-ranked Dota 2 players by MMR from OpenDota.

    Args:
        limit: Number of players to show (default: 20, max: 50).
        turbo: If True, get top turbo mode players. If False or None, get regular ranked players.

    Returns:
        A formatted list of top players with their ranks and MMR.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(50, int(limit)))

    turbo_param = 1 if turbo else None

    data = fetch_json(
        endpoint_opendota_top_players(turbo=turbo_param),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch top players data."

    players = []
    for idx, p in enumerate(data, 1):
        if not isinstance(p, dict):
            continue
        name = p.get("name") or p.get("personaname") or "Unknown"
        account_id = p.get("account_id", 0)
        solo_competitive_rank = p.get("solo_competitive_rank") or "N/A"

        players.append({
            "rank": idx,
            "name": name,
            "account_id": account_id,
            "mmr": solo_competitive_rank,
        })

    players = players[:limit_n]

    if not players:
        return "No top players found."

    mode_str = "Turbo" if turbo else "Ranked"
    lines: List[str] = [
        f"Top {mode_str} Dota 2 Players",
        "(from OpenDota)",
        "",
    ]

    for p in players:
        lines.append(f"#{p['rank']} **{p['name']}** - MMR: {p['mmr']}")
        lines.append(f"  Account ID: {p['account_id']}")
        lines.append("")

    return "\n".join(lines)
