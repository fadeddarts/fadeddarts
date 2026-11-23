#!/usr/bin/env python3
"""
fadeddarts profile asset pipeline
Swiss Minimalist × Neo-Brutalist SVG generators.
Fetches live GitHub telemetry when GITHUB_TOKEN is set; otherwise uses mock data.
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Design tokens ────────────────────────────────────────────────────────────
INK = "#0A0A0A"
BORDER = "#262626"
PAPER = "#F4F4F0"
SLATE = "#8A8A8E"
GOLD = "#FFD000"
DIM = "#1A1A1A"

USERNAME = "fadeddarts"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
SANS = "Inter, Helvetica Neue, Helvetica, Arial, sans-serif"

# ── SVG helpers ───────────────────────────────────────────────────────────────


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_open(w: int, h: int, extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" {extra}>\n'
        f"<defs>\n"
        f'  <style><![CDATA[\n'
        f"    .mono {{ font-family: {FONT}; }}\n"
        f"    .sans {{ font-family: {SANS}; }}\n"
        f"  ]]></style>\n"
        f"</defs>\n"
    )


def svg_close() -> str:
    return "</svg>\n"


def card(x: float, y: float, w: float, h: float) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="{INK}" stroke="{BORDER}" stroke-width="1"/>\n'
    )


def hairline_h(x: float, y: float, w: float) -> str:
    return f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="{BORDER}" stroke-width="1"/>\n'


def hairline_v(x: float, y: float, h: float) -> str:
    return f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + h}" stroke="{BORDER}" stroke-width="1"/>\n'


def label(x: float, y: float, text: str, size: int = 10) -> str:
    return (
        f'<text x="{x}" y="{y}" class="mono" font-size="{size}" '
        f'fill="{SLATE}" letter-spacing="1.5">{esc(text)}</text>\n'
    )


def paper_text(x: float, y: float, text: str, size: int = 14, weight: str = "400") -> str:
    return (
        f'<text x="{x}" y="{y}" class="sans" font-size="{size}" font-weight="{weight}" '
        f'fill="{PAPER}">{esc(text)}</text>\n'
    )


def gold_text(x: float, y: float, text: str, size: int = 12, weight: str = "600") -> str:
    return (
        f'<text x="{x}" y="{y}" class="mono" font-size="{size}" font-weight="{weight}" '
        f'fill="{GOLD}">{esc(text)}</text>\n'
    )


def write_svg(name: str, content: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")
    return path


# ── Data layer ───────────────────────────────────────────────────────────────


def mock_telemetry() -> dict[str, Any]:
    """Deterministic mock so local previews work without a token."""
    weeks: list[list[int]] = []
    for w in range(52):
        days = []
        for d in range(7):
            # Pseudo-activity pattern: denser mid-week, seasonal peaks
            v = ((w * 7 + d) * 17 + 23) % 11
            if d in (0, 6):
                v = max(0, v - 4)
            if 18 <= w <= 28 or 40 <= w <= 48:
                v = min(10, v + 2)
            days.append(v)
        weeks.append(days)

    return {
        "login": USERNAME,
        "name": "Harpuneet Singh",
        "public_repos": 24,
        "followers": 0,
        "following": 1,
        "total_commits": 842,
        "current_streak": 4,
        "longest_streak": 18,
        "contributions_year": 612,
        "weeks": weeks,
        "languages": [
            ("Python", 38.0),
            ("TypeScript", 22.0),
            ("JavaScript", 16.0),
            ("Swift", 9.0),
            ("HTML/CSS", 8.0),
            ("C/C++", 4.0),
            ("Other", 3.0),
        ],
        "status": "COMPILING",
        "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "mock",
    }


def graphql(token: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "fadeddarts-profile-builder",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_telemetry(token: str | None) -> dict[str, Any]:
    if not token:
        print("  GITHUB_TOKEN unset — using mock telemetry")
        return mock_telemetry()

    print("  fetching live GitHub GraphQL telemetry…")
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        followers { totalCount }
        following { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: UPDATED_AT, direction: DESC}) {
          totalCount
          nodes {
            name
            primaryLanguage { name }
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { contributionCount date }
            }
          }
        }
      }
    }
    """
    try:
        data = graphql(token, query, {"login": USERNAME})
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
        print(f"  GraphQL failed ({exc}); falling back to mock")
        return mock_telemetry()

    user = data["user"]
    weeks_raw = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    # Keep last 52 weeks
    weeks_raw = weeks_raw[-52:]
    weeks: list[list[int]] = []
    flat: list[int] = []
    for week in weeks_raw:
        days = [d["contributionCount"] for d in week["contributionDays"]]
        while len(days) < 7:
            days.append(0)
        weeks.append(days[:7])
        flat.extend(days[:7])

    # Streaks (ending at today)
    current = 0
    for c in reversed(flat):
        if c > 0:
            current += 1
        else:
            break
    longest = 0
    run = 0
    for c in flat:
        if c > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    # Language weights across owned repos
    lang_bytes: dict[str, int] = {}
    for node in user["repositories"]["nodes"]:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

    # Normalize / bucket minor languages
    rename = {"CSS": "HTML/CSS", "HTML": "HTML/CSS", "SCSS": "HTML/CSS"}
    merged: dict[str, int] = {}
    for name, size in lang_bytes.items():
        key = rename.get(name, name)
        merged[key] = merged.get(key, 0) + size

    total = sum(merged.values()) or 1
    ranked = sorted(merged.items(), key=lambda kv: kv[1], reverse=True)
    top: list[tuple[str, float]] = []
    other = 0.0
    for i, (name, size) in enumerate(ranked):
        pct = 100.0 * size / total
        if i < 6:
            top.append((name, round(pct, 1)))
        else:
            other += pct
    if other >= 0.5:
        top.append(("Other", round(other, 1)))

    # Approximate commit volume from contribution calendar
    contributions = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    return {
        "login": user["login"],
        "name": user["name"] or "Harpuneet Singh",
        "public_repos": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "total_commits": contributions,
        "current_streak": current,
        "longest_streak": longest,
        "contributions_year": contributions,
        "weeks": weeks,
        "languages": top or mock_telemetry()["languages"],
        "status": "LIVE",
        "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "github",
    }


# ── Asset builders ───────────────────────────────────────────────────────────


def build_hero(data: dict[str, Any]) -> None:
    w, h = 1200, 280
    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))

    # Title-block grid
    parts.append(hairline_h(0, 48, w))
    parts.append(hairline_h(0, h - 40, w))
    parts.append(hairline_v(160, 0, h))
    parts.append(hairline_v(w - 220, 0, h))

    # Corner marks
    for cx, cy in [(12, 12), (w - 12, 12), (12, h - 12), (w - 12, h - 12)]:
        parts.append(
            f'<path d="M{cx - 8},{cy} H{cx + 8} M{cx},{cy - 8} V{cy + 8}" '
            f'stroke="{GOLD}" stroke-width="1.5"/>\n'
        )

    # Left meta column
    parts.append(label(24, 28, "DWG 00 — TITLE BLOCK"))
    parts.append(label(24, 78, "SHEET"))
    parts.append(gold_text(24, 108, "00", 36, "700"))
    parts.append(label(24, 140, "REV"))
    parts.append(paper_text(24, 162, "A", 18, "600"))
    parts.append(label(24, 200, "SCALE"))
    parts.append(paper_text(24, 222, "1 : 1", 14))

    # Center identity
    parts.append(label(180, 28, "SUBJECT / AUTHOR"))
    parts.append(
        f'<text x="180" y="118" class="sans" font-size="42" font-weight="700" '
        f'fill="{PAPER}" letter-spacing="-0.5">{esc(data["name"])}</text>\n'
    )
    parts.append(
        f'<text x="180" y="152" class="mono" font-size="16" fill="{GOLD}">'
        f'/{esc(data["login"])}</text>\n'
    )
    parts.append(
        f'<text x="180" y="190" class="sans" font-size="15" fill="{SLATE}">'
        f'Computer Science @ Toronto Metropolitan University</text>\n'
    )
    parts.append(
        f'<text x="180" y="214" class="sans" font-size="15" fill="{PAPER}">'
        f'Full-Stack &amp; Systems Developer</text>\n'
    )

    # Wireframe motif (right of center)
    gx, gy = 720, 70
    parts.append(
        f'<g stroke="{GOLD}" stroke-width="1" fill="none" opacity="0.9">\n'
        f'  <rect x="{gx}" y="{gy}" width="120" height="120"/>\n'
        f'  <line x1="{gx}" y1="{gy}" x2="{gx + 120}" y2="{gy + 120}"/>\n'
        f'  <line x1="{gx + 120}" y1="{gy}" x2="{gx}" y2="{gy + 120}"/>\n'
        f'  <circle cx="{gx + 60}" cy="{gy + 60}" r="28"/>\n'
        f'  <circle cx="{gx + 60}" cy="{gy + 60}" r="8" fill="{GOLD}" stroke="none"/>\n'
        f'  <path d="M{gx + 20},{gy + 100} L{gx + 60},{gy + 20} L{gx + 100},{gy + 100} Z"/>\n'
        f"</g>\n"
    )

    # Right status column
    parts.append(label(w - 200, 28, "STATUS"))
    parts.append(gold_text(w - 200, 78, data["status"], 18, "700"))
    parts.append(label(w - 200, 110, "COORD / LOC"))
    parts.append(paper_text(w - 200, 132, "TORONTO, ON", 13))
    parts.append(label(w - 200, 164, "REPOS"))
    parts.append(paper_text(w - 200, 186, str(data["public_repos"]), 18, "600"))
    parts.append(label(w - 200, 214, "YR COMMITS"))
    parts.append(paper_text(w - 200, 236, str(data["contributions_year"]), 18, "600"))

    # Footer strip
    parts.append(label(24, h - 16, f"LAST COMPILED  {data['compiled_at']}"))
    parts.append(label(w - 200, h - 16, f"SRC  {data['source'].upper()}"))

    parts.append(svg_close())
    write_svg("hero-blueprint.svg", "".join(parts))


def intensity_color(count: int, peak: int) -> str:
    if count <= 0:
        return DIM
    t = min(1.0, count / max(1, peak))
    # Ramp DIM → GOLD
    # DIM #1A1A1A → GOLD #FFD000
    r = int(0x1A + t * (0xFF - 0x1A))
    g = int(0x1A + t * (0xD0 - 0x1A))
    b = int(0x1A + t * (0x00 - 0x1A))
    return f"#{r:02X}{g:02X}{b:02X}"


def build_telemetry_matrix(data: dict[str, Any]) -> None:
    weeks = data["weeks"]
    cell, gap = 11, 3
    pad_l, pad_t = 72, 64
    grid_w = 52 * (cell + gap) - gap
    grid_h = 7 * (cell + gap) - gap
    w = pad_l + grid_w + 200
    h = pad_t + grid_h + 72

    peak = max((c for week in weeks for c in week), default=1) or 1

    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(label(20, 28, "SHEET 02A — CONTRIBUTION MATRIX"))
    parts.append(gold_text(20, 48, "52-WEEK ACTIVITY · PLOTTER GRID", 12))

    # Day labels
    day_labels = ["M", "", "W", "", "F", "", ""]
    for i, d in enumerate(day_labels):
        if d:
            parts.append(
                f'<text x="52" y="{pad_t + i * (cell + gap) + cell - 1}" '
                f'class="mono" font-size="9" fill="{SLATE}" text-anchor="end">{d}</text>\n'
            )

    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            x = pad_l + wi * (cell + gap)
            y = pad_t + di * (cell + gap)
            fill = intensity_color(count, peak)
            stroke = GOLD if count >= peak * 0.75 and count > 0 else BORDER
            sw = 1.2 if stroke == GOLD else 1
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>\n'
            )

    # Side metrics
    mx = pad_l + grid_w + 28
    parts.append(hairline_v(mx - 16, 48, h - 80))
    metrics = [
        ("CURRENT STREAK", f"{data['current_streak']} d"),
        ("LONGEST STREAK", f"{data['longest_streak']} d"),
        ("YEAR TOTAL", str(data["contributions_year"])),
        ("PUBLIC REPOS", str(data["public_repos"])),
    ]
    for i, (k, v) in enumerate(metrics):
        y = 70 + i * 48
        parts.append(label(mx, y, k, 9))
        parts.append(gold_text(mx, y + 20, v, 20, "700"))

    # Legend
    parts.append(label(20, h - 24, "INTENSITY"))
    for i in range(5):
        c = intensity_color(i, 4)
        parts.append(
            f'<rect x="{100 + i * 16}" y="{h - 34}" width="12" height="12" '
            f'fill="{c}" stroke="{BORDER}" stroke-width="1"/>\n'
        )
    parts.append(label(190, h - 24, "LOW → HIGH", 9))

    parts.append(svg_close())
    write_svg("telemetry-matrix.svg", "".join(parts))


def build_telemetry_languages(data: dict[str, Any]) -> None:
    langs = data["languages"]
    w, h = 900, 320
    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(label(20, 28, "SHEET 02B — LANGUAGE & SYSTEMS DISTRIBUTION"))
    parts.append(gold_text(20, 48, "WEIGHTED BY REPOSITORY BYTE MASS", 12))
    parts.append(hairline_h(20, 60, w - 40))

    bar_x, bar_w = 180, w - 220
    y0 = 88
    row_h = 32

    for i, (name, pct) in enumerate(langs):
        y = y0 + i * row_h
        parts.append(
            f'<text x="24" y="{y + 14}" class="mono" font-size="12" fill="{PAPER}">'
            f"{esc(name.upper())}</text>\n"
        )
        # Track
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="16" '
            f'fill="{DIM}" stroke="{BORDER}" stroke-width="1"/>\n'
        )
        fill_w = max(2, bar_w * (pct / 100.0))
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{fill_w:.1f}" height="16" '
            f'fill="{GOLD}" opacity="0.92"/>\n'
        )
        parts.append(
            f'<text x="{bar_x + bar_w + 8}" y="{y + 13}" class="mono" font-size="11" '
            f'fill="{SLATE}">{pct:.1f}%</text>\n'
        )

    parts.append(label(24, h - 20, f"N = {len(langs)} SERIES · SRC = {data['source'].upper()}"))
    parts.append(svg_close())
    write_svg("telemetry-languages.svg", "".join(parts))


def build_architecture_flow() -> None:
    w, h = 1100, 220
    stages = [
        ("01", "SPEC"),
        ("02", "ISOLATED BRANCH"),
        ("03", "BUILD"),
        ("04", "BENCHMARK"),
        ("05", "SHIP"),
    ]
    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(label(20, 28, "SHEET 02C — WORKFLOW SCHEMATIC"))
    parts.append(gold_text(20, 48, "HOW SYSTEMS MOVE FROM INTENT → ARTIFACT", 12))
    parts.append(hairline_h(20, 60, w - 40))

    box_w, box_h = 160, 72
    gap = 36
    total = len(stages) * box_w + (len(stages) - 1) * gap
    x0 = (w - total) / 2
    y = 100

    for i, (num, name) in enumerate(stages):
        x = x0 + i * (box_w + gap)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" '
            f'fill="{DIM}" stroke="{GOLD if i == len(stages) - 1 else BORDER}" '
            f'stroke-width="1.5"/>\n'
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 24}" class="mono" font-size="10" fill="{SLATE}">'
            f"{num}</text>\n"
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 48}" class="sans" font-size="14" font-weight="600" '
            f'fill="{PAPER}">{esc(name)}</text>\n'
        )
        if i < len(stages) - 1:
            ax = x + box_w
            parts.append(
                f'<line x1="{ax + 4}" y1="{y + box_h / 2}" x2="{ax + gap - 10}" '
                f'y2="{y + box_h / 2}" stroke="{GOLD}" stroke-width="1.5"/>\n'
            )
            parts.append(
                f'<polygon points="{ax + gap - 10},{y + box_h / 2 - 5} '
                f'{ax + gap - 2},{y + box_h / 2} '
                f'{ax + gap - 10},{y + box_h / 2 + 5}" fill="{GOLD}"/>\n'
            )

    parts.append(label(24, h - 18, "LOOP: FAIL BENCHMARK → RETURN TO SPEC"))
    parts.append(svg_close())
    write_svg("architecture-flow.svg", "".join(parts))


def build_stack_matrix() -> None:
    w, h = 1100, 280
    cells = [
        ("PY", "Python"),
        ("TS", "TypeScript"),
        ("JS", "JavaScript"),
        ("SW", "Swift"),
        ("C", "C / C++"),
        ("SQL", "SQL"),
        ("NX", "Next.js"),
        ("R", "React"),
        ("GL", "WebGL"),
        ("FA", "FastAPI"),
        ("PR", "Prisma"),
        ("DK", "Docker"),
        ("GH", "Git"),
        ("iOS", "Vision"),
        ("BS", "BeautifulSoup"),
        ("ND", "Node.js"),
    ]
    cols = 8
    cw, ch = 120, 72
    pad = 24
    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(label(20, 26, "SHEET 04 — TECHNICAL MATRIX"))
    parts.append(gold_text(20, 46, "VECTOR BADGE GRID · MONOCHROME + GOLD", 12))

    grid_y = 64
    for i, (abbr, name) in enumerate(cells):
        col = i % cols
        row = i // cols
        x = pad + col * (cw + 10)
        y = grid_y + row * (ch + 10)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" '
            f'fill="{DIM}" stroke="{BORDER}" stroke-width="1"/>\n'
        )
        # gold corner tick
        parts.append(
            f'<path d="M{x},{y + 12} V{y} H{x + 12}" stroke="{GOLD}" '
            f'stroke-width="1.5" fill="none"/>\n'
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 28}" class="mono" font-size="16" font-weight="700" '
            f'fill="{GOLD}">{esc(abbr)}</text>\n'
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 52}" class="sans" font-size="11" '
            f'fill="{PAPER}">{esc(name)}</text>\n'
        )

    parts.append(svg_close())
    write_svg("stack-matrix.svg", "".join(parts))


def build_footer(data: dict[str, Any]) -> None:
    w, h = 1100, 120
    parts = [svg_open(w, h)]
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(hairline_v(200, 0, h))
    parts.append(hairline_v(520, 0, h))
    parts.append(hairline_v(820, 0, h))

    parts.append(label(20, 28, "END OF DRAWING"))
    parts.append(gold_text(20, 58, "FADED DARTS", 16, "700"))
    parts.append(paper_text(20, 82, "PROFILE README", 12))
    parts.append(label(20, 104, f"COMPILED  {data['compiled_at']}", 9))

    links = [
        (220, "PORTFOLIO", "fadeddarts.github.io/portfolio"),
        (540, "REPOSITORIES", "github.com/fadeddarts"),
        (840, "LINKEDIN", "linkedin.com/in/harpuneet-390-singh"),
    ]
    for x, title, url in links:
        parts.append(label(x, 36, title, 10))
        parts.append(
            f'<text x="{x}" y="68" class="mono" font-size="12" fill="{PAPER}">'
            f"{esc(url)}</text>\n"
        )
        parts.append(
            f'<rect x="{x}" y="84" width="40" height="3" fill="{GOLD}"/>\n'
        )

    parts.append(svg_close())
    write_svg("footer-block.svg", "".join(parts))


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    print("fadeddarts asset build")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = fetch_telemetry(token)
    print(f"  source={data['source']} compiled={data['compiled_at']}")

    build_hero(data)
    build_telemetry_matrix(data)
    build_telemetry_languages(data)
    build_architecture_flow()
    build_stack_matrix()
    build_footer(data)

    meta = {
        "compiled_at": data["compiled_at"],
        "source": data["source"],
        "contributions_year": data["contributions_year"],
        "current_streak": data["current_streak"],
        "languages": data["languages"],
    }
    (ASSETS / "build-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("  wrote assets/build-meta.json")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
