"""Command-line interface for lota."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

from lota.core import DEFAULT_USER_AGENT
from lota.core.ability import load_ability_map
from lota.core.cache import Cache
from lota.core.errors import LotaError
from lota.core.hero import (
    load_hero_map,
    load_hero_name_to_id,
    load_hero_short_map,
    opendota_hero_winrate_by_time_range,
)
from lota.core.http import download_bytes
from lota.core.i18n import display_language, labels_for, t
from lota.core.item import load_item_map
from lota.core.patch import (
    Hit,
    iter_hits_from_patch,
    load_patch_list,
    load_patch_notes,
    make_matcher,
)
from lota.core.utils import filter_and_limit, fmt_date, norm_for_match, suggest_names

ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"
ANSI_DIM = "\x1b[2m"
ANSI_FG_RED = "\x1b[31m"
ANSI_FG_GREEN = "\x1b[32m"
ANSI_FG_YELLOW = "\x1b[33m"
ANSI_FG_BLUE = "\x1b[34m"
ANSI_FG_MAGENTA = "\x1b[35m"
ANSI_FG_CYAN = "\x1b[36m"


def supports_color(mode: str, stream) -> bool:
    m = (mode or "auto").lower()
    if m == "never":
        return False
    if m == "always":
        return True
    try:
        return bool(
            getattr(stream, "isatty")() and os.environ.get("TERM", "") != "dumb"
        )
    except Exception:
        return False


def _ansi_wrap(s: str, *codes: str) -> str:
    if not codes:
        return s
    return "".join(codes) + s + ANSI_RESET


_RE_LEVEL = re.compile(r"\bLevel\s+(\d+)\b")
_RE_SIGNED_NUM = re.compile(r"(?<![\w/])([+-]\d+(?:\.\d+)?%?)")
_RE_FROM_TO = re.compile(
    r"\b(?P<dir>increased|decreased)\s+from\s+(?P<from>[^\s,;]+)\s+to\s+(?P<to>[^\s,;]+)",
    re.I,
)


def stylize_note(text: str, *, color_enabled: bool) -> str:
    if not color_enabled or not text:
        return text

    def repl_level(m: re.Match) -> str:
        return _ansi_wrap(m.group(0), ANSI_BOLD, ANSI_FG_YELLOW)

    text = _RE_LEVEL.sub(repl_level, text)

    def repl_from_to(m: re.Match) -> str:
        direction = m.group("dir")
        frm = m.group("from")
        to = m.group("to")
        dir_code = ANSI_FG_GREEN if direction.lower() == "increased" else ANSI_FG_RED
        return (
            _ansi_wrap(direction, ANSI_BOLD, dir_code)
            + " from "
            + _ansi_wrap(frm, ANSI_DIM)
            + " to "
            + _ansi_wrap(to, ANSI_BOLD)
        )

    text = _RE_FROM_TO.sub(repl_from_to, text)

    def repl_signed(m: re.Match) -> str:
        val = m.group(1)
        c = ANSI_FG_GREEN if val.startswith("+") else ANSI_FG_RED
        return _ansi_wrap(val, ANSI_BOLD, c)

    text = _RE_SIGNED_NUM.sub(repl_signed, text)
    return text


def stylize_patch_header(patch: str, date: str, *, color_enabled: bool) -> str:
    if not color_enabled:
        return f"== {patch}" + (f" ({date})" if date else "") + " ==\n"
    p = _ansi_wrap(patch, ANSI_BOLD, ANSI_FG_BLUE)
    d = _ansi_wrap(f"({date})", ANSI_DIM) if date else ""
    mid = f" {p}" + (f" {d}" if d else "")
    return f"=={mid} ==\n"


def hero_image_urls(hero_short: str) -> List[str]:
    s = hero_short
    return [
        f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{s}.png",
        f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/{s}_full.png",
        f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/{s}_lg.png",
    ]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_bytes_atomic(path: str, data: bytes) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def maybe_download_hero_image(
    hero_short: str,
    *,
    out_dir: str,
    timeout: int,
    user_agent: str,
    debug: bool,
    overwrite: bool,
) -> Optional[str]:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"{hero_short}.png")
    if os.path.exists(out_path) and not overwrite:
        if debug:
            sys.stderr.write(f"[DEBUG][HERO IMG] exists: {out_path}\n")
        return out_path

    last_err: Optional[str] = None
    for url in hero_image_urls(hero_short):
        try:
            data, headers, status = download_bytes(
                url, timeout=timeout, user_agent=user_agent, debug=debug
            )
            ct = (headers.get("content-type") or "").lower()
            if status >= 400 or not data:
                last_err = f"HTTP {status}"
                continue
            if not ct.startswith("image/"):
                last_err = f"unexpected content-type: {ct}"
                continue
            save_bytes_atomic(out_path, data)
            if debug:
                sys.stderr.write(
                    f"[DEBUG][HERO IMG] saved: {out_path} (from {url})\n"
                )
            return out_path
        except Exception as e:
            last_err = str(e)
            continue

    if debug:
        sys.stderr.write(f"[DEBUG][HERO IMG] failed for '{hero_short}': {last_err}\n")
    return None


def cmd_chat(args: argparse.Namespace) -> int:
    from lota.agent import run_chat

    return run_chat()


def cmd_scan(args: argparse.Namespace) -> int:
    cache = Cache(None if args.no_cache else args.cache_dir)
    matcher = make_matcher(args.keyword, regex=args.regex)
    labels = labels_for(args.language)
    color_enabled = supports_color(args.color, sys.stdout)

    patches = load_patch_list(
        language=args.language,
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )
    if not patches:
        raise LotaError("No patches found")

    last_n = max(1, int(args.last))
    selected = patches[-last_n:]

    need_hero = args.scope in ("all", "heroes")
    need_item = args.scope in ("all", "items", "neutral_items")
    hero_map = (
        load_hero_map(
            language=args.language,
            cache=cache,
            timeout=args.timeout,
            user_agent=args.user_agent,
            debug=args.debug,
        )
        if need_hero
        else {}
    )
    ability_map = (
        load_ability_map(
            language=args.language,
            cache=cache,
            timeout=args.timeout,
            user_agent=args.user_agent,
            debug=args.debug,
        )
        if need_hero
        else {}
    )
    item_map = (
        load_item_map(
            language=args.language,
            cache=cache,
            timeout=args.timeout,
            user_agent=args.user_agent,
            debug=args.debug,
        )
        if need_item
        else {}
    )

    hero_name_query = False
    hero_short: Optional[str] = None
    if (
        args.format == "text"
        and not args.regex
        and args.scope in ("all", "heroes")
        and hero_map
    ):
        kw = norm_for_match(args.keyword)
        hero_norms = {norm_for_match(n) for n in hero_map.values() if n}
        hero_name_query = kw in hero_norms
        if hero_name_query:
            short_map = load_hero_short_map(
                language=args.language,
                cache=cache,
                timeout=args.timeout,
                user_agent=args.user_agent,
                debug=args.debug,
            )
            hero_short = short_map.get(kw)

    if hero_short and args.hero_image != "never":
        if args.hero_image == "always" or (
            args.hero_image == "auto" and hero_name_query and args.format == "text"
        ):
            saved = maybe_download_hero_image(
                hero_short,
                out_dir=args.hero_image_dir,
                timeout=args.timeout,
                user_agent=args.user_agent,
                debug=args.debug,
                overwrite=args.hero_image_overwrite,
            )
            if saved:
                msg = f"Hero image saved: {os.path.abspath(saved)}\n"
                if args.format == "text":
                    sys.stdout.write(msg)
                else:
                    sys.stderr.write(msg)

    if args.format == "text" and args.scope in ("items", "neutral_items") and not args.regex:
        item_names = sorted(set(item_map.values()))
        kw = norm_for_match(args.keyword)
        if kw and item_names and not any(kw in norm_for_match(n) for n in item_names):
            sys.stdout.write(
                t(args.language, "unknown_item", keyword=args.keyword) + "\n"
            )
            sys.stdout.write(
                t(
                    args.language,
                    "unknown_item_hint",
                    cmd=f"lota list items --language {display_language(args.language)}",
                )
                + "\n"
            )
            sugg = suggest_names(args.keyword, item_names, limit=20)
            if sugg:
                sys.stdout.write(t(args.language, "unknown_item_suggestions") + "\n")
                for s in sugg:
                    sys.stdout.write(f"- {s}\n")
            else:
                sys.stdout.write(t(args.language, "unknown_item_examples") + "\n")
                for s in item_names[:20]:
                    sys.stdout.write(f"- {s}\n")
            return 0

    include_patch_misses = args.format == "text" and (
        args.scope in ("items", "neutral_items") or hero_name_query
    )

    hits: List[Hit] = []
    hits_by_patch: Dict[str, List[Hit]] = {}
    scan_order: List[tuple] = []
    total_kept = 0

    for p in reversed(selected):
        ver = str(p.get("patch_number") or p.get("patch_name") or "").strip()
        if not ver:
            continue
        ts = int(p.get("patch_timestamp") or 0)
        date = fmt_date(ts)
        scan_order.append((ver, date))

        pobj = load_patch_notes(
            ver,
            language=args.language,
            cache=cache,
            timeout=args.timeout,
            user_agent=args.user_agent,
            debug=args.debug,
        )
        if pobj is None:
            continue

        patch_has_match = False
        for h in iter_hits_from_patch(
            pobj,
            patch_number=ver,
            patch_date=date,
            hero_map=hero_map,
            item_map=item_map,
            ability_map=ability_map,
            labels=labels,
        ):
            if args.scope != "all" and h.scope != args.scope:
                continue
            if (
                matcher(h.text)
                or (h.entity and matcher(h.entity))
                or (h.section and matcher(h.section))
            ):
                patch_has_match = True
                if total_kept < args.max_hits:
                    hits.append(h)
                    hits_by_patch.setdefault(h.patch, []).append(h)
                    total_kept += 1
                else:
                    if include_patch_misses:
                        break

        if include_patch_misses and not patch_has_match:
            hits_by_patch.setdefault(ver, [])

    if args.format == "json":
        payload = {
            "keyword": args.keyword,
            "last": last_n,
            "language": args.language,
            "scope": args.scope,
            "hits": [dataclasses.asdict(h) for h in hits],
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0

    if not hits and not include_patch_misses:
        sys.stdout.write(t(args.language, "no_hits", n=last_n, keyword=args.keyword))
        return 0

    if include_patch_misses:
        for patch, date in scan_order:
            items = hits_by_patch.get(patch, [])
            sys.stdout.write(stylize_patch_header(patch, date, color_enabled=color_enabled))
            if items:
                for h in items:
                    section = h.section
                    if color_enabled:
                        if section == labels["ability_changes"]:
                            section = _ansi_wrap(section, ANSI_BOLD, ANSI_FG_CYAN)
                        elif section == labels["talent_changes"]:
                            section = _ansi_wrap(section, ANSI_BOLD, ANSI_FG_MAGENTA)
                    prefix = f"[{section}]"
                    if h.entity and not (hero_name_query and h.scope == "heroes"):
                        prefix += f"[{h.entity}]"
                    text = stylize_note(h.text, color_enabled=color_enabled).replace(
                        "\n", "\n    "
                    )
                    sys.stdout.write(f"- {prefix} {text}\n")
            else:
                if hero_name_query:
                    sys.stdout.write(
                        f"- [{labels['hero_changes']}] {t(args.language, 'no_patch_matches')}\n"
                    )
                else:
                    scope_label = (
                        labels["item_changes"]
                        if args.scope == "items"
                        else labels["neutral_item_changes"]
                    )
                    sys.stdout.write(
                        f"- [{scope_label}] {t(args.language, 'no_patch_matches')}\n"
                    )
            sys.stdout.write("\n")

        if not hits:
            sys.stdout.write(t(args.language, "no_hits", n=last_n, keyword=args.keyword))
        return 0

    by_patch: Dict[str, List[Hit]] = {}
    for h in hits:
        by_patch.setdefault(h.patch, []).append(h)
    for patch in sorted(
        by_patch.keys(), key=lambda x: selected_index(x, selected), reverse=True
    ):
        items = by_patch[patch]
        date = items[0].patch_date
        sys.stdout.write(stylize_patch_header(patch, date, color_enabled=color_enabled))
        for h in items:
            section = h.section
            if color_enabled:
                if section == labels["ability_changes"]:
                    section = _ansi_wrap(section, ANSI_BOLD, ANSI_FG_CYAN)
                elif section == labels["talent_changes"]:
                    section = _ansi_wrap(section, ANSI_BOLD, ANSI_FG_MAGENTA)
            prefix = f"[{section}]"
            if h.entity and not (hero_name_query and h.scope == "heroes"):
                prefix += f"[{h.entity}]"
            text = stylize_note(h.text, color_enabled=color_enabled).replace(
                "\n", "\n    "
            )
            sys.stdout.write(f"- {prefix} {text}\n")
        sys.stdout.write("\n")
    return 0


def cmd_list_heroes(args: argparse.Namespace) -> int:
    cache = Cache(None if args.no_cache else args.cache_dir)
    hero_map = load_hero_map(
        language=args.language,
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )
    names = sorted(set(hero_map.values()))
    names = filter_and_limit(names, args.query, args.limit)

    if args.format == "json":
        payload = {"language": args.language, "count": len(names), "heroes": names}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0

    for n in names:
        sys.stdout.write(n + "\n")
    return 0


def cmd_list_items(args: argparse.Namespace) -> int:
    cache = Cache(None if args.no_cache else args.cache_dir)
    item_map = load_item_map(
        language=args.language,
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )
    names = sorted(set(item_map.values()))
    names = filter_and_limit(names, args.query, args.limit)

    if args.format == "json":
        payload = {"language": args.language, "count": len(names), "items": names}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0

    for n in names:
        sys.stdout.write(n + "\n")
    return 0


def _fmt_pct(wins: int, games: int) -> str:
    if games <= 0:
        return "n/a"
    return f"{(wins / float(games)) * 100.0:.2f}%"


def cmd_winrate(args: argparse.Namespace) -> int:
    cache = Cache(None if args.no_cache else args.cache_dir)

    hero_map = load_hero_map(
        language=args.language,
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )
    name_to_id = load_hero_name_to_id(
        language=args.language,
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )

    hero_id: Optional[int] = None
    hero_name: str = args.hero

    if getattr(args, "hero_id", None) is not None:
        try:
            hero_id = int(args.hero_id)
        except Exception:
            raise LotaError(f"Invalid hero_id: {args.hero_id}")
    else:
        q = norm_for_match(args.hero)
        hero_id = name_to_id.get(q)
        if hero_id is None:
            names = sorted(set(hero_map.values()))
            sys.stdout.write(
                t(args.language, "winrate.unknown_hero", hero=args.hero) + "\n"
            )
            sugg = suggest_names(args.hero, names, limit=20)
            if sugg:
                sys.stdout.write(t(args.language, "winrate.suggestions") + "\n")
                for s in sugg:
                    sys.stdout.write(f"- {s}\n")
            else:
                sys.stdout.write(
                    t(
                        args.language,
                        "winrate.hint_list",
                        cmd=f"lota list heroes --language {display_language(args.language)}",
                    )
                    + "\n"
                )
            return 2

    hero_name = hero_map.get(hero_id, hero_name)

    patch_list = load_patch_list(
        language="english",
        cache=cache,
        timeout=args.timeout,
        user_agent=args.user_agent,
        debug=args.debug,
    )
    if not patch_list:
        raise LotaError("No patches found")

    last_n = max(1, int(args.last))
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
            timeout=args.timeout,
            user_agent=args.user_agent,
            debug=args.debug,
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
                "start_ts": start_ts,
                "end_ts": end_ts,
                "games": games,
                "wins": wins,
                "winrate": (wr * 100.0) if wr is not None else None,
                "delta_pp": delta_pp,
            }
        )

    rows.reverse()

    if args.format == "json":
        payload = {
            "hero": hero_name,
            "hero_id": hero_id,
            "last": last_n,
            "language": args.language,
            "source": {
                "patch_windows": "dota2.com datafeed patchnoteslist",
                "winrate": "OpenDota explorer",
            },
            "rows": rows,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0

    sys.stdout.write(
        t(args.language, "winrate.hero", hero=hero_name, hero_id=hero_id) + "\n"
    )
    sys.stdout.write(t(args.language, "winrate.range", n=last_n) + "\n\n")
    patch_h = t(args.language, "winrate.table.patch")
    date_h = t(args.language, "winrate.table.date")
    games_h = t(args.language, "winrate.table.games")
    wr_h = t(args.language, "winrate.table.winrate")
    d_h = t(args.language, "winrate.table.delta")
    sys.stdout.write(f"{patch_h:<10} {date_h:<12} {games_h:>8} {wr_h:>9} {d_h:>8}\n")
    sys.stdout.write("-" * 52 + "\n")
    for r in rows:
        games = int(r["games"])
        wins = int(r["wins"])
        wr_s = _fmt_pct(wins, games)
        d = r.get("delta_pp")
        d_s = "n/a" if d is None else (f"{d:+.2f}")
        sys.stdout.write(
            f"{str(r['patch'])[:10]:<10} {str(r['date'])[:12]:<12} {games:>8} {wr_s:>9} {d_s:>8}\n"
        )
    return 0


def selected_index(version: str, selected: List[Dict[str, Any]]) -> int:
    for i, p in enumerate(selected):
        if str(p.get("patch_number") or p.get("patch_name") or "") == version:
            return i
    return -1


def build_parser() -> argparse.ArgumentParser:
    class _LotaHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter
    ):
        def _metavar_formatter(self, action, default_metavar):
            if action.choices is not None:
                visible = [c for c in action.choices if not str(c).startswith("_")]
                if hasattr(action, "_group_actions"):
                    visible = [
                        c for c in visible
                        if not any(
                            getattr(a, "dest", None) == c and getattr(a, "help", None) == argparse.SUPPRESS
                            for a in getattr(action, "_group_actions", [])
                        )
                    ]
                result = "{%s}" % ",".join(visible) if visible else ""
                def fmt(tuple_size):
                    return (result,) * tuple_size if tuple_size else result
                return fmt
            return super()._metavar_formatter(action, default_metavar)

        def _format_action(self, action):
            if action.help == argparse.SUPPRESS:
                return ""
            return super()._format_action(action)

    p = argparse.ArgumentParser(
        prog="lota",
        formatter_class=_LotaHelpFormatter,
        usage="%(prog)s [-h] [chat]",
        description=(
            "Lota - LLM-powered Dota 2 analysis tool.\n"
            "\n"
            "An AI assistant that helps you analyze Dota 2 patch notes, hero changes,\n"
            "item updates, and winrate trends using natural language.\n"
            "\n"
            "Run without arguments to enter interactive chat mode with the AI assistant.\n"
            "\n"
            "Chat Mode Features:\n"
            "  - Natural language queries about Dota 2 patches and heroes\n"
            "  - AI-powered analysis with tool calling (shows which tools are used)\n"
            "  - Markdown formatting rendered in terminal\n"
            "  - Conversation history within session"
        ),
        epilog=(
            "Environment Variables:\n"
            "  OPENAI_API_KEY    OpenAI API key (required)\n"
            "  LOTA_API_KEY      Alternative to OPENAI_API_KEY\n"
            "  LOTA_API_BASE     Custom API endpoint (for OpenAI-compatible services)\n"
            "  LOTA_MODEL        Model to use (default: gpt-5-mini)\n"
            "\n"
            "Example:\n"
            "  lota                           # Start chatting with the AI assistant"
        ),
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help=argparse.SUPPRESS,
    )
    sub = p.add_subparsers(dest="cmd", metavar=" ", title="commands", help=argparse.SUPPRESS)

    chat_p = sub.add_parser(
        "chat",
        help="Enter interactive AI chat mode",
        description=(
            "Start an interactive chat session with the AI assistant.\n"
            "\n"
            "The assistant can analyze Dota 2 patch notes, hero changes, and winrate trends\n"
            "using natural language. It will automatically call the appropriate tools and\n"
            "show you which tools are being used.\n"
            "\n"
            "Chat Commands:\n"
            "  /help, /h     Show help message\n"
            "  /quit, /exit  Exit the chat\n"
            "  /clear        Clear conversation history"
        ),
    )
    chat_p.set_defaults(func=cmd_chat)

    s = sub.add_parser("scan", help=argparse.SUPPRESS)
    s.add_argument(
        "keyword",
        help="Keyword to search for (hero name, item name, or any text)",
    )
    s.add_argument(
        "--last", "-n", type=int, default=5, help="How many recent patches to scan"
    )
    s.add_argument(
        "--language",
        "-l",
        default="english",
        help="Output language: english / chinese",
    )
    s.add_argument(
        "--scope",
        default="all",
        choices=["all", "general", "heroes", "items", "neutral_items", "neutral_creeps"],
        help="Search scope",
    )
    s.add_argument(
        "--regex", action="store_true", help="Treat keyword as a regular expression"
    )
    s.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    s.add_argument(
        "--max-hits",
        type=int,
        default=200,
        help="Maximum number of matched lines to keep",
    )
    s.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    s.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT, help="Custom User-Agent"
    )
    s.add_argument(
        "--hero-image",
        choices=["auto", "always", "never"],
        default="never",
        help="Download hero portrait when keyword is a hero name",
    )
    s.add_argument(
        "--hero-image-dir",
        default="hero-images",
        help="Directory to save hero portraits",
    )
    s.add_argument(
        "--hero-image-overwrite",
        action="store_true",
        help="Overwrite existing hero portrait file",
    )
    s.add_argument(
        "--cache-dir",
        default=".lota-cache",
        help="File cache directory",
    )
    s.add_argument(
        "--no-cache", action="store_true", help="Disable cache"
    )
    s.set_defaults(func=cmd_scan)

    list_p = sub.add_parser("list", help=argparse.SUPPRESS)
    lsub = list_p.add_subparsers(dest="list_cmd", required=True)

    lh = lsub.add_parser("heroes", help="List all available heroes")
    lh.add_argument(
        "--language",
        "-l",
        default="english",
        help="Output language: english / chinese",
    )
    lh.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    lh.add_argument(
        "--query", "-q", default=None, help="Filter by substring (case-insensitive)"
    )
    lh.add_argument(
        "--limit", type=int, default=0, help="Limit output count (0 means no limit)"
    )
    lh.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    lh.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT, help="Custom User-Agent"
    )
    lh.add_argument(
        "--cache-dir",
        default=".lota-cache",
        help="File cache directory",
    )
    lh.add_argument("--no-cache", action="store_true", help="Disable cache")
    lh.set_defaults(func=cmd_list_heroes, debug=False)

    li = lsub.add_parser("items", help="List all available items")
    li.add_argument(
        "--language",
        "-l",
        default="english",
        help="Output language: english / chinese",
    )
    li.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    li.add_argument(
        "--query", "-q", default=None, help="Filter by substring (case-insensitive)"
    )
    li.add_argument(
        "--limit", type=int, default=0, help="Limit output count (0 means no limit)"
    )
    li.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    li.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT, help="Custom User-Agent"
    )
    li.add_argument(
        "--cache-dir",
        default=".lota-cache",
        help="File cache directory",
    )
    li.add_argument("--no-cache", action="store_true", help="Disable cache")
    li.set_defaults(func=cmd_list_items, debug=False)

    w = sub.add_parser("winrate", help=argparse.SUPPRESS)
    w.add_argument(
        "hero",
        help="Hero name (supports English/Chinese based on --language)",
    )
    w.add_argument(
        "--hero-id", default=None, help="Directly specify hero ID (overrides name)"
    )
    w.add_argument("--last", "-n", type=int, default=8, help="How many patches to analyze")
    w.add_argument(
        "--language",
        "-l",
        default="english",
        help="Hero name matching language: english / chinese",
    )
    w.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    w.add_argument("--timeout", type=int, default=20, help="Network timeout in seconds")
    w.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT, help="Custom User-Agent"
    )
    w.add_argument(
        "--cache-dir",
        default=".lota-cache",
        help="File cache directory",
    )
    w.add_argument("--no-cache", action="store_true", help="Disable cache")
    w.set_defaults(func=cmd_winrate)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        args.func = cmd_chat

    try:
        return int(args.func(args))
    except LotaError as e:
        sys.stderr.write(
            t(getattr(args, "language", "english"), "error_prefix") + f"{e}\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
