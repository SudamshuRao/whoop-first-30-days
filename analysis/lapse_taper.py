"""Phase 3: is it low activity, or a drop from the member's own usual level, that goes with longer lapses?
Compares workouts in the 28 days before a lapse with what that member usually does in 28 days."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from survival import kaplan_meier, median_duration, returned_by

con = duckdb.connect("data/whoop.duckdb", read_only=True)
con.sql("set TimeZone = 'UTC'")

lapses = con.sql("""
    select l.lapse_days, l.is_censored, l.workouts_28d_before,
           m.n_workouts / greatest(m.tenure_days / 28.0, 1)  as usual_per_28d,
           case when m.median_gap_days < 1.5 then 'near-daily'
                when m.median_gap_days < 3.5 then 'every 2-3 days'
                else 'weekly or less' end                     as rhythm
    from fct_lapses l
    join dim_members m using (user_id)
""").df()

lapses["vs_usual"] = lapses["workouts_28d_before"] / lapses["usual_per_28d"]
lapses["taper"] = pd.cut(lapses["vs_usual"], [-0.01, 0.5, 0.9, 1.1, 100],
                         labels=["under half of usual", "50-90% of usual", "about usual", "above usual"])


def row(df, label):
    curve = kaplan_meier(df["lapse_days"], ~df["is_censored"])
    share, lo, hi = returned_by(curve, 28)
    return {"group": label, "lapses": len(df), "median_days": median_duration(curve),
            "back_by_28d_%": round(100 * share, 1), "95% CI": f"{100 * lo:.1f}-{100 * hi:.1f}"}


print("\n=== A. Activity before the lapse, relative to the member's own usual level ===")
print(pd.DataFrame([row(g, k) for k, g in lapses.groupby("taper", observed=True)]).to_string(index=False))

print("\n=== B. Same split within each training rhythm (does the pattern hold for everyone?) ===")
rows = [row(g, f"{r} | {t}") for (r, t), g in lapses.groupby(["rhythm", "taper"], observed=True) if len(g) >= 50]
print(pd.DataFrame(rows).to_string(index=False))

print("\nGroups under 50 lapses are hidden. 'usual' = member's total workouts / (tenure in 28-day blocks).")
