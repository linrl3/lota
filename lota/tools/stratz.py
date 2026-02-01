"""Stratz API tools for Dota 2 analysis."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT
from lota.core.cache import Cache
from lota.core.filters import rank_tier_to_str
from lota.core.stratz import (
    QUERY_HERO_META,
    QUERY_HERO_STATS,
    QUERY_LEAGUE,
    QUERY_LIVE_MATCHES,
    QUERY_MATCH,
    QUERY_PLAYER,
    QUERY_PLAYER_HERO_PERFORMANCE,
    QUERY_PLAYER_MATCHES,
    QUERY_PRO_MATCHES,
    QUERY_TEAM,
    stratz_graphql_request,
)
from lota.core.utils import format_duration


def _format_timestamp(ts: Optional[int]) -> str:
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "N/A"


@tool
def stratz_player(
    steam_account_id: int,
) -> str:
    """Get detailed player profile from Stratz API.

    Args:
        steam_account_id: The player's Steam account ID (32-bit, e.g., 87278757).

    Returns:
        Player profile including name, rank, match count, and win rate.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_PLAYER,
            {"steamAccountId": steam_account_id},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching player data: {e}"

    player = result.get("data", {}).get("player")
    if not player:
        return f"Player with Steam Account ID {steam_account_id} not found."

    steam_account = player.get("steamAccount", {})
    name = steam_account.get("name", "Unknown")
    rank = steam_account.get("seasonRank")
    leaderboard = steam_account.get("seasonLeaderboardRank")
    pro_account = steam_account.get("proSteamAccount")

    match_count = player.get("matchCount", 0)
    win_count = player.get("winCount", 0)
    winrate = (win_count / match_count * 100) if match_count > 0 else 0

    lines: List[str] = [
        f"Player: {name}",
        f"Steam Account ID: {steam_account_id}",
    ]

    if pro_account:
        pro_name = pro_account.get("name")
        team = pro_account.get("team")
        if pro_name:
            lines.append(f"Pro Name: {pro_name}")
        if team:
            lines.append(f"Team: {team.get('name', 'Unknown')} [{team.get('tag', '')}]")

    lines.append("")
    rank_str = rank_tier_to_str(rank)
    if leaderboard:
        lines.append(f"Rank: {rank_str} (Leaderboard #{leaderboard})")
    else:
        lines.append(f"Rank: {rank_str}")

    lines.append("")
    lines.append(f"Total Matches: {match_count}")
    lines.append(f"Wins: {win_count}")
    lines.append(f"Losses: {match_count - win_count}")
    lines.append(f"Win Rate: {winrate:.1f}%")

    first_match = player.get("firstMatchDate")
    last_match = player.get("lastMatchDate")
    if first_match:
        lines.append(f"First Match: {_format_timestamp(first_match)}")
    if last_match:
        lines.append(f"Last Match: {_format_timestamp(last_match)}")

    profile_uri = steam_account.get("profileUri")
    if profile_uri:
        lines.append("")
        lines.append(f"Profile: {profile_uri}")

    return "\n".join(lines)


@tool
def stratz_player_matches(
    steam_account_id: int,
    limit: int = 10,
) -> str:
    """Get recent matches for a player from Stratz API.

    Args:
        steam_account_id: The player's Steam account ID (32-bit).
        limit: Number of matches to retrieve (default: 10, max: 50).

    Returns:
        List of recent matches with hero, KDA, and result.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    take = max(1, min(50, limit))

    try:
        result = stratz_graphql_request(
            QUERY_PLAYER_MATCHES,
            {"steamAccountId": steam_account_id, "take": take, "skip": 0},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching player matches: {e}"

    player = result.get("data", {}).get("player")
    if not player:
        return f"Player with Steam Account ID {steam_account_id} not found."

    matches = player.get("matches", [])
    if not matches:
        return f"No matches found for player {steam_account_id}."

    lines: List[str] = [
        f"Recent Matches for Player {steam_account_id}",
        "",
        f"{'Match ID':<12} {'Hero':<18} {'K/D/A':<10} {'GPM':>5} {'Duration':>8} {'Result':>8}",
        "-" * 70,
    ]

    for match in matches:
        match_id = match.get("id", 0)
        duration = format_duration(match.get("durationSeconds", 0))
        players = match.get("players", [])

        if players:
            p = players[0]
            hero = p.get("hero", {})
            hero_name = hero.get("displayName", "Unknown")[:18]
            kills = p.get("kills", 0)
            deaths = p.get("deaths", 0)
            assists = p.get("assists", 0)
            kda = f"{kills}/{deaths}/{assists}"
            gpm = p.get("goldPerMinute", 0)
            is_victory = p.get("isVictory", False)
            result_str = "Won" if is_victory else "Lost"

            lines.append(
                f"{match_id:<12} {hero_name:<18} {kda:<10} {gpm:>5} {duration:>8} {result_str:>8}"
            )

    return "\n".join(lines)


@tool
def stratz_match(
    match_id: int,
) -> str:
    """Get detailed match information from Stratz API.

    Args:
        match_id: The match ID to look up.

    Returns:
        Detailed match information including players, heroes, and stats.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_MATCH,
            {"matchId": match_id},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching match data: {e}"

    match = result.get("data", {}).get("match")
    if not match:
        return f"Match {match_id} not found."

    duration = format_duration(match.get("durationSeconds", 0))
    start_time = _format_timestamp(match.get("startDateTime"))
    radiant_win = match.get("didRadiantWin", False)
    radiant_kills = match.get("radiantKills", 0)
    dire_kills = match.get("direKills", 0)

    lines: List[str] = [
        f"Match ID: {match_id}",
        f"Date: {start_time}",
        f"Duration: {duration}",
        f"Winner: {'Radiant' if radiant_win else 'Dire'}",
        f"Score: Radiant {radiant_kills} - {dire_kills} Dire",
        "",
    ]

    players = match.get("players", [])
    radiant_players = [p for p in players if p.get("isRadiant")]
    dire_players = [p for p in players if not p.get("isRadiant")]

    def format_player_line(p: dict) -> str:
        hero = p.get("hero", {})
        hero_name = hero.get("displayName", "Unknown")[:15]
        steam_acc = p.get("steamAccount", {})
        player_name = steam_acc.get("name", "Unknown")[:12]
        pro = steam_acc.get("proSteamAccount")
        if pro and pro.get("name"):
            player_name = pro.get("name")[:12]
        kills = p.get("kills", 0)
        deaths = p.get("deaths", 0)
        assists = p.get("assists", 0)
        gpm = p.get("goldPerMinute", 0)
        xpm = p.get("experiencePerMinute", 0)
        nw = p.get("networth", 0)
        return f"  {player_name:<12} {hero_name:<15} {kills:>2}/{deaths:>2}/{assists:>2} {gpm:>4} {xpm:>4} {nw:>6}"

    lines.append("RADIANT" + (" (Winner)" if radiant_win else ""))
    lines.append(f"  {'Player':<12} {'Hero':<15} {'K/D/A':>8} {'GPM':>4} {'XPM':>4} {'NW':>6}")
    lines.append("  " + "-" * 55)
    for p in radiant_players:
        lines.append(format_player_line(p))

    lines.append("")
    lines.append("DIRE" + (" (Winner)" if not radiant_win else ""))
    lines.append(f"  {'Player':<12} {'Hero':<15} {'K/D/A':>8} {'GPM':>4} {'XPM':>4} {'NW':>6}")
    lines.append("  " + "-" * 55)
    for p in dire_players:
        lines.append(format_player_line(p))

    pick_bans = match.get("pickBans", [])
    if pick_bans:
        lines.append("")
        lines.append("Draft:")
        bans = [pb for pb in pick_bans if not pb.get("isPick")]
        picks = [pb for pb in pick_bans if pb.get("isPick")]
        if bans:
            lines.append(f"  Bans: {len(bans)} heroes banned")
        if picks:
            lines.append(f"  Picks: {len(picks)} heroes picked")

    return "\n".join(lines)


@tool
def stratz_hero_stats(
    hero_id: int,
) -> str:
    """Get hero statistics from Stratz API.

    Args:
        hero_id: The hero ID to look up (e.g., 1 for Anti-Mage).

    Returns:
        Hero statistics across different rank brackets.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_HERO_STATS,
            {"heroId": hero_id},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching hero stats: {e}"

    hero_stats = result.get("data", {}).get("heroStats", {})
    stats = hero_stats.get("stats", [])

    if not stats:
        return f"No statistics found for hero ID {hero_id}."

    lines: List[str] = [
        f"Hero Statistics (ID: {hero_id})",
        "",
        f"{'Bracket':<12} {'Matches':>10} {'Wins':>10} {'Win Rate':>10} {'Picks':>10} {'Bans':>10}",
        "-" * 65,
    ]

    bracket_names = {
        "IMMORTAL": "Immortal",
        "DIVINE": "Divine",
        "ANCIENT": "Ancient",
    }

    for stat in stats:
        bracket = stat.get("bracketBasicId", "Unknown")
        bracket_name = bracket_names.get(bracket, bracket)
        match_count = stat.get("matchCount", 0)
        win_count = stat.get("winCount", 0)
        pick_count = stat.get("pickCount", 0)
        ban_count = stat.get("banCount", 0)
        winrate = (win_count / match_count * 100) if match_count > 0 else 0

        lines.append(
            f"{bracket_name:<12} {match_count:>10} {win_count:>10} {winrate:>9.1f}% {pick_count:>10} {ban_count:>10}"
        )

    return "\n".join(lines)


@tool
def stratz_hero_meta(
    limit: int = 20,
) -> str:
    """Get current hero meta from Stratz API (Immortal bracket).

    Args:
        limit: Number of heroes to show (default: 20).

    Returns:
        Hero meta statistics sorted by pick rate.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    take = max(1, min(150, limit))

    try:
        result = stratz_graphql_request(
            QUERY_HERO_META,
            {"take": take},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching hero meta: {e}"

    hero_stats = result.get("data", {}).get("heroStats", {})
    stats = hero_stats.get("stats", [])

    if not stats:
        return "No hero meta data available."

    sorted_stats = sorted(stats, key=lambda x: x.get("matchCount", 0), reverse=True)[:take]

    lines: List[str] = [
        "Hero Meta (Immortal Bracket)",
        "",
        f"{'Hero ID':>8} {'Matches':>10} {'Wins':>10} {'Win Rate':>10} {'Picks':>10} {'Bans':>10}",
        "-" * 60,
    ]

    for stat in sorted_stats:
        hero_id = stat.get("heroId", 0)
        match_count = stat.get("matchCount", 0)
        win_count = stat.get("winCount", 0)
        pick_count = stat.get("pickCount", 0)
        ban_count = stat.get("banCount", 0)
        winrate = (win_count / match_count * 100) if match_count > 0 else 0

        lines.append(
            f"{hero_id:>8} {match_count:>10} {win_count:>10} {winrate:>9.1f}% {pick_count:>10} {ban_count:>10}"
        )

    return "\n".join(lines)


@tool
def stratz_live_matches() -> str:
    """Get currently live matches from Stratz API.

    Returns:
        List of live matches with teams, scores, and league info.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_LIVE_MATCHES,
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching live matches: {e}"

    live = result.get("data", {}).get("live", {})
    matches = live.get("matches", [])

    if not matches:
        return "No live matches currently."

    lines: List[str] = [
        "Live Matches",
        "",
    ]

    for match in matches[:20]:
        match_id = match.get("matchId", 0)
        game_time = match.get("gameTime", 0)
        radiant_score = match.get("radiantScore", 0)
        dire_score = match.get("direScore", 0)
        spectators = match.get("spectators", 0)
        avg_rank = match.get("averageRank")

        radiant_team = match.get("radiantTeam")
        dire_team = match.get("direTeam")
        league = match.get("league")

        radiant_name = radiant_team.get("name", "Radiant") if radiant_team else "Radiant"
        dire_name = dire_team.get("name", "Dire") if dire_team else "Dire"

        lines.append(f"Match ID: {match_id}")
        lines.append(f"  {radiant_name} {radiant_score} - {dire_score} {dire_name}")
        lines.append(f"  Game Time: {format_duration(game_time)}")

        if league:
            league_name = league.get("displayName", "Unknown")
            tier = league.get("tier", "")
            lines.append(f"  League: {league_name} (Tier {tier})")

        if avg_rank:
            lines.append(f"  Avg Rank: {rank_tier_to_str(avg_rank)}")

        lines.append(f"  Spectators: {spectators}")
        lines.append("")

    return "\n".join(lines)


@tool
def stratz_league(
    league_id: int,
) -> str:
    """Get league information from Stratz API.

    Args:
        league_id: The league ID to look up.

    Returns:
        League details including teams and standings.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_LEAGUE,
            {"leagueId": league_id},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching league data: {e}"

    league = result.get("data", {}).get("league")
    if not league:
        return f"League {league_id} not found."

    name = league.get("displayName", "Unknown")
    description = league.get("description", "")
    tier = league.get("tier", "")
    region = league.get("region", "")
    prize_pool = league.get("prizePool", 0)
    start_date = _format_timestamp(league.get("startDateTime"))
    end_date = _format_timestamp(league.get("endDateTime"))

    lines: List[str] = [
        f"League: {name}",
        f"League ID: {league_id}",
    ]

    if description:
        lines.append(f"Description: {description[:100]}")

    lines.append(f"Tier: {tier}")
    if region:
        lines.append(f"Region: {region}")
    if prize_pool:
        lines.append(f"Prize Pool: ${prize_pool:,}")
    lines.append(f"Start: {start_date}")
    lines.append(f"End: {end_date}")

    tables = league.get("tables", [])
    if tables:
        lines.append("")
        lines.append("Standings:")
        for table in tables[:1]:
            teams = table.get("tableTeams", [])
            for i, team_entry in enumerate(teams[:10], 1):
                team = team_entry.get("team", {})
                team_name = team.get("name", "Unknown")
                match_count = team_entry.get("matchCount", 0)
                wins = team_entry.get("matchWins", 0)
                points = team_entry.get("points", 0)
                lines.append(f"  {i}. {team_name}: {wins}W-{match_count - wins}L ({points} pts)")

    return "\n".join(lines)


@tool
def stratz_pro_matches(
    limit: int = 10,
) -> str:
    """Get recent professional matches from Stratz API.

    Args:
        limit: Number of matches to retrieve (default: 10, max: 50).

    Returns:
        List of recent pro matches with teams and results.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    take = max(1, min(50, limit))

    try:
        result = stratz_graphql_request(
            QUERY_PRO_MATCHES,
            {"take": take, "skip": 0},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching pro matches: {e}"

    matches = result.get("data", {}).get("proMatches", [])
    if not matches:
        return "No professional matches found."

    lines: List[str] = [
        "Recent Professional Matches",
        "",
        f"{'Match ID':<12} {'Radiant':<15} {'Dire':<15} {'Duration':>8} {'Winner':>10}",
        "-" * 65,
    ]

    for match in matches:
        match_id = match.get("id", 0)
        duration = format_duration(match.get("durationSeconds", 0))
        radiant_win = match.get("didRadiantWin", False)

        radiant_team = match.get("radiantTeam")
        dire_team = match.get("direTeam")
        league = match.get("league")

        radiant_name = (radiant_team.get("tag") or radiant_team.get("name", "Radiant"))[:15] if radiant_team else "Radiant"
        dire_name = (dire_team.get("tag") or dire_team.get("name", "Dire"))[:15] if dire_team else "Dire"
        winner = radiant_name if radiant_win else dire_name

        lines.append(f"{match_id:<12} {radiant_name:<15} {dire_name:<15} {duration:>8} {winner:>10}")

        if league:
            league_name = league.get("displayName", "")[:30]
            if league_name:
                lines.append(f"             League: {league_name}")

    return "\n".join(lines)


@tool
def stratz_team(
    team_id: int,
) -> str:
    """Get team information from Stratz API.

    Args:
        team_id: The team ID to look up.

    Returns:
        Team details including roster and win/loss record.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    try:
        result = stratz_graphql_request(
            QUERY_TEAM,
            {"teamId": team_id},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching team data: {e}"

    team = result.get("data", {}).get("team")
    if not team:
        return f"Team {team_id} not found."

    name = team.get("name", "Unknown")
    tag = team.get("tag", "")
    win_count = team.get("winCount", 0)
    loss_count = team.get("lossCount", 0)
    total = win_count + loss_count
    winrate = (win_count / total * 100) if total > 0 else 0
    last_match = _format_timestamp(team.get("lastMatchDateTime"))

    lines: List[str] = [
        f"Team: {name} [{tag}]",
        f"Team ID: {team_id}",
        "",
        f"Record: {win_count}W - {loss_count}L ({winrate:.1f}%)",
        f"Last Match: {last_match}",
    ]

    members = team.get("members", [])
    if members:
        lines.append("")
        lines.append("Roster:")
        for member in members:
            steam_acc = member.get("steamAccount", {})
            player_name = steam_acc.get("name", "Unknown")
            pro = steam_acc.get("proSteamAccount")
            if pro:
                pro_name = pro.get("name")
                position = pro.get("position")
                if pro_name:
                    player_name = pro_name
                if position:
                    lines.append(f"  - {player_name} (Pos {position})")
                else:
                    lines.append(f"  - {player_name}")
            else:
                lines.append(f"  - {player_name}")

    return "\n".join(lines)


@tool
def stratz_player_heroes(
    steam_account_id: int,
    limit: int = 10,
) -> str:
    """Get player's hero performance statistics from Stratz API.

    Args:
        steam_account_id: The player's Steam account ID (32-bit).
        limit: Number of heroes to show (default: 10).

    Returns:
        Player's most played heroes with performance stats.
    """
    cache = Cache(DEFAULT_CACHE_DIR)
    take = max(1, min(50, limit))

    try:
        result = stratz_graphql_request(
            QUERY_PLAYER_HERO_PERFORMANCE,
            {"steamAccountId": steam_account_id, "take": take},
            cache=cache,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        return f"Error fetching player hero performance: {e}"

    player = result.get("data", {}).get("player")
    if not player:
        return f"Player with Steam Account ID {steam_account_id} not found."

    heroes = player.get("heroesPerformance", [])
    if not heroes:
        return f"No hero performance data for player {steam_account_id}."

    lines: List[str] = [
        f"Hero Performance for Player {steam_account_id}",
        "",
        f"{'Hero':<18} {'Games':>6} {'Wins':>6} {'WR%':>6} {'Avg K':>6} {'Avg D':>6} {'Avg A':>6} {'GPM':>5}",
        "-" * 70,
    ]

    for hero_perf in heroes:
        hero = hero_perf.get("hero", {})
        hero_name = hero.get("displayName", "Unknown")[:18]
        match_count = hero_perf.get("matchCount", 0)
        win_count = hero_perf.get("winCount", 0)
        winrate = (win_count / match_count * 100) if match_count > 0 else 0
        avg_kills = hero_perf.get("avgKills", 0) or 0
        avg_deaths = hero_perf.get("avgDeaths", 0) or 0
        avg_assists = hero_perf.get("avgAssists", 0) or 0
        avg_gpm = hero_perf.get("avgGpm", 0) or 0

        lines.append(
            f"{hero_name:<18} {match_count:>6} {win_count:>6} {winrate:>5.1f}% {avg_kills:>6.1f} {avg_deaths:>6.1f} {avg_assists:>6.1f} {avg_gpm:>5.0f}"
        )

    return "\n".join(lines)
