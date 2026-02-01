"""Internationalization utilities."""

from __future__ import annotations

from typing import Any, Dict

_I18N: Dict[str, Dict[str, str]] = {
    "en": {
        "no_hits": "No matches found for '{keyword}' in the last {n} patches.\n",
        "no_patch_matches": "No matching changes in this patch.",
        "unknown_item": "Unknown item: {keyword}",
        "unknown_item_hint": "Run: {cmd}",
        "unknown_item_suggestions": "Similar items:",
        "unknown_item_examples": "Example items:",
        "error_prefix": "Error: ",
        "labels.hero_changes": "Hero Changes",
        "labels.ability_changes": "Ability Changes",
        "labels.talent_changes": "Talent Changes",
        "labels.item_changes": "Item Changes",
        "labels.neutral_item_changes": "Neutral Items",
        "winrate.hero": "Hero: {hero} (id={hero_id})",
        "winrate.range": "Range: last {n} patches (patch windows from dota2.com, winrate from OpenDota Explorer)",
        "winrate.table.patch": "Patch",
        "winrate.table.date": "Date",
        "winrate.table.games": "Games",
        "winrate.table.winrate": "Winrate",
        "winrate.table.delta": "Δ(pp)",
        "winrate.unknown_hero": "Unknown hero: {hero}",
        "winrate.suggestions": "Similar heroes:",
        "winrate.hint_list": "Run: {cmd}",
    },
    "zh": {
        "no_hits": "最近 {n} 个版本中未找到匹配：{keyword}\n",
        "no_patch_matches": "该版本没有匹配的改动。",
        "unknown_item": "未识别的道具：{keyword}",
        "unknown_item_hint": "可运行：{cmd}",
        "unknown_item_suggestions": "相近的道具候选：",
        "unknown_item_examples": "部分可用道具示例：",
        "error_prefix": "错误：",
        "labels.hero_changes": "英雄改动",
        "labels.ability_changes": "技能改动",
        "labels.talent_changes": "天赋改动",
        "labels.item_changes": "道具改动",
        "labels.neutral_item_changes": "中立道具",
        "winrate.hero": "英雄：{hero} (id={hero_id})",
        "winrate.range": "范围：最近 {n} 个版本（版本时间来自 dota2.com，胜率来自 OpenDota Explorer）",
        "winrate.table.patch": "版本",
        "winrate.table.date": "日期",
        "winrate.table.games": "场次",
        "winrate.table.winrate": "胜率",
        "winrate.table.delta": "Δ(pp)",
        "winrate.unknown_hero": "未识别的英雄：{hero}",
        "winrate.suggestions": "相近的英雄候选：",
        "winrate.hint_list": "可运行：{cmd}",
    },
}


def _lang_key(language: str) -> str:
    """Normalize datafeed language to a compact language key."""
    lang = (language or "").strip().lower()
    return "zh" if lang in {"chinese", "schinese", "tchinese", "zh", "cn"} else "en"


def datafeed_language(language: str) -> str:
    """Map user-facing language to dota2.com datafeed language."""
    lang = (language or "").strip().lower()
    if lang in {"chinese", "zh", "cn"}:
        return "schinese"
    if lang in {"schinese", "tchinese", "english"}:
        return lang
    return "english"


def display_language(language: str) -> str:
    """Return a canonical, user-facing language token."""
    return "chinese" if _lang_key(language) == "zh" else "english"


def t(language: str, key: str, **kwargs: Any) -> str:
    """Get translated string."""
    lang = _lang_key(language)
    template = _I18N.get(lang, _I18N["en"]).get(key) or _I18N["en"].get(key) or key
    return template.format(**kwargs)


def labels_for(language: str) -> Dict[str, str]:
    """Get labels dictionary for a language."""
    return {
        "hero_changes": t(language, "labels.hero_changes"),
        "ability_changes": t(language, "labels.ability_changes"),
        "talent_changes": t(language, "labels.talent_changes"),
        "item_changes": t(language, "labels.item_changes"),
        "neutral_item_changes": t(language, "labels.neutral_item_changes"),
    }
