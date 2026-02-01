from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.constants import ITEM_STAGE_DISPLAY, ITEM_STAGE_MAP
from lota.core.endpoints import endpoint_opendota_hero_item_popularity
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


@tool
def hero_item_popularity(
    hero: str,
    top: int = 10,
    stage: str = "all",
    language: str = "english",
) -> str:
    """Get hero item popularity data from professional matches.

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        top: Number of items to show per stage (default: 10).
        stage: Item stage to show - 'start' (starting items), 'early' (early game), 'mid' (mid game), 'late' (late game), or 'all' (default: 'all').
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing item popularity data.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    data = fetch_json(
        endpoint_opendota_hero_item_popularity(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"No item popularity data found for {hero_name}."

    stages_to_show: List[str] = []
    if stage.lower() == "all":
        stages_to_show = list(ITEM_STAGE_MAP.values())
    else:
        stage_key = ITEM_STAGE_MAP.get(stage.lower())
        if stage_key:
            stages_to_show = [stage_key]
        else:
            return f"Unknown stage: '{stage}'. Valid stages: start, early, mid, late, all."

    lines: List[str] = [
        f"Item Popularity for {hero_name}",
        "(Professional match data)",
        "",
    ]

    top_n = max(1, min(50, int(top)))

    for stage_key in stages_to_show:
        stage_data = data.get(stage_key)
        if not stage_data or not isinstance(stage_data, dict):
            continue

        items: List[dict] = []
        for item_name, count in stage_data.items():
            if isinstance(count, (int, float)) and count > 0:
                items.append({"item": item_name, "count": int(count)})

        items.sort(key=lambda x: -x["count"])
        items = items[:top_n]

        if items:
            lines.append(f"=== {ITEM_STAGE_DISPLAY.get(stage_key, stage_key)} ===")
            lines.append(f"{'Rank':<5} {'Item':<30} {'Count':>8}")
            lines.append("-" * 48)

            for i, item in enumerate(items, 1):
                lines.append(f"{i:<5} {item['item']:<30} {item['count']:>8}")

            lines.append("")

    if len(lines) <= 3:
        return f"No item popularity data found for {hero_name}."

    lines.append("Data from OpenDota professional matches")

    return "\n".join(lines)
