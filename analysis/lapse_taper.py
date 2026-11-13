"""Phase 3: does slowing down relative to your own usual level go with longer lapses?
Two baselines for "usual":
  - whole history: the member's average over all time (includes the future, so look-ahead)
  - past only: the 12 weeks before the last 28 days (what a live trigger could actually compute)"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from survival import kaplan_meier, median_duration, returned_by

con = duckdb.connect("data/whoop.duckdb", read_only=True)
con.sql("set TimeZone = 'UTC'")

lapses = con.sql("""
    select l.lapse_days, l.is_censored, l.workouts_28d_before, l.workouts_baseline_84d,
           l.has_full_baseline,
           m.n_workouts / greatest(m.tenure_days / 28.0, 1)  as usual_whole_history,
           case when m.median_gap_days < 1.5 then 'near-daily'
                when m.median_gap_days < 3.5 then 'every 2-3 days'
                else 'weekly or less' end                     as rhythm
    from fct_lapses l
    join dim_members m using (user_id)
""").df()

BINS = [-0.01, 0.5, 0.9, 1.1, np.inf]
LABELS = ["under half of usual", "50-90% of usual", "about usual", "above usual"]

lapses["taper_whole"] = pd.cut(lapses["workouts_28d_before"] / lapses["usual_whole_history"], BINS, labels=LABELS)
past_usual = lapses["workouts_baseline_84d"] / 3
lapses["taper_past"] = pd.cut(lapses["workouts_28d_before"] / past_usual.where(past_usual > 0), BINS, labels=LABELS)
lapses["taper_past"] = lapses["taper_past"].cat.add_categories("no workouts in baseline")
lapses.loc[lapses["has_full_baseline"] & (lapses["workouts_baseline_84d"] == 0), "taper_past"] = "no workouts in baseline"


def row(df, label):
    curve = kaplan_meier(df["lapse_days"], ~df["is_censored"])
    share, lo, hi = returned_by(curve, 28)
    return {"group": label, "lapses": len(df), "median_days": median_duration(curve),
            "back_by_28d_%": round(100 * share, 1), "95% CI": f"{100 * lo:.1f}-{100 * hi:.1f}"}


def show(title, df, by):
    print(f"\n=== {title} ===")
    print(pd.DataFrame([row(g, " | ".join(map(str, k)) if isinstance(k, tuple) else str(k))
                        for k, g in df.groupby(by, observed=True) if len(g) >= 50]).to_string(index=False))


show("A. Whole-history baseline (look-ahead, for reference)", lapses, "taper_whole")

eligible = lapses[lapses["has_full_baseline"]]
print(f"\nPast-only baseline needs 112+ days of history: {len(eligible):,} of {len(lapses):,} lapses qualify.")
print(f"Of those, {int((eligible['workouts_baseline_84d'] == 0).sum()):,} had no workouts in the 12-week baseline "
      "(coming straight off an earlier lapse) and are shown as their own group.")
show("B. Past-only baseline (what a live trigger could use)", eligible, "taper_past")
show("C. Past-only baseline within each training rhythm", eligible, ["rhythm", "taper_past"])
print("\nGroups under 50 lapses are hidden.")
