"""Print the pre-registered HeartSteps readout results."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from readout_models import run_all

con = duckdb.connect("data/whoop.duckdb", read_only=True)
r = run_all(con)


def line(name, e):
    print(f"{name:32s} {e['pct']:+6.1f}%  (95% CI {e['pct_lo']:+.1f}% to {e['pct_hi']:+.1f}%)  "
          f"~{e['steps']:+.0f} steps  p={e['p']:.3f}")


print(f"Sample: {r['n_people']} people, {r['n_dp']:,} decision points, {r['n_cc']:,} with an outcome")
print(f"Average 30-minute steps with no suggestion: {r['baseline_steps']:.0f}\n")
print("PRIMARY")
line("Suggestion vs none", r["primary"])
print("\nSENSITIVITY")
line("Missing outcome = 0 steps", r["sensitivity_zero_fill"])
print("\nSECONDARY 1: effect by study day")
for d, e in r["by_day"].items():
    line(f"  day {d}", e)
line("  change per extra day (log scale, as %)", r["decay_slope"])
print("\nSECONDARY 2: type of suggestion")
line("  walking vs none", r["walking"])
line("  anti-sedentary vs none", r["anti_sedentary"])
print("\nSECONDARY 3: location")
line("  elsewhere", r["elsewhere"])
line("  home or work", r["home_or_work"])
print("\nGUARDRAILS (share of sent suggestions)")
print(r["guardrails_by_week"].round(3).to_string())
print("Flags:", r["guardrail_flags"])
print(f"\nDECISION (pre-registered rule): {r['decision']}")
