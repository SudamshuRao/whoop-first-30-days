"""Download recent public Google Play reviews of the WHOOP app (com.whoop.android).

Keeps review text, star rating, date, app version and whether WHOOP replied.
Drops reviewer names and profile images: the analysis never needs to know who wrote what.
The raw file stays in data/ (git-ignored); only aggregated themes appear on the site.

Usage: uv run python scripts/download_reviews.py [--max 10000] [--force]
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews

APP_ID = "com.whoop.android"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "reviews" / "whoop_google_play.parquet"
BATCH = 200


def fetch(max_reviews: int) -> pd.DataFrame:
    rows, token, seen = [], None, set()
    while len(rows) < max_reviews:
        batch, token = reviews(APP_ID, lang="en", country="us", sort=Sort.NEWEST,
                               count=min(BATCH, max_reviews - len(rows)), continuation_token=token)
        new = [r for r in batch if r["reviewId"] not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["reviewId"])
            rows.append({
                "review_id": r["reviewId"],
                "reviewed_at": r["at"],
                "score": r["score"],
                "content": r["content"],
                "thumbs_up": r["thumbsUpCount"],
                "app_version": r["reviewCreatedVersion"],
                "has_reply": r["replyContent"] is not None,
            })
        print(f"  {len(rows):,} reviews, back to {rows[-1]['reviewed_at']:%Y-%m-%d}", flush=True)
        if token is None or getattr(token, "token", None) is None:
            break
        time.sleep(0.5)
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10_000)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if OUT.exists() and not args.force:
        print(f"skip      {OUT.name} (already downloaded; use --force to refresh)")
        df = pd.read_parquet(OUT)
    else:
        print(f"Downloading up to {args.max:,} newest English reviews of {APP_ID} ...")
        df = fetch(args.max)
        if df.empty:
            print("ERROR: no reviews returned")
            return 1
        OUT.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT, index=False)

    text = df["content"].fillna("").str.strip()
    print(f"\nReviews: {len(df):,}  ({df['reviewed_at'].min():%Y-%m-%d} to {df['reviewed_at'].max():%Y-%m-%d})")
    print(f"With text: {(text != '').mean():.1%}; median length {text.str.split().str.len().median():.0f} words")
    print(f"Answered by WHOOP: {df['has_reply'].mean():.1%}")
    print("\nStars   share")
    print((df["score"].value_counts(normalize=True).sort_index() * 100).round(1).to_string())
    print("\nReviews per quarter (most recent 8):")
    q = df["reviewed_at"].dt.to_period("Q").value_counts().sort_index().tail(8)
    print(q.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
