"""List every review where the keyword rule and the hand label disagree, with the words that fired the rule.

False positive: the rule tagged the theme but the hand label did not.
False negative: the hand label has the theme but the rule missed it.
Usage: uv run python analysis/review_disagreements.py [theme ...]
"""
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    con = duckdb.connect(str(ROOT / "data" / "whoop.duckdb"), read_only=True)
    patterns = dict(con.sql("select theme, pattern from review_themes").fetchall())
    df = con.sql("""
        select l.review_id, l.theme, l.is_mentioned = 1 as by_hand,
               t.review_id is not null as by_rule, r.content
        from review_hand_labels l
        join fct_reviews r using (review_id)
        left join fct_review_themes t using (review_id, theme)
        where (l.is_mentioned = 1) <> (t.review_id is not null)
        order by l.theme, by_rule desc, l.review_id
    """).df()
    wanted = sys.argv[1:] or list(patterns)
    for theme in wanted:
        sub = df[df["theme"] == theme]
        print(f"\n=== {theme}: {int(sub['by_rule'].sum())} false positives, {int((~sub['by_rule']).sum())} false negatives")
        for _, r in sub.iterrows():
            words = r["content"].split()
            text = " ".join(words[:45]) + (" ..." if len(words) > 45 else "")
            if r["by_rule"]:
                hits = sorted({m.group(0) for m in re.finditer(patterns[theme], r["content"].lower())})
                print(f"  FP  fired on {hits}: {text}")
            else:
                print(f"  FN  {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
