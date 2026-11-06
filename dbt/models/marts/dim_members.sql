-- One row per Endomondo member.
with workouts as (
    select * from {{ ref('fct_workouts') }}
),

lapses as (
    select user_id, count(*) as n_lapses
    from {{ ref('int_endomondo__lapses') }}
    group by user_id
),

genders as (
    select user_id, mode(gender) as gender
    from {{ ref('stg_endomondo__workouts') }}
    group by user_id
)

select
    w.user_id,
    any_value(g.gender)                                   as gender,
    min(w.start_ts)                                       as first_workout_ts,
    max(w.start_ts)                                       as last_workout_ts,
    count(*)                                              as n_workouts,
    date_diff('day', min(w.start_ts), max(w.start_ts))    as tenure_days,
    mode(w.sport_group)                                   as primary_sport_group,
    median(w.days_since_prev)                             as median_gap_days,
    bool_or(w.sport_group = 'strength')                   as has_strength_workouts,
    coalesce(any_value(l.n_lapses), 0)                    as n_lapses
from workouts w
left join genders g using (user_id)
left join lapses l using (user_id)
group by w.user_id
