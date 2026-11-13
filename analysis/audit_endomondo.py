"""Phase 1 audit of the flattened Endomondo workouts. Prints answers to the audit questions."""
import duckdb

con = duckdb.connect()
con.sql("set TimeZone = 'UTC'")
con.sql("""
    create view w as
    select * from read_parquet('data/clean/endomondo_workouts.parquet')
""")

def section(title, sql):
    print(f"\n=== {title} ===")
    con.sql(sql).show(max_rows=40)

section("A. Overview", """
    select count(*) as workouts, count(distinct user_id) as users,
           min(start_ts) as first_start, max(start_ts) as last_start
    from w
""")

section("B. Workouts by start year (spot broken clocks)", """
    select year(start_ts) as yr, count(*) as workouts, count(distinct user_id) as users
    from w group by 1 order by 1
""")

section("C. Workouts per user", """
    with u as (select user_id, count(*) as n from w group by 1)
    select min(n) as min, quantile_cont(n, 0.10) as p10, quantile_cont(n, 0.25) as p25,
           median(n) as median, quantile_cont(n, 0.75) as p75, quantile_cont(n, 0.90) as p90,
           max(n) as max,
           count(*) filter (where n < 10) as users_under_10,
           count(*) filter (where n < 50) as users_under_50
    from u
""")

section("D. Users by year of their first workout (are starts spread out?)", """
    with u as (select user_id, min(start_ts) as first_ts from w
               where year(start_ts) between 2005 and 2020 group by 1)
    select year(first_ts) as first_year, count(*) as users from u group by 1 order by 1
""")

section("E. Span of each user's history in days (first to last workout)", """
    with u as (select user_id, date_diff('day', min(start_ts), max(start_ts)) as span_days
               from w where year(start_ts) between 2005 and 2020 group by 1)
    select min(span_days) as min, quantile_cont(span_days, 0.10) as p10, median(span_days) as median,
           quantile_cont(span_days, 0.90) as p90, max(span_days) as max
    from u
""")

section("F. Workouts in each user's first 30 days (looks like a real start, or mid-history?)", """
    with clean as (select * from w where year(start_ts) between 2005 and 2020),
         firsts as (select user_id, min(start_ts) as first_ts from clean group by 1),
         first30 as (
            select c.user_id, count(*) as n30
            from clean c join firsts f using (user_id)
            where c.start_ts < f.first_ts + interval 30 day
            group by 1)
    select min(n30) as min, quantile_cont(n30, 0.25) as p25, median(n30) as median,
           quantile_cont(n30, 0.75) as p75, max(n30) as max
    from first30
""")

section("G. Sport mix (top 15)", """
    select sport, count(*) as workouts, count(distinct user_id) as users,
           round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_workouts
    from w group by 1 order by 2 desc limit 15
""")
