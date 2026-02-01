"""Player heroes tool."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_player_heroes
from lota.core.filters import PlayerMatchFilters
from lota.core.http import fetch_json


@tool
def player_heroes(
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
    """Get hero pool statistics for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).
        limit: Maximum number of heroes to return.
        offset: Number of heroes to skip for pagination.
        win: Filter by win status (1 for wins, 0 for losses).
        patch: Filter by patch ID.
        game_mode: Filter by game mode ID (e.g., 1=All Pick, 2=Captains Mode, 22=Ranked All Pick).
        lobby_type: Filter by lobby type ID (e.g., 0=Normal, 7=Ranked).
        region: Filter by region ID.
        date: Filter by number of days (matches within last N days).
        lane_role: Filter by lane role (1=Safe, 2=Mid, 3=Off, 4=Jungle).
        hero_id: Filter by specific hero ID.
        is_radiant: Filter by team side (1 for Radiant, 0 for Dire).
        significant: Filter by significant matches (1=significant only, 0=all).
        sort: Sort field (e.g., 'games', 'win', 'last_played').

    Returns:
        A list of heroes with games played, wins, and winrate statistics.
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
        endpoint_opendota_player_heroes(account_id, filters),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No hero data found for account_id {account_id}."

    heroes_with_games = [h for h in data if h.get("games", 0) > 0]

    if not heroes_with_games:
        return f"No hero data found for account_id {account_id} with the given filters."

    lines: List[str] = [
        f"Hero pool statistics for account_id {account_id}",
        f"Total heroes played: {len(heroes_with_games)}",
        "",
        f"{'Hero ID':>8} {'Games':>8} {'Wins':>8} {'Winrate':>10}",
        "-" * 40,
    ]

    for hero in heroes_with_games[:30]:
        hero_id_val = hero.get("hero_id", 0)
        games = hero.get("games", 0)
        wins = hero.get("win", 0)
        winrate = (wins / games * 100) if games > 0 else 0

        lines.append(f"{hero_id_val:>8} {games:>8} {wins:>8} {winrate:>9.1f}%")

    if len(heroes_with_games) > 30:
        lines.append(f"\n... and {len(heroes_with_games) - 30} more heroes")

    return "\n".join(lines)
