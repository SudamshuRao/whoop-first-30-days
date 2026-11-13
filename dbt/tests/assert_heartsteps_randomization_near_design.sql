-- The trial sent a suggestion with probability 0.6 at available decision points.
-- Fails (returns a row) if the observed rate drifts more than 3 points from that.
select avg(is_sent::int) as observed_send_rate
from {{ ref('stg_heartsteps__decision_points') }}
where is_available
having abs(avg(is_sent::int) - 0.6) > 0.03
