-- One row per workout, with sport group and position in the member's history.
with workouts as (
    select * from {{ ref('stg_endomondo__workouts') }}
),

gaps as (
    select workout_id, workout_number, days_since_prev
    from {{ ref('int_endomondo__workout_gaps') }}
),

sport_groups as (
    select * from {{ ref('sport_groups') }}
)

select
    w.workout_id,
    w.user_id,
    w.sport,
    coalesce(sg.sport_group, 'other')  as sport_group,
    w.start_ts,
    cast(w.start_ts as date)           as start_date,
    w.duration_s,
    w.calories,
    g.workout_number,
    g.days_since_prev
from workouts w
join gaps g using (workout_id)
left join sport_groups sg using (sport)
