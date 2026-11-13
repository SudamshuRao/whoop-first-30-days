"""Shared loader for lapse analysis: one row per lapse with rhythm and the past-only activity group.
Used by the site pages so every number comes from the same definitions."""
import duckdb
import numpy as np
import pandas as pd

BINS = [-0.01, 0.5, 0.9, 1.1, np.inf]
LABELS = ["under half of usual", "50-90% of usual", "about usual", "above usual"]
REPEAT = "back after 12+ weeks away"


def load_lapses(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.sql("""
        select l.*, m.n_workouts, m.tenure_days,
               case when m.median_gap_days < 1.5 then 'near-daily'
                    when m.median_gap_days < 3.5 then 'every 2-3 days'
                    else 'weekly or less' end as rhythm
        from fct_lapses l
        join dim_members m using (user_id)
    """).df()
    df["ended"] = ~df["is_censored"]

    # Past-only baseline: workouts in the 12 weeks before the last 28 days, scaled to 28 days
    past_usual = df["workouts_baseline_84d"] / 3
    group = pd.cut(df["workouts_28d_before"] / past_usual.where(past_usual > 0), BINS, labels=LABELS)
    group = group.cat.add_categories([REPEAT])
    group[df["has_full_baseline"] & (df["workouts_baseline_84d"] == 0)] = REPEAT
    df["activity_group"] = group.where(df["has_full_baseline"])

    # Whole-history baseline (look-ahead), kept only to show why it was rejected
    whole_usual = df["n_workouts"] / np.maximum(df["tenure_days"] / 28.0, 1)
    df["activity_group_lookahead"] = pd.cut(df["workouts_28d_before"] / whole_usual, BINS, labels=LABELS)
    return df
