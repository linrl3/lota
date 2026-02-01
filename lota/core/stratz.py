"""Stratz GraphQL API client."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from typing import Any, Dict, Optional

from lota.core.cache import Cache
from lota.core.errors import LotaError

STRATZ_GRAPHQL_ENDPOINT = "https://api.stratz.com/graphql"
STRATZ_USER_AGENT = "lota-cli/0.2 (+https://stratz.com)"


def get_stratz_api_key() -> Optional[str]:
    return os.environ.get("STRATZ_API_KEY")


def stratz_graphql_request(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    *,
    cache: Optional[Cache] = None,
    timeout: int = 30,
    debug: bool = False,
) -> Dict[str, Any]:
    api_key = get_stratz_api_key()
    if not api_key:
        raise LotaError(
            "STRATZ_API_KEY not set. Get your API key at https://stratz.com/api "
            "and set it in your environment or .env file."
        )

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    payload_json = json.dumps(payload)
    cache_key = f"stratz:{hash(payload_json)}"

    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            if debug:
                sys.stderr.write(f"[DEBUG][STRATZ CACHE HIT] {cache_key}\n")
            return json.loads(cached)

    if debug:
        sys.stderr.write(
            f"[DEBUG][STRATZ] POST {STRATZ_GRAPHQL_ENDPOINT} timeout={timeout}s\n"
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": STRATZ_USER_AGENT,
    }

    t0 = time.time()
    req = urllib.request.Request(
        STRATZ_GRAPHQL_ENDPOINT,
        data=payload_json.encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            dt_ms = int((time.time() - t0) * 1000)
            if debug:
                sys.stderr.write(
                    f"[DEBUG][STRATZ] <- bytes={len(data)} elapsed_ms={dt_ms}\n"
                )
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise LotaError(f"Stratz API error ({e.code}): {error_body}") from e
    except Exception as e:
        raise LotaError(f"Stratz API request failed: {e}") from e

    if not data:
        raise LotaError("Empty response from Stratz API")

    try:
        result = json.loads(data)
    except json.JSONDecodeError as e:
        raise LotaError(f"Failed to parse Stratz API response: {e}") from e

    if "errors" in result and result["errors"]:
        error_messages = [err.get("message", str(err)) for err in result["errors"]]
        raise LotaError(f"Stratz GraphQL errors: {'; '.join(error_messages)}")

    if cache:
        cache.set(cache_key, data)

    return result


QUERY_PLAYER = """
query GetPlayer($steamAccountId: Long!) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    steamAccount {
      id
      name
      avatar
      profileUri
      isAnonymous
      seasonRank
      seasonLeaderboardRank
      proSteamAccount {
        name
        team {
          id
          name
          tag
        }
      }
    }
    matchCount
    winCount
    firstMatchDate
    lastMatchDate
  }
}
"""

QUERY_PLAYER_MATCHES = """
query GetPlayerMatches($steamAccountId: Long!, $take: Int, $skip: Int) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { take: $take, skip: $skip }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      gameMode
      lobbyType
      players(steamAccountId: $steamAccountId) {
        isRadiant
        hero {
          id
          shortName
          displayName
        }
        kills
        deaths
        assists
        networth
        goldPerMinute
        experiencePerMinute
        isVictory
        position
        lane
        role
      }
    }
  }
}
"""

QUERY_MATCH = """
query GetMatch($matchId: Long!) {
  match(id: $matchId) {
    id
    didRadiantWin
    durationSeconds
    startDateTime
    endDateTime
    gameMode
    lobbyType
    regionId
    rank
    bracket
    parsedDateTime
    analysisOutcome
    radiantKills
    direKills
    players {
      steamAccountId
      steamAccount {
        name
        proSteamAccount {
          name
        }
      }
      isRadiant
      hero {
        id
        shortName
        displayName
      }
      kills
      deaths
      assists
      networth
      goldPerMinute
      experiencePerMinute
      numLastHits
      numDenies
      level
      position
      lane
      role
      isVictory
      item0Id
      item1Id
      item2Id
      item3Id
      item4Id
      item5Id
      backpack0Id
      backpack1Id
      backpack2Id
    }
    pickBans {
      isPick
      heroId
      order
      isRadiant
    }
  }
}
"""

QUERY_HERO_STATS = """
query GetHeroStats($heroId: Short!) {
  heroStats {
    stats(heroIds: [$heroId], bracketBasicIds: [IMMORTAL, DIVINE, ANCIENT]) {
      heroId
      matchCount
      winCount
      bracketBasicId
      pickCount
      banCount
    }
  }
}
"""

QUERY_HERO_META = """
query GetHeroMeta($take: Int) {
  heroStats {
    stats(bracketBasicIds: [IMMORTAL], take: $take) {
      heroId
      matchCount
      winCount
      pickCount
      banCount
    }
  }
}
"""

QUERY_LIVE_MATCHES = """
query GetLiveMatches {
  live {
    matches {
      matchId
      gameTime
      radiantScore
      direScore
      radiantLead
      gameState
      averageRank
      delay
      spectators
      radiantTeam {
        id
        name
        tag
      }
      direTeam {
        id
        name
        tag
      }
      players {
        steamAccountId
        heroId
        isRadiant
        numKills
        numDeaths
        numAssists
        goldPerMinute
        experiencePerMinute
        networth
      }
      league {
        id
        displayName
        tier
      }
    }
  }
}
"""

QUERY_LEAGUE = """
query GetLeague($leagueId: Int!) {
  league(id: $leagueId) {
    id
    displayName
    description
    tier
    region
    startDateTime
    endDateTime
    prizePool
    nodeGroups {
      id
      name
      nodeGroupType
    }
    tables {
      tableTeams {
        team {
          id
          name
          tag
        }
        matchCount
        matchWins
        points
      }
    }
  }
}
"""

QUERY_PRO_MATCHES = """
query GetProMatches($take: Int, $skip: Int) {
  proMatches(request: { take: $take, skip: $skip }) {
    id
    didRadiantWin
    durationSeconds
    startDateTime
    gameMode
    lobbyType
    radiantTeam {
      id
      name
      tag
    }
    direTeam {
      id
      name
      tag
    }
    league {
      id
      displayName
      tier
    }
  }
}
"""

QUERY_TEAM = """
query GetTeam($teamId: Int!) {
  team(teamId: $teamId) {
    id
    name
    tag
    logo
    winCount
    lossCount
    lastMatchDateTime
    members {
      steamAccountId
      steamAccount {
        name
        proSteamAccount {
          name
          position
        }
      }
    }
  }
}
"""

QUERY_PLAYER_HERO_PERFORMANCE = """
query GetPlayerHeroPerformance($steamAccountId: Long!, $take: Int) {
  player(steamAccountId: $steamAccountId) {
    heroesPerformance(request: { take: $take }) {
      hero {
        id
        shortName
        displayName
      }
      matchCount
      winCount
      avgKills
      avgDeaths
      avgAssists
      avgGpm
      avgXpm
    }
  }
}
"""
