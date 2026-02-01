"""List heroes tool."""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.hero import load_hero_map
from lota.core.utils import filter_and_limit


@tool
def list_heroes(
    language: str = "english",
    query: Optional[str] = None,
    limit: int = 50,
) -> str:
    """List all available Dota 2 heroes.

    Args:
        language: Output language - 'english' or 'chinese' (default: 'english').
        query: Optional substring to filter hero names (case-insensitive).
        limit: Maximum number of heroes to return (default: 50).

    Returns:
        A formatted list of hero names.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    hero_map = load_hero_map(
        language=language,
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )
    names = sorted(set(hero_map.values()))
    names = filter_and_limit(names, query, limit)

    if not names:
        if query:
            return f"No heroes found matching '{query}'."
        return "No heroes found."

    result = f"Found {len(names)} heroes"
    if query:
        result += f" matching '{query}'"
    result += ":\n"
    result += "\n".join(f"- {name}" for name in names)
    return result
