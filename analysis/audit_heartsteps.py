"""Phase 1 audit of HeartSteps V1. Checks the trial ran as designed.
Deliberately does NOT compare outcomes between sent and not sent: that is Phase 4,
after the analysis plan is written down."""
import duckdb

con = duckdb.connect()
con.sql("set TimeZone = 'UTC'")
for name in ["users", "suggestions"]:
    con.sql(f"""create view {name} as
                select * from read_csv('data/raw/heartsteps/{name}.csv', sample_size = -1)""")

def section(title, sql):
    print(f"\n=== {title} ===")
    con.sql(sql).show(max_rows=40)

section("A. Decision points per participant", """
    with u as (select "user.index" as uid, count(*) as n from suggestions group by 1)
    select count(*) as participants, sum(n) as decision_points,
           min(n) as min, median(n) as median, max(n) as max
    from u
""")

section("B. Availability and randomization (design: 60% sent when available)", """
    select avail, send, count(*) as n,
           round(100.0 * count(*) / sum(count(*)) over (partition by avail), 1) as pct_within_avail
    from suggestions group by 1, 2 order by 1, 2
""")

section("C. Missing 30-minute step outcome (tracker), available points only", """
    select send, count(*) as n,
           count(*) filter (where jbsteps30 is null) as missing_outcome,
           round(100.0 * count(*) filter (where jbsteps30 is null) / count(*), 1) as pct_missing
    from suggestions where avail group by 1 order by 1
""")

section("D. Balance check: steps in the 30 minutes BEFORE (should match across arms)", """
    select send, count(jbsteps30pre) as n,
           round(avg(ln(jbsteps30pre + 0.5)), 3) as mean_log_pre_steps,
           round(median(jbsteps30pre), 0) as median_pre_steps
    from suggestions where avail group by 1 order by 1
""")

section("E. Responses to sent suggestions (guardrail inputs)", """
    select coalesce(response, 'missing') as response, count(*) as n,
           round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
    from suggestions where send group by 1 order by 2 desc
""")

section("F. Location at decision time, bucketed", """
    select case when "dec.location.category" = 'home' then 'home'
                when "dec.location.category" = 'work' then 'work'
                when "dec.location.category" is null then 'missing'
                else 'other' end as location, count(*) as n
    from suggestions group by 1 order by 2 desc
""")

section("G. Study length and dropout", """
    select count(*) as participants, min(totaldays) as min_days, median(totaldays) as median_days,
           max(totaldays) as max_days, count("dropout.date") as with_dropout_date
    from users
""")
