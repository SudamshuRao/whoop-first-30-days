"""Phase 5: size a member-level A/B test of a proactive check-in sent when a member lapses.

Outcome: back within 14 days of the lapse being detected (day 28 after the last workout),
the same definition as the Lapses & returns page. Every input comes from the marts.
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lapse_data import load_lapses  # noqa: E402
from survival import kaplan_meier, returned_by  # noqa: E402

ALPHA, POWER = 0.05, 0.80
LIFTS = [0.01, 0.02, 0.03, 0.05]          # absolute lifts in the return rate, in proportion points
BASES = [10_000, 50_000, 100_000]          # members eligible to be enrolled when they lapse
RNG_SEED, N_SIMS = 7, 2000


def n_per_arm(p0: float, lift: float, alpha: float = ALPHA, power: float = POWER) -> int:
    """Members per arm for a two-sided two-proportion z-test."""
    p1 = p0 + lift
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    pbar = (p0 + p1) / 2
    n = (z_a * np.sqrt(2 * pbar * (1 - pbar)) + z_b * np.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / lift ** 2
    return int(np.ceil(n))


def simulated_power(outcomes: np.ndarray, n: int, lift: float, sims: int = N_SIMS, seed: int = RNG_SEED) -> float:
    """Check the formula on the real outcomes: resample lapses into two arms, add the lift to one, test."""
    rng = np.random.default_rng(seed)
    p0 = outcomes.mean()
    flip = lift / (1 - p0)                    # share of non-returners the check-in brings back
    hits = 0
    for _ in range(sims):
        c = rng.choice(outcomes, n)
        t = rng.choice(outcomes, n)
        t = t | (rng.random(n) < flip)
        pc, pt = c.mean(), t.mean()
        pp = (pc + pt) / 2
        z = (pt - pc) / np.sqrt(2 * pp * (1 - pp) / n)
        hits += abs(z) > stats.norm.ppf(1 - ALPHA / 2)
    return hits / sims


def icc(df: pd.DataFrame) -> float:
    """Within-member correlation of the outcome (one-way ANOVA estimator)."""
    g = df.groupby("user_id")["y"]
    k = g.size()
    n, a = k.sum(), len(k)
    grand = df["y"].mean()
    msb = (k * (g.mean() - grand) ** 2).sum() / (a - 1)
    msw = ((df["y"] - g.transform("mean")) ** 2).sum() / (n - a)
    k0 = (n - (k ** 2).sum() / n) / (a - 1)
    return float((msb - msw) / (msb + (k0 - 1) * msw))


def covariate_r2(df: pd.DataFrame) -> float:
    """Share of outcome variance explained by what is known when the lapse is detected."""
    X = pd.DataFrame({
        "log_recent": np.log1p(df["workouts_28d_before"]),
        "log_tenure": np.log1p(df["tenure_days_at_lapse"]),
        "prior_lapses": df.groupby("user_id").cumcount(),
    })
    X = X.join(pd.get_dummies(df[["lapse_month", "rhythm", "primary_sport_group"]].astype(str),
                              drop_first=True, dtype=float))
    return float(sm.OLS(df["y"].astype(float), sm.add_constant(X)).fit().rsquared)


def run_all(con: duckdb.DuckDBPyConnection) -> dict:
    lapses = load_lapses(con).sort_values(["user_id", "last_workout_ts"])
    out = {}

    # Baseline: same Kaplan-Meier figure as the Lapses & returns page
    curve = kaplan_meier(lapses["lapse_days"], lapses["ended"])
    out["p0"], out["p0_lo"], out["p0_hi"] = returned_by(curve, 28)

    # Lapses with a known 14-day outcome, for the checks below
    known = lapses.dropna(subset=["returned_within_window"]).copy()
    known["y"] = known["returned_within_window"].astype(bool)
    out["n_known"] = len(known)
    out["p0_known"] = float(known["y"].mean())

    # Sample size at each lift
    out["sizes"] = pd.DataFrame(
        [{"lift": d, "n_per_arm": n_per_arm(out["p0"], d)} for d in LIFTS]).set_index("lift")
    out["sizes"]["total"] = 2 * out["sizes"]["n_per_arm"]

    # Simulation check of the 2-point row on the real outcomes
    n2 = int(out["sizes"].loc[0.02, "n_per_arm"])
    out["sim_power_2pt"] = simulated_power(known["y"].to_numpy(), n2, 0.02)

    # Why enrol each member once: outcomes repeat within members
    out["icc"] = icc(known)
    per_member = known.groupby("user_id").size()
    out["lapses_per_lapsed_member"] = float(per_member.mean())
    out["design_effect"] = 1 + (out["lapses_per_lapsed_member"] - 1) * out["icc"]

    # Covariate adjustment: how much smaller could the test be?
    out["r2"] = covariate_r2(known)

    # Enrolment speed: lapses per member-year, pooled over all members
    rate = con.sql("""
        select sum(n_lapses) / sum(tenure_days / 365.25) from dim_members where tenure_days > 0
    """).fetchall()[0][0]
    out["lapses_per_member_year"] = float(rate)
    weekly = {b: b * rate / 52 for b in BASES}
    out["weeks"] = pd.DataFrame(
        {f"{b:,} members": [row.total / weekly[b] for row in out["sizes"].itertuples()] for b in BASES},
        index=out["sizes"].index)
    return out


if __name__ == "__main__":
    con = duckdb.connect(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "data" / "whoop.duckdb"), read_only=True)
    r = run_all(con)
    print(f"Baseline: back within 14 days = {r['p0']:.1%} (95% CI {r['p0_lo']:.1%} to {r['p0_hi']:.1%})")
    print(f"Lapses with a known 14-day outcome: {r['n_known']:,} (raw share {r['p0_known']:.1%})")
    print("\nMembers needed (80% power, two-sided alpha 0.05):")
    print(r["sizes"].rename(index=lambda d: f"+{100 * d:.0f} pts").to_string())
    print(f"\nSimulated power at the +2 pt size, on the real outcomes: {r['sim_power_2pt']:.1%}")
    print(f"Within-member correlation (ICC): {r['icc']:.3f}; "
          f"lapses per lapsed member: {r['lapses_per_lapsed_member']:.1f}; "
          f"design effect if every lapse counted: {r['design_effect']:.2f}")
    print(f"Variance explained by pre-lapse covariates (R^2): {r['r2']:.3f}")
    print(f"Lapses per member-year (pooled): {r['lapses_per_member_year']:.2f}")
    print("\nWeeks of enrolment needed, by size of the eligible member base:")
    print(r["weeks"].rename(index=lambda d: f"+{100 * d:.0f} pts").round(1).to_string())
