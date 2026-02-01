"""Interactive chat loop for the agent."""

from __future__ import annotations

import atexit
import os
import re
import sys
from typing import Optional

try:
    import readline
except ImportError:
    readline = None

from langchain_core.messages import AIMessage, HumanMessage

from lota.agent.config import LLMConfig
from lota.agent.graph import create_agent

HISTORY_FILE = os.path.expanduser("~/.lota_history")
HISTORY_LENGTH = 1000


def _setup_readline() -> None:
    """Setup readline for command history and line editing."""
    if readline is None:
        return

    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    readline.set_history_length(HISTORY_LENGTH)
    atexit.register(_save_history)


def _save_history() -> None:
    """Save command history to file."""
    if readline is None:
        return
    try:
        readline.write_history_file(HISTORY_FILE)
    except Exception:
        pass

ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"
ANSI_DIM = "\x1b[2m"
ANSI_ITALIC = "\x1b[3m"
ANSI_UNDERLINE = "\x1b[4m"
ANSI_FG_GREEN = "\x1b[32m"
ANSI_FG_BLUE = "\x1b[34m"
ANSI_FG_CYAN = "\x1b[36m"
ANSI_FG_YELLOW = "\x1b[33m"
ANSI_FG_MAGENTA = "\x1b[35m"
ANSI_FG_WHITE = "\x1b[37m"
ANSI_BG_GRAY = "\x1b[48;5;236m"


def _color(text: str, *codes: str, enabled: bool = True) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + ANSI_RESET


def _markdown_to_ansi(text: str, color_enabled: bool) -> str:
    """Convert basic Markdown formatting to ANSI escape codes."""
    if not color_enabled or not text:
        return text

    result = text

    result = re.sub(
        r"^(#{1,6})\s+(.+)$",
        lambda m: f"{ANSI_BOLD}{ANSI_FG_CYAN}{m.group(2)}{ANSI_RESET}",
        result,
        flags=re.MULTILINE,
    )

    result = re.sub(
        r"\*\*\*(.+?)\*\*\*",
        lambda m: f"{ANSI_BOLD}{ANSI_ITALIC}{m.group(1)}{ANSI_RESET}",
        result,
    )

    result = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: f"{ANSI_BOLD}{m.group(1)}{ANSI_RESET}",
        result,
    )

    result = re.sub(
        r"(?<!\*)\*([^*\n]+?)\*(?!\*)",
        lambda m: f"{ANSI_ITALIC}{m.group(1)}{ANSI_RESET}",
        result,
    )

    result = re.sub(
        r"`([^`\n]+?)`",
        lambda m: f"{ANSI_BG_GRAY}{ANSI_FG_WHITE}{m.group(1)}{ANSI_RESET}",
        result,
    )

    result = re.sub(
        r"^(\s*)[-*]\s+",
        lambda m: f"{m.group(1)}{ANSI_FG_CYAN}•{ANSI_RESET} ",
        result,
        flags=re.MULTILINE,
    )

    result = re.sub(
        r"^(\s*)(\d+)\.\s+",
        lambda m: f"{m.group(1)}{ANSI_FG_CYAN}{m.group(2)}.{ANSI_RESET} ",
        result,
        flags=re.MULTILINE,
    )

    return result


def _print_welcome(color_enabled: bool) -> None:
    print()
    title = _color("🎮 Lota", ANSI_BOLD, ANSI_FG_CYAN, enabled=color_enabled)
    subtitle = _color("Dota 2 Analysis Assistant", ANSI_DIM, enabled=color_enabled)
    print(f"{title} - {subtitle}")
    print(_color("Type /help for commands, /quit to exit", ANSI_DIM, enabled=color_enabled))
    print()


def _print_help(color_enabled: bool) -> None:
    print()
    print(_color("Available Commands:", ANSI_BOLD, enabled=color_enabled))
    print("  /help, /h     - Show this help message")
    print("  /quit, /exit  - Exit the chat")
    print("  /clear        - Clear the conversation history")
    print()
    print(_color("Available Tools:", ANSI_BOLD, enabled=color_enabled))
    print("  - scan_patch_notes: Search patch notes by keyword")
    print("  - list_heroes/list_items: List available heroes or items")
    print("  - hero_winrate: Get a hero's winrate trend over patches")
    print("  - top_heroes_by_winrate: Get top/bottom winrate heroes in a patch")
    print("  - hero_counters: Find counters and matchups for a hero")
    print("  - hero_meta: Get pro pick/ban rates and pub winrates")
    print("  - pro_matches: Get recent professional matches")
    print("  - search_player/player_stats: Search and get player stats")
    print("  - hero_rankings: Get top players for a hero")
    print("  - hero_abilities: Get hero abilities and talents")
    print()
    print(_color("Example Questions:", ANSI_BOLD, enabled=color_enabled))
    print("  - What changed for Invoker in the last 3 patches?")
    print("  - Who counters Anti-Mage?")
    print("  - What are the most picked heroes in pro?")
    print("  - Show me recent pro matches")
    print("  - Search for player Miracle")
    print("  - Who are the best Invoker players?")
    print("  - What are Anti-Mage's abilities?")
    print()


def _format_tool_call(tool_name: str, tool_args: dict, color_enabled: bool) -> str:
    """Format a tool call for display."""
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in tool_args.items())
    tool_display = _color(tool_name, ANSI_BOLD, ANSI_FG_MAGENTA, enabled=color_enabled)
    return f"🔧 Calling {tool_display}({args_str})"


def run_chat(config: Optional[LLMConfig] = None) -> int:
    """Run the interactive chat loop."""
    color_enabled = sys.stdout.isatty()

    _setup_readline()

    try:
        agent = create_agent(config)
    except Exception as e:
        print(f"Error initializing agent: {e}", file=sys.stderr)
        print("Make sure you have set LOTA_API_KEY or OPENAI_API_KEY environment variable.", file=sys.stderr)
        return 1

    _print_welcome(color_enabled)

    messages = []
    all_tool_calls_shown = set()

    while True:
        try:
            prompt = _color("You: ", ANSI_BOLD, ANSI_FG_GREEN, enabled=color_enabled)
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(_color("Goodbye!", ANSI_DIM, enabled=color_enabled))
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/quit", "/exit", "/q"):
            print(_color("Goodbye!", ANSI_DIM, enabled=color_enabled))
            break
        elif cmd in ("/help", "/h"):
            _print_help(color_enabled)
            continue
        elif cmd == "/clear":
            messages = []
            all_tool_calls_shown = set()
            print(_color("Conversation cleared.", ANSI_DIM, enabled=color_enabled))
            continue

        messages.append(HumanMessage(content=user_input))

        print()

        try:
            final_response = None

            for event in agent.stream({"messages": messages}, stream_mode="values"):
                event_messages = event.get("messages", [])
                if not event_messages:
                    continue

                for msg in event_messages:
                    if isinstance(msg, AIMessage):
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tc_id = tc.get("id", "")
                                if tc_id and tc_id not in all_tool_calls_shown:
                                    all_tool_calls_shown.add(tc_id)
                                    tool_name = tc.get("name", "unknown")
                                    tool_args = tc.get("args", {})
                                    print(_color(
                                        _format_tool_call(tool_name, tool_args, color_enabled),
                                        ANSI_DIM,
                                        enabled=color_enabled
                                    ))
                                    sys.stdout.flush()

                last_msg = event_messages[-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    if not (hasattr(last_msg, "tool_calls") and last_msg.tool_calls):
                        final_response = last_msg.content

            assistant_label = _color("Assistant: ", ANSI_BOLD, ANSI_FG_BLUE, enabled=color_enabled)
            if final_response:
                formatted_response = _markdown_to_ansi(final_response, color_enabled)
                print(f"{assistant_label}{formatted_response}")
                messages = event_messages
            else:
                print(f"{assistant_label}I couldn't generate a response. Please try again.")

        except Exception as e:
            assistant_label = _color("Assistant: ", ANSI_BOLD, ANSI_FG_BLUE, enabled=color_enabled)
            error_msg = _color(f"Error: {e}", ANSI_FG_YELLOW, enabled=color_enabled)
            print(f"{assistant_label}{error_msg}")

        print()

    return 0
