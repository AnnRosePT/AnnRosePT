"""
Generates the purple GitHub stats cards used in README.md:
  assets/stats/overview.svg   - contribution / repo summary
  assets/stats/languages.svg  - most-used languages (by bytes, own non-fork repos)

Runs inside GitHub Actions (.github/workflows/stats.yml) with the built-in
GITHUB_TOKEN, so no paid service or third-party stats server is needed.
Locally, without a token, it renders from scripts/seed_stats.json.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "AnnRosePT")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stats"

# Brand palette
BG = "#101014"
BORDER = "#2A1F44"
TITLE = "#C69AF5"
TEXT = "#D8C9ED"
WHITE = "#FFFFFF"
MUTED = "#9A8BB5"
LANG_COLORS = ["#9338C8", "#C69AF5", "#6A3FC4", "#E2C8FF", "#4B2A99", "#B07CE8"]
FONT = "'Segoe UI', Inter, Ubuntu, 'Helvetica Neue', Arial, sans-serif"


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_live():
    base = gql(
        """query($login:String!){ user(login:$login){
              createdAt
              contributionsCollection{ contributionYears totalCommitContributions
                                       totalPullRequestContributions totalIssueContributions }
              repositories(ownerAffiliations:OWNER, isFork:false, first:100, privacy:PUBLIC){
                totalCount
                nodes{ stargazerCount languages(first:10, orderBy:{field:SIZE,direction:DESC}){
                         edges{ size node{ name } } } } } } }""",
        {"login": USER},
    )["user"]
    total = 0
    for year in base["contributionsCollection"]["contributionYears"]:
        y = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from,to:$to){
                   contributionCalendar{ totalContributions } } } }""",
            {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )
        total += y["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    langs = {}
    stars = 0
    for repo in base["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = base["contributionsCollection"]
    return {
        "total_contributions": total,
        "commits_this_year": cc["totalCommitContributions"],
        "pull_requests": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "public_repos": base["repositories"]["totalCount"],
        "stars": stars,
        "languages": langs,
    }


def card(width, height, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="glow" x1="1" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#9338C8" stop-opacity="0.28"/>
      <stop offset="0.55" stop-color="#382078" stop-opacity="0.06"/>
      <stop offset="1" stop-color="#101014" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="16" fill="{BG}" stroke="{BORDER}"/>
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="16" fill="url(#glow)"/>
  <text x="28" y="42" fill="{TITLE}" font-family="{FONT}" font-size="17" font-weight="600" letter-spacing="0.3">{escape(title)}</text>
{body}
</svg>
"""


def overview_svg(s):
    rows = [
        ("Total contributions", s["total_contributions"]),
        ("Commits this year", s["commits_this_year"]),
        ("Pull requests", s["pull_requests"]),
        ("Public repositories", s["public_repos"]),
        ("Stars earned", s["stars"]),
    ]
    body = []
    for i, (label, value) in enumerate(rows):
        y = 82 + i * 28
        body.append(
            f'  <circle cx="34" cy="{y-5}" r="3.5" fill="#9338C8"/>\n'
            f'  <text x="48" y="{y}" fill="{TEXT}" font-family="{FONT}" font-size="14">{label}</text>\n'
            f'  <text x="392" y="{y}" fill="{WHITE}" font-family="{FONT}" font-size="14" font-weight="600" text-anchor="end">{value:,}</text>'
        )
    return card(420, 220, "GitHub Activity", "\n".join(body))


def languages_svg(langs):
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(v for _, v in top) or 1
    body = ['  <clipPath id="bar"><rect x="28" y="62" width="364" height="10" rx="5"/></clipPath>', '  <g clip-path="url(#bar)">']
    x = 28.0
    for i, (name, v) in enumerate(top):
        w = 364 * v / total
        body.append(f'    <rect x="{x:.2f}" y="62" width="{w + 0.5:.2f}" height="10" fill="{LANG_COLORS[i]}"/>')
        x += w
    body.append("  </g>")
    for i, (name, v) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = 34 + col * 186, 108 + row * 34
        pct = 100 * v / total
        body.append(
            f'  <circle cx="{cx}" cy="{cy-5}" r="5" fill="{LANG_COLORS[i]}"/>\n'
            f'  <text x="{cx+14}" y="{cy}" fill="{TEXT}" font-family="{FONT}" font-size="14">{escape(name)}'
            f' <tspan fill="{MUTED}">{pct:.1f}%</tspan></text>'
        )
    return card(420, 220, "Most-Used Languages", "\n".join(body))


def main():
    if TOKEN:
        stats = fetch_live()
    else:
        stats = json.loads((ROOT / "scripts" / "seed_stats.json").read_text())
        print("No GITHUB_TOKEN - rendering from seed_stats.json", file=sys.stderr)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "overview.svg").write_text(overview_svg(stats), encoding="utf-8")
    (OUT / "languages.svg").write_text(languages_svg(stats["languages"]), encoding="utf-8")
    print(f"Wrote stats cards at {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")


if __name__ == "__main__":
    main()
