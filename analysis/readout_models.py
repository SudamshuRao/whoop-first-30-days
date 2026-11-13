"""HeartSteps readout: the models exactly as pre-registered in site/readout.qmd (commit e39c0a7).
Shared by analysis/readout_analysis.py and the readout page."""
import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

DESIGN_P = 0.6


def load(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.sql("""
        select participant_id, study_day, study_week, location, response,
               is_sent, coalesce(is_sent_walking, false) as is_walk,
               coalesce(is_sent_anti_sedentary, false) as is_sed,
               steps_30m_after, steps_30m_before, has_outcome
        from fct_decision_points
        where is_in_primary_analysis
    """).df()
    df["a"] = df["is_sent"].astype(int)
    df["pre_missing"] = df["steps_30m_before"].isna().astype(int)
    df["log_pre"] = np.log(df["steps_30m_before"].fillna(0) + 0.5)
    df["home_work"] = df["location"].isin(["home", "work"]).astype(int)
    return df


def _fit(df, y, terms):
    X = sm.add_constant(df[terms].astype(float))
    groups = df["participant_id"]
    model = sm.OLS(df[y], X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    dof = groups.nunique() - 1
    return model, dof


def _effect(model, dof, weights: dict, baseline_steps: float) -> dict:
    """A linear combination of coefficients, with a 95% CI on t(dof); reported on the % and steps scale."""
    names = model.params.index
    w = np.array([weights.get(n, 0.0) for n in names])
    est = float(w @ model.params.values)
    se = float(np.sqrt(w @ model.cov_params().values @ w))
    t = stats.t.ppf(0.975, dof)
    lo, hi = est - t * se, est + t * se
    p = 2 * stats.t.sf(abs(est / se), dof)
    pct = lambda b: 100 * (np.exp(b) - 1)
    return {"log_effect": est, "se": se, "p": p,
            "pct": pct(est), "pct_lo": pct(lo), "pct_hi": pct(hi),
            "steps": baseline_steps * (np.exp(est) - 1), "ci_excludes_zero": lo > 0 or hi < 0, "positive": est > 0}


def run_all(con: duckdb.DuckDBPyConnection) -> dict:
    df = load(con)
    cc = df[df["has_outcome"]].copy()
    cc["y"] = np.log(cc["steps_30m_after"] + 0.5)
    cc["a_c"] = cc["a"] - DESIGN_P
    controls = ["log_pre", "pre_missing"]
    baseline = float(cc.loc[cc["a"] == 0, "steps_30m_after"].mean())
    out = {"n_people": int(df["participant_id"].nunique()), "n_dp": len(df), "n_cc": len(cc),
           "baseline_steps": baseline, "mean_steps_all": float(cc["steps_30m_after"].mean())}

    # Primary
    m, dof = _fit(cc, "y", ["a_c"] + controls)
    out["primary"] = _effect(m, dof, {"a_c": 1}, baseline)

    # Sensitivity: missing outcome = zero steps
    zf = df.copy()
    zf["y"] = np.log(zf["steps_30m_after"].fillna(0) + 0.5)
    zf["a_c"] = zf["a"] - DESIGN_P
    m, dof = _fit(zf, "y", ["a_c"] + controls)
    out["sensitivity_zero_fill"] = _effect(m, dof, {"a_c": 1}, baseline)

    # Secondary 1: does the effect fade over study days?
    cc["a_c_x_day"] = cc["a_c"] * cc["study_day"]
    m, dof = _fit(cc, "y", ["a_c", "a_c_x_day", "study_day"] + controls)
    out["by_day"] = {d: _effect(m, dof, {"a_c": 1, "a_c_x_day": d}, baseline) for d in (0, 10, 20, 30, 40)}
    out["decay_slope"] = _effect(m, dof, {"a_c_x_day": 1}, baseline)
    # Same model, evaluated on every day of the six-week trial, for the chart
    out["by_day_curve"] = {d: _effect(m, dof, {"a_c": 1, "a_c_x_day": d}, baseline) for d in range(0, 42)}

    # Secondary 2: walking vs anti-sedentary, each vs nothing (probabilities estimated from the data)
    p_walk, p_sed = df["is_walk"].mean(), df["is_sed"].mean()
    cc["walk_c"] = cc["is_walk"].astype(int) - p_walk
    cc["sed_c"] = cc["is_sed"].astype(int) - p_sed
    m, dof = _fit(cc, "y", ["walk_c", "sed_c"] + controls)
    out["walking"] = _effect(m, dof, {"walk_c": 1}, baseline)
    out["anti_sedentary"] = _effect(m, dof, {"sed_c": 1}, baseline)

    # Secondary 3: home/work vs elsewhere
    cc["a_c_x_hw"] = cc["a_c"] * cc["home_work"]
    m, dof = _fit(cc, "y", ["a_c", "a_c_x_hw", "home_work"] + controls)
    out["elsewhere"] = _effect(m, dof, {"a_c": 1}, baseline)
    out["home_or_work"] = _effect(m, dof, {"a_c": 1, "a_c_x_hw": 1}, baseline)

    # Guardrails: shares of sent suggestions by study week (denominator = all sent)
    sent = df[df["a"] == 1]
    g = sent.groupby("study_week").agg(
        sent=("a", "size"),
        bad=("response", lambda r: (r == "bad").mean()),
        no_response=("response", lambda r: (r == "no_response").mean()),
        snoozed=("response", lambda r: (r == "snoozed").mean()),
        people=("participant_id", "nunique"))
    out["guardrails_by_week"] = g
    first, last = 1, 6  # the trial ran six weeks; later weeks hold only a few participants
    out["guardrail_flags"] = {
        "bad rose > 10 pts": bool(g.loc[last, "bad"] - g.loc[first, "bad"] > 0.10),
        "no response rose > 10 pts": bool(g.loc[last, "no_response"] - g.loc[first, "no_response"] > 0.10),
        "snoozed > 5% in any week": bool((g["snoozed"] > 0.05).any()),
    }

    # Decision rule, applied mechanically
    prim = out["primary"]
    secondary = [out["by_day"][0], out["walking"], out["anti_sedentary"], out["elsewhere"], out["home_or_work"]]
    any_flag = any(out["guardrail_flags"].values())
    if prim["positive"] and prim["ci_excludes_zero"] and not any_flag:
        decision = "Go"
    elif (prim["positive"] and prim["ci_excludes_zero"] and any_flag) or \
         any(s["positive"] and s["ci_excludes_zero"] for s in secondary):
        decision = "Go with changes"
    else:
        decision = "No go"
    out["decision"] = decision
    return out
