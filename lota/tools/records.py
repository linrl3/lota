from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_records
from lota.core.http import fetch_json
from lota.core.utils import format_duration


@tool
def game_records(
    field: str = "kills",
    limit: int = 10,
) -> str:
    """Get game records from OpenDota (highest kills, longest match, etc.).

    Args:
        field: The record field to query. Options include:
            - kills: Most kills in a game
            - deaths: Most deaths in a game
            - assists: Most assists in a game
            - gold_per_min: Highest GPM
            - xp_per_min: Highest XPM
            - last_hits: Most last hits
            - denies: Most denies
            - hero_damage: Most hero damage
            - tower_damage: Most tower damage
            - hero_healing: Most hero healing
            - duration: Longest match duration
        limit: Number of records to show (default: 10, max: 20).

    Returns:
        A formatted list of game records for the specified field.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(20, int(limit)))

    valid_fields = [
        "kills", "deaths", "assists", "gold_per_min", "xp_per_min",
        "last_hits", "denies", "hero_damage", "tower_damage",
        "hero_healing", "duration",
    ]

    if field not in valid_fields:
        return f"Invalid field '{field}'. Valid options: {', '.join(valid_fields)}"

    data = fetch_json(
        endpoint_opendota_records(field),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return f"Failed to fetch records for '{field}'."

    records = []
    for idx, r in enumerate(data, 1):
        if not isinstance(r, dict):
            continue
        match_id = r.get("match_id", 0)
        value = r.get(field, 0)
        hero_id = r.get("hero_id", 0)
        start_time = r.get("start_time", 0)

        records.append({
            "rank": idx,
            "match_id": match_id,
            "value": value,
            "hero_id": hero_id,
            "start_time": start_time,
        })

    records = records[:limit_n]

    if not records:
        return f"No records found for '{field}'."

    field_display = field.replace("_", " ").title()

    lines: List[str] = [
        f"Game Records: {field_display}",
        "(from OpenDota)",
        "",
    ]

    for r in records:
        if field == "duration":
            value_str = format_duration(r["value"])
        else:
            value_str = f"{r['value']:,}"

        lines.append(f"#{r['rank']} **{value_str}** - Hero ID: {r['hero_id']}")
        lines.append(f"  Match ID: {r['match_id']}")
        lines.append("")

    return "\n".join(lines)
