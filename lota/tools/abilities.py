"""Hero abilities tool."""

from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_hero_data
from lota.core.hero import load_hero_name_to_id
from lota.core.http import fetch_json
from lota.core.utils import norm_for_match, strip_html, suggest_names


@tool
def hero_abilities(
    hero: str,
    language: str = "english",
) -> str:
    """Get the abilities for a specific hero with descriptions.

    Args:
        hero: Hero name to get abilities for (e.g., 'Invoker', 'Anti-Mage').
        language: Language for output - 'english' or 'chinese' (default: 'english').

    Returns:
        A list of the hero's abilities with descriptions, cooldowns, and mana costs.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    name_to_id = load_hero_name_to_id(
        language=language,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    q = norm_for_match(hero)
    hero_id = name_to_id.get(q)
    if hero_id is None:
        sugg = suggest_names(hero, list(name_to_id.keys()), limit=10)
        if sugg:
            return f"Unknown hero: '{hero}'. Did you mean: {', '.join(sugg)}?"
        return f"Unknown hero: '{hero}'. Use list_heroes tool to see available heroes."

    data = fetch_json(
        endpoint_hero_data(hero_id, language),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    heroes = (((data or {}).get("result") or {}).get("data") or {}).get("heroes") or []
    if not heroes:
        return "No data found for hero."

    hero_data = heroes[0]
    hero_name = hero_data.get("name_loc") or hero
    abilities = hero_data.get("abilities", [])

    if not abilities:
        return f"No ability data found for {hero_name}."

    lines: List[str] = [
        f"Abilities for {strip_html(hero_name)}",
        "",
    ]

    for ab in abilities:
        if ab.get("is_item"):
            continue

        name = ab.get("name_loc") or ab.get("name") or "Unknown"
        desc = ab.get("desc_loc") or ""
        cooldowns = ab.get("cooldowns", [])
        mana_costs = ab.get("mana_costs", [])

        name = strip_html(name)
        desc = strip_html(desc)

        if len(desc) > 200:
            desc = desc[:197] + "..."

        lines.append(f"**{name}**")
        if desc:
            lines.append(f"  {desc}")

        info_parts = []
        if cooldowns and any(c > 0 for c in cooldowns):
            cd_str = "/".join(str(int(c)) for c in cooldowns if c > 0)
            info_parts.append(f"CD: {cd_str}s")
        if mana_costs and any(m > 0 for m in mana_costs):
            mana_str = "/".join(str(int(m)) for m in mana_costs if m > 0)
            info_parts.append(f"Mana: {mana_str}")

        if info_parts:
            lines.append(f"  [{' | '.join(info_parts)}]")

        lines.append("")

    talents = hero_data.get("talents", [])
    if talents:
        lines.append("**Talents**")
        for i in range(0, len(talents), 2):
            left = talents[i] if i < len(talents) else None
            right = talents[i+1] if i+1 < len(talents) else None
            level = 10 + (i // 2) * 5
            left_name = strip_html(left.get("name_loc", "")) if left else ""
            right_name = strip_html(right.get("name_loc", "")) if right else ""
            lines.append(f"  Lv{level}: {left_name} | {right_name}")

    return "\n".join(lines)
