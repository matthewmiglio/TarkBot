"""Rank tarkbot.org blog posts by how many downloads they drive per day.

Pulls per-post totals from the tarkbot_blog_post_stats() Postgres function
(dashboard/sql/tarkbot_blog_post_stats.sql) and reads each post's publish date
from website/src/lib/posts.ts, so a post that has been up for two days is not
judged against one that has been up for two months.

The ranking number is downloads per day:
    visitors per day since publishing  x  conversion rate
where conversion is "clicked download after opening this post" over visitors,
pulled toward the blog-wide average so one visitor who downloaded does not make
a post look like a 100% converter. /generate-blog reads the --json output to
pick its next topic.

Needs scripts/.env (gitignored) with SUPABASE_URL and SUPABASE_SERVICE_KEY.

    python scripts/blog_performance.py              table, best first
    python scripts/blog_performance.py --json       the same, as JSON
    python scripts/blog_performance.py --self-check  asserts the scoring maths
"""

import json
import re
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_TS = ROOT / "website" / "src" / "lib" / "posts.ts"
ENV_FILE = Path(__file__).resolve().parent / ".env"

# How many visitors' worth of weight the blog-wide average gets. With 20, a post
# needs a few dozen visitors before its own rate outweighs the average.
# ponytail: a fixed prior. Tune it once there is enough traffic to see what fits.
PRIOR_VISITORS = 20


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def published_posts() -> dict[str, date]:
    """slug -> publish date, read straight out of posts.ts so there is one source of truth."""
    text = POSTS_TS.read_text(encoding="utf-8")
    pairs = re.findall(r'slug:\s*"([^"]+)".*?date:\s*"(\d{4}-\d{2}-\d{2})"', text, re.S)
    return {slug: date.fromisoformat(d) for slug, d in pairs}


def fetch_stats(env: dict[str, str]) -> list[dict]:
    url = env["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/tarkbot_blog_post_stats"
    key = env["SUPABASE_SERVICE_KEY"]
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def score(posts: dict[str, date], stats: list[dict], today: date) -> list[dict]:
    """One row per published post (zeros when it has no traffic yet), best first."""
    by_slug = {s["path"].removeprefix("/blog/"): s for s in stats}
    total_visitors = sum(s["visitors"] for s in stats)
    total_clicked = sum(s["clicked_download"] for s in stats)
    blog_rate = total_clicked / total_visitors if total_visitors else 0.0

    rows = []
    for slug in sorted(set(posts) | set(by_slug)):
        s = by_slug.get(slug, {})
        published = posts.get(slug)
        if published is None and s.get("first_view"):
            # On the site but gone from posts.ts (renamed or deleted): age it by its first view.
            published = datetime.fromisoformat(s["first_view"].replace("Z", "+00:00")).date()
        age_days = max(1, (today - published).days) if published else 1
        visitors = s.get("visitors", 0)
        clicked = s.get("clicked_download", 0)
        conversion = (clicked + blog_rate * PRIOR_VISITORS) / (visitors + PRIOR_VISITORS)
        rows.append({
            "slug": slug,
            "published": published.isoformat() if published else None,
            "age_days": age_days,
            "in_posts_ts": slug in posts,
            "views": s.get("views", 0),
            "visitors": visitors,
            "reached_download": s.get("reached_download", 0),
            "clicked_download": clicked,
            "views_per_day": round(s.get("views", 0) / age_days, 2),
            "conversion": round(conversion, 4),
            "downloads_per_day": round(visitors / age_days * conversion, 4),
        })
    rows.sort(key=lambda r: (-r["downloads_per_day"], -r["views_per_day"], r["slug"]))
    return rows


def self_check() -> None:
    today = date(2026, 11, 1)
    posts = {"old": date(2026, 10, 2), "new": date(2026, 10, 31), "quiet": date(2026, 10, 30)}
    stats = [
        # 300 visitors over 30 days, 15 downloads.
        {"path": "/blog/old", "first_view": "2026-10-02T00:00:00Z", "views": 400, "visitors": 300,
         "reached_download": 40, "clicked_download": 15},
        # 30 visitors in its first day, 3 downloads: far more per day despite the smaller totals.
        {"path": "/blog/new", "first_view": "2026-10-31T00:00:00Z", "views": 35, "visitors": 30,
         "reached_download": 6, "clicked_download": 3},
        # Deleted from posts.ts but still has traffic: aged by first view.
        {"path": "/blog/gone", "first_view": "2026-10-22T00:00:00Z", "views": 10, "visitors": 10,
         "reached_download": 1, "clicked_download": 0},
    ]
    rows = {r["slug"]: r for r in score(posts, stats, today)}
    ranked = [r["slug"] for r in score(posts, stats, today)]

    assert ranked[0] == "new", f"newer post with the higher daily rate should lead, got {ranked}"
    assert rows["old"]["age_days"] == 30 and rows["new"]["age_days"] == 1
    assert rows["quiet"]["visitors"] == 0 and rows["quiet"]["downloads_per_day"] == 0, "no traffic scores zero"
    assert rows["gone"]["age_days"] == 10 and not rows["gone"]["in_posts_ts"]
    # Smoothing: 1 download from 1 visitor must not read as a 100% converter.
    one = score({"x": date(2026, 10, 1)}, [{"path": "/blog/x", "first_view": None, "views": 1,
                 "visitors": 1, "reached_download": 1, "clicked_download": 1}], today)[0]
    assert one["conversion"] < 0.1, one
    # The publish date parser finds every post in the real posts.ts.
    assert len(published_posts()) >= 1
    print("blog_performance self-check passed")


def main() -> None:
    if "--self-check" in sys.argv:
        self_check()
        return
    if not ENV_FILE.exists():
        sys.exit(f"missing {ENV_FILE}: add SUPABASE_URL and SUPABASE_SERVICE_KEY")
    rows = score(published_posts(), fetch_stats(load_env(ENV_FILE)), datetime.now(timezone.utc).date())

    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
        return
    print(f"{'post':40} {'age':>4} {'views':>6} {'views/d':>8} {'visitors':>8} {'dl':>4} {'conv':>6} {'dl/day':>7}")
    for r in rows:
        print(f"{r['slug'][:40]:40} {r['age_days']:>4} {r['views']:>6} {r['views_per_day']:>8} "
              f"{r['visitors']:>8} {r['clicked_download']:>4} {r['conversion']:>6.1%} {r['downloads_per_day']:>7}")


if __name__ == "__main__":
    main()
