"""Download ~1000 user tweets via Nitter date windows into TwExportly-style CSV."""

from __future__ import annotations

import argparse
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dateutil import parser as date_parser
from ntscraper import Nitter

TARGET = 1000
INSTANCE = "https://nitter.kareem.one"
WINDOW_DAYS = 14  # Elon posts a lot; shorter windows paginate better
PAUSE_SEC = 3
APP_DIR = Path(__file__).resolve().parent


def parse_created_at(raw: str) -> str:
    cleaned = re.sub(r"[·•]", " ", raw or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    try:
        return date_parser.parse(cleaned).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OverflowError):
        return cleaned


def row_from_tweet(t: dict) -> dict:
    stats = t.get("stats") or {}
    media_type = ""
    media_urls = ""
    if t.get("videos"):
        media_type = "video"
        media_urls = "|".join(t["videos"])
    elif t.get("gifs"):
        media_type = "gif"
        media_urls = "|".join(t["gifs"])
    elif t.get("pictures"):
        media_type = "photo"
        media_urls = "|".join(t["pictures"])

    tweet_type = "Tweet"
    if t.get("is-retweet"):
        tweet_type = "Retweet"
    elif t.get("quoted-post"):
        tweet_type = "Quote"
    elif t.get("replying-to"):
        tweet_type = "Reply"

    return {
        "tweet_id": f"'{t.get('id', '')}",
        "text": t.get("text", ""),
        "language": "",
        "type": tweet_type,
        "bookmark_count": "",
        "favorite_count": stats.get("likes", 0) or 0,
        "retweet_count": stats.get("retweets", 0) or 0,
        "reply_count": stats.get("comments", 0) or 0,
        "view_count": "",
        "created_at": parse_created_at(t.get("date", "")),
        "client": "",
        "hashtags": ",".join(re.findall(r"#(\w+)", t.get("text") or "")),
        "urls": t.get("external-link", "") or "",
        "media_type": media_type,
        "media_urls": media_urls,
    }


def fetch_window(scraper: Nitter, screen_name: str, since: str, until: str) -> list[dict]:
    for attempt in range(1, 4):
        try:
            payload = scraper.get_tweets(
                screen_name,
                mode="user",
                number=400,
                since=since,
                until=until,
                instance=INSTANCE,
                max_retries=5,
            )
            return payload.get("tweets") or []
        except Exception as exc:
            print(f"  attempt {attempt} failed ({since}..{until}): {exc}")
            time.sleep(PAUSE_SEC * attempt)
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("screen_name", help="X/Twitter handle without @")
    parser.add_argument("--target", type=int, default=TARGET)
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    args = parser.parse_args()

    screen_name = args.screen_name.lstrip("@")
    out = APP_DIR / f"TwExportly_{screen_name}_tweets_{datetime.now():%Y_%m_%d}.csv"

    scraper = Nitter(log_level=1, skip_instance_check=True)
    seen: set[str] = set()
    rows: list[dict] = []

    if out.exists():
        old = pd.read_csv(out)
        for _, r in old.iterrows():
            tid = str(r.get("tweet_id", "")).lstrip("'")
            if tid and tid not in seen:
                seen.add(tid)
                rows.append(r.to_dict())
        print(f"Resumed {len(rows)} existing rows from {out.name}")

    end: date = datetime.now(timezone.utc).date()
    oldest = end - timedelta(days=365 * 8)

    print(f"Fetching up to {args.target} unique @{screen_name} tweets via {INSTANCE}...")
    while len(rows) < args.target and end > oldest:
        start = end - timedelta(days=args.window_days)
        since = start.isoformat()
        until = end.isoformat()
        print(f"Window {since} -> {until} (have {len(rows)})")
        tweets = fetch_window(scraper, screen_name, since, until)
        added = 0
        for t in tweets:
            tid = str(t.get("id", ""))
            if not tid or tid in seen:
                continue
            seen.add(tid)
            rows.append(row_from_tweet(t))
            added += 1
            if len(rows) >= args.target:
                break
        print(f"  +{added} new ({len(tweets)} returned)")
        end = start
        pd.DataFrame(rows).to_csv(out, index=False)
        time.sleep(PAUSE_SEC)

    df = pd.DataFrame(rows[: args.target])
    df.to_csv(out, index=False)
    print(f"Done. Wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
