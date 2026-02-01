"""Player advanced statistics tools."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_player_counts,
    endpoint_opendota_player_rankings,
    endpoint_opendota_player_ratings,
    endpoint_opendota_player_totals,
)
from lota.core.filters import PlayerMatchFilters
from lota.core.http import fetch_json


@tool
def player_totals(
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
    """Get totals in stats for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).
        limit: Maximum number of results to return.
        offset: Number of results to skip for pagination.
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
        sort: Sort field.

    Returns:
        Totals for various stats like kills, deaths, assists, gold, XP, etc.
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
        endpoint_opendota_player_totals(account_id, filters),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No totals data found for account_id {account_id}."

    lines: List[str] = [
        f"Totals for account_id {account_id}",
        "",
        f"{'Field':<25} {'Total':>15} {'Games':>10}",
        "-" * 55,
    ]

    for item in data:
        field = item.get("field", "Unknown")
        total = item.get("sum", 0)
        n = item.get("n", 0)

        if isinstance(total, float):
            lines.append(f"{field:<25} {total:>15.2f} {n:>10}")
        else:
            lines.append(f"{field:<25} {total:>15} {n:>10}")

    return "\n".join(lines)


@tool
def player_counts(
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
    """Get counts in categories for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).
        limit: Maximum number of results to return.
        offset: Number of results to skip for pagination.
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
        sort: Sort field.

    Returns:
        Counts for various categories like leaver_status, game_mode, lobby_type, lane_role, region, patch, etc.
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
        endpoint_opendota_player_counts(account_id, filters),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"No counts data found for account_id {account_id}."

    lines: List[str] = [
        f"Counts for account_id {account_id}",
        "",
    ]

    for category, values in data.items():
        if not values or not isinstance(values, dict):
            continue

        lines.append(f"--- {category} ---")
        lines.append(f"{'Value':<15} {'Games':>10} {'Wins':>10}")

        for key, stats in list(values.items())[:10]:
            games = stats.get("games", 0)
            wins = stats.get("win", 0)
            lines.append(f"{str(key):<15} {games:>10} {wins:>10}")

        lines.append("")

    return "\n".join(lines)


@tool
def player_ratings(
    account_id: int,
) -> str:
    """Get MMR rating history for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).

    Returns:
        Historical MMR ratings including solo and party MMR over time.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_player_ratings(account_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No rating data found for account_id {account_id}."

    if not data:
        return f"No rating history available for account_id {account_id}."

    lines: List[str] = [
        f"Rating history for account_id {account_id}",
        f"Total records: {len(data)}",
        "",
        f"{'Date':<12} {'Solo MMR':>12} {'Party MMR':>12}",
        "-" * 40,
    ]

    for record in data[-20:]:
        time_val = record.get("time", "")
        if time_val:
            date_str = time_val[:10] if len(time_val) >= 10 else time_val
        else:
            date_str = "Unknown"

        solo_mmr = record.get("solo_competitive_rank") or "-"
        party_mmr = record.get("competitive_rank") or "-"

        lines.append(f"{date_str:<12} {str(solo_mmr):>12} {str(party_mmr):>12}")

    if len(data) > 20:
        lines.insert(5, f"(showing last 20 of {len(data)} records)\n")

    return "\n".join(lines)


@tool
def player_rankings(
    account_id: int,
) -> str:
    """Get hero rankings for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).

    Returns:
        Player's ranking percentile for each hero they have played.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_player_rankings(account_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No ranking data found for account_id {account_id}."

    if not data:
        return f"No hero rankings available for account_id {account_id}."

    lines: List[str] = [
        f"Hero rankings for account_id {account_id}",
        f"Total heroes ranked: {len(data)}",
        "",
        f"{'Hero ID':>8} {'Percentile':>12} {'Card':>8}",
        "-" * 35,
    ]

    sorted_data = sorted(data, key=lambda x: x.get("percent_rank", 0), reverse=True)

    for ranking in sorted_data[:30]:
        hero_id_val = ranking.get("hero_id", 0)
        percent_rank = ranking.get("percent_rank", 0)
        card = ranking.get("card", 0)

        percentile = percent_rank * 100

        lines.append(f"{hero_id_val:>8} {percentile:>11.2f}% {card:>8}")

    if len(data) > 30:
        lines.append(f"\n... and {len(data) - 30} more heroes")

    return "\n".join(lines)
