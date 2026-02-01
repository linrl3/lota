from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import (
    endpoint_opendota_scenarios_item_timings,
    endpoint_opendota_scenarios_lane_roles,
)
from lota.core.http import fetch_json


@tool
def item_timings(
    item: Optional[str] = None,
    hero_id: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Get item timing win rate analysis from OpenDota scenarios.

    Args:
        item: Item name to filter by (e.g., "bfury", "manta").
        hero_id: Hero ID to filter by.
        limit: Number of results to show (default: 20, max: 50).

    Returns:
        A formatted list of item timing statistics with win rates.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(50, int(limit)))

    data = fetch_json(
        endpoint_opendota_scenarios_item_timings(item=item, hero_id=hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch item timings data."

    timings = []
    for t in data:
        if not isinstance(t, dict):
            continue
        item_name = t.get("item") or "Unknown"
        timing_hero_id = t.get("hero_id", 0)
        time_bucket = t.get("time", 0)
        games = t.get("games", 0)
        wins = t.get("wins", 0)
        win_rate = (wins / games * 100) if games > 0 else 0

        timings.append({
            "item": item_name,
            "hero_id": timing_hero_id,
            "time": time_bucket,
            "games": games,
            "wins": wins,
            "win_rate": win_rate,
        })

    timings = timings[:limit_n]

    if not timings:
        return "No item timing data found."

    filter_info = []
    if item:
        filter_info.append(f"Item: {item}")
    if hero_id:
        filter_info.append(f"Hero ID: {hero_id}")
    filter_str = f" ({', '.join(filter_info)})" if filter_info else ""

    lines: List[str] = [
        f"Item Timing Win Rate Analysis{filter_str}",
        "(from OpenDota)",
        "",
    ]

    for t in timings:
        time_min = t["time"] // 60
        lines.append(f"**{t['item']}** @ {time_min}min - Hero ID: {t['hero_id']}")
        lines.append(f"  Win Rate: {t['win_rate']:.1f}% ({t['wins']}/{t['games']} games)")
        lines.append("")

    return "\n".join(lines)


@tool
def lane_roles(
    lane_role: Optional[str] = None,
    hero_id: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Get lane role win rate analysis from OpenDota scenarios.

    Args:
        lane_role: Lane role to filter by (1=Safe, 2=Mid, 3=Off, 4=Jungle).
        hero_id: Hero ID to filter by.
        limit: Number of results to show (default: 20, max: 50).

    Returns:
        A formatted list of lane role statistics with win rates.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(50, int(limit)))

    data = fetch_json(
        endpoint_opendota_scenarios_lane_roles(lane_role=lane_role, hero_id=hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch lane roles data."

    lane_names = {
        1: "Safe Lane",
        2: "Mid Lane",
        3: "Off Lane",
        4: "Jungle",
    }

    roles = []
    for r in data:
        if not isinstance(r, dict):
            continue
        role_id = r.get("lane_role", 0)
        role_hero_id = r.get("hero_id", 0)
        time_bucket = r.get("time", 0)
        games = r.get("games", 0)
        wins = r.get("wins", 0)
        win_rate = (wins / games * 100) if games > 0 else 0

        roles.append({
            "lane_role": role_id,
            "lane_name": lane_names.get(role_id, f"Role {role_id}"),
            "hero_id": role_hero_id,
            "time": time_bucket,
            "games": games,
            "wins": wins,
            "win_rate": win_rate,
        })

    roles = roles[:limit_n]

    if not roles:
        return "No lane role data found."

    filter_info = []
    if lane_role:
        filter_info.append(f"Lane: {lane_role}")
    if hero_id:
        filter_info.append(f"Hero ID: {hero_id}")
    filter_str = f" ({', '.join(filter_info)})" if filter_info else ""

    lines: List[str] = [
        f"Lane Role Win Rate Analysis{filter_str}",
        "(from OpenDota)",
        "",
    ]

    for r in roles:
        time_min = r["time"] // 60
        lines.append(f"**{r['lane_name']}** @ {time_min}min - Hero ID: {r['hero_id']}")
        lines.append(f"  Win Rate: {r['win_rate']:.1f}% ({r['wins']}/{r['games']} games)")
        lines.append("")

    return "\n".join(lines)
