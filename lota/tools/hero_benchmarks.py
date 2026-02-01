from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_benchmarks
from lota.core.http import fetch_json
from lota.core.utils import resolve_hero


@tool
def hero_benchmarks(
    hero: str,
    language: str = "english",
) -> str:
    """Get hero benchmark data showing percentile statistics (GPM, XPM, kills, etc.).

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing benchmark percentile data for the hero.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(
        hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
    )
    if error:
        return error

    data = fetch_json(
        endpoint_opendota_benchmarks(hero_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return f"No benchmark data found for {hero_name}."

    result = data.get("result")
    if not result or not isinstance(result, dict):
        return f"No benchmark data found for {hero_name}."

    lines: List[str] = [
        f"Benchmarks for {hero_name}",
        "(Percentile statistics from public matches)",
        "",
    ]

    stat_display = {
        "gold_per_min": "GPM (Gold Per Minute)",
        "xp_per_min": "XPM (XP Per Minute)",
        "kills_per_min": "Kills Per Minute",
        "last_hits_per_min": "Last Hits Per Minute",
        "hero_damage_per_min": "Hero Damage Per Minute",
        "hero_healing_per_min": "Hero Healing Per Minute",
        "tower_damage": "Tower Damage",
        "stuns_per_min": "Stuns Per Minute",
        "lhten": "Last Hits at 10 min",
    }

    for stat_key, stat_name in stat_display.items():
        stat_data = result.get(stat_key)
        if not stat_data or not isinstance(stat_data, list):
            continue

        lines.append(f"=== {stat_name} ===")
        lines.append(f"{'Percentile':<12} {'Value':>12}")
        lines.append("-" * 28)

        for entry in stat_data:
            if not isinstance(entry, dict):
                continue
            pct = entry.get("percentile")
            val = entry.get("value")
            if pct is None or val is None:
                continue
            pct_str = f"{float(pct) * 100:.0f}%"
            if isinstance(val, float):
                val_str = f"{val:.2f}"
            else:
                val_str = str(val)
            lines.append(f"{pct_str:<12} {val_str:>12}")

        lines.append("")

    if len(lines) <= 3:
        return f"No benchmark data found for {hero_name}."

    lines.append("Data from OpenDota public matches")

    return "\n".join(lines)
