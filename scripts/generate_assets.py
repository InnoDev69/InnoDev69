#!/usr/bin/env python3
"""
Genera los assets SVG del README (stats, lenguajes y racha de contribuciones)
usando datos reales obtenidos de la API GraphQL de GitHub.

Variables de entorno requeridas:
  GH_TOKEN   -> token con permisos de lectura (read:user, repo si hay privados)
  GH_LOGIN   -> usuario de GitHub a consultar (por defecto: InnoDev69)
"""

import os
import sys
import datetime
import requests

GITHUB_LOGIN = os.environ.get("GH_LOGIN", "InnoDev69")
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
API_URL = "https://api.github.com/graphql"

# Paleta compartida con el README
COLOR_BG = "#0d1117"
COLOR_CARD = "#161b22"
COLOR_BORDER = "#a41c1c"
COLOR_TEXT = "#e6e6e6"
COLOR_MUTED = "#8b8f98"
COLOR_ACCENT = "#a41c1c"

QUERY = """
query ($login: String!) {
  user(login: $login) {
    name
    login
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
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
    response = requests.post(
        API_URL,
        json={"query": QUERY, "variables": {"login": GITHUB_LOGIN}},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

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

    longest = current = 0
    running = 0
    for _, count in days:
        if count > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

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
        totals[lang["name"]] = totals.get(lang["name"], {"count": 0, "color": lang["color"] or COLOR_ACCENT})
        totals[lang["name"]]["count"] += 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1]["count"], reverse=True)
    return ranked[:6]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def card_shell(width, height, body):
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg {{ fill: {COLOR_CARD}; }}
    .border {{ fill: none; stroke: {COLOR_BORDER}; stroke-width: 1.5; }}
    .title {{ font: 600 15px 'Segoe UI', Ubuntu, Sans-Serif; fill: {COLOR_TEXT}; }}
    .label {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {COLOR_MUTED}; }}
    .value {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {COLOR_TEXT}; }}
    .accent {{ fill: {COLOR_ACCENT}; }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10"/>
  <rect class="border" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10"/>
  {body}
</svg>"""


def generate_stats_svg(user):
    contrib = user["contributionsCollection"]
    repos = user["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)
    total_repos = user["repositories"]["totalCount"]
    followers = user["followers"]["totalCount"]
    commits = contrib["totalCommitContributions"]
    prs = contrib["totalPullRequestContributions"]
    issues = contrib["totalIssueContributions"]

    rows = [
        ("Repositorios públicos", total_repos),
        ("Estrellas totales", total_stars),
        ("Commits (último año)", commits),
        ("Pull requests", prs),
        ("Issues", issues),
        ("Seguidores", followers),
    ]

    body_parts = [
        f'<text x="25" y="35" class="title">Estadísticas de {esc(user["name"] or user["login"])}</text>',
        f'<rect x="25" y="45" width="40" height="3" class="accent"/>',
    ]
    y = 78
    for label, value in rows:
        body_parts.append(f'<text x="25" y="{y}" class="label">{esc(label)}</text>')
        body_parts.append(f'<text x="{450 - 25}" y="{y}" text-anchor="end" class="value">{esc(value)}</text>')
        y += 28

    height = y + 15
    return card_shell(450, height, "\n  ".join(body_parts))


def generate_streak_svg(current, longest, total):
    columns = [
        ("Racha actual", current),
        ("Racha más larga", longest),
        ("Contribuciones (año)", total),
    ]
    width = 450
    height = 140
    col_width = width / len(columns)

    body_parts = [f'<text x="25" y="30" class="title">Racha de contribuciones</text>',
                  f'<rect x="25" y="40" width="40" height="3" class="accent"/>']

    for i, (label, value) in enumerate(columns):
        cx = col_width * i + col_width / 2
        body_parts.append(f'<text x="{cx}" y="90" text-anchor="middle" class="value" style="font-size:22px">{esc(value)}</text>')
        body_parts.append(f'<text x="{cx}" y="112" text-anchor="middle" class="label">{esc(label)}</text>')
        if i > 0:
            body_parts.append(f'<line x1="{col_width * i}" y1="60" x2="{col_width * i}" y2="120" stroke="{COLOR_BORDER}" stroke-width="0.5" opacity="0.4"/>')

    return card_shell(width, height, "\n  ".join(body_parts))


def generate_languages_svg(languages):
    width = 450
    row_h = 26
    height = 55 + row_h * len(languages)
    max_count = max((v["count"] for _, v in languages), default=1)
    bar_max_width = 260

    body_parts = [
        '<text x="25" y="35" class="title">Lenguajes principales</text>',
        '<rect x="25" y="45" width="40" height="3" class="accent"/>',
    ]
    y = 75
    for name, info in languages:
        bar_w = max(6, int(bar_max_width * info["count"] / max_count))
        body_parts.append(f'<text x="25" y="{y}" class="label">{esc(name)}</text>')
        body_parts.append(f'<rect x="150" y="{y - 12}" width="{bar_max_width}" height="10" rx="5" fill="{COLOR_CARD}" stroke="{COLOR_MUTED}" stroke-width="0.5" opacity="0.4"/>')
        body_parts.append(f'<rect x="150" y="{y - 12}" width="{bar_w}" height="10" rx="5" fill="{info["color"]}"/>')
        body_parts.append(f'<text x="{150 + bar_max_width + 10}" y="{y}" class="value">{info["count"]}</text>')
        y += row_h

    return card_shell(width, height, "\n  ".join(body_parts))


def main():
    user = fetch_data()
    contrib = user["contributionsCollection"]
    current, longest, total = compute_streaks(contrib["contributionCalendar"]["weeks"])
    languages = compute_languages(user["repositories"]["nodes"])

    os.makedirs("assets", exist_ok=True)

    with open("assets/stats.svg", "w", encoding="utf-8") as f:
        f.write(generate_stats_svg(user))

    with open("assets/streak.svg", "w", encoding="utf-8") as f:
        f.write(generate_streak_svg(current, longest, total))

    with open("assets/languages.svg", "w", encoding="utf-8") as f:
        f.write(generate_languages_svg(languages))

    print("Assets generados correctamente en /assets")


if __name__ == "__main__":
    main()
