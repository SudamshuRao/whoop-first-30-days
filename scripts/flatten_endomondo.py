"""Flatten Endomondo metadata to one row per workout, saved as Parquet.

Each line of endomondoMeta.json.gz is a Python dict literal (single quotes, None),
so it is parsed with ast.literal_eval, not json.loads. Per-sample lists such as
timestamps are reduced to start time, end time and sample count.
"""
import ast
import gzip
import sys
import time
from collections import Counter
from itertools import islice
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

SRC = Path("data/raw/endomondo/endomondoMeta.json.gz")
DEST = Path("data/clean/endomondo_workouts.parquet")
BATCH = 2_000            # lines read per batch, keeps memory flat
MAX_ERROR_RATE = 0.001   # fail if more than 0.1% of lines can't be parsed


def parse_line(line: bytes):
    """Return (row, key_signature) for one workout, or (None, error_name)."""
    try:
        rec = ast.literal_eval(line.decode("utf-8"))
    except (ValueError, SyntaxError, UnicodeDecodeError) as e:
        return None, type(e).__name__
    row = {k: v for k, v in rec.items() if not isinstance(v, (list, dict))}
    ts = rec.get("timestamp") or []
    row["start_raw"] = ts[0] if ts else None
    row["end_raw"] = ts[-1] if ts else None
    row["n_samples"] = len(ts)
    return row, tuple(sorted(rec.keys()))


def to_utc(s: pd.Series) -> pd.Series:
    """Timestamps may be ISO strings or Unix seconds; return UTC datetimes."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s, unit="s", utc=True)
    return pd.to_datetime(s, utc=True, errors="coerce", format="ISO8601")


def main() -> int:
    if not SRC.exists():
        print(f"{SRC} not found. Run scripts/download_endomondo.py first.")
        return 1
    DEST.parent.mkdir(parents=True, exist_ok=True)

    rows, key_sets, errors = [], Counter(), Counter()
    n_lines, t0 = 0, time.time()
    with gzip.open(SRC, "rb") as f, Pool() as pool:
        while batch := list(islice(f, BATCH)):
            for row, info in pool.map(parse_line, batch, chunksize=50):
                if row is None:
                    errors[info] += 1
                else:
                    rows.append(row)
                    key_sets[info] += 1
            n_lines += len(batch)
            if n_lines % 20_000 < BATCH:
                print(f"  {n_lines:>9,} lines parsed  ({time.time() - t0:,.0f}s)")

    df = pd.DataFrame(rows).rename(columns={"userId": "user_id", "id": "workout_id"})
    df["start_ts"] = to_utc(df.pop("start_raw"))
    df["end_ts"] = to_utc(df.pop("end_raw"))
    for col in df.columns[df.dtypes == object]:
        df[col] = df[col].astype("string")   # Parquet needs one type per column
    df.to_parquet(DEST, index=False)

    n_err = sum(errors.values())
    print(f"\nlines read        {n_lines:,}  ({time.time() - t0:,.0f}s)")
    print(f"workouts kept     {len(df):,}")
    print(f"parse errors      {n_err:,}  {dict(errors)}")
    print(f"users             {df['user_id'].nunique():,}")
    print(f"duplicate ids     {df['workout_id'].duplicated().sum():,}")
    print(f"missing start     {df['start_ts'].isna().sum():,}")
    print(f"date range        {df['start_ts'].min()}  to  {df['start_ts'].max()}")
    print(f"columns           {list(df.columns)}")
    print(f"key layouts       {len(key_sets)} distinct; most common has {key_sets.most_common(1)[0][1]:,} rows")
    print(f"top sports        {df['sport'].value_counts().head(8).to_dict()}")
    print(f"saved             {DEST}  ({DEST.stat().st_size / 1e6:,.1f} MB)")

    return 0 if n_err <= MAX_ERROR_RATE * n_lines else 1


if __name__ == "__main__":
    sys.exit(main())
