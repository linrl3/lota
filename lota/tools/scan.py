"""Scan patch notes tool."""

from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.ability import load_ability_map
from lota.core.cache import Cache
from lota.core.hero import load_hero_map
from lota.core.i18n import labels_for
from lota.core.item import load_item_map
from lota.core.patch import Hit, iter_hits_from_patch, load_patch_list, load_patch_notes, make_matcher
from lota.core.utils import fmt_date


@tool
def scan_patch_notes(
    keyword: str,
    last: int = 5,
    language: str = "english",
    scope: str = "all",
    regex: bool = False,
) -> str:
    """Search Dota 2 patch notes for a keyword across recent patches.

    Args:
        keyword: The keyword or hero/item name to search for in patch notes.
        last: Number of recent patches to scan (default: 5).
        language: Output language - 'english' or 'chinese' (default: 'english').
        scope: Search scope - 'all', 'general', 'heroes', 'items', 'neutral_items', or 'neutral_creeps' (default: 'all').
        regex: If True, treat keyword as a regular expression (default: False).

    Returns:
        A formatted string containing matching patch notes.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    matcher = make_matcher(keyword, regex=regex)
    labels = labels_for(language)

    patches = load_patch_list(
        language=language,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )
    if not patches:
        return "No patches found."

    last_n = max(1, int(last))
    selected = patches[-last_n:]

    need_hero = scope in ("all", "heroes")
    need_item = scope in ("all", "items", "neutral_items")
    hero_map = (
        load_hero_map(
            language=language,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if need_hero
        else {}
    )
    ability_map = (
        load_ability_map(
            language=language,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if need_hero
        else {}
    )
    item_map = (
        load_item_map(
            language=language,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if need_item
        else {}
    )

    hits: List[Hit] = []
    for p in reversed(selected):
        ver = str(p.get("patch_number") or p.get("patch_name") or "").strip()
        if not ver:
            continue
        ts = int(p.get("patch_timestamp") or 0)
        date = fmt_date(ts)

        pobj = load_patch_notes(
            ver,
            language=language,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        if pobj is None:
            continue

        for h in iter_hits_from_patch(
            pobj,
            patch_number=ver,
            patch_date=date,
            hero_map=hero_map,
            item_map=item_map,
            ability_map=ability_map,
            labels=labels,
        ):
            if scope != "all" and h.scope != scope:
                continue
            if (
                matcher(h.text)
                or (h.entity and matcher(h.entity))
                or (h.section and matcher(h.section))
            ):
                hits.append(h)
                if len(hits) >= 100:
                    break
        if len(hits) >= 100:
            break

    if not hits:
        return f"No matches found for '{keyword}' in the last {last_n} patches."

    lines: List[str] = []
    current_patch = ""
    for h in hits:
        if h.patch != current_patch:
            if current_patch:
                lines.append("")
            lines.append(f"== {h.patch} ({h.patch_date}) ==")
            current_patch = h.patch
        prefix = f"[{h.section}]"
        if h.entity:
            prefix += f"[{h.entity}]"
        lines.append(f"- {prefix} {h.text}")

    return "\n".join(lines)
