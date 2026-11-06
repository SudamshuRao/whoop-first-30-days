-- One row per member per week since their first workout, up to the data end.
-- Inactive weeks are included (zero workouts), so weekly active rates and streaks are correct.
with members as (
    select user_id, first_workout_ts from {{ ref('dim_members') }}
),

workouts as (
    select user_id, start_ts from {{ ref('fct_workouts') }}
),

spine as (
    select
        user_id,
        first_workout_ts,
        unnest(range(0, floor(date_diff('day', first_workout_ts,
              '{{ var("endomondo_valid_to") }}'::timestamptz) / 7)::bigint + 1)) as week_number
    from members
),

weekly_counts as (
    select
        w.user_id,
        floor(date_diff('day', m.first_workout_ts, w.start_ts) / 7)::bigint as week_number,
        count(*) as n_workouts
    from workouts w
    join members m using (user_id)
    group by all
),

weeks as (
    select
        s.user_id,
        s.week_number,
        s.first_workout_ts + to_days(cast(7 * s.week_number as integer))      as week_start_ts,
        coalesce(c.n_workouts, 0)                                             as n_workouts,
        coalesce(c.n_workouts, 0) > 0                                         as is_active
    from spine s
    left join weekly_counts c using (user_id, week_number)
),

islands as (
    -- Gaps-and-islands: every inactive week starts a new island
    select *,
        sum(case when is_active then 0 else 1 end)
            over (partition by user_id order by week_number) as island_id
    from weeks
)

select
    user_id,
    week_number,
    week_start_ts,
    week_start_ts + interval 7 day <= '{{ var("endomondo_valid_to") }}'::timestamptz as is_complete_week,
    n_workouts,
    is_active,
    -- Consecutive active weeks ending at this week (0 when inactive)
    case when is_active
         then sum(is_active::int) over (partition by user_id, island_id order by week_number)
         else 0 end                                                           as active_streak_weeks
from islands
