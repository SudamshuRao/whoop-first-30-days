-- Only a member's final gap can still be open at the data end.
select user_id, count(*) as open_lapses
from {{ ref('int_endomondo__lapses') }}
where is_censored
group by user_id
having count(*) > 1
