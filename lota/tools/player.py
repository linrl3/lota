"""Player search and stats tool."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_player,
    endpoint_opendota_player_wl,
    endpoint_opendota_search,
)
from lota.core.filters import rank_tier_to_str
from lota.core.http import fetch_json


@tool
def search_player(
    query: str,
    limit: int = 5,
) -> str:
    """Search for Dota 2 players by name using OpenDota.

    Args:
        query: Player name to search for (e.g., 'Miracle', 'Arteezy').
        limit: Maximum number of results to show (default: 5).

    Returns:
        A list of matching players with their account IDs.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_search(query),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"No players found matching '{query}'."

    limit_n = max(1, min(20, int(limit)))
    players = data[:limit_n]

    if not players:
        return f"No players found matching '{query}'."

    lines: List[str] = [
        f"Search results for '{query}'",
        "(use account_id with player_stats tool for details)",
        "",
        f"{'Name':<25} {'Account ID':>12}",
        "-" * 40,
    ]

    for p in players:
        name = p.get("personaname", "Unknown")[:25]
        account_id = p.get("account_id", 0)
        lines.append(f"{name:<25} {account_id:>12}")

    return "\n".join(lines)


@tool
def player_stats(
    account_id: int,
    patch: Optional[int] = None,
    hero_id: Optional[int] = None,
    date: Optional[int] = None,
    game_mode: Optional[int] = None,
    lobby_type: Optional[int] = None,
    region: Optional[int] = None,
    lane_role: Optional[int] = None,
) -> str:
    """Get detailed stats for a Dota 2 player by account ID using OpenDota.

    Args:
        account_id: The player's account ID (get from search_player tool).
        patch: Filter by patch ID (from dotaconstants).
        hero_id: Filter by hero ID.
        date: Filter by days previous (e.g., 30 for last 30 days).
        game_mode: Filter by game mode ID (1=All Pick, 2=Captain's Mode, 22=All Draft, 23=Turbo).
        lobby_type: Filter by lobby type ID (0=Normal, 7=Ranked).
        region: Filter by region ID.
        lane_role: Filter by lane role (1=Safe, 2=Mid, 3=Off, 4=Jungle).

    Returns:
        Player profile including rank, win/loss record, and other stats.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    profile_data = fetch_json(
        endpoint_opendota_player(account_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not profile_data or not isinstance(profile_data, dict):
        return f"Player with account_id {account_id} not found."

    from lota.core.filters import PlayerMatchFilters

    filters = PlayerMatchFilters(
        patch=patch,
        hero_id=hero_id,
        date=date,
        game_mode=game_mode,
        lobby_type=lobby_type,
        region=region,
        lane_role=lane_role,
    )

    wl_data = fetch_json(
        endpoint_opendota_player_wl(account_id, filters),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    profile = profile_data.get("profile", {})
    name = profile.get("personaname") or profile.get("name") or "Unknown"
    pro_name = profile.get("name")
    rank_tier = profile_data.get("rank_tier")
    leaderboard_rank = profile_data.get("leaderboard_rank")

    wins = wl_data.get("win", 0) if wl_data else 0
    losses = wl_data.get("lose", 0) if wl_data else 0
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    lines: List[str] = [
        f"Player: {name}",
    ]

    if pro_name and pro_name != name:
        lines.append(f"Pro Name: {pro_name}")

    lines.append(f"Account ID: {account_id}")
    lines.append("")

    rank_str = rank_tier_to_str(rank_tier)
    if leaderboard_rank:
        lines.append(f"Rank: {rank_str} (Leaderboard #{leaderboard_rank})")
    else:
        lines.append(f"Rank: {rank_str}")

    lines.append("")

    filter_parts = []
    if patch:
        filter_parts.append(f"patch={patch}")
    if hero_id:
        filter_parts.append(f"hero_id={hero_id}")
    if date:
        filter_parts.append(f"last {date} days")
    if game_mode:
        filter_parts.append(f"game_mode={game_mode}")
    if lobby_type:
        filter_parts.append(f"lobby_type={lobby_type}")
    if region:
        filter_parts.append(f"region={region}")
    if lane_role:
        filter_parts.append(f"lane_role={lane_role}")

    if filter_parts:
        lines.append(f"Win/Loss Record (filtered: {', '.join(filter_parts)}):")
    else:
        lines.append("Win/Loss Record (from OpenDota):")

    lines.append(f"  Wins: {wins}")
    lines.append(f"  Losses: {losses}")
    lines.append(f"  Total: {total}")
    lines.append(f"  Winrate: {winrate:.1f}%")

    steam_url = profile.get("profileurl")
    if steam_url:
        lines.append("")
        lines.append(f"Steam: {steam_url}")

    return "\n".join(lines)
