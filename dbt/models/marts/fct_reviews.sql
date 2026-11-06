-- One row per review, with how many themes it mentions.
with theme_counts as (
    select review_id, count(*) as n_themes
    from {{ ref('fct_review_themes') }}
    group by review_id
)

select
    r.*,
    coalesce(t.n_themes, 0) as n_themes
from {{ ref('stg_reviews__google_play') }} r
left join theme_counts t using (review_id)
