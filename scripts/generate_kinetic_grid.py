#!/usr/bin/env python3
"""
SMIL contribution-grid laser sweep — fallback when Platane/snk output is absent.
Uses the same GraphQL contribution calendar as build_assets.py (mock if no token).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Reuse telemetry fetch from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_assets import (  # noqa: E402
    ACCENT,
    ACCENT_DIM,
    ACCENT_MID,
    ASSETS,
    BORDER,
    DIM,
    INK,
    PAPER,
    SLATE,
    fetch_telemetry,
    intensity_color,
    write_svg,
)

MONO = '"Noto Sans Mono", Menlo, Consolas, monospace'
SANS = '"Noto Sans", Montserrat, Helvetica, Arial, sans-serif'


def build_grid(data: dict) -> None:
    weeks = data["weeks"]
    cell, gap = 12, 3
    pad_l, pad_t = 48, 56
    cols, rows = 52, 7
    grid_w = cols * (cell + gap) - gap
    grid_h = rows * (cell + gap) - gap
    w = pad_l + grid_w + 24
    h = pad_t + grid_h + 48
    peak = max((c for week in weeks for c in week), default=1) or 1

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">\n',
        "<defs>\n",
        f'<style><![CDATA[\n'
        f"  .mono {{ font-family: {MONO}; }}\n"
        f"  .sans {{ font-family: {SANS}; }}\n"
        f"  @keyframes laser {{\n"
        f"    0% {{ transform: translateX(0); }}\n"
        f"    100% {{ transform: translateX({grid_w}px); }}\n"
        f"  }}\n"
        f"  .laser {{\n"
        f"    animation: laser 6s linear infinite;\n"
        f"  }}\n"
        f"]]></style>\n",
        f'<linearGradient id="laserGrad" x1="0" y1="0" x2="0" y2="1">\n'
        f'  <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0"/>\n'
        f'  <stop offset="50%" stop-color="{ACCENT}" stop-opacity="0.85"/>\n'
        f'  <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>\n'
        f"</linearGradient>\n",
        "</defs>\n",
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="{INK}" '
        f'stroke="{BORDER}" stroke-width="1"/>\n',
        f'<text x="16" y="28" class="mono" font-size="10" fill="{SLATE}" '
        f'letter-spacing="1.5">SHEET 02K — KINETIC CONTRIBUTION GRID</text>\n',
        f'<text x="16" y="44" class="mono" font-size="11" fill="{ACCENT}">'
        f"LASER SWEEP · 52 × 7 · LIVE CALENDAR</text>\n",
    ]

    for wi, week in enumerate(weeks[-52:]):
        for di, count in enumerate(week):
            x = pad_l + wi * (cell + gap)
            y = pad_t + di * (cell + gap)
            fill = intensity_color(count, peak)
            # Staggered illuminate when laser passes (SMIL)
            delay = wi * 0.11
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'fill="{fill}" stroke="{BORDER}" stroke-width="1">\n'
                f'  <animate attributeName="stroke" values="{BORDER};{ACCENT};{BORDER}" '
                f'dur="6s" begin="{delay:.2f}s" repeatCount="indefinite"/>\n'
                f'  <animate attributeName="opacity" values="0.75;1;0.75" '
                f'dur="6s" begin="{delay:.2f}s" repeatCount="indefinite"/>\n'
                f"</rect>\n"
            )

    # CSS laser + SMIL twin
    parts.append(
        f'<g class="laser">\n'
        f'  <rect x="{pad_l}" y="{pad_t - 4}" width="4" height="{grid_h + 8}" '
        f'fill="url(#laserGrad)"/>\n'
        f"</g>\n"
    )
    parts.append(
        f'<rect x="{pad_l}" y="{pad_t - 4}" width="3" height="{grid_h + 8}" fill="{ACCENT}" opacity="0.35">\n'
        f'  <animate attributeName="x" values="{pad_l};{pad_l + grid_w};{pad_l}" '
        f'dur="6s" repeatCount="indefinite"/>\n'
        f"</rect>\n"
    )

    parts.append(
        f'<text x="16" y="{h - 14}" class="mono" font-size="9" fill="{SLATE}">'
        f'TOTAL {data["contributions_year"]} · STREAK {data["current_streak"]}d · '
        f'SRC {data["source"].upper()}</text>\n'
    )
    parts.append("</svg>\n")
    write_svg("grid-animation.svg", "".join(parts))


def main() -> int:
    print("fadeddarts kinetic grid")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = fetch_telemetry(token)
    build_grid(data)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
