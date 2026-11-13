-- One row per trial participant.
with source as (
    select * from {{ source('heartsteps', 'users') }}
)

select
    "user.index"          as participant_id,
    age,
    gender,
    totaldays             as total_days,
    "dropout.date"        as dropout_date,
    "travel.start"        as travel_start,
    "travel.end"          as travel_end,
    "first.notif.utime"   as first_notification_utc,
    "last.notif.utime"    as last_notification_utc
from source
