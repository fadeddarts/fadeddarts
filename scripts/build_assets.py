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
ACCENT = "#2B6CFF"  # electric signal blue (replaces gold)
ACCENT_MID = "#1A4ACC"
ACCENT_DIM = "#142A66"
DIM = "#1A1A1A"

USERNAME = "fadeddarts"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Common, widely-available stacks (Google Sans ≈ system UI; Playfair for display)
MONO = '"Noto Sans Mono", "SF Mono", Menlo, Consolas, monospace'
SANS = '"Noto Sans", Montserrat, "Google Sans", "Segoe UI", Helvetica, Arial, sans-serif'
DISPLAY = '"Playfair Display", Georgia, "Times New Roman", serif'

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
        f"    .mono {{ font-family: {MONO}; }}\n"
        f"    .sans {{ font-family: {SANS}; }}\n"
        f"    .display {{ font-family: {DISPLAY}; }}\n"
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


def accent_text(x: float, y: float, text: str, size: int = 12, weight: str = "600") -> str:
    return (
        f'<text x="{x}" y="{y}" class="mono" font-size="{size}" font-weight="{weight}" '
        f'fill="{ACCENT}">{esc(text)}</text>\n'
    )


def write_svg(name: str, content: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")
    return path


def lerp_hex(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ai = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    bi = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    rgb = [int(ai[i] + (bi[i] - ai[i]) * t) for i in range(3)]
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def intensity_color(count: int, peak: int) -> str:
    if count <= 0:
        return DIM
    t = min(1.0, count / max(1, peak))
    if t < 0.45:
        return lerp_hex(BORDER, ACCENT_MID, t / 0.45)
    return lerp_hex(ACCENT_MID, ACCENT, (t - 0.45) / 0.55)


# ── Data layer ───────────────────────────────────────────────────────────────


def mock_telemetry() -> dict[str, Any]:
    weeks: list[list[int]] = []
    for w in range(52):
        days = []
        for d in range(7):
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
        "pull_requests": 14,
        "total_commits": 842,
        "current_streak": 4,
        "longest_streak": 18,
        "contributions_year": 612,
        "weeks": weeks,
        "languages": [
            ("TypeScript", 33.0),
            ("HTML/CSS", 28.0),
            ("JavaScript", 16.0),
            ("Python", 14.0),
            ("Swift", 6.0),
            ("Other", 3.0),
        ],
        "status": "COMPILING",
        "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "mock",
    }


def _ssl_context():
    try:
        import certifi  # type: ignore
        import ssl

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        import ssl

        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()


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
    ctx = _ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        import ssl

        with urllib.request.urlopen(
            req, timeout=45, context=ssl._create_unverified_context()
        ) as resp:
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
        pullRequests(first: 1) { totalCount }
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
    weeks_raw = user["contributionsCollection"]["contributionCalendar"]["weeks"][-52:]
    weeks: list[list[int]] = []
    flat: list[int] = []
    for week in weeks_raw:
        days = [d["contributionCount"] for d in week["contributionDays"]]
        while len(days) < 7:
            days.append(0)
        weeks.append(days[:7])
        flat.extend(days[:7])

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

    lang_bytes: dict[str, int] = {}
    for node in user["repositories"]["nodes"]:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

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

    contributions = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    return {
        "login": user["login"],
        "name": user["name"] or "Harpuneet Singh",
        "public_repos": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "pull_requests": user["pullRequests"]["totalCount"],
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
    parts.append(hairline_h(0, 48, w))
    parts.append(hairline_h(0, h - 40, w))
    parts.append(hairline_v(160, 0, h))
    parts.append(hairline_v(w - 220, 0, h))

    for cx, cy in [(12, 12), (w - 12, 12), (12, h - 12), (w - 12, h - 12)]:
        parts.append(
            f'<path d="M{cx - 8},{cy} H{cx + 8} M{cx},{cy - 8} V{cy + 8}" '
            f'stroke="{ACCENT}" stroke-width="1.5"/>\n'
        )

    parts.append(label(24, 28, "DWG 00 — TITLE BLOCK"))
    parts.append(label(24, 78, "SHEET"))
    parts.append(accent_text(24, 108, "00", 36, "700"))
    parts.append(label(24, 140, "REV"))
    parts.append(paper_text(24, 162, "B", 18, "600"))
    parts.append(label(24, 200, "SCALE"))
    parts.append(paper_text(24, 222, "1 : 1", 14))

    parts.append(label(180, 28, "SUBJECT / AUTHOR"))
    parts.append(
        f'<text x="180" y="118" class="display" font-size="42" font-weight="700" '
        f'fill="{PAPER}" letter-spacing="-0.5">{esc(data["name"])}</text>\n'
    )
    parts.append(
        f'<text x="180" y="152" class="mono" font-size="16" fill="{ACCENT}">'
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

    gx, gy = 720, 70
    parts.append(
        f'<g stroke="{ACCENT}" stroke-width="1" fill="none" opacity="0.9">\n'
        f'  <rect x="{gx}" y="{gy}" width="120" height="120"/>\n'
        f'  <line x1="{gx}" y1="{gy}" x2="{gx + 120}" y2="{gy + 120}"/>\n'
        f'  <line x1="{gx + 120}" y1="{gy}" x2="{gx}" y2="{gy + 120}"/>\n'
        f'  <circle cx="{gx + 60}" cy="{gy + 60}" r="28"/>\n'
        f'  <circle cx="{gx + 60}" cy="{gy + 60}" r="8" fill="{ACCENT}" stroke="none"/>\n'
        f'  <path d="M{gx + 20},{gy + 100} L{gx + 60},{gy + 20} L{gx + 100},{gy + 100} Z"/>\n'
        f"</g>\n"
    )

    parts.append(label(w - 200, 28, "STATUS"))
    parts.append(accent_text(w - 200, 78, data["status"], 18, "700"))
    parts.append(label(w - 200, 110, "COORD / LOC"))
    parts.append(paper_text(w - 200, 132, "TORONTO, ON", 13))
    parts.append(label(w - 200, 164, "REPOS"))
    parts.append(paper_text(w - 200, 186, str(data["public_repos"]), 18, "600"))
    parts.append(label(w - 200, 214, "YR COMMITS"))
    parts.append(paper_text(w - 200, 236, str(data["contributions_year"]), 18, "600"))

    parts.append(label(24, h - 16, f"LAST COMPILED  {data['compiled_at']}"))
    parts.append(label(w - 200, h - 16, f"SRC  {data['source'].upper()}"))
    parts.append(svg_close())
    write_svg("hero-blueprint.svg", "".join(parts))


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
    parts.append(accent_text(20, 48, "52-WEEK ACTIVITY · PLOTTER GRID", 12))

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
            stroke = ACCENT if count >= peak * 0.75 and count > 0 else BORDER
            sw = 1.2 if stroke == ACCENT else 1
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>\n'
            )

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
        parts.append(accent_text(mx, y + 20, v, 20, "700"))

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
    parts.append(accent_text(20, 48, "WEIGHTED BY REPOSITORY BYTE MASS", 12))
    parts.append(hairline_h(20, 60, w - 40))

    bar_x, bar_w = 180, w - 220
    y0 = 88
    for i, (name, pct) in enumerate(langs):
        y = y0 + i * 32
        parts.append(
            f'<text x="24" y="{y + 14}" class="mono" font-size="12" fill="{PAPER}">'
            f"{esc(name.upper())}</text>\n"
        )
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="16" '
            f'fill="{DIM}" stroke="{BORDER}" stroke-width="1"/>\n'
        )
        fill_w = max(2, bar_w * (pct / 100.0))
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{fill_w:.1f}" height="16" '
            f'fill="{ACCENT}" opacity="0.92"/>\n'
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
    parts.append(accent_text(20, 48, "HOW SYSTEMS MOVE FROM INTENT → ARTIFACT", 12))
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
            f'fill="{DIM}" stroke="{ACCENT if i == len(stages) - 1 else BORDER}" '
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
                f'y2="{y + box_h / 2}" stroke="{ACCENT}" stroke-width="1.5"/>\n'
            )
            parts.append(
                f'<polygon points="{ax + gap - 10},{y + box_h / 2 - 5} '
                f'{ax + gap - 2},{y + box_h / 2} '
                f'{ax + gap - 10},{y + box_h / 2 + 5}" fill="{ACCENT}"/>\n'
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
    parts.append(accent_text(20, 46, "VECTOR BADGE GRID · MONOCHROME + SIGNAL", 12))

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
        parts.append(
            f'<path d="M{x},{y + 12} V{y} H{x + 12}" stroke="{ACCENT}" '
            f'stroke-width="1.5" fill="none"/>\n'
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 28}" class="mono" font-size="16" font-weight="700" '
            f'fill="{ACCENT}">{esc(abbr)}</text>\n'
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
    parts.append(accent_text(20, 58, "FADED DARTS", 16, "700"))
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
        parts.append(f'<rect x="{x}" y="84" width="40" height="3" fill="{ACCENT}"/>\n')

    parts.append(svg_close())
    write_svg("footer-block.svg", "".join(parts))


def build_kinetic_telemetry(data: dict[str, Any]) -> None:
    """840×320 kinetic instrument: isometric skyline + radar + oscilloscope."""
    w, h = 840, 320
    weeks = data["weeks"]
    # Aggregate weekly totals for skyline columns
    weekly = [sum(days) for days in weeks]
    while len(weekly) < 52:
        weekly.insert(0, 0)
    weekly = weekly[-52:]
    peak_w = max(weekly) or 1
    peak_d = max((c for week in weeks for c in week), default=1) or 1

    # Radar axes normalized 0..1
    commits_n = min(1.0, data["contributions_year"] / 400.0)
    repos_n = min(1.0, data["public_repos"] / 40.0)
    prs_n = min(1.0, data.get("pull_requests", 0) / 40.0)
    streak_n = min(1.0, max(data["current_streak"], data["longest_streak"]) / 30.0)
    axes = [
        ("COMMITS", commits_n),
        ("REPOS", repos_n),
        ("PULL REQUESTS", prs_n),
        ("STREAK", streak_n),
    ]

    top_lang = data["languages"][0][0] if data["languages"] else "—"

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">\n'
    )
    parts.append("<defs>\n")
    parts.append(
        f'<style><![CDATA[\n'
        f"  .mono {{ font-family: {MONO}; }}\n"
        f"  .sans {{ font-family: {SANS}; }}\n"
        f"  .display {{ font-family: {DISPLAY}; }}\n"
        f"  @keyframes scan {{\n"
        f"    0% {{ transform: translateX(0); opacity: 0.15; }}\n"
        f"    8% {{ opacity: 0.95; }}\n"
        f"    92% {{ opacity: 0.95; }}\n"
        f"    100% {{ transform: translateX(470px); opacity: 0.15; }}\n"
        f"  }}\n"
        f"  @keyframes pulse {{\n"
        f"    0%, 100% {{ opacity: 0.35; }}\n"
        f"    50% {{ opacity: 1; }}\n"
        f"  }}\n"
        f"  @keyframes ring {{\n"
        f"    0% {{ r: 18; opacity: 0.7; }}\n"
        f"    100% {{ r: 78; opacity: 0; }}\n"
        f"  }}\n"
        f"  @keyframes dash {{\n"
        f"    to {{ stroke-dashoffset: -420; }}\n"
        f"  }}\n"
        f"  @keyframes nodeblink {{\n"
        f"    0%, 100% {{ opacity: 0.55; }}\n"
        f"    50% {{ opacity: 1; }}\n"
        f"  }}\n"
        f"  .scan-beam {{\n"
        f"    animation: scan 4.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;\n"
        f"  }}\n"
        f"  .tower-pulse {{\n"
        f"    animation: pulse 2.4s ease-in-out infinite;\n"
        f"  }}\n"
        f"  .radar-ring {{\n"
        f"    fill: none; stroke: {ACCENT}; stroke-width: 1;\n"
        f"    animation: ring 2.8s linear infinite;\n"
        f"  }}\n"
        f"  .wave {{\n"
        f"    fill: none; stroke: {ACCENT}; stroke-width: 1.6;\n"
        f"    stroke-dasharray: 12 8;\n"
        f"    animation: dash 2.2s linear infinite;\n"
        f"  }}\n"
        f"  .node {{\n"
        f"    animation: nodeblink 1.6s ease-in-out infinite;\n"
        f"  }}\n"
        f"]]></style>\n"
    )
    parts.append(
        f'<linearGradient id="beamGrad" x1="0" y1="0" x2="0" y2="1">\n'
        f'  <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0"/>\n'
        f'  <stop offset="35%" stop-color="{ACCENT}" stop-opacity="0.55"/>\n'
        f'  <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>\n'
        f"</linearGradient>\n"
    )
    parts.append(
        f'<linearGradient id="panelGrad" x1="0" y1="0" x2="1" y2="1">\n'
        f'  <stop offset="0%" stop-color="{INK}"/>\n'
        f'  <stop offset="100%" stop-color="{DIM}"/>\n'
        f"</linearGradient>\n"
    )
    parts.append("</defs>\n")

    # Frame + structural grid
    parts.append(card(0.5, 0.5, w - 1, h - 1))
    parts.append(f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="url(#panelGrad)" opacity="0.35"/>\n')
    for gx in range(0, w, 40):
        parts.append(f'<line x1="{gx}" y1="36" x2="{gx}" y2="{h - 1}" stroke="{BORDER}" stroke-width="1" opacity="0.45"/>\n')
    for gy in range(36, h, 40):
        parts.append(f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke="{BORDER}" stroke-width="1" opacity="0.45"/>\n')

    parts.append(hairline_h(0, 36, w))
    parts.append(hairline_v(520, 36, h - 36))
    parts.append(label(14, 24, "KINETIC TELEMETRY & ARCHITECTURAL SYNTHESIZER"))
    parts.append(accent_text(620, 24, f"SRC {data['source'].upper()} · {data['compiled_at']}", 9))

    # ── Left: isometric weekly skyline ──────────────────────────────────────
    parts.append(label(16, 54, "01  ISOMETRIC COMMIT SKYLINE — 52 WEEKS"))

    # Isometric projection helpers
    # Column along week index; height from weekly total
    origin_x, origin_y = 48, 268
    sx, sy = 7.2, 4.0  # isometric scale
    max_h = 118.0

    # Ground plane diamond-ish grid
    parts.append(
        f'<path d="M{origin_x},{origin_y} L{origin_x + 52 * sx},{origin_y - 52 * sy * 0.35} '
        f'L{origin_x + 52 * sx + 28},{origin_y - 52 * sy * 0.35 - 14} '
        f'L{origin_x + 28},{origin_y - 14} Z" fill="{DIM}" stroke="{BORDER}" stroke-width="1"/>\n'
    )

    for i, total in enumerate(weekly):
        t = total / peak_w
        height = 6 + t * max_h
        # isometric base position
        bx = origin_x + i * sx
        by = origin_y - i * sy * 0.35
        # box dimensions in iso
        hw, hd = 5.5, 4.5
        top_y = by - height
        fill = intensity_color(max(1, total) if total else 0, peak_w) if total else DIM
        # faces: left, right, top
        # right face
        parts.append(
            f'<polygon points="{bx},{by} {bx + hw},{by - hd} {bx + hw},{top_y - hd} {bx},{top_y}" '
            f'fill="{fill}" stroke="{BORDER}" stroke-width="0.6" opacity="0.95"/>\n'
        )
        # left/back face (darker)
        left_fill = lerp_hex(fill, INK, 0.35)
        parts.append(
            f'<polygon points="{bx},{by} {bx},{top_y} {bx - hw * 0.55},{top_y - hd * 0.4} '
            f'{bx - hw * 0.55},{by - hd * 0.4}" '
            f'fill="{left_fill}" stroke="{BORDER}" stroke-width="0.5" opacity="0.9"/>\n'
        )
        # top face
        top_fill = lerp_hex(fill, ACCENT, 0.25) if total else BORDER
        parts.append(
            f'<polygon class="{"tower-pulse" if t > 0.55 else ""}" '
            f'style="animation-delay:{(i % 12) * 0.12:.2f}s" '
            f'points="{bx},{top_y} {bx + hw},{top_y - hd} '
            f'{bx + hw - hw * 0.55},{top_y - hd - hd * 0.4} {bx - hw * 0.55},{top_y - hd * 0.4}" '
            f'fill="{top_fill}" stroke="{ACCENT if t > 0.7 else BORDER}" stroke-width="0.7"/>\n'
        )

    # Scanning laser beam
    parts.append(
        f'<g class="scan-beam">\n'
        f'  <rect x="{origin_x}" y="58" width="3" height="210" fill="url(#beamGrad)"/>\n'
        f'  <line x1="{origin_x + 1.5}" y1="58" x2="{origin_x + 1.5}" y2="268" '
        f'stroke="{ACCENT}" stroke-width="1.2" opacity="0.9"/>\n'
        f"</g>\n"
    )

    # SMIL fallback scan for environments that strip CSS animation on img
    parts.append(
        f'<rect x="{origin_x}" y="58" width="2" height="210" fill="{ACCENT}" opacity="0.25">\n'
        f'  <animate attributeName="x" values="{origin_x};{origin_x + 470};{origin_x}" '
        f'dur="4.8s" repeatCount="indefinite"/>\n'
        f'  <animate attributeName="opacity" values="0.1;0.55;0.1" dur="4.8s" repeatCount="indefinite"/>\n'
        f"</rect>\n"
    )

    # ── Right top: radar ─────────────────────────────────────────────────────
    parts.append(label(536, 54, "02  RADAR — COMMITS / REPOS / PRS / STREAK"))
    cx, cy, rr = 680, 130, 58
    for ring_r in (20, 38, 58):
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="{BORDER}" stroke-width="1"/>\n'
        )
    # Animated pulse rings (CSS + SMIL)
    parts.append(
        f'<circle class="radar-ring" cx="{cx}" cy="{cy}" r="18" stroke="{ACCENT}">\n'
        f'  <animate attributeName="r" values="18;78" dur="2.8s" repeatCount="indefinite"/>\n'
        f'  <animate attributeName="opacity" values="0.7;0" dur="2.8s" repeatCount="indefinite"/>\n'
        f"</circle>\n"
    )
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="18" fill="none" stroke="{ACCENT}" opacity="0.4">\n'
        f'  <animate attributeName="r" values="18;78" dur="2.8s" begin="1.4s" repeatCount="indefinite"/>\n'
        f'  <animate attributeName="opacity" values="0.55;0" dur="2.8s" begin="1.4s" repeatCount="indefinite"/>\n'
        f"</circle>\n"
    )

    # Axis lines + labels
    poly_pts: list[str] = []
    for i, (name, val) in enumerate(axes):
        ang = -math.pi / 2 + i * (math.pi / 2)
        x2 = cx + math.cos(ang) * rr
        y2 = cy + math.sin(ang) * rr
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{BORDER}" stroke-width="1"/>\n'
        )
        lx = cx + math.cos(ang) * (rr + 14)
        ly = cy + math.sin(ang) * (rr + 14)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" class="mono" font-size="8" fill="{SLATE}" '
            f'text-anchor="middle" dominant-baseline="middle">{esc(name)}</text>\n'
        )
        px = cx + math.cos(ang) * rr * max(0.12, val)
        py = cy + math.sin(ang) * rr * max(0.12, val)
        poly_pts.append(f"{px:.1f},{py:.1f}")

    parts.append(
        f'<polygon points="{" ".join(poly_pts)}" fill="{ACCENT}" fill-opacity="0.18" '
        f'stroke="{ACCENT}" stroke-width="1.5"/>\n'
    )
    for i, pt in enumerate(poly_pts):
        px, py = pt.split(",")
        delay = i * 0.2
        parts.append(
            f'<circle class="node" style="animation-delay:{delay:.1f}s" '
            f'cx="{px}" cy="{py}" r="3.2" fill="{ACCENT}">\n'
            f'  <animate attributeName="opacity" values="0.5;1;0.5" dur="1.6s" '
            f'begin="{delay:.1f}s" repeatCount="indefinite"/>\n'
            f"</circle>\n"
        )

    # ── Right bottom: oscilloscope ───────────────────────────────────────────
    parts.append(hairline_h(520, 198, w - 520))
    parts.append(label(536, 216, "03  CODE VELOCITY OSCILLOSCOPE"))

    # Waveform from weekly rhythm
    path_cmds: list[str] = []
    wx0, wy0, ww, wh = 540, 248, 270, 42
    for i, total in enumerate(weekly):
        x = wx0 + (i / 51) * ww
        amp = (total / peak_w) * (wh / 2)
        # Add slight sine for continuous motion feel
        y = wy0 + math.sin(i * 0.55) * 3 - amp
        path_cmds.append(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}")
    wave_d = " ".join(path_cmds)
    parts.append(
        f'<rect x="{wx0 - 4}" y="{wy0 - wh / 2 - 4}" width="{ww + 8}" height="{wh + 12}" '
        f'fill="{DIM}" stroke="{BORDER}" stroke-width="1"/>\n'
    )
    parts.append(f'<path class="wave" d="{wave_d}"/>\n')
    # SMIL dashoffset fallback
    parts.append(
        f'<path d="{wave_d}" fill="none" stroke="{ACCENT}" stroke-width="1.2" '
        f'stroke-dasharray="10 7" opacity="0.55">\n'
        f'  <animate attributeName="stroke-dashoffset" from="0" to="-420" '
        f'dur="2.2s" repeatCount="indefinite"/>\n'
        f"</path>\n"
    )

    # Readouts
    parts.append(
        f'<text x="540" y="308" class="mono" font-size="9" fill="{SLATE}">'
        f'TOTAL_COMMITS <tspan fill="{ACCENT}" font-weight="700">{data["contributions_year"]}</tspan>'
        f'   ACTIVE_STREAK <tspan fill="{ACCENT}" font-weight="700">{data["current_streak"]}d</tspan>'
        f'   TOP_LANGUAGE <tspan fill="{PAPER}" font-weight="700">{esc(top_lang.upper())}</tspan>'
        f"</text>\n"
    )

    parts.append(svg_close())
    write_svg("kinetic-telemetry.svg", "".join(parts))


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    print("fadeddarts asset build")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    data = fetch_telemetry(token)
    print(f"  source={data['source']} compiled={data['compiled_at']}")

    build_hero(data)
    build_kinetic_telemetry(data)
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
        "pull_requests": data.get("pull_requests", 0),
        "languages": data["languages"],
        "accent": ACCENT,
    }
    (ASSETS / "build-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("  wrote assets/build-meta.json")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
