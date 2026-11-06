"""Phase 3: compare a fixed lapse definition (14+ days) with a personal one (3x the member's usual gap).
Reads marts only."""
import duckdb

con = duckdb.connect("data/whoop.duckdb", read_only=True)
con.sql("set TimeZone = 'UTC'")

con.sql("""
    create temp view gaps as
    select
        w.user_id,
        w.days_since_prev                       as gap_days,
        m.median_gap_days,
        case when m.median_gap_days < 1.5 then '1 near-daily'
             when m.median_gap_days < 3.5 then '2 every 2-3 days'
             when m.median_gap_days < 7.5 then '3 about weekly'
             else '4 less than weekly' end      as rhythm,
        w.days_since_prev >= 14                 as is_fixed_lapse,
        w.days_since_prev >= 3 * m.median_gap_days as is_personal_lapse
    from fct_workouts w
    join dim_members m using (user_id)
    where w.days_since_prev is not null
""")

def section(title, sql):
    print(f"\n=== {title} ===")
    con.sql(sql).show(max_rows=20)

section("A. Members by training rhythm (their median gap between workouts)", """
    select rhythm, count(distinct user_id) as members,
           round(median(median_gap_days), 1) as typical_gap_days,
           round(3 * median(median_gap_days), 1) as personal_threshold_days
    from gaps group by 1 order by 1
""")

section("B. How often each definition fires (share of all gaps)", """
    select coalesce(rhythm, 'all members') as rhythm, count(*) as gaps,
           round(100.0 * avg(is_fixed_lapse::int), 2)    as pct_fixed,
           round(100.0 * avg(is_personal_lapse::int), 2) as pct_personal
    from gaps group by rollup (gaps.rhythm) order by gaps.rhythm nulls last
""")

section("C. Agreement between the definitions", """
    select is_fixed_lapse, is_personal_lapse, count(*) as gaps,
           count(distinct user_id) as members,
           round(median(gap_days), 1) as median_gap_days
    from gaps group by 1, 2 order by 1, 2
""")

section("D. Lapses per member-year under each definition", """
    with per_member as (
        select g.user_id, m.tenure_days,
               sum(g.is_fixed_lapse::int)    as fixed_lapses,
               sum(g.is_personal_lapse::int) as personal_lapses
        from gaps g join dim_members m using (user_id)
        group by all
    )
    select round(median(fixed_lapses    / nullif(tenure_days / 365.25, 0)), 1) as fixed_per_year,
           round(median(personal_lapses / nullif(tenure_days / 365.25, 0)), 1) as personal_per_year
    from per_member
""")
