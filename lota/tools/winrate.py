"""Hero winrate tool."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.hero import opendota_hero_winrate_by_time_range
from lota.core.patch import load_patch_list
from lota.core.utils import fmt_date, resolve_hero


@tool
def hero_winrate(
    hero: str,
    last: int = 8,
    language: str = "english",
) -> str:
    """Get hero winrate statistics across recent patches using OpenDota data.

    Args:
        hero: Hero name to analyze (e.g., 'Invoker', 'Anti-Mage').
        last: Number of recent patches to analyze (default: 8).
        language: Language for hero name matching - 'english' or 'chinese' (default: 'english').

    Returns:
        A formatted table showing winrate trends across patches.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    hero_id, hero_name, error = resolve_hero(hero, language, cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)
    if error:
        return error

    patch_list = load_patch_list(
        language="english",
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )
    if not patch_list:
        return "Failed to load patch list."

    last_n = max(1, int(last))
    selected = patch_list[-last_n:]

    now_ts = int(time.time())

    rows: List[Dict[str, Any]] = []
    prev_wr: Optional[float] = None
    for i, p in enumerate(selected):
        ver = str(p.get("patch_number") or p.get("patch_name") or "?").strip()
        start_ts = int(p.get("patch_timestamp") or 0)
        end_ts = (
            int(selected[i + 1].get("patch_timestamp") or 0)
            if (i + 1) < len(selected)
            else now_ts
        )
        pdate = fmt_date(start_ts)
        games, wins = opendota_hero_winrate_by_time_range(
            hero_id,
            start_ts,
            end_ts,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
            user_agent=DEFAULT_USER_AGENT,
        )
        wr = (wins / float(games)) if games > 0 else None
        delta_pp: Optional[float] = None
        if wr is not None and prev_wr is not None:
            delta_pp = (wr - prev_wr) * 100.0
        prev_wr = wr if wr is not None else prev_wr
        rows.append(
            {
                "patch": ver,
                "date": pdate,
                "games": games,
                "wins": wins,
                "winrate": (wr * 100.0) if wr is not None else None,
                "delta_pp": delta_pp,
            }
        )

    rows.reverse()

    lines: List[str] = [
        f"Hero: {hero_name} (id={hero_id})",
        f"Range: last {last_n} patches (winrate from OpenDota)",
        "",
        f"{'Patch':<10} {'Date':<12} {'Games':>8} {'Winrate':>9} {'Δ(pp)':>8}",
        "-" * 52,
    ]

    for r in rows:
        games = int(r["games"])
        wins = int(r["wins"])
        wr_s = f"{r['winrate']:.2f}%" if r["winrate"] is not None else "n/a"
        d = r.get("delta_pp")
        d_s = "n/a" if d is None else f"{d:+.2f}"
        lines.append(
            f"{str(r['patch'])[:10]:<10} {str(r['date'])[:12]:<12} {games:>8} {wr_s:>9} {d_s:>8}"
        )

    return "\n".join(lines)
