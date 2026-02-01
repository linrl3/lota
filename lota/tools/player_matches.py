"""Player matches tool."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_player_matches
from lota.core.filters import PlayerMatchFilters
from lota.core.http import fetch_json


@tool
def player_matches(
    account_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    win: Optional[int] = None,
    patch: Optional[int] = None,
    game_mode: Optional[int] = None,
    lobby_type: Optional[int] = None,
    region: Optional[int] = None,
    date: Optional[int] = None,
    lane_role: Optional[int] = None,
    hero_id: Optional[int] = None,
    is_radiant: Optional[int] = None,
    significant: Optional[int] = None,
    sort: Optional[str] = None,
) -> str:
    """Get match history for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).
        limit: Maximum number of matches to return.
        offset: Number of matches to skip for pagination.
        win: Filter by win status (1 for wins, 0 for losses).
        patch: Filter by patch ID.
        game_mode: Filter by game mode ID (e.g., 1=All Pick, 2=Captains Mode, 22=Ranked All Pick).
        lobby_type: Filter by lobby type ID (e.g., 0=Normal, 7=Ranked).
        region: Filter by region ID.
        date: Filter by number of days (matches within last N days).
        lane_role: Filter by lane role (1=Safe, 2=Mid, 3=Off, 4=Jungle).
        hero_id: Filter by hero ID.
        is_radiant: Filter by team side (1 for Radiant, 0 for Dire).
        significant: Filter by significant matches (1=significant only, 0=all).
        sort: Sort field (e.g., 'match_id', 'duration', 'kills').

    Returns:
        A list of matches with match details including hero, result, KDA, and duration.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    filters = PlayerMatchFilters(
        limit=limit,
        offset=offset,
        win=win,
        patch=patch,
        game_mode=game_mode,
        lobby_type=lobby_type,
        region=region,
        date=date,
        lane_role=lane_role,
        hero_id=hero_id,
        is_radiant=is_radiant,
        significant=significant,
        sort=sort,
    )

    data = fetch_json(
        endpoint_opendota_player_matches(account_id, filters),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No matches found for account_id {account_id}."

    if not data:
        return f"No matches found for account_id {account_id} with the given filters."

    lines: List[str] = [
        f"Match history for account_id {account_id}",
        f"Total matches returned: {len(data)}",
        "",
        f"{'Match ID':<12} {'Hero ID':>8} {'Result':>8} {'K/D/A':>12} {'Duration':>10}",
        "-" * 55,
    ]

    for match in data[:50]:
        match_id = match.get("match_id", 0)
        hero_id_val = match.get("hero_id", 0)
        player_slot = match.get("player_slot", 0)
        radiant_win = match.get("radiant_win", False)

        is_radiant_player = player_slot < 128
        won = (is_radiant_player and radiant_win) or (not is_radiant_player and not radiant_win)
        result = "Win" if won else "Loss"

        kills = match.get("kills", 0)
        deaths = match.get("deaths", 0)
        assists = match.get("assists", 0)
        kda = f"{kills}/{deaths}/{assists}"

        duration_sec = match.get("duration", 0)
        duration_min = duration_sec // 60
        duration_sec_rem = duration_sec % 60
        duration_str = f"{duration_min}:{duration_sec_rem:02d}"

        lines.append(f"{match_id:<12} {hero_id_val:>8} {result:>8} {kda:>12} {duration_str:>10}")

    if len(data) > 50:
        lines.append(f"\n... and {len(data) - 50} more matches")

    return "\n".join(lines)
