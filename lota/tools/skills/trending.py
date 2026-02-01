"""Trending heroes analysis skill - combines multiple hero data sources."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_hero_stats
from lota.core.hero import load_hero_map, opendota_top_heroes_by_winrate
from lota.core.http import fetch_json
from lota.core.patch import load_patch_list
from lota.core.utils import fmt_date

RANK_BRACKETS: Dict[str, int] = {
    "herald": 1,
    "guardian": 2,
    "crusader": 3,
    "archon": 4,
    "legend": 5,
    "ancient": 6,
    "divine": 7,
    "immortal": 7,
}

RANK_NAMES: Dict[int, str] = {
    1: "Herald",
    2: "Guardian",
    3: "Crusader",
    4: "Archon",
    5: "Legend",
    6: "Ancient",
    7: "Divine/Immortal",
}

ROLE_ALIASES: Dict[str, str] = {
    "carry": "Carry",
    "core": "Carry",
    "pos1": "Carry",
    "safelane": "Carry",
    "support": "Support",
    "sup": "Support",
    "pos4": "Support",
    "pos5": "Support",
    "mid": "Nuker",
    "midlane": "Nuker",
    "pos2": "Nuker",
    "nuker": "Nuker",
    "offlane": "Initiator",
    "off": "Initiator",
    "pos3": "Initiator",
    "initiator": "Initiator",
    "disabler": "Disabler",
    "durable": "Durable",
    "tank": "Durable",
    "escape": "Escape",
    "pusher": "Pusher",
}

ROLE_DISPLAY_NAMES: Dict[str, str] = {
    "Carry": "Carry (Pos 1)",
    "Support": "Support (Pos 4/5)",
    "Nuker": "Mid/Nuker (Pos 2)",
    "Initiator": "Offlane/Initiator (Pos 3)",
    "Disabler": "Disabler",
    "Durable": "Durable/Tank",
    "Escape": "Escape",
    "Pusher": "Pusher",
}


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _parse_rank(rank_str: Optional[str]) -> Optional[int]:
    if not rank_str:
        return None
    rank_lower = rank_str.strip().lower()
    if rank_lower in RANK_BRACKETS:
        return RANK_BRACKETS[rank_lower]
    try:
        rank_num = int(rank_lower)
        if 1 <= rank_num <= 8:
            return rank_num
    except ValueError:
        pass
    return None


def _parse_role(role_str: Optional[str]) -> Optional[str]:
    if not role_str:
        return None
    role_lower = role_str.strip().lower()
    return ROLE_ALIASES.get(role_lower)


def _hero_has_role(hero_roles: List[str], target_role: str) -> bool:
    if not hero_roles:
        return False
    return target_role in hero_roles


@tool
def trending_heroes_analysis(
    scope: str = "all",
    rank: Optional[str] = None,
    role: Optional[str] = None,
    top: int = 10,
    language: str = "english",
) -> str:
    """Analyze trending heroes in current meta, combining pro scene and pub data.

    This is a composite skill that provides a comprehensive view of the current meta by combining:
    - Pro scene most picked heroes
    - Pro scene most banned heroes
    - Current patch highest winrate heroes
    - Public matches most popular heroes (can be filtered by rank and role)

    Args:
        scope: Analysis scope - 'all' (everything), 'pro' (pro scene only), 'pub' (public matches only). Default: 'all'.
        rank: Filter by rank bracket for pub data - 'herald', 'guardian', 'crusader', 'archon', 'legend', 'ancient', 'divine', 'immortal' (divine and immortal are combined), or number 1-7. Default: None (all ranks combined).
        role: Filter by hero role - 'carry'/'pos1', 'support'/'pos4'/'pos5', 'mid'/'pos2'/'nuker', 'offlane'/'pos3'/'initiator', 'disabler', 'durable'/'tank', 'escape', 'pusher'. Default: None (all roles).
        top: Number of heroes to show in each category (default: 10, max: 20).
        language: Language for hero names - 'english' or 'chinese' (default: 'english').

    Returns:
        A comprehensive trending heroes report with multiple perspectives.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    top_n = max(1, min(20, int(top)))
    scope_lower = scope.lower()
    rank_id = _parse_rank(rank)
    target_role = _parse_role(role)

    hero_map = load_hero_map(
        language=language,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    hero_stats = fetch_json(
        endpoint_opendota_hero_stats(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not hero_stats or not isinstance(hero_stats, list):
        return "Failed to fetch hero stats data from OpenDota."

    heroes_data = []
    for h in hero_stats:
        if not isinstance(h, dict):
            continue

        hero_roles = h.get("roles", [])
        if target_role and not _hero_has_role(hero_roles, target_role):
            continue

        hero_id = h.get("id", 0)
        hero_name = hero_map.get(hero_id) or h.get("localized_name", f"Hero#{hero_id}")
        pro_pick = h.get("pro_pick", 0) or 0
        pro_win = h.get("pro_win", 0) or 0
        pro_ban = h.get("pro_ban", 0) or 0

        if rank_id:
            pub_pick = h.get(f"{rank_id}_pick", 0) or 0
            pub_win = h.get(f"{rank_id}_win", 0) or 0
        else:
            pub_pick = h.get("pub_pick", 0) or 0
            pub_win = h.get("pub_win", 0) or 0

        pro_winrate = (pro_win / pro_pick * 100.0) if pro_pick > 0 else 0.0
        pub_winrate = (pub_win / pub_pick * 100.0) if pub_pick > 0 else 0.0

        heroes_data.append({
            "id": hero_id,
            "name": hero_name,
            "roles": hero_roles,
            "pro_pick": pro_pick,
            "pro_win": pro_win,
            "pro_ban": pro_ban,
            "pro_winrate": pro_winrate,
            "pub_pick": pub_pick,
            "pub_win": pub_win,
            "pub_winrate": pub_winrate,
        })

    rank_label = RANK_NAMES.get(rank_id, "All Ranks") if rank_id else "All Ranks"
    role_label = ROLE_DISPLAY_NAMES.get(target_role, "All Roles") if target_role else "All Roles"

    filter_parts = []
    if rank_id:
        filter_parts.append(rank_label)
    if target_role:
        filter_parts.append(role_label)
    filter_str = " | ".join(filter_parts) if filter_parts else ""

    sections: List[str] = ["=== Trending Heroes Analysis ==="]
    if filter_str:
        sections.append(f"Filter: {filter_str}")
    sections.append("")

    if scope_lower in ("all", "pro"):
        pro_pick_sorted = sorted(heroes_data, key=lambda x: -x["pro_pick"])[:top_n]
        sections.append("【Pro Scene - Most Picked】")
        sections.append(f"{'Rank':<5} {'Hero':<18} {'Picks':>8} {'WR':>8}")
        sections.append("-" * 42)
        for i, h in enumerate(pro_pick_sorted, 1):
            wr_str = f"{h['pro_winrate']:.1f}%" if h['pro_pick'] > 0 else "n/a"
            sections.append(f"{i:<5} {h['name']:<18} {h['pro_pick']:>8} {wr_str:>8}")
        sections.append("")

        pro_ban_sorted = sorted(heroes_data, key=lambda x: -x["pro_ban"])[:top_n]
        sections.append("【Pro Scene - Most Banned】")
        sections.append(f"{'Rank':<5} {'Hero':<18} {'Bans':>8}")
        sections.append("-" * 34)
        for i, h in enumerate(pro_ban_sorted, 1):
            sections.append(f"{i:<5} {h['name']:<18} {h['pro_ban']:>8}")
        sections.append("")

    if scope_lower in ("all", "pub"):
        pub_pick_sorted = sorted(heroes_data, key=lambda x: -x["pub_pick"])[:top_n]
        sections.append("【Public Matches - Most Popular】")
        sections.append(f"{'Rank':<5} {'Hero':<18} {'Picks':>10} {'WR':>8}")
        sections.append("-" * 44)
        for i, h in enumerate(pub_pick_sorted, 1):
            picks_str = _format_number(h['pub_pick'])
            wr_str = f"{h['pub_winrate']:.1f}%"
            sections.append(f"{i:<5} {h['name']:<18} {picks_str:>10} {wr_str:>8}")
        sections.append("")

        min_games = 1000 if not rank_id else 500
        pub_winrate_sorted = sorted(
            [h for h in heroes_data if h["pub_pick"] >= min_games],
            key=lambda x: -x["pub_winrate"]
        )[:top_n]
        sections.append("【Public Matches - Highest Winrate】")
        sections.append(f"{'Rank':<5} {'Hero':<18} {'Picks':>10} {'WR':>8}")
        sections.append("-" * 44)
        for i, h in enumerate(pub_winrate_sorted, 1):
            picks_str = _format_number(h['pub_pick'])
            wr_str = f"{h['pub_winrate']:.1f}%"
            sections.append(f"{i:<5} {h['name']:<18} {picks_str:>10} {wr_str:>8}")
        sections.append("")

    if scope_lower == "all" and not rank_id and not target_role:
        patch_list = load_patch_list(
            language="english",
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )

        if patch_list:
            current_patch = patch_list[-1]
            patch_name = str(current_patch.get("patch_number") or current_patch.get("patch_name") or "?").strip()
            start_ts = int(current_patch.get("patch_timestamp") or 0)
            end_ts = int(time.time())
            patch_date = fmt_date(start_ts)

            winrate_heroes = opendota_top_heroes_by_winrate(
                start_ts,
                end_ts,
                limit=top_n,
                min_games=1000,
                order="desc",
                cache=cache,
                timeout=DEFAULT_TIMEOUT,
                user_agent=DEFAULT_USER_AGENT,
            )

            if winrate_heroes:
                sections.append(f"【Current Patch Highest Winrate】(Patch {patch_name}, since {patch_date})")
                sections.append(f"{'Rank':<5} {'Hero':<18} {'Games':>10} {'WR':>8}")
                sections.append("-" * 44)
                for i, h in enumerate(winrate_heroes, 1):
                    hero_id = h["hero_id"]
                    hero_name = hero_map.get(hero_id, f"Hero#{hero_id}")
                    games = h["games"]
                    winrate = h["winrate"]
                    sections.append(f"{i:<5} {hero_name:<18} {games:>10} {winrate:>7.1f}%")
                sections.append("")

    sections.append("Data source: OpenDota API")
    notes = []
    if rank_id:
        notes.append(f"Pub data filtered by {rank_label}")
    if target_role:
        notes.append(f"Heroes filtered by {role_label} role")
    if not notes:
        notes.append("Pro data is cumulative, pub data reflects recent trends")
    sections.append(f"Note: {'; '.join(notes)}")

    return "\n".join(sections)
