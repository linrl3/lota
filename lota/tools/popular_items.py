"""Popular items analysis tool."""

from __future__ import annotations

from typing import Dict, List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.constants import ITEM_STAGE_MAP
from lota.core.endpoints import endpoint_opendota_hero_item_popularity
from lota.core.http import fetch_json


def _get_item_names(cache: Cache) -> Dict[int, str]:
    items_data = fetch_json(
        "https://api.opendota.com/api/constants/items",
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )
    item_id_to_name = {}
    if items_data and isinstance(items_data, dict):
        for name, info in items_data.items():
            if isinstance(info, dict) and "id" in info:
                item_id_to_name[info["id"]] = info.get("dname", name)
    return item_id_to_name


@tool
def popular_items(
    limit: int = 20,
    stage: str = "late",
) -> str:
    """Get the most popular items across all heroes based on pro match data.

    This aggregates item popularity data from the most popular heroes to show overall trends.

    Args:
        limit: Number of top items to show (default: 20).
        stage: Game stage - 'start' (0-10min), 'early' (10-25min), 'mid' (25-40min), 'late' (40+min), or 'all' (default: 'late').

    Returns:
        A list of the most popular items with total pick counts across heroes.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    top_hero_ids = [1, 2, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 25]

    item_counts: Dict[int, int] = {}

    stages_to_check = list(ITEM_STAGE_MAP.values()) if stage == "all" else [ITEM_STAGE_MAP.get(stage, "late_game_items")]

    for hero_id in top_hero_ids:
        data = fetch_json(
            endpoint_opendota_hero_item_popularity(hero_id),
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if not data or not isinstance(data, dict):
            continue

        for stage_key in stages_to_check:
            stage_data = data.get(stage_key, {})
            if isinstance(stage_data, dict):
                for item_id_str, count in stage_data.items():
                    try:
                        item_id = int(item_id_str)
                        item_counts[item_id] = item_counts.get(item_id, 0) + int(count)
                    except (ValueError, TypeError):
                        continue

    if not item_counts:
        return "No item data found."

    item_names = _get_item_names(cache)

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    stage_display = stage.replace("_", " ").title() if stage != "all" else "All Stages"
    lines: List[str] = [
        f"Most Popular Items in Pro Matches ({stage_display})",
        f"(aggregated from {len(top_hero_ids)} popular heroes)",
        "",
        f"{'Rank':<5} {'Item':<30} {'Total Picks':>12}",
        "-" * 50,
    ]

    for i, (item_id, count) in enumerate(sorted_items, 1):
        item_name = item_names.get(item_id, f"Item {item_id}")
        lines.append(f"{i:<5} {item_name:<30} {count:>12,}")

    return "\n".join(lines)


@tool
def popular_items_by_role(
    role: str = "carry",
    limit: int = 15,
    stage: str = "late",
) -> str:
    """Get popular items for a specific role based on typical heroes for that role.

    Args:
        role: The role to analyze - 'carry', 'mid', 'offlane', 'support', or 'hard_support' (default: 'carry').
        limit: Number of top items to show (default: 15).
        stage: Game stage - 'start', 'early', 'mid', 'late', or 'all' (default: 'late').

    Returns:
        A list of popular items for the specified role with pick counts.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    role_heroes = {
        "carry": [1, 8, 11, 12, 44, 46, 47, 49, 67, 70, 72, 81],
        "mid": [6, 10, 13, 14, 22, 31, 33, 39, 41, 48, 56, 63],
        "offlane": [2, 3, 7, 15, 18, 19, 23, 26, 28, 38, 52, 57],
        "support": [5, 17, 20, 25, 27, 30, 32, 35, 36, 37, 42, 43],
        "hard_support": [5, 30, 32, 36, 37, 45, 50, 51, 53, 58, 64, 65],
    }

    role_lower = role.lower().replace(" ", "_").replace("-", "_")
    if role_lower not in role_heroes:
        return f"Unknown role '{role}'. Available roles: carry, mid, offlane, support, hard_support"

    hero_ids = role_heroes[role_lower]

    stages_to_check = list(ITEM_STAGE_MAP.values()) if stage == "all" else [ITEM_STAGE_MAP.get(stage, "late_game_items")]

    item_counts: Dict[int, int] = {}

    for hero_id in hero_ids:
        data = fetch_json(
            endpoint_opendota_hero_item_popularity(hero_id),
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if not data or not isinstance(data, dict):
            continue

        for stage_key in stages_to_check:
            stage_data = data.get(stage_key, {})
            if isinstance(stage_data, dict):
                for item_id_str, count in stage_data.items():
                    try:
                        item_id = int(item_id_str)
                        item_counts[item_id] = item_counts.get(item_id, 0) + int(count)
                    except (ValueError, TypeError):
                        continue

    if not item_counts:
        return f"No item data found for {role}."

    item_names = _get_item_names(cache)

    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    role_display = role.replace("_", " ").title()
    stage_display = stage.replace("_", " ").title() if stage != "all" else "All Stages"
    lines: List[str] = [
        f"Popular Items for {role_display} ({stage_display})",
        f"(based on {len(hero_ids)} typical {role_display} heroes in pro matches)",
        "",
        f"{'Rank':<5} {'Item':<30} {'Total Picks':>12}",
        "-" * 50,
    ]

    for i, (item_id, count) in enumerate(sorted_items, 1):
        item_name = item_names.get(item_id, f"Item {item_id}")
        lines.append(f"{i:<5} {item_name:<30} {count:>12,}")

    return "\n".join(lines)
