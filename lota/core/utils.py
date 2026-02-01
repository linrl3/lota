"""Common utility functions."""

from __future__ import annotations

import datetime as _dt
import difflib
import html
import re
from typing import Dict, Iterable, List, Optional

_RE_BR = re.compile(r"<\s*br\s*/?\s*>", re.I)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"\s+")


def strip_html(s: str) -> str:
    """Convert HTML snippets in patch notes into searchable plain text."""
    if not s:
        return ""
    s = _RE_BR.sub("\n", s)
    s = _RE_TAG.sub("", s)
    s = html.unescape(s)
    lines = [
        _RE_WS.sub(" ", line).strip()
        for line in s.splitlines()
        if _RE_WS.sub(" ", line).strip()
    ]
    return "\n".join(lines)


def fmt_date(ts: int) -> str:
    """Format a Unix timestamp as YYYY-MM-DD."""
    try:
        return _dt.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        return ""


def norm_for_match(s: str) -> str:
    """Normalize a string for matching (lowercase, stripped)."""
    return (s or "").strip().lower()


def suggest_names(keyword: str, names: List[str], *, limit: int = 20) -> List[str]:
    """Return a small set of human-friendly suggestions for an unknown name."""
    kw = norm_for_match(keyword)
    if not kw or not names:
        return []

    sub = [n for n in names if kw in norm_for_match(n)]
    if sub:
        return sub[:limit]

    norm_to_orig: Dict[str, str] = {}
    norms: List[str] = []
    for n in names:
        nn = norm_for_match(n)
        if not nn:
            continue
        if nn not in norm_to_orig:
            norm_to_orig[nn] = n
            norms.append(nn)
    close = difflib.get_close_matches(kw, norms, n=limit, cutoff=0.6)
    return [norm_to_orig[c] for c in close]


def filter_and_limit(
    names: Iterable[str], query: Optional[str], limit: int
) -> List[str]:
    """Filter names by query substring and limit results."""
    q = norm_for_match(query or "")
    out: List[str] = []
    for n in names:
        if q and q not in norm_for_match(n):
            continue
        out.append(n)
        if limit and len(out) >= limit:
            break
    return out


def format_duration(seconds: int) -> str:
    """Format seconds as MM:SS."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def format_time_ago(timestamp: int) -> str:
    """Format a Unix timestamp as relative time (e.g., '2 hours ago')."""
    import time

    now = int(time.time())
    diff = now - timestamp
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = diff // 60
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = diff // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"


def to_int(v, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def deep_get(obj: dict, *keys, default=None):
    """Safely get a nested value from a dictionary."""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key, default)
        if obj is None:
            return default
    return obj


def _resolve_hero_from_maps(
    hero_input: str,
    hero_map: Dict[int, str],
    name_to_id: Dict[str, int],
    short_map: Dict[str, int],
) -> tuple:
    """Resolve hero input to (hero_id, hero_name) or (None, error_message)."""
    hero_lower = hero_input.strip().lower()

    if hero_lower.isdigit():
        hero_id = int(hero_lower)
        if hero_id in hero_map:
            return hero_id, hero_map[hero_id]
        return None, f"Unknown hero ID: {hero_id}"

    if hero_lower in name_to_id:
        hero_id = name_to_id[hero_lower]
        return hero_id, hero_map.get(hero_id, hero_input)

    if hero_lower in short_map:
        hero_id = short_map[hero_lower]
        return hero_id, hero_map.get(hero_id, hero_input)

    suggestions = suggest_names(hero_input, list(name_to_id.keys()), limit=5)
    if suggestions:
        return None, f"Unknown hero: {hero_input}. Did you mean: {', '.join(suggestions)}?"
    return None, f"Unknown hero: {hero_input}"


def resolve_hero(
    hero_input: str,
    language: str,
    cache,
    timeout: int,
    user_agent: str,
) -> tuple:
    """Resolve hero input to (hero_id, hero_name, error) tuple.

    This is a convenience wrapper that loads the required hero maps
    and calls the underlying resolution logic.

    Args:
        hero_input: Hero name or ID to resolve.
        language: Language for hero name matching ('english' or 'chinese').
        cache: Cache instance for HTTP requests.
        timeout: HTTP timeout in seconds.
        user_agent: User-Agent string for HTTP requests.

    Returns:
        Tuple of (hero_id, hero_name, error). If successful, error is None.
        If failed, hero_id and hero_name are None and error contains the message.
    """
    from lota.core.hero import load_hero_map, load_hero_name_to_id

    hero_map = load_hero_map(
        language=language,
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
    )
    name_to_id = load_hero_name_to_id(
        language=language,
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
    )
    short_map = {}
    for name, hid in name_to_id.items():
        short_map[name] = hid

    result = _resolve_hero_from_maps(hero_input, hero_map, name_to_id, short_map)

    if result[0] is None:
        return None, None, result[1]
    return result[0], result[1], None
