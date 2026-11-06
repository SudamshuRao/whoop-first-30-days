-- One row per workout, with the gap in days since the same member's previous workout.
with workouts as (
    select * from {{ ref('stg_endomondo__workouts') }}
)

select
    workout_id,
    user_id,
    sport,
    start_ts,
    row_number() over w                                            as workout_number,
    lag(start_ts) over w                                           as prev_start_ts,
    date_diff('second', lag(start_ts) over w, start_ts) / 86400.0  as days_since_prev
from workouts
window w as (partition by user_id order by start_ts, workout_id)
