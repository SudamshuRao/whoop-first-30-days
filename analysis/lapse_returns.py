"""Phase 3: how long lapses last and what goes with a fast return.
Uses a Kaplan-Meier estimate so lapses still open at the data end (censored) are handled correctly.
Reads marts only."""
import duckdb
import numpy as np
import pandas as pd

con = duckdb.connect("data/whoop.duckdb", read_only=True)
con.sql("set TimeZone = 'UTC'")

lapses = con.sql("""
    select l.lapse_id, l.lapse_days, l.is_censored, l.lapse_year, l.lapse_month,
           l.workouts_28d_before, l.tenure_days_at_lapse, l.primary_sport_group,
           case when m.median_gap_days < 1.5 then 'near-daily'
                when m.median_gap_days < 3.5 then 'every 2-3 days'
                else 'weekly or less' end as rhythm
    from fct_lapses l
    join dim_members m using (user_id)
""").df()

CHECKPOINTS = [21, 28, 42, 60, 90, 180, 365]


def kaplan_meier(df: pd.DataFrame) -> pd.Series:
    """Share of lapses still ongoing at each whole day (S(t)), handling censoring."""
    days = np.floor(df["lapse_days"].to_numpy())
    ended = ~df["is_censored"].to_numpy()
    surv, s = {}, 1.0
    for t in np.unique(days[ended]):
        at_risk = (days >= t).sum()
        events = ((days == t) & ended).sum()
        s *= 1 - events / at_risk
        surv[t] = s
    return pd.Series(surv)


def still_lapsed_at(curve: pd.Series, day: int) -> float:
    past = curve[curve.index <= day]
    return 1.0 if past.empty else float(past.iloc[-1])


def median_duration(curve: pd.Series) -> float:
    below = curve[curve <= 0.5]
    return float(below.index[0]) if not below.empty else float("nan")


def summarise(df: pd.DataFrame, label: str) -> dict:
    curve = kaplan_meier(df)
    row = {"group": label, "lapses": len(df), "median_days": median_duration(curve)}
    for d in CHECKPOINTS:
        row[f"back_by_{d}d_%"] = round(100 * (1 - still_lapsed_at(curve, d)), 1)
    return row


def table(title: str, groups):
    print(f"\n=== {title} ===")
    print(pd.DataFrame([summarise(g, str(k)) for k, g in groups]).to_string(index=False))


print("Days are counted from the last workout before the lapse; every lapse is 14+ days by definition.")
table("A. All lapses", [("all", lapses)])
table("B. By training rhythm", lapses.groupby("rhythm"))
lapses["activity_28d"] = pd.qcut(lapses["workouts_28d_before"], 4, duplicates="drop")
table("C. By workouts in the 28 days before the lapse (quartiles)", lapses.groupby("activity_28d", observed=True))
lapses["tenure"] = pd.cut(lapses["tenure_days_at_lapse"], [-1, 365, 730, 1460, 99999],
                          labels=["<1 yr", "1-2 yrs", "2-4 yrs", "4+ yrs"])
table("D. By how long they had been a member", lapses.groupby("tenure", observed=True))
table("E. By primary sport", lapses.groupby("primary_sport_group"))
table("F. By year the lapse started", lapses.groupby("lapse_year"))
lapses["season"] = lapses["lapse_month"].map({12: "Dec-Feb", 1: "Dec-Feb", 2: "Dec-Feb", 3: "Mar-May", 4: "Mar-May",
                                              5: "Mar-May", 6: "Jun-Aug", 7: "Jun-Aug", 8: "Jun-Aug",
                                              9: "Sep-Nov", 10: "Sep-Nov", 11: "Sep-Nov"})
table("G. By season the lapse started (calendar months; hemisphere unknown)", lapses.groupby("season"))
