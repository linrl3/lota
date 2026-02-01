"""Pro matches tool."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_pro_matches
from lota.core.http import fetch_json
from lota.core.utils import format_duration, format_time_ago


@tool
def pro_matches(
    limit: int = 10,
    less_than_match_id: Optional[int] = None,
) -> str:
    """Get recent professional Dota 2 matches from OpenDota.

    Args:
        limit: Number of recent matches to show (default: 10, max: 30).
        less_than_match_id: Get matches with match ID lower than this value (for pagination).

    Returns:
        A formatted list of recent pro matches with teams, scores, and leagues.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    limit_n = max(1, min(30, int(limit)))

    data = fetch_json(
        endpoint_opendota_pro_matches(less_than_match_id=less_than_match_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, list):
        return "Failed to fetch pro matches data."

    matches = []
    for m in data:
        if not isinstance(m, dict):
            continue
        radiant_name = m.get("radiant_name") or "Radiant"
        dire_name = m.get("dire_name") or "Dire"
        radiant_score = m.get("radiant_score", 0)
        dire_score = m.get("dire_score", 0)
        radiant_win = m.get("radiant_win", False)
        duration = m.get("duration", 0)
        start_time = m.get("start_time", 0)
        league_name = m.get("league_name", "Unknown League")
        match_id = m.get("match_id", 0)

        winner = radiant_name if radiant_win else dire_name
        loser = dire_name if radiant_win else radiant_name
        winner_score = radiant_score if radiant_win else dire_score
        loser_score = dire_score if radiant_win else radiant_score

        matches.append({
            "match_id": match_id,
            "winner": winner,
            "loser": loser,
            "winner_score": winner_score,
            "loser_score": loser_score,
            "duration": duration,
            "start_time": start_time,
            "league": league_name,
        })

    matches = matches[:limit_n]

    if not matches:
        return "No recent pro matches found."

    lines: List[str] = [
        "Recent Professional Matches",
        "(from OpenDota)",
        "",
    ]

    if less_than_match_id:
        lines.insert(2, f"(matches before ID {less_than_match_id})")

    for m in matches:
        time_ago = format_time_ago(m["start_time"])
        duration_str = format_duration(m["duration"])
        score_str = f"{m['winner_score']}-{m['loser_score']}"

        lines.append(f"**{m['winner']}** vs {m['loser']} ({score_str}) - {duration_str}")
        lines.append(f"  Match ID: {m['match_id']} | League: {m['league']} | {time_ago}")
        lines.append("")

    if matches:
        last_match_id = matches[-1]["match_id"]
        lines.append(f"(Use less_than_match_id={last_match_id} to get older matches)")

    return "\n".join(lines)
