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
)

select
    l.*,
    year(l.last_workout_ts)                                       as lapse_year,
    month(l.last_workout_ts)                                      as lapse_month,
    date_diff('day', m.first_workout_ts, l.last_workout_ts)       as tenure_days_at_lapse,
    p.workouts_28d_before,
    m.primary_sport_group,
    m.median_gap_days,
    -- Alternative definition for Phase 3: the gap is at least 3x this member's usual gap
    l.lapse_days >= 3 * m.median_gap_days                         as is_personal_lapse
from lapses l
join members m using (user_id)
left join pre_lapse_activity p using (lapse_id)
