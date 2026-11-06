-- One row per workout. Drops workouts with impossible dates (see the data audit).
with source as (
    select * from {{ source('endomondo', 'endomondo_workouts') }}
)

select
    workout_id,
    user_id,
    lower(trim(sport))  as sport,
    start_ts,
    end_ts,
    duration            as duration_s,
    distance,
    calories,
    ascent,
    descent,
    gender
from source
where start_ts >= '{{ var("endomondo_valid_from") }}'::timestamptz
  and start_ts <  '{{ var("endomondo_valid_to") }}'::timestamptz
