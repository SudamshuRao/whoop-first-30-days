-- Decision points with study day/week, a travel flag and the log-step outcomes the readout needs.
with decision_points as (
    select * from {{ ref('stg_heartsteps__decision_points') }}
),

participants as (
    select * from {{ ref('stg_heartsteps__participants') }}
),

first_days as (
    select participant_id, min(cast(decision_local as date)) as first_day
    from decision_points
    group by participant_id
)

select
    dp.*,
    date_diff('day', f.first_day, cast(dp.decision_local as date))                     as study_day,
    floor(date_diff('day', f.first_day, cast(dp.decision_local as date)) / 7)::int + 1 as study_week,
    coalesce(cast(dp.decision_local as date) between p.travel_start and p.travel_end, false)
                                                                                       as is_during_travel,
    dp.is_available                                                                    as is_randomized,
    dp.steps_30m_after is not null                                                     as has_outcome,
    ln(dp.steps_30m_after + 0.5)                                                       as log_steps_after,
    ln(dp.steps_30m_before + 0.5)                                                      as log_steps_before
from decision_points dp
left join first_days f using (participant_id)
left join participants p using (participant_id)
