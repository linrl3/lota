from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_team,
    endpoint_opendota_team_heroes,
    endpoint_opendota_team_matches,
    endpoint_opendota_team_players,
    endpoint_opendota_teams,
)
from lota.core.http import fetch_json


@tool
def list_teams(
    page: Optional[int] = None,
) -> str:
    """Get list of professional Dota 2 teams.

    Args:
        page: Page number for pagination (default: None for first page).

    Returns:
        List of teams with their basic information.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_teams(page=page),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return "Could not fetch teams data."

    lines: List[str] = [
        "Professional Dota 2 Teams",
        "",
    ]

    for team in data[:50]:
        team_id = team.get("team_id")
        name = team.get("name") or f"Team {team_id}"
        tag = team.get("tag") or ""
        rating = team.get("rating", 0)
        wins = team.get("wins", 0)
        losses = team.get("losses", 0)
        last_match_time = team.get("last_match_time", 0)

        lines.append(f"**{name}** [{tag}] (ID: {team_id})")
        lines.append(f"  Rating: {rating:.1f}")
        lines.append(f"  Record: {wins}W - {losses}L")
        if last_match_time:
            from datetime import datetime
            last_match = datetime.fromtimestamp(last_match_time)
            lines.append(f"  Last Match: {last_match.strftime('%Y-%m-%d')}")
        lines.append("")

    if not data:
        lines.append("No teams found.")

    if page is not None:
        lines.append(f"Page: {page}")

    return "\n".join(lines)


@tool
def team_info(
    team_id: int,
) -> str:
    """Get detailed information about a specific team.

    Args:
        team_id: The team ID to look up.

    Returns:
        Detailed team information including name, tag, rating, and record.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_team(team_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch data for team {team_id}."

    name = data.get("name") or f"Team {team_id}"
    tag = data.get("tag") or ""
    rating = data.get("rating", 0)
    wins = data.get("wins", 0)
    losses = data.get("losses", 0)
    logo_url = data.get("logo_url") or ""

    lines: List[str] = [
        f"**{name}** [{tag}]",
        f"Team ID: {team_id}",
        f"Rating: {rating:.1f}",
        f"Record: {wins}W - {losses}L",
    ]

    if wins + losses > 0:
        winrate = wins / (wins + losses) * 100
        lines.append(f"Win Rate: {winrate:.1f}%")

    if logo_url:
        lines.append(f"Logo: {logo_url}")

    return "\n".join(lines)


@tool
def team_matches(
    team_id: int,
    limit: int = 20,
) -> str:
    """Get match history for a specific team.

    Args:
        team_id: The team ID to look up.
        limit: Maximum number of matches to show (default: 20).

    Returns:
        List of recent matches for the team.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_team_matches(team_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch matches for team {team_id}."

    lines: List[str] = [
        f"Recent Matches for Team {team_id}",
        "",
    ]

    for match in data[:limit]:
        match_id = match.get("match_id")
        opposing_team_name = match.get("opposing_team_name") or "Unknown"
        radiant = match.get("radiant")
        radiant_win = match.get("radiant_win")
        duration = match.get("duration", 0)
        league_name = match.get("league_name") or ""

        if radiant:
            won = radiant_win
        else:
            won = not radiant_win

        result = "Win" if won else "Loss"
        mins = duration // 60

        lines.append(f"Match {match_id}: vs {opposing_team_name}")
        lines.append(f"  Result: {result} ({mins}min)")
        if league_name:
            lines.append(f"  League: {league_name}")
        lines.append("")

    if not data:
        lines.append("No matches found.")

    return "\n".join(lines)


@tool
def team_players(
    team_id: int,
) -> str:
    """Get current and former players of a team.

    Args:
        team_id: The team ID to look up.

    Returns:
        List of players who have played for the team.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_team_players(team_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch players for team {team_id}."

    lines: List[str] = [
        f"Players for Team {team_id}",
        "",
    ]

    current_players = []
    former_players = []

    for player in data:
        account_id = player.get("account_id")
        name = player.get("name") or f"Player {account_id}"
        games_played = player.get("games_played", 0)
        wins = player.get("wins", 0)
        is_current = player.get("is_current_team_member", False)

        player_info = {
            "account_id": account_id,
            "name": name,
            "games_played": games_played,
            "wins": wins,
        }

        if is_current:
            current_players.append(player_info)
        else:
            former_players.append(player_info)

    if current_players:
        lines.append("**Current Roster:**")
        for p in current_players:
            winrate = (p["wins"] / p["games_played"] * 100) if p["games_played"] > 0 else 0
            lines.append(f"  - {p['name']} (ID: {p['account_id']})")
            lines.append(f"    Games: {p['games_played']}, Win Rate: {winrate:.1f}%")
        lines.append("")

    if former_players:
        lines.append("**Former Players:**")
        for p in sorted(former_players, key=lambda x: x["games_played"], reverse=True)[:10]:
            winrate = (p["wins"] / p["games_played"] * 100) if p["games_played"] > 0 else 0
            lines.append(f"  - {p['name']} (ID: {p['account_id']})")
            lines.append(f"    Games: {p['games_played']}, Win Rate: {winrate:.1f}%")

    if not data:
        lines.append("No players found.")

    return "\n".join(lines)


@tool
def team_heroes(
    team_id: int,
    limit: int = 20,
) -> str:
    """Get most played heroes for a team.

    Args:
        team_id: The team ID to look up.
        limit: Maximum number of heroes to show (default: 20).

    Returns:
        List of heroes most played by the team with statistics.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_team_heroes(team_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return f"Could not fetch heroes for team {team_id}."

    lines: List[str] = [
        f"Most Played Heroes for Team {team_id}",
        "",
    ]

    sorted_heroes = sorted(data, key=lambda x: x.get("games_played", 0), reverse=True)

    for hero in sorted_heroes[:limit]:
        hero_id = hero.get("hero_id")
        localized_name = hero.get("localized_name") or f"Hero {hero_id}"
        games_played = hero.get("games_played", 0)
        wins = hero.get("wins", 0)

        if games_played > 0:
            winrate = wins / games_played * 100
            lines.append(f"**{localized_name}** (ID: {hero_id})")
            lines.append(f"  Games: {games_played}, Wins: {wins}, Win Rate: {winrate:.1f}%")
            lines.append("")

    if not data:
        lines.append("No hero data found.")

    return "\n".join(lines)
