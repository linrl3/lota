"""Ward analysis tool with heatmap generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from lota.core import DEFAULT_CACHE_DIR, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from lota.core.cache import Cache
from lota.core.endpoints import endpoint_opendota_match
from lota.core.hero import load_hero_map
from lota.core.http import fetch_json

MINIMAP_URL = "https://www.opendota.com/assets/images/dota2/map/minimap.jpg"

MAP_MIN = 64
MAP_MAX = 192
MAP_SIZE = MAP_MAX - MAP_MIN


def _download_minimap(cache: Cache, timeout: int, user_agent: str) -> Optional[str]:
    """Download the Dota 2 minimap image."""
    import urllib.request

    cache_path = Path(cache.cache_dir) / "minimap.jpg"
    if cache_path.exists():
        return str(cache_path)

    try:
        req = urllib.request.Request(MINIMAP_URL, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
        return str(cache_path)
    except Exception:
        return None


def _generate_heatmap(
    ward_positions: List[Tuple[int, int, str]],
    output_path: str,
    title: str,
    minimap_path: Optional[str] = None,
    match_info: Dict[str, Optional[Any]] = None,
) -> bool:
    """Generate a ward heatmap image."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        return False

    fig, ax = plt.subplots(figsize=(10, 10))

    if minimap_path and os.path.exists(minimap_path):
        try:
            from PIL import Image
            img = Image.open(minimap_path)
            img_flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
            ax.imshow(img_flipped, extent=[0, 256, 0, 256], origin='lower', alpha=0.9, zorder=1)
        except Exception:
            ax.set_facecolor('#1a1a2e')
    else:
        ax.set_facecolor('#1a1a2e')

    obs_x = [p[0] for p in ward_positions if p[2] == 'obs']
    obs_y = [p[1] for p in ward_positions if p[2] == 'obs']
    sen_x = [p[0] for p in ward_positions if p[2] == 'sen']
    sen_y = [p[1] for p in ward_positions if p[2] == 'sen']

    if obs_x:
        ax.scatter(obs_x, obs_y, c='yellow', s=200, alpha=0.9, marker='o',
                   edgecolors='#ff6600', linewidths=2, label=f'Observer ({len(obs_x)})', zorder=5)

    if sen_x:
        ax.scatter(sen_x, sen_y, c='#00ffff', s=120, alpha=0.9, marker='s',
                   edgecolors='#0066ff', linewidths=2, label=f'Sentry ({len(sen_x)})', zorder=4)

    if obs_x or sen_x:
        all_x = obs_x + sen_x
        all_y = obs_y + sen_y

        heatmap_data = np.zeros((256, 256))
        for x, y in zip(all_x, all_y):
            xi = int(x)
            yi = int(y)
            if 0 <= xi < 256 and 0 <= yi < 256:
                for dx in range(-10, 11):
                    for dy in range(-10, 11):
                        dist = (dx*dx + dy*dy) ** 0.5
                        if dist <= 10:
                            nxi, nyi = xi + dx, yi + dy
                            if 0 <= nxi < 256 and 0 <= nyi < 256:
                                heatmap_data[nyi, nxi] += max(0, 1 - dist/10)

        if heatmap_data.max() > 0:
            colors = ['#00000000', '#ff000020', '#ff660040', '#ffff0060']
            cmap = LinearSegmentedColormap.from_list('ward_heat', colors)
            ax.imshow(heatmap_data, extent=[0, 256, 0, 256],
                     origin='lower', cmap=cmap, alpha=0.5, zorder=2)

    ax.set_xlim(64, 192)
    ax.set_ylim(64, 192)
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=11, facecolor='#222222', edgecolor='white',
              labelcolor='white', framealpha=0.9)

    ax.axhline(y=128, color='white', linestyle='--', alpha=0.4, linewidth=1)
    ax.axvline(x=128, color='white', linestyle='--', alpha=0.4, linewidth=1)

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.patch.set_facecolor('#0a0a14')

    if match_info:
        match_id = match_info.get('match_id', '')
        radiant_name = match_info.get('radiant_name', 'Radiant')
        dire_name = match_info.get('dire_name', 'Dire')
        radiant_win = match_info.get('radiant_win')
        duration = match_info.get('duration', 0)
        team_filter = match_info.get('team_filter', 'Both Teams')

        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else ""

        if radiant_win is True:
            result_str = f"{radiant_name} Victory"
        elif radiant_win is False:
            result_str = f"{dire_name} Victory"
        else:
            result_str = ""

        title_text = f"Ward Heatmap - Match {match_id}"
        fig.suptitle(title_text, fontsize=14, color='white', fontweight='bold', y=0.98)

        info_text = f"{radiant_name}  vs  {dire_name}"
        if duration_str:
            info_text += f"  |  {duration_str}"
        if result_str:
            info_text += f"  |  {result_str}"

        fig.text(0.5, 0.02, info_text, ha='center', fontsize=11, color='#cccccc')
        fig.text(0.5, -0.01, f"Showing: {team_filter}", ha='center', fontsize=10, color='#888888')
    else:
        ax.set_title(title, fontsize=14, color='white', pad=10, fontweight='bold')

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(output_path, dpi=150, facecolor='#0a0a14', edgecolor='none',
                bbox_inches='tight', pad_inches=0.15)
    plt.close()

    return True


@tool
def ward_analysis(
    match_id: int,
    team: str = "both",
    generate_heatmap: bool = True,
    output_dir: str = ".",
) -> str:
    """Analyze ward placements in a Dota 2 match and optionally generate a heatmap image.

    Args:
        match_id: The match ID to analyze (from OpenDota).
        team: Which team's wards to analyze - 'radiant', 'dire', or 'both' (default: 'both').
        generate_heatmap: Whether to generate a heatmap image (default: True).
        output_dir: Directory to save the heatmap image (default: current directory).

    Returns:
        Ward placement statistics and path to generated heatmap image if created.
    """
    cache = Cache(DEFAULT_CACHE_DIR)

    data = fetch_json(
        endpoint_opendota_match(match_id),
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    if not data or "error" in data:
        return f"Match {match_id} not found or not parsed. Try requesting a parse first."

    radiant_team_name = data.get("radiant_name") or "Radiant"
    dire_team_name = data.get("dire_name") or "Dire"
    radiant_win = data.get("radiant_win")
    duration = data.get("duration", 0)

    players = data.get("players", [])
    if not players:
        return f"No player data found for match {match_id}."

    hero_map = load_hero_map(
        language="english",
        cache=cache,
        timeout=DEFAULT_TIMEOUT,
        user_agent=DEFAULT_USER_AGENT,
    )

    radiant_wards: List[Dict[str, Any]] = []
    dire_wards: List[Dict[str, Any]] = []

    for p in players:
        player_slot = p.get("player_slot", 0)
        is_radiant = player_slot < 128
        hero_id = p.get("hero_id", 0)
        hero_name = hero_map.get(hero_id, f"Hero {hero_id}")

        obs_log = p.get("obs_log", []) or []
        sen_log = p.get("sen_log", []) or []

        for w in obs_log:
            ward_data = {
                "type": "obs",
                "hero": hero_name,
                "x": w.get("x", 0),
                "y": w.get("y", 0),
                "time": w.get("time", 0),
            }
            if is_radiant:
                radiant_wards.append(ward_data)
            else:
                dire_wards.append(ward_data)

        for w in sen_log:
            ward_data = {
                "type": "sen",
                "hero": hero_name,
                "x": w.get("x", 0),
                "y": w.get("y", 0),
                "time": w.get("time", 0),
            }
            if is_radiant:
                radiant_wards.append(ward_data)
            else:
                dire_wards.append(ward_data)

    radiant_obs = len([w for w in radiant_wards if w["type"] == "obs"])
    radiant_sen = len([w for w in radiant_wards if w["type"] == "sen"])
    dire_obs = len([w for w in dire_wards if w["type"] == "obs"])
    dire_sen = len([w for w in dire_wards if w["type"] == "sen"])

    lines: List[str] = [
        f"Ward Analysis for Match {match_id}",
        f"{radiant_team_name} vs {dire_team_name}",
        "",
        f"**{radiant_team_name}** (Radiant):",
        f"  Observer Wards: {radiant_obs}",
        f"  Sentry Wards: {radiant_sen}",
        "",
        f"**{dire_team_name}** (Dire):",
        f"  Observer Wards: {dire_obs}",
        f"  Sentry Wards: {dire_sen}",
        "",
    ]

    if team.lower() == "radiant":
        wards_to_show = radiant_wards
        team_filter = radiant_team_name
    elif team.lower() == "dire":
        wards_to_show = dire_wards
        team_filter = dire_team_name
    else:
        wards_to_show = radiant_wards + dire_wards
        team_filter = "Both Teams"

    if not wards_to_show:
        lines.append("No ward data available (match may not be parsed).")
        return "\n".join(lines)

    by_hero: Dict[str, List[Dict]] = {}
    for w in wards_to_show:
        hero = w["hero"]
        if hero not in by_hero:
            by_hero[hero] = []
        by_hero[hero].append(w)

    lines.append(f"Ward Breakdown ({team_filter}):")
    for hero, wards in sorted(by_hero.items(), key=lambda x: -len(x[1])):
        obs_count = len([w for w in wards if w["type"] == "obs"])
        sen_count = len([w for w in wards if w["type"] == "sen"])
        lines.append(f"  {hero}: {obs_count} obs, {sen_count} sen")

    if generate_heatmap:
        try:
            minimap_path = _download_minimap(cache, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT)

            ward_positions = [(w["x"], w["y"], w["type"]) for w in wards_to_show]

            output_path = os.path.join(output_dir, f"ward_heatmap_{match_id}.png")

            match_info = {
                "match_id": match_id,
                "radiant_name": radiant_team_name,
                "dire_name": dire_team_name,
                "radiant_win": radiant_win,
                "duration": duration,
                "team_filter": team_filter,
            }

            success = _generate_heatmap(
                ward_positions,
                output_path,
                f"Ward Heatmap - Match {match_id}",
                minimap_path,
                match_info,
            )

            if success:
                lines.append("")
                lines.append(f"Heatmap saved to: {os.path.abspath(output_path)}")
            else:
                lines.append("")
                lines.append("Could not generate heatmap (matplotlib not available).")
        except Exception as e:
            lines.append("")
            lines.append(f"Error generating heatmap: {str(e)}")

    return "\n".join(lines)
