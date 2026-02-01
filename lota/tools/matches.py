"""Match tools."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_find_matches,
    endpoint_opendota_match,
    endpoint_opendota_request_parse,
)
from lota.core.http import fetch_json
from lota.core.utils import format_duration, format_time_ago


@tool
def match_details(
    match_id: int,
) -> str:
    """Get detailed information about a specific Dota 2 match from OpenDota.

    Args:
        match_id: The match ID to look up.

    Returns:
        Detailed match information including players, heroes, scores, and statistics.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_match(match_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"Failed to fetch match data for match ID {match_id}."

    radiant_score = data.get("radiant_score", 0)
    dire_score = data.get("dire_score", 0)
    radiant_win = data.get("radiant_win", False)
    duration = data.get("duration", 0)
    start_time = data.get("start_time", 0)
    game_mode = data.get("game_mode", 0)
    lobby_type = data.get("lobby_type", 0)

    lines: List[str] = [
        f"Match {match_id} Details",
        "(from OpenDota)",
        "",
        f"**Result**: {'Radiant Victory' if radiant_win else 'Dire Victory'}",
        f"**Score**: Radiant {radiant_score} - {dire_score} Dire",
        f"**Duration**: {format_duration(duration)}",
        f"**Played**: {format_time_ago(start_time)}",
        f"**Game Mode**: {game_mode} | **Lobby Type**: {lobby_type}",
        "",
    ]

    players = data.get("players", [])
    if players:
        radiant_players = [p for p in players if p.get("isRadiant", p.get("player_slot", 0) < 128)]
        dire_players = [p for p in players if not p.get("isRadiant", p.get("player_slot", 0) < 128)]

        lines.append("**Radiant Team**:")
        for p in radiant_players:
            hero_id = p.get("hero_id", 0)
            kills = p.get("kills", 0)
            deaths = p.get("deaths", 0)
            assists = p.get("assists", 0)
            name = p.get("personaname") or "Anonymous"
            lines.append(f"  - {name} (Hero {hero_id}): {kills}/{deaths}/{assists}")

        lines.append("")
        lines.append("**Dire Team**:")
        for p in dire_players:
            hero_id = p.get("hero_id", 0)
            kills = p.get("kills", 0)
            deaths = p.get("deaths", 0)
            assists = p.get("assists", 0)
            name = p.get("personaname") or "Anonymous"
            lines.append(f"  - {name} (Hero {hero_id}): {kills}/{deaths}/{assists}")

    return "\n".join(lines)


@tool
def find_matches(
    team_a: List[Optional[int]] = None,
    team_b: List[Optional[int]] = None,
) -> str:
    """Find matches by hero composition from OpenDota.

    Args:
        team_a: List of hero IDs on team A (up to 5).
        team_b: List of hero IDs on team B (up to 5).

    Returns:
        A list of matches matching the specified hero composition.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    if not team_a and not team_b:
        return "Please specify at least one hero in team_a or team_b."

    data = fetch_json(
        endpoint_opendota_find_matches(team_a=team_a, team_b=team_b),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch matches or no matches found."

    if len(data) == 0:
        return "No matches found with the specified hero composition."

    lines: List[str] = [
        "Matches Found by Hero Composition",
        "(from OpenDota)",
        "",
    ]

    for m in data[:20]:
        if not isinstance(m, dict):
            continue
        match_id = m.get("match_id", 0)
        start_time = m.get("start_time", 0)
        radiant_win = m.get("radiant_win", False)
        avg_mmr = m.get("avg_mmr") or "N/A"

        lines.append(f"Match {match_id}")
        lines.append(f"  Winner: {'Radiant' if radiant_win else 'Dire'} | Avg MMR: {avg_mmr} | {format_time_ago(start_time)}")
        lines.append("")

    return "\n".join(lines)


@tool
def request_parse(
    match_id: int,
) -> str:
    """Request OpenDota to parse a specific match replay.

    Args:
        match_id: The match ID to request parsing for.

    Returns:
        Status of the parse request.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_request_parse(match_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"Failed to request parse for match ID {match_id}."

    job_id = data.get("job", {}).get("jobId")
    if job_id:
        return f"Parse request submitted for match {match_id}. Job ID: {job_id}"

    return f"Parse request submitted for match {match_id}. Response: {data}"
