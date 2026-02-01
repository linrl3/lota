"""Tournament listing tool."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_pro_matches
from lota.core.http import fetch_json


@tool
def recent_tournaments(
    limit: int = 10,
) -> str:
    """Get recent Dota 2 tournaments with match counts and teams.

    Args:
        limit: Maximum number of tournaments to show (default: 10).

    Returns:
        List of recent tournaments with match counts, teams, and latest results.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_pro_matches(100),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data:
        return "Could not fetch tournament data."

    tournaments: Dict[int, Dict[str, Any]] = {}

    for m in data:
        league_id = m.get("leagueid")
        if not league_id:
            continue

        if league_id not in tournaments:
            tournaments[league_id] = {
                "name": m.get("league_name") or f"League {league_id}",
                "matches": [],
                "teams": set(),
                "latest_time": 0,
            }

        t = tournaments[league_id]
        t["matches"].append(m)

        radiant = m.get("radiant_name")
        dire = m.get("dire_name")
        if radiant:
            t["teams"].add(radiant)
        if dire:
            t["teams"].add(dire)

        start_time = m.get("start_time", 0)
        if start_time > t["latest_time"]:
            t["latest_time"] = start_time

    sorted_tournaments = sorted(
        tournaments.values(),
        key=lambda x: x["latest_time"],
        reverse=True
    )[:limit]

    lines: List[str] = [
        "Recent Dota 2 Tournaments",
        "",
    ]

    for t in sorted_tournaments:
        name = t["name"]
        match_count = len(t["matches"])
        teams = sorted(t["teams"])
        latest = datetime.fromtimestamp(t["latest_time"])

        lines.append(f"**{name}**")
        lines.append(f"  Matches: {match_count} (recent)")
        lines.append(f"  Last match: {latest.strftime('%Y-%m-%d %H:%M')}")

        if teams:
            team_str = ", ".join(teams[:6])
            if len(teams) > 6:
                team_str += f" (+{len(teams)-6} more)"
            lines.append(f"  Teams: {team_str}")

        recent_matches = sorted(t["matches"], key=lambda x: x.get("start_time", 0), reverse=True)[:3]
        if recent_matches:
            lines.append("  Recent results:")
            for m in recent_matches:
                radiant = m.get("radiant_name") or "Radiant"
                dire = m.get("dire_name") or "Dire"
                radiant_win = m.get("radiant_win")
                if radiant_win is True:
                    result = f"{radiant} > {dire}"
                elif radiant_win is False:
                    result = f"{dire} > {radiant}"
                else:
                    result = f"{radiant} vs {dire}"
                duration = m.get("duration", 0)
                mins = duration // 60
                lines.append(f"    - {result} ({mins}min)")

        lines.append("")

    if not sorted_tournaments:
        lines.append("No recent tournaments found.")

    return "\n".join(lines)
