from __future__ import annotations

from datetime import datetime
from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_league,
    endpoint_opendota_league_matches,
    endpoint_opendota_league_teams,
    endpoint_opendota_leagues,
)
from lota.core.http import fetch_json


@tool
def list_leagues() -> str:
    """Get list of Dota 2 leagues/tournaments.

    Returns:
        List of leagues with their basic information.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_leagues(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return "Could not fetch leagues data."

    lines: List[str] = [
        "Dota 2 Leagues",
        "",
    ]

    sorted_leagues = sorted(data, key=lambda x: x.get("leagueid", 0), reverse=True)

    for league in sorted_leagues[:50]:
        league_id = league.get("leagueid")
        name = league.get("name") or f"League {league_id}"
        tier = league.get("tier") or "unknown"

        lines.append(f"**{name}** (ID: {league_id})")
        lines.append(f"  Tier: {tier}")
        lines.append("")

    if not data:
        lines.append("No leagues found.")

    return "\n".join(lines)


@tool
def league_info(
    league_id: int,
) -> str:
    """Get detailed information about a specific league.

    Args:
        league_id: The league ID to look up.

    Returns:
        Detailed league information including name, tier, and prize pool.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_league(league_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch data for league {league_id}."

    name = data.get("name") or f"League {league_id}"
    tier = data.get("tier") or "unknown"
    banner = data.get("banner") or ""

    lines: List[str] = [
        f"**{name}**",
        f"League ID: {league_id}",
        f"Tier: {tier}",
    ]

    if banner:
        lines.append(f"Banner: {banner}")

    return "\n".join(lines)


@tool
def league_matches(
    league_id: int,
    limit: int = 20,
) -> str:
    """Get matches from a specific league.

    Args:
        league_id: The league ID to look up.
        limit: Maximum number of matches to show (default: 20).

    Returns:
        List of matches from the league.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_league_matches(league_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch matches for league {league_id}."

    lines: List[str] = [
        f"Matches for League {league_id}",
        "",
    ]

    sorted_matches = sorted(data, key=lambda x: x.get("start_time", 0), reverse=True)

    for match in sorted_matches[:limit]:
        match_id = match.get("match_id")
        radiant_name = match.get("radiant_name") or "Radiant"
        dire_name = match.get("dire_name") or "Dire"
        radiant_win = match.get("radiant_win")
        duration = match.get("duration", 0)
        start_time = match.get("start_time", 0)

        if radiant_win is True:
            result = f"{radiant_name} > {dire_name}"
        elif radiant_win is False:
            result = f"{dire_name} > {radiant_name}"
        else:
            result = f"{radiant_name} vs {dire_name}"

        mins = duration // 60

        lines.append(f"Match {match_id}")
        lines.append(f"  {result} ({mins}min)")
        if start_time:
            match_time = datetime.fromtimestamp(start_time)
            lines.append(f"  Date: {match_time.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

    if not data:
        lines.append("No matches found.")

    return "\n".join(lines)


@tool
def league_teams(
    league_id: int,
) -> str:
    """Get teams participating in a specific league.

    Args:
        league_id: The league ID to look up.

    Returns:
        List of teams in the league with their statistics.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_league_teams(league_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch teams for league {league_id}."

    lines: List[str] = [
        f"Teams in League {league_id}",
        "",
    ]

    sorted_teams = sorted(data, key=lambda x: x.get("wins", 0), reverse=True)

    for team in sorted_teams:
        team_id = team.get("team_id")
        name = team.get("name") or f"Team {team_id}"
        tag = team.get("tag") or ""
        wins = team.get("wins", 0)
        losses = team.get("losses", 0)

        lines.append(f"**{name}** [{tag}] (ID: {team_id})")
        lines.append(f"  Record: {wins}W - {losses}L")
        if wins + losses > 0:
            winrate = wins / (wins + losses) * 100
            lines.append(f"  Win Rate: {winrate:.1f}%")
        lines.append("")

    if not data:
        lines.append("No teams found.")

    return "\n".join(lines)
