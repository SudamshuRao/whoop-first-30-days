-- One row per decision point: a moment when the app could send an activity suggestion.
with source as (
    select * from {{ source('heartsteps', 'suggestions') }}
)

select
    "user.index" * 1000 + "decision.index"   as decision_point_id,
    "user.index"                              as participant_id,
    "decision.index"                          as decision_index,
    "sugg.decision.utime"                     as decision_utc,
    "sugg.decision.utime"
        + to_seconds(cast("sugg.gmtoff" as bigint)) as decision_local,
    cast("sugg.decision.slot" as integer)     as slot,
    coalesce(avail, false)                    as is_available,
    send                                      as is_sent,
    "send.active"                             as is_sent_walking,
    "send.sedentary"                          as is_sent_anti_sedentary,
    case when response like 'snoozed%' then 'snoozed'
         else response end                    as response,
    case when "dec.location.category" in ('home', 'work') then "dec.location.category"
         when "dec.location.category" is null
           or "dec.location.category" = 'unknown' then 'unknown'
         else 'other' end                     as location,
    "dec.weather.condition"                   as weather,
    "dec.temperature"                         as temperature,
    jbsteps30pre                              as steps_30m_before,
    jbsteps30                                 as steps_30m_after
from source
