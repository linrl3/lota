"""Global constants for lota."""

DEFAULT_CACHE_DIR = ".lota-cache"
DEFAULT_TIMEOUT = 20
DEFAULT_TIMEOUT_LONG = 30
DEFAULT_USER_AGENT = "lota-cli/0.2 (+https://www.dota2.com)"

NPC_HERO_PREFIX = "npc_dota_hero_"

ITEM_STAGE_MAP = {
    "start": "start_game_items",
    "early": "early_game_items",
    "mid": "mid_game_items",
    "late": "late_game_items",
}

ITEM_STAGE_DISPLAY = {
    "start_game_items": "Starting Items",
    "early_game_items": "Early Game Items",
    "mid_game_items": "Mid Game Items",
    "late_game_items": "Late Game Items",
}
