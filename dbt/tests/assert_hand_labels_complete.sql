-- Every hand-labelled review has exactly one 0/1 label for every theme.
select review_id, count(*) as n_labels, count(distinct theme) as n_themes
from {{ ref('review_hand_labels') }}
group by review_id
having count(*) <> (select count(*) from {{ ref('review_themes') }})
    or count(distinct theme) <> (select count(*) from {{ ref('review_themes') }})
    or bool_or(is_mentioned not in (0, 1))
