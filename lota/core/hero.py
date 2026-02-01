"""Hero data loading functions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lota.core.cache import Cache
from lota.core.constants import NPC_HERO_PREFIX
from lota.core.endpoints import endpoint_hero_list, endpoint_opendota_explorer
from lota.core.http import fetch_json
from lota.core.utils import norm_for_match, strip_html, to_int


def load_hero_map(
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Dict[int, str]:
    """Load hero_id -> localized name mapping."""
    obj = fetch_json(
        endpoint_hero_list(language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    heroes = (((obj or {}).get("result") or {}).get("data") or {}).get("heroes") or []
    out: Dict[int, str] = {}
    for h in heroes:
        try:
            hid = int(h.get("id"))
        except Exception:
            continue
        name = (
            h.get("name_loc")
            or h.get("name_english_loc")
            or h.get("name")
            or f"Hero#{hid}"
        )
        out[hid] = strip_html(str(name))
    return out


def load_hero_name_to_id(
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Dict[str, int]:
    """Return mapping from localized hero name (lowercased) to hero id."""
    obj = fetch_json(
        endpoint_hero_list(language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    heroes = (((obj or {}).get("result") or {}).get("data") or {}).get("heroes") or []
    out: Dict[str, int] = {}
    for h in heroes:
        try:
            hid = int(h.get("id"))
        except Exception:
            continue
        for k in ("name_loc", "name_english_loc", "name"):
            n = h.get(k)
            if not n:
                continue
            loc = norm_for_match(strip_html(str(n)))
            if loc:
                out[loc] = hid
    return out


def load_hero_short_map(
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Dict[str, str]:
    """Return mapping from localized hero name (lowercased) to hero short name (e.g. 'viper')."""
    obj = fetch_json(
        endpoint_hero_list(language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    heroes = (((obj or {}).get("result") or {}).get("data") or {}).get("heroes") or []
    out: Dict[str, str] = {}
    for h in heroes:
        npc = str(h.get("name") or "")
        if npc.startswith(NPC_HERO_PREFIX):
            short = npc[len(NPC_HERO_PREFIX):]
        else:
            continue
        for k in ("name_loc", "name_english_loc", "name"):
            n = h.get(k)
            if not n:
                continue
            loc = norm_for_match(strip_html(str(n)))
            if loc:
                out[loc] = short
    return out


def opendota_hero_winrate_by_time_range(
    hero_id: int,
    start_ts: int,
    end_ts: int,
    *,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Tuple[int, int]:
    """Return (games, wins) for hero within [start_ts, end_ts) (OpenDota explorer)."""
    sql = (
        "SELECT "
        "  COUNT(*) AS games, "
        "  SUM(CASE WHEN ((matches.radiant_win = true AND player_matches.player_slot < 128) "
        "            OR (matches.radiant_win = false AND player_matches.player_slot >= 128)) "
        "      THEN 1 ELSE 0 END) AS wins "
        "FROM player_matches "
        "JOIN matches USING(match_id) "
        f"WHERE matches.start_time >= {int(start_ts)} AND matches.start_time < {int(end_ts)} "
        f"AND player_matches.hero_id = {int(hero_id)}"
    )
    obj = fetch_json(
        endpoint_opendota_explorer(sql),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    rows = (obj or {}).get("rows") or []
    if not rows:
        return 0, 0
    r0 = rows[0] if isinstance(rows[0], dict) else {}
    return to_int(r0.get("games")), to_int(r0.get("wins"))


def opendota_top_heroes_by_winrate(
    start_ts: int,
    end_ts: int,
    *,
    limit: int = 10,
    min_games: int = 1000,
    order: str = "desc",
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> List[Dict[str, Any]]:
    """Return top heroes by winrate within [start_ts, end_ts) (OpenDota explorer).

    Args:
        start_ts: Start timestamp (inclusive)
        end_ts: End timestamp (exclusive)
        limit: Number of heroes to return
        min_games: Minimum games threshold to filter out low-sample heroes
        order: 'desc' for highest winrate first, 'asc' for lowest

    Returns:
        List of dicts with hero_id, games, wins, winrate
    """
    order_dir = "DESC" if order == "desc" else "ASC"
    sql = (
        "SELECT "
        "  player_matches.hero_id, "
        "  COUNT(*) AS games, "
        "  SUM(CASE WHEN ((matches.radiant_win = true AND player_matches.player_slot < 128) "
        "            OR (matches.radiant_win = false AND player_matches.player_slot >= 128)) "
        "      THEN 1 ELSE 0 END) AS wins "
        "FROM player_matches "
        "JOIN matches USING(match_id) "
        f"WHERE matches.start_time >= {int(start_ts)} AND matches.start_time < {int(end_ts)} "
        "GROUP BY player_matches.hero_id "
        f"HAVING COUNT(*) >= {int(min_games)} "
        f"ORDER BY (SUM(CASE WHEN ((matches.radiant_win = true AND player_matches.player_slot < 128) "
        "            OR (matches.radiant_win = false AND player_matches.player_slot >= 128)) "
        f"      THEN 1 ELSE 0 END)::float / COUNT(*)) {order_dir} "
        f"LIMIT {int(limit)}"
    )
    obj = fetch_json(
        endpoint_opendota_explorer(sql),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    rows = (obj or {}).get("rows") or []

    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        hero_id = to_int(row.get("hero_id"))
        games = to_int(row.get("games"))
        wins = to_int(row.get("wins"))
        winrate = (wins / float(games) * 100.0) if games > 0 else 0.0
        result.append({
            "hero_id": hero_id,
            "games": games,
            "wins": wins,
            "winrate": winrate,
        })

    return result
