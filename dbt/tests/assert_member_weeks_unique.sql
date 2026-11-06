-- One row per member per week.
select user_id, week_number, count(*) as n
from {{ ref('fct_member_weeks') }}
group by all
having count(*) > 1
