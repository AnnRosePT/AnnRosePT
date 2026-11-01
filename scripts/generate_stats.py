"""
Minecraft-style "Statistics" cards for the profile README (purple / amethyst theme):
  assets/stats/overview.svg   - contributions, commits, PRs, repos, current + longest streak
  assets/stats/languages.svg  - most-used languages (bytes across own non-fork repos)

Runs in GitHub Actions (.github/workflows/stats.yml) with the built-in GITHUB_TOKEN.
Without a token it renders scripts/seed_stats.json. The pixel font is embedded so it
renders the same everywhere.
"""
import base64
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "AnnRosePT")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stats"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

PANEL, DARK, LIGHT, EDGE = "#211538", "#120a22", "#3f2a6e", "#0b0716"
WHITE, LAV, MUTED, GOLD = "#FFFFFF", "#D8C9ED", "#9A86C4", "#FFD84A"
LANG_COLORS = ["#9338C8", "#C69AF5", "#6A3FC4", "#E9DCFF", "#4B2A99", "#B07CE8"]


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


def streaks(days):
    """days: {date: count}. Current streak may end today or yesterday."""
    if not days:
        return 0, 0
    longest = run = 0
    d, end = min(days), max(days)
    while d <= end:
        run = run + 1 if days.get(d, 0) > 0 else 0
        longest = max(longest, run)
        d += timedelta(days=1)
    cur, d = 0, end
    if days.get(d, 0) == 0:
        d -= timedelta(days=1)
    while days.get(d, 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    return cur, longest


def fetch_live():
    base = gql(
        """query($login:String!){ user(login:$login){
              contributionsCollection{ contributionYears totalCommitContributions totalPullRequestContributions }
              repositories(ownerAffiliations:OWNER, isFork:false, first:100, privacy:PUBLIC){
                totalCount
                nodes{ languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } } } } }""",
        {"login": USER},
    )["user"]
    total, days = 0, {}
    for year in base["contributionsCollection"]["contributionYears"]:
        cal = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from,to:$to){ contributionCalendar{ totalContributions
                   weeks{ contributionDays{ date contributionCount } } } } } }""",
            {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]["contributionCalendar"]
        total += cal["totalContributions"]
        for w in cal["weeks"]:
            for dd in w["contributionDays"]:
                d = date.fromisoformat(dd["date"])
                if d <= date.today():
                    days[d] = dd["contributionCount"]
    cur, longest = streaks(days)
    langs = {}
    for repo in base["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = base["contributionsCollection"]
    return {
        "total_contributions": total,
        "commits_this_year": cc["totalCommitContributions"],
        "pull_requests": cc["totalPullRequestContributions"],
        "public_repos": base["repositories"]["totalCount"],
        "current_streak": cur,
        "longest_streak": longest,
        "languages": langs,
    }


def font_css():
    out = []
    for weight, f in ((400, "pixelify-sans-latin-400-normal.woff2"), (700, "pixelify-sans-latin-700-normal.woff2")):
        p = FONT_DIR / f
        if p.exists():
            b = base64.b64encode(p.read_bytes()).decode()
            out.append(f"@font-face{{font-family:PX;font-weight:{weight};src:url(data:font/woff2;base64,{b}) format('woff2')}}")
    return "".join(out)


FONT = "PX, 'Courier New', monospace"


def card(w, h, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}" shape-rendering="crispEdges">
  <style>{font_css()} text{{font-family:{FONT}}}</style>
  <rect width="{w}" height="{h}" fill="{EDGE}"/>
  <rect x="4" y="4" width="{w-8}" height="{h-8}" fill="{PANEL}"/>
  <rect x="4" y="4" width="{w-8}" height="5" fill="{LIGHT}"/><rect x="4" y="4" width="5" height="{h-8}" fill="{LIGHT}"/>
  <rect x="4" y="{h-9}" width="{w-8}" height="5" fill="{DARK}"/><rect x="{w-9}" y="4" width="5" height="{h-8}" fill="{DARK}"/>
  <text x="26" y="44" fill="#2a1748" font-size="22" font-weight="700">{escape(title)}</text>
  <text x="24" y="42" fill="{WHITE}" font-size="22" font-weight="700">{escape(title)}</text>
{body}
</svg>
"""


def overview_svg(s):
    rows = [
        ("Total contributions", s["total_contributions"]),
        ("Commits this year", s["commits_this_year"]),
        ("Pull requests", s["pull_requests"]),
        ("Public repositories", s["public_repos"]),
        ("Current streak", f'{s.get("current_streak", 0)} days'),
        ("Longest streak", f'{s.get("longest_streak", 0)} days'),
    ]
    body = []
    for i, (label, value) in enumerate(rows):
        y = 78 + i * 25
        v = f"{value:,}" if isinstance(value, int) else value
        color = GOLD if "streak" in label else WHITE
        body.append(
            f'  <rect x="26" y="{y-11}" width="8" height="8" fill="#9a6ad6"/>\n'
            f'  <text x="44" y="{y}" fill="{LAV}" font-size="16">{label}</text>\n'
            f'  <text x="394" y="{y}" fill="{color}" font-size="16" font-weight="700" text-anchor="end">{v}</text>'
        )
    return card(420, 232, "Statistics", "\n".join(body))


def languages_svg(langs):
    top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(v for _, v in top) or 1
    # XP-bar style: segmented, blocky
    body = ['  <rect x="24" y="62" width="372" height="18" fill="#0b0716"/>']
    x = 27.0
    for i, (name, v) in enumerate(top):
        w = 366 * v / total
        body.append(f'  <rect x="{x:.1f}" y="65" width="{max(w, 2):.1f}" height="12" fill="{LANG_COLORS[i]}"/>')
        x += w
    for i in range(1, 18):
        body.append(f'  <rect x="{24 + i * 372 / 18:.1f}" y="65" width="2" height="12" fill="#0b0716" opacity=".55"/>')
    for i, (name, v) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = 26 + col * 186, 118 + row * 34
        body.append(
            f'  <rect x="{cx}" y="{cy-12}" width="12" height="12" fill="{LANG_COLORS[i]}"/>\n'
            f'  <text x="{cx+20}" y="{cy}" fill="{LAV}" font-size="16">{escape(name)} <tspan fill="{MUTED}">{100*v/total:.1f}%</tspan></text>'
        )
    return card(420, 232, "Most-Used Languages", "\n".join(body))


def main():
    if TOKEN:
        stats = fetch_live()
    else:
        stats = json.loads((ROOT / "scripts" / "seed_stats.json").read_text())
        print("No GITHUB_TOKEN - rendering from seed_stats.json", file=sys.stderr)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "overview.svg").write_text(overview_svg(stats), encoding="utf-8")
    (OUT / "languages.svg").write_text(languages_svg(stats["languages"]), encoding="utf-8")
    print("Wrote stats cards")


if __name__ == "__main__":
    main()
