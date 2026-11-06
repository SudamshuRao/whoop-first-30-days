-- Each review is tagged with a theme at most once.
select review_id, theme, count(*) as n
from {{ ref('fct_review_themes') }}
group by review_id, theme
having count(*) > 1
