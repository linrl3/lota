"""API endpoint URLs."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from lota.core.i18n import datafeed_language

if TYPE_CHECKING:
    from lota.core.filters import PlayerMatchFilters

OPENDOTA_BASE = "https://api.opendota.com/api"
DOTA2_DATAFEED = "https://www.dota2.com/datafeed"


def _build_query_string(params: Dict[str, Any]) -> str:
    """Build URL query string from params dict, filtering out None values."""
    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return ""
    return "?" + urllib.parse.urlencode(filtered, doseq=True)


def _endpoint_opendota_player_resource(
    account_id: int,
    resource: str,
    filters: Optional["PlayerMatchFilters"] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    """Generic player resource endpoint builder.

    Args:
        account_id: Player's account ID.
        resource: Resource path (e.g., 'matches', 'heroes', 'wl').
        filters: Optional PlayerMatchFilters for query parameters.
        extra_params: Optional additional parameters (e.g., 'project' for matches).

    Returns:
        Full URL for the endpoint.
    """
    params = filters.to_dict() if filters else {}
    if extra_params:
        params.update(extra_params)
    return f"{OPENDOTA_BASE}/players/{account_id}/{resource}{_build_query_string(params)}"


def endpoint_patch_list(language: str) -> str:
    return f"https://www.dota2.com/datafeed/patchnoteslist?language={datafeed_language(language)}"


def endpoint_patch_notes(version: str, language: str) -> str:
    return f"https://www.dota2.com/datafeed/patchnotes?version={version}&language={datafeed_language(language)}"


def endpoint_hero_list(language: str) -> str:
    return f"https://www.dota2.com/datafeed/herolist?language={datafeed_language(language)}"


def endpoint_item_list(language: str) -> str:
    return f"https://www.dota2.com/datafeed/itemlist?language={datafeed_language(language)}"


def endpoint_ability_list(language: str) -> str:
    return f"https://www.dota2.com/datafeed/abilitylist?language={datafeed_language(language)}"


def endpoint_hero_data(hero_id: int, language: str = "english") -> str:
    return f"{DOTA2_DATAFEED}/herodata?language={language}&hero_id={hero_id}"


def endpoint_opendota_explorer(sql: str) -> str:
    q = urllib.parse.urlencode({"sql": sql})
    return f"{OPENDOTA_BASE}/explorer?{q}"


def endpoint_opendota_heroes() -> str:
    return f"{OPENDOTA_BASE}/heroes"


def endpoint_opendota_hero_stats() -> str:
    return f"{OPENDOTA_BASE}/heroStats"


def endpoint_opendota_hero_matchups(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/heroes/{hero_id}/matchups"


def endpoint_opendota_hero_durations(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/heroes/{hero_id}/durations"


def endpoint_opendota_hero_item_popularity(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/heroes/{hero_id}/itemPopularity"


def endpoint_opendota_hero_matches(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/heroes/{hero_id}/matches"


def endpoint_opendota_hero_players(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/heroes/{hero_id}/players"


def endpoint_opendota_benchmarks(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/benchmarks?hero_id={hero_id}"


def endpoint_opendota_rankings(hero_id: int) -> str:
    return f"{OPENDOTA_BASE}/rankings?hero_id={hero_id}"


def endpoint_opendota_match(match_id: int) -> str:
    return f"{OPENDOTA_BASE}/matches/{match_id}"


def endpoint_opendota_pro_matches(
    less_than_match_id: Optional[int] = None,
) -> str:
    params = {"less_than_match_id": less_than_match_id}
    return f"{OPENDOTA_BASE}/proMatches{_build_query_string(params)}"


def endpoint_opendota_public_matches(
    less_than_match_id: Optional[int] = None,
    min_rank: Optional[int] = None,
    max_rank: Optional[int] = None,
) -> str:
    params = {
        "less_than_match_id": less_than_match_id,
        "min_rank": min_rank,
        "max_rank": max_rank,
    }
    return f"{OPENDOTA_BASE}/publicMatches{_build_query_string(params)}"


def endpoint_opendota_parsed_matches(
    less_than_match_id: Optional[int] = None,
) -> str:
    params = {"less_than_match_id": less_than_match_id}
    return f"{OPENDOTA_BASE}/parsedMatches{_build_query_string(params)}"


def endpoint_opendota_find_matches(
    team_a: Optional[List[int]] = None,
    team_b: Optional[List[int]] = None,
) -> str:
    params: Dict[str, Any] = {}
    if team_a:
        params["teamA"] = team_a
    if team_b:
        params["teamB"] = team_b
    return f"{OPENDOTA_BASE}/findMatches{_build_query_string(params)}"


def endpoint_opendota_request_parse(match_id: int) -> str:
    return f"{OPENDOTA_BASE}/request/{match_id}"


def endpoint_opendota_request_status(job_id: str) -> str:
    return f"{OPENDOTA_BASE}/request/{job_id}"


def endpoint_opendota_search(query: str) -> str:
    q = urllib.parse.urlencode({"q": query})
    return f"{OPENDOTA_BASE}/search?{q}"


def endpoint_opendota_player(account_id: int) -> str:
    return f"{OPENDOTA_BASE}/players/{account_id}"


def endpoint_opendota_player_wl(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player win/loss stats."""
    return _endpoint_opendota_player_resource(account_id, "wl", filters)


def endpoint_opendota_player_recent_matches(account_id: int) -> str:
    return f"{OPENDOTA_BASE}/players/{account_id}/recentMatches"


def endpoint_opendota_player_matches(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
    project: Optional[List[str]] = None,
) -> str:
    """Get player matches."""
    extra = {"project": project} if project else None
    return _endpoint_opendota_player_resource(account_id, "matches", filters, extra)


def endpoint_opendota_player_heroes(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player heroes stats."""
    return _endpoint_opendota_player_resource(account_id, "heroes", filters)


def endpoint_opendota_player_peers(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player peers stats."""
    return _endpoint_opendota_player_resource(account_id, "peers", filters)


def endpoint_opendota_player_pros(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player pro matches stats."""
    return _endpoint_opendota_player_resource(account_id, "pros", filters)


def endpoint_opendota_player_totals(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player totals stats."""
    return _endpoint_opendota_player_resource(account_id, "totals", filters)


def endpoint_opendota_player_counts(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player counts stats."""
    return _endpoint_opendota_player_resource(account_id, "counts", filters)


def endpoint_opendota_player_histograms(
    account_id: int,
    field: str,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player histograms for a specific field."""
    return _endpoint_opendota_player_resource(account_id, f"histograms/{field}", filters)


def endpoint_opendota_player_wardmap(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player ward map data."""
    return _endpoint_opendota_player_resource(account_id, "wardmap", filters)


def endpoint_opendota_player_wordcloud(
    account_id: int,
    filters: Optional["PlayerMatchFilters"] = None,
) -> str:
    """Get player word cloud data."""
    return _endpoint_opendota_player_resource(account_id, "wordcloud", filters)


def endpoint_opendota_player_ratings(account_id: int) -> str:
    return f"{OPENDOTA_BASE}/players/{account_id}/ratings"


def endpoint_opendota_player_rankings(account_id: int) -> str:
    return f"{OPENDOTA_BASE}/players/{account_id}/rankings"


def endpoint_opendota_player_refresh(account_id: int) -> str:
    return f"{OPENDOTA_BASE}/players/{account_id}/refresh"


def endpoint_opendota_leagues() -> str:
    return f"{OPENDOTA_BASE}/leagues"


def endpoint_opendota_league(league_id: int) -> str:
    return f"{OPENDOTA_BASE}/leagues/{league_id}"


def endpoint_opendota_league_matches(league_id: int) -> str:
    return f"{OPENDOTA_BASE}/leagues/{league_id}/matches"


def endpoint_opendota_league_teams(league_id: int) -> str:
    return f"{OPENDOTA_BASE}/leagues/{league_id}/teams"


def endpoint_opendota_teams(page: Optional[int] = None) -> str:
    params = {"page": page}
    return f"{OPENDOTA_BASE}/teams{_build_query_string(params)}"


def endpoint_opendota_team(team_id: int) -> str:
    return f"{OPENDOTA_BASE}/teams/{team_id}"


def endpoint_opendota_team_matches(team_id: int) -> str:
    return f"{OPENDOTA_BASE}/teams/{team_id}/matches"


def endpoint_opendota_team_players(team_id: int) -> str:
    return f"{OPENDOTA_BASE}/teams/{team_id}/players"


def endpoint_opendota_team_heroes(team_id: int) -> str:
    return f"{OPENDOTA_BASE}/teams/{team_id}/heroes"


def endpoint_opendota_pro_players() -> str:
    return f"{OPENDOTA_BASE}/proPlayers"


def endpoint_opendota_top_players(turbo: Optional[int] = None) -> str:
    params = {"turbo": turbo}
    return f"{OPENDOTA_BASE}/topPlayers{_build_query_string(params)}"


def endpoint_opendota_live() -> str:
    return f"{OPENDOTA_BASE}/live"


def endpoint_opendota_distributions() -> str:
    return f"{OPENDOTA_BASE}/distributions"


def endpoint_opendota_constants(resource: str) -> str:
    return f"{OPENDOTA_BASE}/constants/{resource}"


def endpoint_opendota_scenarios_item_timings(
    item: Optional[str] = None,
    hero_id: Optional[int] = None,
) -> str:
    params = {"item": item, "hero_id": hero_id}
    return f"{OPENDOTA_BASE}/scenarios/itemTimings{_build_query_string(params)}"


def endpoint_opendota_scenarios_lane_roles(
    lane_role: Optional[str] = None,
    hero_id: Optional[int] = None,
) -> str:
    params = {"lane_role": lane_role, "hero_id": hero_id}
    return f"{OPENDOTA_BASE}/scenarios/laneRoles{_build_query_string(params)}"


def endpoint_opendota_scenarios_misc(scenario: Optional[str] = None) -> str:
    params = {"scenario": scenario}
    return f"{OPENDOTA_BASE}/scenarios/misc{_build_query_string(params)}"


def endpoint_opendota_records(field: str) -> str:
    return f"{OPENDOTA_BASE}/records/{field}"


def endpoint_opendota_schema() -> str:
    return f"{OPENDOTA_BASE}/schema"


def endpoint_opendota_health() -> str:
    return f"{OPENDOTA_BASE}/health"


def endpoint_opendota_metadata() -> str:
    return f"{OPENDOTA_BASE}/metadata"
