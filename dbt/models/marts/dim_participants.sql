-- One row per HeartSteps participant, with how much of the trial they contributed.
with participants as (
    select * from {{ ref('stg_heartsteps__participants') }}
),

decision_points as (
    select * from {{ ref('fct_decision_points') }}
)

select
    p.*,
    count(dp.decision_point_id)                                      as n_decision_points,
    count(*) filter (where dp.is_in_primary_analysis)                as n_in_primary_analysis,
    count(*) filter (where dp.is_in_primary_analysis and dp.is_sent) as n_sent_in_primary_analysis,
    max(dp.study_day)                                                as last_study_day
from participants p
left join decision_points dp using (participant_id)
group by all
