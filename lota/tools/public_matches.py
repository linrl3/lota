"""Public matches tool."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_public_matches
from lota.core.http import fetch_json
from lota.core.utils import format_duration, format_time_ago


@tool
def public_matches(
    limit: int = 10,
    min_rank: Optional[int] = None,
    max_rank: Optional[int] = None,
) -> str:
    """Get recent public Dota 2 matches from OpenDota.

    Args:
        limit: Number of recent matches to show (default: 10, max: 30).
        min_rank: Minimum rank tier to filter matches (e.g., 10=Herald, 80=Immortal).
        max_rank: Maximum rank tier to filter matches.

    Returns:
        A formatted list of recent public matches with basic information.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(30, int(limit)))

    data = fetch_json(
        endpoint_opendota_public_matches(
            min_rank=min_rank,
            max_rank=max_rank,
        ),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch public matches data."

    matches = []
    for m in data:
        if not isinstance(m, dict):
            continue
        match_id = m.get("match_id", 0)
        radiant_win = m.get("radiant_win")
        duration = m.get("duration", 0)
        start_time = m.get("start_time", 0)
        avg_rank_tier = m.get("avg_rank_tier")
        num_rank_tier = m.get("num_rank_tier")

        matches.append({
            "match_id": match_id,
            "radiant_win": radiant_win,
            "duration": duration,
            "start_time": start_time,
            "avg_rank_tier": avg_rank_tier,
            "num_rank_tier": num_rank_tier,
        })

    matches = matches[:limit_n]

    if not matches:
        return "No recent public matches found."

    lines: List[str] = [
        "Recent Public Matches",
        "(from OpenDota)",
        "",
    ]

    for m in matches:
        time_ago = format_time_ago(m["start_time"])
        duration_str = format_duration(m["duration"])
        winner = "Radiant" if m["radiant_win"] else "Dire" if m["radiant_win"] is not None else "Unknown"
        rank_str = f"Rank: {m['avg_rank_tier']}" if m["avg_rank_tier"] else "Rank: N/A"

        lines.append(f"Match {m['match_id']}")
        lines.append(f"  Winner: {winner} | Duration: {duration_str} | {rank_str} | {time_ago}")
        lines.append("")

    return "\n".join(lines)
