"""Patch note loading and parsing functions."""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, Iterable, List

from lota.core.cache import Cache
from lota.core.endpoints import endpoint_patch_list, endpoint_patch_notes
from lota.core.errors import LotaError
from lota.core.http import fetch_json
from lota.core.utils import strip_html


@dataclasses.dataclass
class Hit:
    """A single patch note hit."""

    patch: str
    patch_date: str
    scope: str
    section: str
    entity: str
    text: str


def load_patch_list(
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> List[Dict[str, Any]]:
    """Load the list of patches from dota2.com."""
    obj = fetch_json(
        endpoint_patch_list(language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )
    patches = obj.get("patches") or []
    if not isinstance(patches, list):
        raise LotaError("Invalid patch list format")
    patches = sorted(patches, key=lambda p: int(p.get("patch_timestamp", 0)))
    return patches


def load_patch_notes(
    version: str,
    *,
    language: str,
    cache: Cache,
    timeout: int,
    user_agent: str,
    debug: bool = False,
) -> Dict[str, Any]:
    """Load patch notes for a specific version."""
    return fetch_json(
        endpoint_patch_notes(version, language),
        cache=cache,
        timeout=timeout,
        user_agent=user_agent,
        debug=debug,
    )


def iter_hits_from_patch(
    patch_obj: Dict[str, Any],
    *,
    patch_number: str,
    patch_date: str,
    hero_map: Dict[int, str],
    item_map: Dict[int, str],
    ability_map: Dict[int, str],
    labels: Dict[str, str],
) -> Iterable[Hit]:
    """Iterate over all hits from a patch object."""
    for sec in patch_obj.get("general_notes") or []:
        title = strip_html(str(sec.get("title") or "General"))
        for g in sec.get("generic") or []:
            note = strip_html(str(g.get("note") or ""))
            if note:
                yield Hit(patch_number, patch_date, "general", title, "", note)

    for h in patch_obj.get("heroes") or []:
        try:
            hid = int(h.get("hero_id"))
        except Exception:
            hid = -1
        hname = hero_map.get(hid, f"Hero#{hid}" if hid != -1 else "Hero")
        for n in h.get("hero_notes") or []:
            note = strip_html(str(n.get("note") or ""))
            if note:
                yield Hit(
                    patch_number,
                    patch_date,
                    "heroes",
                    labels["hero_changes"],
                    hname,
                    note,
                )

        for ab in h.get("abilities") or []:
            try:
                abid = int(ab.get("ability_id"))
            except Exception:
                abid = -1
            abname = ability_map.get(
                abid, f"Ability#{abid}" if abid != -1 else "Ability"
            )
            for n in ab.get("ability_notes") or []:
                note = strip_html(str(n.get("note") or ""))
                if note:
                    yield Hit(
                        patch_number,
                        patch_date,
                        "heroes",
                        labels["ability_changes"],
                        hname,
                        f"{abname}: {note}",
                    )
        for n in h.get("talent_notes") or []:
            note = strip_html(str(n.get("note") or ""))
            if note:
                yield Hit(
                    patch_number,
                    patch_date,
                    "heroes",
                    labels["talent_changes"],
                    hname,
                    note,
                )

    for label, scope_key in (("items", "items"), ("neutral_items", "neutral_items")):
        for it in patch_obj.get(scope_key) or []:
            try:
                aid = int(it.get("ability_id"))
            except Exception:
                aid = -1
            iname = item_map.get(aid, f"ItemAbility#{aid}" if aid != -1 else "Item")
            for n in it.get("ability_notes") or []:
                note = strip_html(str(n.get("note") or ""))
                if note:
                    section = (
                        labels["item_changes"]
                        if label == "items"
                        else labels["neutral_item_changes"]
                    )
                    yield Hit(patch_number, patch_date, label, section, iname, note)

    for sec in patch_obj.get("neutral_creeps") or []:
        if isinstance(sec, dict):
            title = strip_html(str(sec.get("title") or "Neutral Creeps"))
            generic = sec.get("generic") or sec.get("notes") or []
            if isinstance(generic, list):
                for g in generic:
                    if isinstance(g, dict):
                        note = strip_html(str(g.get("note") or ""))
                    else:
                        note = strip_html(str(g))
                    if note:
                        yield Hit(
                            patch_number, patch_date, "neutral_creeps", title, "", note
                        )


def make_matcher(keyword: str, *, regex: bool, ignore_case: bool = True):
    """Create a matcher function for searching patch notes."""
    if regex:
        flags = re.I if ignore_case else 0
        try:
            r = re.compile(keyword, flags)
        except re.error as e:
            raise LotaError(f"Invalid regex: {e}") from e

        def _m(s: str) -> bool:
            return bool(r.search(s))

        return _m

    if ignore_case:
        kw = keyword.lower()

        def _m(s: str) -> bool:
            return kw in s.lower()

        return _m
    else:

        def _m(s: str) -> bool:
            return keyword in s

        return _m
