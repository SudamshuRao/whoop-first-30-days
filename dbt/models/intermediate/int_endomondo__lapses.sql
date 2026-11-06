-- One row per lapse: a gap of {{ var('lapse_days') }}+ days between a member's workouts.
-- Includes open lapses still running when the data ends; those are censored.
with gaps as (
    select * from {{ ref('int_endomondo__workout_gaps') }}
),

data_end as (
    -- Collection end, not the latest workout: stray late rows would make everyone look lapsed.
    select '{{ var("endomondo_valid_to") }}'::timestamptz as data_end_ts
),

closed_lapses as (
    select
        user_id,
        prev_start_ts    as last_workout_ts,
        start_ts         as return_ts,
        days_since_prev  as lapse_days,
        false            as is_censored
    from gaps
    where days_since_prev >= {{ var('lapse_days') }}
),

open_lapses as (
    select
        g.user_id,
        max(g.start_ts)                                                    as last_workout_ts,
        null::timestamptz                                                  as return_ts,
        date_diff('second', max(g.start_ts), any_value(d.data_end_ts)) / 86400.0 as lapse_days,
        true                                                               as is_censored
    from gaps g
    cross join data_end d
    group by g.user_id
    having date_diff('second', max(g.start_ts), any_value(d.data_end_ts)) / 86400.0 >= {{ var('lapse_days') }}
),

all_lapses as (
    select * from closed_lapses
    union all
    select * from open_lapses
)

select
    md5(user_id::varchar || '|' || last_workout_ts::varchar)  as lapse_id,
    user_id,
    last_workout_ts,
    last_workout_ts + to_days({{ var('lapse_days') }})        as detected_ts,
    return_ts,
    lapse_days,
    is_censored,
    -- true/false when we can tell; null when the data ends before the return window closes
    case
        when not is_censored
            then lapse_days <= {{ var('lapse_days') }} + {{ var('return_window_days') }}
        when lapse_days > {{ var('lapse_days') }} + {{ var('return_window_days') }}
            then false
    end                                                       as returned_within_window
from all_lapses
