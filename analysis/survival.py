"""Kaplan-Meier helpers shared by the analysis scripts and the site pages."""
import numpy as np
import pandas as pd


def kaplan_meier(durations, ended) -> pd.DataFrame:
    """Kaplan-Meier curve on whole days.

    Returns one row per day with an event: S (share still lapsed) and Greenwood variance terms.
    """
    days = np.floor(np.asarray(durations, dtype=float))
    ended = np.asarray(ended, dtype=bool)
    rows, s, green = [], 1.0, 0.0
    for t in np.unique(days[ended]):
        n = (days >= t).sum()
        d = ((days == t) & ended).sum()
        s *= 1 - d / n
        if n > d:
            green += d / (n * (n - d))
        rows.append((t, s, green))
    return pd.DataFrame(rows, columns=["day", "S", "greenwood"]).set_index("day")


def returned_by(curve: pd.DataFrame, day: int) -> tuple[float, float, float]:
    """Share returned by `day` (1 - S) with a 95% Greenwood confidence interval."""
    past = curve[curve.index <= day]
    if past.empty:
        return 0.0, 0.0, 0.0
    s, g = past["S"].iloc[-1], past["greenwood"].iloc[-1]
    se = s * np.sqrt(g)
    return 1 - s, max(0.0, 1 - s - 1.96 * se), min(1.0, 1 - s + 1.96 * se)


def median_duration(curve: pd.DataFrame) -> float:
    below = curve[curve["S"] <= 0.5]
    return float(below.index[0]) if not below.empty else float("nan")
