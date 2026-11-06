"""Look at the WHOOP reviews before defining themes: volume and stars by era,
the words that separate negative from positive reviews, and a random sample to read.
Exploration only; the themes themselves are defined later and checked by hand."""
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "reviews" / "whoop_google_play.parquet"
LAUNCH_5 = pd.Timestamp("2025-05-08")      # WHOOP 5.0 / MG launch
STOP = set("""a an the and or but if so to of in on at for with from by as is are was were be been being it its
this that these those i me my we our you your he she they them their his her im ive id dont doesnt didnt cant wont
not no just very really also get got have has had do does did will would can could should one all any some more
most much many than then there here what when which who how why up out about into over after again only even
still now too app whoop""".split())


def tokens(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower().replace("'", "")) if w not in STOP and len(w) > 1]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


def distinctive(neg: pd.Series, pos: pd.Series, top: int = 30, min_count: int = 8) -> pd.DataFrame:
    """Terms most over-represented in negative reviews, by smoothed log-odds (counted once per review)."""
    cn = Counter(t for s in neg for t in set(tokens(s)))
    cp = Counter(t for s in pos for t in set(tokens(s)))
    rows = []
    for t, k in cn.items():
        if k < min_count:
            continue
        p_neg = (k + 1) / (len(neg) + 2)
        p_pos = (cp.get(t, 0) + 1) / (len(pos) + 2)
        rows.append((t, k, cp.get(t, 0), np.log(p_neg / p_pos)))
    df = pd.DataFrame(rows, columns=["term", "neg_reviews", "pos_reviews", "log_odds"])
    return df.sort_values("log_odds", ascending=False).head(top)


def main() -> int:
    df = pd.read_parquet(PATH)
    df["era"] = np.where(df["reviewed_at"] >= LAUNCH_5, "since 5.0 launch", "before 5.0 launch")
    df["sentiment"] = pd.cut(df["score"], [0, 2, 3, 5], labels=["negative (1-2)", "neutral (3)", "positive (4-5)"])

    print("Reviews and star mix by era")
    print(pd.crosstab(df["era"], df["sentiment"], margins=True).to_string())
    print((pd.crosstab(df["era"], df["sentiment"], normalize="index") * 100).round(1).to_string())

    recent = df[df["era"] == "since 5.0 launch"]
    neg = recent.loc[recent["score"] <= 2, "content"].fillna("")
    pos = recent.loc[recent["score"] >= 4, "content"].fillna("")
    pd.set_option("display.width", 160)
    print(f"\nWords and pairs most typical of negative reviews since the 5.0 launch ({len(neg)} neg vs {len(pos)} pos)")
    print(distinctive(neg, pos).to_string(index=False, float_format="%.2f"))
    print(f"\n... and most typical of positive reviews")
    print(distinctive(pos, neg, top=20).to_string(index=False, float_format="%.2f"))

    rng = np.random.default_rng(11)
    for label, sub, n in [("NEGATIVE", recent[recent["score"] <= 2], 25), ("POSITIVE", recent[recent["score"] >= 4], 10)]:
        print(f"\n--- {n} random {label} reviews since the 5.0 launch (first 60 words) ---")
        for _, r in sub.iloc[rng.choice(len(sub), min(n, len(sub)), replace=False)].iterrows():
            words = r["content"].split()
            print(f"[{r['score']}*] " + " ".join(words[:60]) + (" ..." if len(words) > 60 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
