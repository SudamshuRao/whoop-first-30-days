-- One row per lapse, with what the member looked like going into it.
with lapses as (
    select * from {{ ref('int_endomondo__lapses') }}
),

members as (
    select * from {{ ref('dim_members') }}
),

workouts as (
    select user_id, start_ts from {{ ref('fct_workouts') }}
),

pre_lapse_activity as (
    -- Workouts in the 28 days up to and including the last workout before the lapse
    select l.lapse_id, count(*) as workouts_28d_before
    from lapses l
    join workouts w
      on w.user_id = l.user_id
     and w.start_ts >  l.last_workout_ts - interval 28 day
     and w.start_ts <= l.last_workout_ts
    group by l.lapse_id
),

baseline_activity as (
    -- The 12 weeks before that 28-day window (days 29-112 before the last workout).
    -- Uses only the past, so a live trigger could compute it too.
    select l.lapse_id, count(*) as workouts_baseline_84d
    from lapses l
    join workouts w
      on w.user_id = l.user_id
     and w.start_ts >  l.last_workout_ts - interval 112 day
     and w.start_ts <= l.last_workout_ts - interval 28 day
    group by l.lapse_id
)

select
    l.*,
    year(l.last_workout_ts)                                       as lapse_year,
    month(l.last_workout_ts)                                      as lapse_month,
    date_diff('day', m.first_workout_ts, l.last_workout_ts)       as tenure_days_at_lapse,
    p.workouts_28d_before,
    coalesce(b.workouts_baseline_84d, 0)                          as workouts_baseline_84d,
    -- Baseline is only meaningful if the member had 112+ days of history before the lapse
    date_diff('day', m.first_workout_ts, l.last_workout_ts) >= 112 as has_full_baseline,
    m.primary_sport_group,
    m.median_gap_days,
    -- Alternative definition for Phase 3: the gap is at least 3x this member's usual gap
    l.lapse_days >= 3 * m.median_gap_days                         as is_personal_lapse
from lapses l
join members m using (user_id)
left join pre_lapse_activity p using (lapse_id)
left join baseline_activity b using (lapse_id)
