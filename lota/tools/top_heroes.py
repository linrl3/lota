"""Top heroes by winrate tool."""

from __future__ import annotations

import time
from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.hero import load_hero_map, opendota_top_heroes_by_winrate
from lota.core.patch import load_patch_list
from lota.core.utils import fmt_date


def _find_patch_time_range(patch_list: List[dict], patch_version: str) -> Optional[tuple]:
    """Find the time range for a specific patch version.

    Returns (start_ts, end_ts, patch_name, patch_date) or None if not found.
    """
    patch_version = patch_version.strip().lower()

    for i, p in enumerate(patch_list):
        pname = str(p.get("patch_number") or p.get("patch_name") or "").strip()
        if pname.lower() == patch_version or pname.lower().startswith(patch_version):
            start_ts = int(p.get("patch_timestamp") or 0)
            if i + 1 < len(patch_list):
                end_ts = int(patch_list[i + 1].get("patch_timestamp") or 0)
            else:
                end_ts = int(time.time())
            return start_ts, end_ts, pname, fmt_date(start_ts)

    return None


@tool
def top_heroes_by_winrate(
    top: int = 10,
    order: str = "highest",
    patch: Optional[str] = None,
    min_games: int = 1000,
    language: str = "english",
) -> str:
    """Get top heroes ranked by winrate in a specific patch using OpenDota data.

    Args:
        top: Number of heroes to return (default: 10).
        order: 'highest' for best winrate, 'lowest' for worst winrate (default: 'highest').
        patch: Patch version to analyze (e.g., '7.40', '7.39b'). If not specified, uses current patch.
        min_games: Minimum games threshold to filter out low-sample heroes (default: 1000).
        language: Language for hero names - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing top heroes by winrate.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_map = load_hero_map(
        language=language,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    patch_list = load_patch_list(
        language="english",
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )
    if not patch_list:
        return "Failed to load patch list."

    if patch:
        result = _find_patch_time_range(patch_list, patch)
        if result is None:
            available = [str(p.get("patch_number") or p.get("patch_name") or "") for p in patch_list[-10:]]
            return f"Patch '{patch}' not found. Recent patches: {', '.join(available)}"
        start_ts, end_ts, patch_name, patch_date = result
        is_current = (end_ts >= int(time.time()) - 3600)
    else:
        current_patch = patch_list[-1]
        patch_name = str(current_patch.get("patch_number") or current_patch.get("patch_name") or "?").strip()
        start_ts = int(current_patch.get("patch_timestamp") or 0)
        end_ts = int(time.time())
        patch_date = fmt_date(start_ts)
        is_current = True

    order_type = "desc" if order.lower() in ("highest", "best", "top", "desc") else "asc"

    heroes = opendota_top_heroes_by_winrate(
        start_ts,
        end_ts,
        limit=max(1, min(50, int(top))),
        min_games=max(100, int(min_games)),
        order=order_type,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not heroes:
        return f"No hero data found for patch {patch_name}. Try lowering min_games threshold."

    order_label = "Highest" if order_type == "desc" else "Lowest"
    date_range = f"{patch_date} - now" if is_current else f"{patch_date} - {fmt_date(end_ts)}"
    lines: List[str] = [
        f"Patch: {patch_name} ({date_range})",
        f"{order_label} Winrate Heroes (min {min_games} games, from OpenDota)",
        "",
        f"{'Rank':<5} {'Hero':<20} {'Games':>10} {'Winrate':>10}",
        "-" * 50,
    ]

    for i, h in enumerate(heroes, 1):
        hero_id = h["hero_id"]
        hero_name = hero_map.get(hero_id, f"Hero#{hero_id}")
        games = h["games"]
        winrate = h["winrate"]
        lines.append(f"{i:<5} {hero_name:<20} {games:>10} {winrate:>9.2f}%")

    return "\n".join(lines)
