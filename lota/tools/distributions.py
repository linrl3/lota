from __future__ import annotations

from typing import List

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_distributions
from lota.core.http import fetch_json


@tool
def mmr_distribution() -> str:
    """Get MMR distribution statistics from OpenDota.

    Returns:
        A formatted summary of MMR distribution across different ranks.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_distributions(),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or not isinstance(data, dict):
        return "Failed to fetch MMR distribution data."

    mmr_data = data.get("mmr", {})
    if not mmr_data:
        return "No MMR distribution data available."

    rows = mmr_data.get("rows", [])
    if not rows or not isinstance(rows, list):
        return "No MMR distribution rows found."

    sum_data = mmr_data.get("sum", {})
    total_count = sum_data.get("count", 0) if isinstance(sum_data, dict) else 0

    lines: List[str] = [
        "MMR Distribution Statistics",
        "(from OpenDota)",
        "",
    ]

    if total_count:
        lines.append(f"Total Players: {total_count:,}")
        lines.append("")

    rank_names = {
        1: "Herald",
        2: "Guardian",
        3: "Crusader",
        4: "Archon",
        5: "Legend",
        6: "Ancient",
        7: "Divine",
        8: "Immortal",
    }

    rank_buckets = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        bin_val = row.get("bin", 0)
        count = row.get("count", 0)
        rank_tier = bin_val // 1000 if bin_val else 0
        if rank_tier > 0:
            if rank_tier not in rank_buckets:
                rank_buckets[rank_tier] = 0
            rank_buckets[rank_tier] += count

    lines.append("Distribution by Rank:")
    lines.append("")

    for rank_id in sorted(rank_buckets.keys()):
        rank_name = rank_names.get(rank_id, f"Rank {rank_id}")
        count = rank_buckets[rank_id]
        percentage = (count / total_count * 100) if total_count > 0 else 0
        lines.append(f"**{rank_name}**: {count:,} players ({percentage:.1f}%)")

    lines.append("")

    return "\n".join(lines)
