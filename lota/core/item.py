"""Item data loading functions."""

from __future__ import annotations

from typing import Dict

from lota.core.cache import Cache
from lota.core.endpoints import endpoint_item_list
from lota.core.http import fetch_json
from lota.core.utils import strip_html


def load_item_map(
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Dict[int, str]:
    """Load item_id -> localized name mapping."""
    obj = fetch_json(
        endpoint_item_list(language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    itemabilities = (
        (((obj or {}).get("result") or {}).get("data") or {}).get("itemabilities") or []
    )
    out: Dict[int, str] = {}
    for it in itemabilities:
        try:
            aid = int(it.get("id"))
        except Exception:
            continue
        name = (
            it.get("name_loc")
            or it.get("name_english_loc")
            or it.get("name")
            or f"ItemAbility#{aid}"
        )
        out[aid] = strip_html(str(name))
    return out
