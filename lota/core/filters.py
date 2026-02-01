"""Common filter parameters for OpenDota API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlayerMatchFilters:
    """Common filter parameters for player match queries.

    These parameters are shared across multiple OpenDota player endpoints:
    - /players/{account_id}/matches
    - /players/{account_id}/heroes
    - /players/{account_id}/peers
    - /players/{account_id}/pros
    - /players/{account_id}/totals
    - /players/{account_id}/counts
    - /players/{account_id}/histograms/{field}
    - /players/{account_id}/wardmap
    - /players/{account_id}/wordcloud
    - /players/{account_id}/wl
    """

    limit: Optional[int] = None
    offset: Optional[int] = None
    win: Optional[int] = None
    patch: Optional[int] = None
    game_mode: Optional[int] = None
    lobby_type: Optional[int] = None
    region: Optional[int] = None
    date: Optional[int] = None
    lane_role: Optional[int] = None
    hero_id: Optional[int] = None
    is_radiant: Optional[int] = None
    included_account_id: List[int] = field(default_factory=list)
    excluded_account_id: List[int] = field(default_factory=list)
    with_hero_id: List[int] = field(default_factory=list)
    against_hero_id: List[int] = field(default_factory=list)
    significant: Optional[int] = None
    having: Optional[int] = None
    sort: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for URL query parameters."""
        params: Dict[str, Any] = {
            "limit": self.limit,
            "offset": self.offset,
            "win": self.win,
            "patch": self.patch,
            "game_mode": self.game_mode,
            "lobby_type": self.lobby_type,
            "region": self.region,
            "date": self.date,
            "lane_role": self.lane_role,
            "hero_id": self.hero_id,
            "is_radiant": self.is_radiant,
            "significant": self.significant,
            "having": self.having,
            "sort": self.sort,
        }
        if self.included_account_id:
            params["included_account_id"] = self.included_account_id
        if self.excluded_account_id:
            params["excluded_account_id"] = self.excluded_account_id
        if self.with_hero_id:
            params["with_hero_id"] = self.with_hero_id
        if self.against_hero_id:
            params["against_hero_id"] = self.against_hero_id
        return {k: v for k, v in params.items() if v is not None}


GAME_MODES = {
    0: "Unknown",
    1: "All Pick",
    2: "Captain's Mode",
    3: "Random Draft",
    4: "Single Draft",
    5: "All Random",
    6: "Intro",
    7: "Diretide",
    8: "Reverse Captain's Mode",
    9: "Greeviling",
    10: "Tutorial",
    11: "Mid Only",
    12: "Least Played",
    13: "Limited Heroes",
    14: "Compendium Matchmaking",
    15: "Custom",
    16: "Captain's Draft",
    17: "Balanced Draft",
    18: "Ability Draft",
    19: "Event",
    20: "All Random Deathmatch",
    21: "1v1 Mid",
    22: "All Draft",
    23: "Turbo",
    24: "Mutation",
}

LOBBY_TYPES = {
    0: "Normal",
    1: "Practice",
    2: "Tournament",
    3: "Tutorial",
    4: "Co-op with bots",
    5: "Ranked Team MM",
    6: "Ranked Solo MM",
    7: "Ranked",
    8: "1v1 Mid",
    9: "Battle Cup",
}

LANE_ROLES = {
    1: "Safe Lane",
    2: "Mid Lane",
    3: "Off Lane",
    4: "Jungle",
}

REGIONS = {
    0: "Automatic",
    1: "US West",
    2: "US East",
    3: "Europe West",
    5: "Southeast Asia",
    6: "Dubai",
    7: "Australia",
    8: "Stockholm",
    9: "Austria",
    10: "Brazil",
    11: "South Africa",
    12: "PW Telecom Shanghai",
    13: "PW Unicom",
    14: "Chile",
    15: "Peru",
    16: "India",
    17: "PW Telecom Guangdong",
    18: "PW Telecom Zhejiang",
    19: "Japan",
    20: "PW Telecom Wuhan",
    25: "PW Unicom Tianjin",
    37: "Taiwan",
    38: "Argentina",
}

RANK_TIERS = {
    0: "Uncalibrated",
    10: "Herald 0",
    11: "Herald 1",
    12: "Herald 2",
    13: "Herald 3",
    14: "Herald 4",
    15: "Herald 5",
    20: "Guardian 0",
    21: "Guardian 1",
    22: "Guardian 2",
    23: "Guardian 3",
    24: "Guardian 4",
    25: "Guardian 5",
    30: "Crusader 0",
    31: "Crusader 1",
    32: "Crusader 2",
    33: "Crusader 3",
    34: "Crusader 4",
    35: "Crusader 5",
    40: "Archon 0",
    41: "Archon 1",
    42: "Archon 2",
    43: "Archon 3",
    44: "Archon 4",
    45: "Archon 5",
    50: "Legend 0",
    51: "Legend 1",
    52: "Legend 2",
    53: "Legend 3",
    54: "Legend 4",
    55: "Legend 5",
    60: "Ancient 0",
    61: "Ancient 1",
    62: "Ancient 2",
    63: "Ancient 3",
    64: "Ancient 4",
    65: "Ancient 5",
    70: "Divine 0",
    71: "Divine 1",
    72: "Divine 2",
    73: "Divine 3",
    74: "Divine 4",
    75: "Divine 5",
    80: "Immortal",
}


def rank_tier_to_str(rank_tier: Optional[int]) -> str:
    """Convert rank tier number to readable string."""
    if not rank_tier:
        return "Unknown"
    if rank_tier in RANK_TIERS:
        return RANK_TIERS[rank_tier]
    medal = rank_tier // 10
    stars = rank_tier % 10
    medals = {
        1: "Herald",
        2: "Guardian",
        3: "Crusader",
        4: "Archon",
        5: "Legend",
        6: "Ancient",
        7: "Divine",
        8: "Immortal",
    }
    medal_name = medals.get(medal, "Unknown")
    if medal == 8:
        return "Immortal"
    return f"{medal_name} {stars}" if stars else medal_name


def game_mode_to_str(game_mode: Optional[int]) -> str:
    """Convert game mode ID to readable string."""
    if game_mode is None:
        return "Unknown"
    return GAME_MODES.get(game_mode, f"Mode {game_mode}")


def lobby_type_to_str(lobby_type: Optional[int]) -> str:
    """Convert lobby type ID to readable string."""
    if lobby_type is None:
        return "Unknown"
    return LOBBY_TYPES.get(lobby_type, f"Lobby {lobby_type}")


def lane_role_to_str(lane_role: Optional[int]) -> str:
    """Convert lane role ID to readable string."""
    if lane_role is None:
        return "Unknown"
    return LANE_ROLES.get(lane_role, f"Lane {lane_role}")


def region_to_str(region: Optional[int]) -> str:
    """Convert region ID to readable string."""
    if region is None:
        return "Unknown"
    return REGIONS.get(region, f"Region {region}")
