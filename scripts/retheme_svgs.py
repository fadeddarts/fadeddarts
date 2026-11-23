#!/usr/bin/env python3
"""
Remap third-party generated SVGs (snk, github-profile-3d-contrib, etc.)
into the fadeddarts Swiss Neo-Brutalist palette.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

INK = "#0A0A0A"
BORDER = "#262626"
PAPER = "#F4F4F0"
SLATE = "#8A8A8E"
ACCENT = "#2B6CFF"
ACCENT_MID = "#1A4ACC"
ACCENT_DIM = "#142A66"
DIM = "#1A1A1A"

# Source greens / greys commonly emitted by contribution tools → our palette
REMAP: list[tuple[str, str]] = [
    # GitHub contribution greens
    ("#ebedf0", DIM),
    ("#EBEDF0", DIM),
    ("#9be9a8", ACCENT_DIM),
    ("#9BE9A8", ACCENT_DIM),
    ("#40c463", ACCENT_MID),
    ("#40C463", ACCENT_MID),
    ("#30a14e", ACCENT_MID),
    ("#30A14E", ACCENT_MID),
    ("#216e39", ACCENT),
    ("#216E39", ACCENT),
    ("#39d353", ACCENT),
    ("#39D353", ACCENT),
    ("#26a641", ACCENT_MID),
    ("#26A641", ACCENT_MID),
    ("#006d32", ACCENT),
    ("#006D32", ACCENT),
    ("#0e4429", ACCENT_DIM),
    ("#0E4429", ACCENT_DIM),
    # Dark theme greys / backgrounds
    ("#161b22", INK),
    ("#161B22", INK),
    ("#0d1117", INK),
    ("#0D1117", INK),
    ("#21262d", BORDER),
    ("#21262D", BORDER),
    ("#30363d", BORDER),
    ("#30363D", BORDER),
    ("#ffffff", PAPER),
    ("#FFFFFF", PAPER),
    ("#c9d1d9", PAPER),
    ("#C9D1D9", PAPER),
    ("#8b949e", SLATE),
    ("#8B949E", SLATE),
    # snk defaults
    ("#000000", INK),
    ("#fff", PAPER),
    ("#FFF", PAPER),
    # leftover gold from prior theme
    ("#FFD000", ACCENT),
    ("#ffd000", ACCENT),
    ("#856D00", ACCENT_MID),
    ("#856d00", ACCENT_MID),
]

TARGETS = [
    "profile-3d.svg",
    "grid-animation.svg",
    "github-contribution-grid-snake.svg",
    "github-contribution-grid-snake-dark.svg",
    "profile-3d-contrib.svg",
]


def remap_content(text: str) -> str:
    out = text
    for src, dst in REMAP:
        out = out.replace(src, dst)
    # Catch rgb() greens that snk sometimes emits
    out = re.sub(
        r"rgb\(\s*57\s*,\s*211\s*,\s*83\s*\)",
        ACCENT,
        out,
        flags=re.I,
    )
    out = re.sub(
        r"rgb\(\s*64\s*,\s*196\s*,\s*99\s*\)",
        ACCENT_MID,
        out,
        flags=re.I,
    )
    return out


def process_file(path: Path) -> bool:
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8", errors="ignore")
    updated = remap_content(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        print(f"  rethemed {path.relative_to(ROOT)}")
        return True
    print(f"  unchanged {path.relative_to(ROOT)}")
    return False


def main() -> int:
    print("fadeddarts retheme")
    ASSETS.mkdir(parents=True, exist_ok=True)
    touched = 0
    # Explicit targets + any svg mentioning snake / 3d / grid
    candidates = set()
    for name in TARGETS:
        candidates.add(ASSETS / name)
    for path in ASSETS.glob("*.svg"):
        low = path.name.lower()
        if any(k in low for k in ("snake", "snk", "3d", "grid", "contrib", "profile-3d")):
            candidates.add(path)

    for path in sorted(candidates):
        if process_file(path):
            touched += 1

    print(f"done ({touched} files updated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
