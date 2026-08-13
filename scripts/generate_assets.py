#!/usr/bin/env python3
"""
Genera los assets SVG del README (stats, lenguajes, racha y proyectos)
usando datos reales obtenidos de la API GraphQL de GitHub.

Variables de entorno:
  GH_TOKEN       -> token con permisos de lectura (obligatorio)
  GH_LOGIN       -> usuario de GitHub a consultar (default: InnoDev69)
  DISPLAY_NAME   -> nombre a mostrar en la card (opcional; si no se
                     define, se usa el campo "name" del perfil, y si
                     ese campo está vacío, el login)
"""

import os
import sys
import math
import datetime
import requests

GITHUB_LOGIN = os.environ.get("GH_LOGIN", "InnoDev69")
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
DISPLAY_NAME_OVERRIDE = os.environ.get("DISPLAY_NAME")
API_URL = "https://api.github.com/graphql"

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BG_START = "#0f1218"
BG_END = "#1b1f28"
BORDER = "#a41c1c"
ACCENT_1 = "#a41c1c"
ACCENT_2 = "#ff5b5b"
TEXT = "#f3f3f3"
MUTED = "#9099a8"
TRACK = "#262b35"

CARD_WIDTH = 480

QUERY = """
query ($login: String!) {
  user(login: $login) {
    name
    login
    avatarUrl(size: 200)
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        url
        description
        stargazerCount
        primaryLanguage { name color }
      }
    }
  }
}
"""


def fetch_data():
    if not GITHUB_TOKEN:
        print("ERROR: falta la variable de entorno GH_TOKEN", file=sys.stderr)
        sys.exit(1)
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    r = requests.post(API_URL, json={"query": QUERY, "variables": {"login": GITHUB_LOGIN}},
                       headers=headers, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        print(f"ERROR de la API: {payload['errors']}", file=sys.stderr)
        sys.exit(1)
    return payload["data"]["user"]


def compute_streaks(weeks):
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    days.sort(key=lambda d: d[0])
    today = datetime.date.today().isoformat()
    days = [d for d in days if d[0] <= today]

    longest = running = 0
    for _, count in days:
        if count > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    current = 0
    for _, count in reversed(days):
        if count > 0:
            current += 1
        else:
            break

    total = sum(c for _, c in days)
    return current, longest, total


def compute_languages(repos):
    totals = {}
    for repo in repos:
        lang = repo.get("primaryLanguage")
        if not lang:
            continue
        entry = totals.setdefault(lang["name"], {"count": 0, "color": lang["color"] or ACCENT_2})
        entry["count"] += 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1]["count"], reverse=True)
    total = sum(v["count"] for _, v in ranked)
    return ranked[:6], total


def top_projects(repos, n=2):
    scored = sorted(repos, key=lambda r: r["stargazerCount"], reverse=True)
    return scored[:n]


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def truncate(text, length):
    text = text or "Sin descripción."
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Primitivas / iconos vectoriales (sin emojis, sin fuentes externas)
# ---------------------------------------------------------------------------

def defs_block():
    return f"""<defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{BG_START}"/>
      <stop offset="1" stop-color="{BG_END}"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{ACCENT_1}"/>
      <stop offset="1" stop-color="{ACCENT_2}"/>
    </linearGradient>
    <clipPath id="avatarClip"><circle cx="0" cy="0" r="26"/></clipPath>
  </defs>"""


def card_open(width, height, title, subtitle=None, avatar_url=None):
    header_h = 78 if subtitle else 64
    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(defs_block())
    parts.append(f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="url(#bgGrad)" stroke="{BORDER}" stroke-width="1.3"/>')

    if avatar_url:
        cx, cy = 46, 46
        parts.append(f'<g transform="translate({cx},{cy})">')
        parts.append(f'<circle r="28" fill="{TRACK}"/>')
        parts.append(f'<g clip-path="url(#avatarClip)"><image href="{avatar_url}" x="-26" y="-26" width="52" height="52"/></g>')
        parts.append(f'<circle r="27" fill="none" stroke="url(#accentGrad)" stroke-width="1.6"/>')
        parts.append("</g>")
        text_x = 84
    else:
        text_x = 26

    parts.append(f'<text x="{text_x}" y="34" font-family="Segoe UI, Ubuntu, sans-serif" font-size="19" font-weight="700" fill="{TEXT}">{esc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{text_x}" y="56" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12.5" fill="{MUTED}">{esc(subtitle)}</text>')

    parts.append(f'<rect x="26" y="{header_h}" width="{width - 52}" height="1" fill="{TRACK}"/>')
    return "\n  ".join(parts), header_h + 20


def card_close():
    return "</svg>"


def icon(name, cx, cy, color, size=8):
    s = size / 8.0
    g = [f'<g transform="translate({cx},{cy}) scale({s})" stroke="{color}" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">']

    if name == "repo":
        g.append('<rect x="-6" y="-7" width="12" height="14" rx="2"/>')
        g.append('<line x1="-6" y1="-2.5" x2="6" y2="-2.5"/>')
    elif name == "star":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = 7 if i % 2 == 0 else 3
            pts.append(f"{r * math.cos(ang):.2f},{r * math.sin(ang):.2f}")
        g.append(f'<polygon points="{" ".join(pts)}" fill="{color}" stroke="none"/>')
    elif name == "commit":
        g.append('<circle r="3"/>')
        g.append('<line x1="-8" y1="0" x2="-3" y2="0"/>')
        g.append('<line x1="3" y1="0" x2="8" y2="0"/>')
    elif name == "branch":
        g.append('<circle cx="-5" cy="-5" r="2"/>')
        g.append('<circle cx="-5" cy="5" r="2"/>')
        g.append('<circle cx="5" cy="5" r="2"/>')
        g.append('<line x1="-5" y1="-3" x2="-5" y2="3"/>')
        g.append('<path d="M -5 -3 C -5 -6 5 -6 5 3"/>')
    elif name == "issue":
        g.append('<circle r="7"/>')
        g.append('<line x1="0" y1="-3.2" x2="0" y2="1"/>')
        g.append('<circle cx="0" cy="4" r="0.9" fill="' + color + '" stroke="none"/>')
    elif name == "users":
        g.append('<circle cx="-3" cy="-3" r="3"/>')
        g.append('<circle cx="4" cy="-1" r="2.3"/>')
        g.append('<path d="M -9 7 C -9 1 3 1 3 7"/>')
        g.append('<path d="M 1 7 C 1 3 9 3 9 7"/>')
    elif name == "flame":
        g.append(f'<path d="M 0 -8 C 4 -4 6 -1 4 3 C 6 1 7 -1 7 -1 C 8 3 6 8 0 8 '
                  f'C -6 8 -8 3 -7 -1 C -7 -1 -6 1 -4 2 C -5 -3 -2 -6 0 -8 Z" '
                  f'fill="{color}" stroke="none"/>')
    elif name == "code":
        g.append('<polyline points="-3,-6 -8,0 -3,6"/>')
        g.append('<polyline points="3,-6 8,0 3,6"/>')
    elif name == "calendar":
        g.append('<rect x="-7" y="-6" width="14" height="13" rx="2"/>')
        g.append('<line x1="-7" y1="-2" x2="7" y2="-2"/>')
        g.append('<line x1="-3.5" y1="-8" x2="-3.5" y2="-5"/>')
        g.append('<line x1="3.5" y1="-8" x2="3.5" y2="-5"/>')

    g.append("</g>")
    return "".join(g)


def stat_row(y, icon_name, label, value, width):
    parts = [icon(icon_name, 40, y - 5, ACCENT_2, size=13)]
    parts.append(f'<text x="64" y="{y}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13.5" fill="{MUTED}">{esc(label)}</text>')
    parts.append(f'<text x="{width - 26}" y="{y}" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" font-size="15" font-weight="700" fill="{TEXT}">{esc(value)}</text>')
    return "\n  ".join(parts)


# ---------------------------------------------------------------------------
# Generadores de cada card
# ---------------------------------------------------------------------------

def generate_stats_svg(user):
    contrib = user["contributionsCollection"]
    repos = user["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)

    rows = [
        ("repo", "Repositorios públicos", user["repositories"]["totalCount"]),
        ("star", "Estrellas totales", total_stars),
        ("commit", "Commits (último año)", contrib["totalCommitContributions"]),
        ("branch", "Pull requests", contrib["totalPullRequestContributions"]),
        ("issue", "Issues", contrib["totalIssueContributions"]),
        ("users", "Seguidores", user["followers"]["totalCount"]),
    ]

    display_name = DISPLAY_NAME_OVERRIDE or user["name"] or user["login"]
    row_h = 40
    height = 96 + row_h * len(rows) + 14

    header, start_y = card_open(CARD_WIDTH, height, f"Estadísticas de {display_name}",
                                 f"@{user['login']}", avatar_url=user["avatarUrl"])
    body = [header]
    y = start_y + 14
    for icon_name, label, value in rows:
        body.append(stat_row(y, icon_name, label, value, CARD_WIDTH))
        y += row_h
    body.append(card_close())
    return "\n  ".join(body)


def generate_streak_svg(current, longest, total):
    height = 178
    header, start_y = card_open(CARD_WIDTH, height, "Racha de contribuciones")

    cols = [("flame", "Racha actual", current), ("calendar", "Racha más larga", longest),
            ("star", "Contribuciones (año)", total)]
    col_w = CARD_WIDTH / 3
    body = [header]
    for i, (icon_name, label, value) in enumerate(cols):
        cx = col_w * i + col_w / 2
        body.append(icon(icon_name, cx, start_y + 16, ACCENT_2, size=11))
        body.append(f'<text x="{cx}" y="{start_y + 62}" text-anchor="middle" font-family="Segoe UI, Ubuntu, sans-serif" font-size="24" font-weight="700" fill="{TEXT}">{esc(value)}</text>')
        body.append(f'<text x="{cx}" y="{start_y + 82}" text-anchor="middle" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12" fill="{MUTED}">{esc(label)}</text>')
        if i > 0:
            body.append(f'<line x1="{col_w * i}" y1="{start_y}" x2="{col_w * i}" y2="{height - 24}" stroke="{TRACK}" stroke-width="1"/>')
    body.append(card_close())
    return "\n  ".join(body)


def generate_languages_svg(languages, total):
    row_h = 32
    height = 96 + row_h * len(languages)
    header, start_y = card_open(CARD_WIDTH, height, "Lenguajes principales")

    bar_x = 150
    bar_w = CARD_WIDTH - bar_x - 70
    body = [header]
    y = start_y + 10
    for name, info in languages:
        pct = round(100 * info["count"] / total) if total else 0
        fill_w = max(6, int(bar_w * info["count"] / total)) if total else 6
        body.append(f'<text x="26" y="{y + 5}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" fill="{MUTED}">{esc(name)}</text>')
        body.append(f'<rect x="{bar_x}" y="{y - 6}" width="{bar_w}" height="9" rx="4.5" fill="{TRACK}"/>')
        body.append(f'<rect x="{bar_x}" y="{y - 6}" width="{fill_w}" height="9" rx="4.5" fill="{info["color"]}"/>')
        body.append(f'<text x="{CARD_WIDTH - 26}" y="{y + 5}" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12.5" font-weight="700" fill="{TEXT}">{pct}%</text>')
        y += row_h
    body.append(card_close())
    return "\n  ".join(body)


def generate_projects_svg(projects):
    row_h = 92
    height = 88 + row_h * len(projects)
    header, start_y = card_open(CARD_WIDTH, height, "Proyectos destacados")

    body = [header]
    y = start_y - 6
    for repo in projects:
        lang = repo.get("primaryLanguage")
        lang_name = lang["name"] if lang else "—"
        lang_color = lang["color"] if lang else MUTED

        body.append(f'<rect x="26" y="{y}" width="{CARD_WIDTH - 52}" height="{row_h - 14}" rx="10" fill="{TRACK}" opacity="0.55"/>')
        body.append(f'<text x="42" y="{y + 26}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14.5" font-weight="700" fill="{TEXT}">{esc(repo["name"])}</text>')
        body.append(f'<text x="42" y="{y + 47}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12" fill="{MUTED}">{esc(truncate(repo["description"], 58))}</text>')
        body.append(f'<circle cx="42" cy="{y + 64}" r="4.5" fill="{lang_color}"/>')
        body.append(f'<text x="52" y="{y + 68}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="11.5" fill="{MUTED}">{esc(lang_name)}</text>')
        body.append(icon("star", CARD_WIDTH - 90, y + 64, ACCENT_2, size=10))
        body.append(f'<text x="{CARD_WIDTH - 78}" y="{y + 68}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="11.5" font-weight="700" fill="{TEXT}">{repo["stargazerCount"]}</text>')
        y += row_h
    body.append(card_close())
    return "\n  ".join(body)


def main():
    user = fetch_data()
    contrib = user["contributionsCollection"]
    current, longest, total = compute_streaks(contrib["contributionCalendar"]["weeks"])
    languages, lang_total = compute_languages(user["repositories"]["nodes"])
    projects = top_projects(user["repositories"]["nodes"], n=2)

    os.makedirs("assets", exist_ok=True)
    with open("assets/stats.svg", "w", encoding="utf-8") as f:
        f.write(generate_stats_svg(user))
    with open("assets/streak.svg", "w", encoding="utf-8") as f:
        f.write(generate_streak_svg(current, longest, total))
    with open("assets/languages.svg", "w", encoding="utf-8") as f:
        f.write(generate_languages_svg(languages, lang_total))
    with open("assets/projects.svg", "w", encoding="utf-8") as f:
        f.write(generate_projects_svg(projects))

    print("Assets generados correctamente en /assets")


if __name__ == "__main__":
    main()
