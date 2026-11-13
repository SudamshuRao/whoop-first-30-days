-- One row per HeartSteps decision point, ready for the experiment readout.
-- is_in_primary_analysis reproduces the published sample: randomized, not during travel.
with decision_points as (
    select * from {{ ref('int_heartsteps__decision_points') }}
),

participants as (
    select participant_id, age, gender from {{ ref('stg_heartsteps__participants') }}
)

select
    dp.*,
    p.age,
    p.gender,
    dp.is_randomized and not dp.is_during_travel  as is_in_primary_analysis
from decision_points dp
left join participants p using (participant_id)
