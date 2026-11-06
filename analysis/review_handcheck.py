"""Hand labels for the WHOOP review themes, in two sets.

  dev   The first 100 reviews. `adjudicate` shows only the reviews where your first labels and the
        current rules disagree, with both answers, and you decide under the written definitions.
        Used to improve the rules, so its accuracy figures are optimistic.
  test  `label` shows 60 NEW reviews, blind (no rule tags, no stars). Labelled once the rules are frozen.
        The only accuracy figures to report.

Every answer is saved as you go; quit any time and run again to resume.
Each run rewrites dbt/seeds/review_hand_labels.csv (split, review_id, theme, is_mentioned; no review text).

Usage:
  uv run python analysis/review_handcheck.py export       # write the seed from the labels so far
  uv run python analysis/review_handcheck.py adjudicate   # dev set: settle disagreements
  uv run python analysis/review_handcheck.py label        # test set: 60 fresh reviews, blind
"""
import json
import sys
import textwrap
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "reviews"
FIRST_PASS = RAW / "hand_labels_progress.json"     # original blind dev labels (8 themes)
ADJUDICATED = RAW / "hand_labels_adjudicated.json"
TEST = RAW / "hand_labels_test.json"
SEED = ROOT / "dbt" / "seeds" / "review_hand_labels.csv"
DEV_N, TEST_N, TEST_SEED = 100, 60, 7


def connect():
    return duckdb.connect(str(ROOT / "data" / "whoop.duckdb"), read_only=True)


def themes(con=None) -> pd.DataFrame:
    """Theme names and definitions straight from the seed file, so they match the rules exactly."""
    return pd.read_csv(ROOT / "dbt" / "seeds" / "review_themes.csv")[["theme", "label", "definition"]]


def load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save(path: Path, labels: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(labels, indent=1))


def legend(th: pd.DataFrame, full: bool) -> None:
    if full:
        print("\nLabel what the review talks about, good or bad. A review can have several themes or none.")
        for i, r in enumerate(th.itertuples(), 1):
            print(f"  {i}  {r.theme:<18} {r.definition}")
        print("Type numbers (e.g. '1 4'). Enter alone = none.  b = back   g = full guide   q = save and quit\n")
    else:
        print("  " + "   ".join(f"{i} {t}" for i, t in enumerate(th["theme"], 1)))


def parse(answer: str, th: pd.DataFrame):
    parts = answer.replace(",", " ").split()
    if not all(p.isdigit() and 1 <= int(p) <= len(th) for p in parts):
        return None
    return sorted({th["theme"].iloc[int(p) - 1] for p in parts})


def show(i: int, n: int, text: str) -> None:
    print(f"\n[{i + 1}/{n}]")
    print(textwrap.fill(text, width=100, initial_indent="  ", subsequent_indent="  "))


def export(con) -> None:
    th = list(themes(con)["theme"])
    first, adj, test = load(FIRST_PASS), load(ADJUDICATED), load(TEST)
    rows = []
    for rid, labs in first.items():
        final = adj.get(rid, labs)
        rows += [{"split": "dev", "review_id": rid, "theme": t, "is_mentioned": int(t in final)} for t in th]
    if len(test) >= TEST_N:
        rows += [{"split": "test", "review_id": rid, "theme": t, "is_mentioned": int(t in labs)}
                 for rid, labs in test.items() for t in th]
    pd.DataFrame(rows, columns=["split", "review_id", "theme", "is_mentioned"]).to_csv(SEED, index=False)
    n_test = len(test) if len(test) >= TEST_N else 0
    print(f"Wrote {SEED.relative_to(ROOT)}: {len(first)} dev reviews ({len(adj)} adjudicated), "
          f"{n_test} test reviews. Now run: make build")


def adjudicate(con) -> None:
    th = themes(con)
    first, adj = load(FIRST_PASS), load(ADJUDICATED)
    rules = con.sql("select review_id, theme from fct_review_themes").df().groupby("review_id")["theme"].apply(set)
    text = dict(con.sql("select review_id, content from fct_reviews").fetchall())
    todo = [rid for rid in sorted(first) if set(first[rid]) != rules.get(rid, set())]
    print(f"{len(todo)} of {len(first)} dev reviews have a disagreement between your first labels and the rules.")
    print("For each, type the final themes under the definitions below.  y = keep yours   r = take the rules'")
    legend(th, full=True)
    i = 0
    while i < len(todo):
        rid = todo[i]
        if rid in adj:
            i += 1
            continue
        show(i, len(todo), text[rid])
        num = {t: str(k) for k, t in enumerate(th["theme"], 1)}
        fmt = lambda s: " ".join(f"{num[t]}:{t}" for t in sorted(s)) or "none"
        print(f"  yours: {fmt(first[rid])}\n  rules: {fmt(rules.get(rid, set()))}")
        legend(th, full=False)
        a = input("final> ").strip().lower()
        if a == "q":
            break
        if a == "g":
            legend(th, full=True); continue
        if a == "b":
            prev = [j for j in range(i) if todo[j] in adj]
            if prev:
                i = prev[-1]; adj.pop(todo[i]); save(ADJUDICATED, adj)
            continue
        chosen = sorted(first[rid]) if a == "y" else sorted(rules.get(rid, set())) if a == "r" else parse(a, th)
        if chosen is None:
            print(f"  ? use y, r, or numbers 1-{len(th)}"); continue
        adj[rid] = chosen; save(ADJUDICATED, adj)
        print(f"  saved: {', '.join(chosen) or 'none'}")
        i += 1
    print(f"\nAdjudicated {sum(r in adj for r in todo)} of {len(todo)}.")
    export(con)


def label(con) -> None:
    th = themes(con)
    dev = set(load(FIRST_PASS))
    test = load(TEST)
    pool = con.sql("select review_id, content from fct_reviews where is_since_whoop_5 order by review_id").df()
    pool = pool[~pool["review_id"].isin(dev)]
    sample = pool.sample(n=TEST_N, random_state=TEST_SEED).reset_index(drop=True)
    legend(th, full=True)
    print("Take your time: about 20-30 seconds a review. Check the numbers before pressing Enter.")
    i = 0
    while i < len(sample):
        rid, text = sample.loc[i, "review_id"], sample.loc[i, "content"]
        if rid in test:
            i += 1
            continue
        show(i, len(sample), text)
        legend(th, full=False)
        a = input("themes> ").strip().lower()
        if a == "q":
            break
        if a == "g":
            legend(th, full=True); continue
        if a == "b":
            prev = [j for j in range(i) if sample.loc[j, "review_id"] in test]
            if prev:
                i = prev[-1]; test.pop(sample.loc[i, "review_id"]); save(TEST, test)
            continue
        chosen = parse(a, th)
        if chosen is None:
            print(f"  ? use numbers 1-{len(th)}"); continue
        test[rid] = chosen; save(TEST, test)
        print(f"  saved: {', '.join(chosen) or 'none'}")
        i += 1
    print(f"\nLabelled {len(test)} of {TEST_N} test reviews.")
    export(con)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in {"export", "adjudicate", "label"}:
        print(__doc__); return 1
    con = connect() if mode != "export" else None
    {"export": export, "adjudicate": adjudicate, "label": label}[mode](con)
    return 0


if __name__ == "__main__":
    sys.exit(main())
